"""
BidirectionalSyncWorkflow — DAG-orchestrated two-way CRM synchronisation.

Parallelises pull and local-gather, then sequences conflict detection,
auto-resolution, parallel push/apply, and logging.

Step graph:
  pull_remote_changes ──┐
  gather_local_changes ─┤── detect_conflicts ── resolve_auto ─┬── push_to_crm
                        │                                      ├── apply_remote
                        │                                      └── log_results
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.entities.field_mapping import FieldMapping
from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)
from searce_scout.crm_sync.domain.services.conflict_resolution import (
    ConflictResolutionService,
    ResolutionStrategy,
)
from searce_scout.crm_sync.domain.services.field_mapper import FieldMapperService
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType


class BidirectionalSyncWorkflow:
    """Orchestrates a full bidirectional sync cycle via a DAG of async steps."""

    def __init__(
        self,
        crm_client: CRMClientPort,
        sync_log_repository: SyncLogRepositoryPort,
        conflict_resolution_service: ConflictResolutionService,
        field_mapper_service: FieldMapperService,
        field_mappings: tuple[FieldMapping, ...],
        event_bus: EventBusPort,
        default_strategy: ResolutionStrategy = ResolutionStrategy.LAST_WRITE_WINS,
    ) -> None:
        self._crm_client = crm_client
        self._sync_log_repository = sync_log_repository
        self._conflict_resolution_service = conflict_resolution_service
        self._field_mapper_service = field_mapper_service
        self._field_mappings = field_mappings
        self._event_bus = event_bus
        self._default_strategy = default_strategy

    async def run(
        self,
        record_type: str,
        since: str,
    ) -> dict[str, int]:
        """Execute the full bidirectional sync and return result counts."""

        rt = RecordType(record_type)
        since_dt = datetime.fromisoformat(since)

        # ------------------------------------------------------------------
        # Step functions
        # ------------------------------------------------------------------

        async def pull_remote_changes(
            context: dict[str, Any], _completed: dict[str, Any]
        ) -> Any:
            return await self._crm_client.get_changes_since(
                record_type=rt,
                since=since_dt,
            )

        async def gather_local_changes(
            context: dict[str, Any], _completed: dict[str, Any]
        ) -> Any:
            return await self._sync_log_repository.find_pending()

        async def detect_conflicts(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            remote_records: tuple[dict[str, str], ...] = completed["pull_remote_changes"]
            local_records: tuple[CRMRecord, ...] = completed["gather_local_changes"]

            # Build a lookup of remote changes by external_id
            remote_by_id: dict[str, dict[str, str]] = {}
            for remote in remote_records:
                ext_id = remote.get("Id") or remote.get("id", "")
                if ext_id:
                    remote_by_id[ext_id] = remote

            conflicts: list[tuple[CRMRecord, dict[str, str]]] = []
            local_only: list[CRMRecord] = []
            remote_only: list[dict[str, str]] = []

            matched_remote_ids: set[str] = set()
            for local_rec in local_records:
                if local_rec.external_id and local_rec.external_id in remote_by_id:
                    # Both sides changed — potential conflict
                    conflicts.append((local_rec, remote_by_id[local_rec.external_id]))
                    matched_remote_ids.add(local_rec.external_id)
                else:
                    local_only.append(local_rec)

            for ext_id, remote_data in remote_by_id.items():
                if ext_id not in matched_remote_ids:
                    remote_only.append(remote_data)

            return {
                "conflicts": conflicts,
                "local_only": local_only,
                "remote_only": remote_only,
            }

        async def resolve_auto_conflicts(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            detection = completed["detect_conflicts"]
            conflicts: list[tuple[CRMRecord, dict[str, str]]] = detection["conflicts"]

            auto_resolved: list[CRMRecord] = []
            flagged: list[CRMRecord] = []

            for local_rec, remote_fields in conflicts:
                if self._default_strategy == ResolutionStrategy.MANUAL_FLAG:
                    # Flag for manual review
                    flagged_rec = local_rec.mark_conflict("bidirectional_conflict")
                    flagged.append(flagged_rec)
                else:
                    resolved_fields = self._conflict_resolution_service.resolve(
                        local_fields=local_rec.fields,
                        remote_fields=remote_fields,
                        strategy=self._default_strategy,
                    )
                    resolved_rec = local_rec.update_fields(resolved_fields)
                    auto_resolved.append(resolved_rec)

            return {
                "auto_resolved": auto_resolved,
                "flagged": flagged,
                "local_only": detection["local_only"],
                "remote_only": detection["remote_only"],
            }

        async def push_to_crm(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            resolution = completed["resolve_auto_conflicts"]
            to_push: list[CRMRecord] = (
                resolution["auto_resolved"] + resolution["local_only"]
            )

            now = datetime.now(UTC)
            pushed: list[CRMRecord] = []

            for record in to_push:
                crm_fields = self._field_mapper_service.map_to_crm(
                    fields=record.fields,
                    mappings=self._field_mappings,
                )
                if record.external_id:
                    await self._crm_client.update_record(
                        external_id=record.external_id,
                        fields=crm_fields,
                    )
                    synced = record.mark_synced(
                        external_id=record.external_id, synced_at=now
                    )
                else:
                    external_id = await self._crm_client.create_record(
                        record_type=rt,
                        fields=crm_fields,
                    )
                    synced = record.mark_synced(
                        external_id=external_id, synced_at=now
                    )
                pushed.append(synced)

            return pushed

        async def apply_remote(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            resolution = completed["resolve_auto_conflicts"]
            remote_only: list[dict[str, str]] = resolution["remote_only"]

            now = datetime.now(UTC)
            applied: list[CRMRecord] = []

            for crm_data in remote_only:
                local_fields = self._field_mapper_service.map_from_crm(
                    crm_data=crm_data,
                    mappings=self._field_mappings,
                )
                ext_id = crm_data.get("Id") or crm_data.get("id", "")

                record = CRMRecord(
                    record_id=CRMRecordId(str(uuid4())),
                    provider=CRMProvider(context["provider"]),
                    record_type=rt,
                    local_id=ext_id,
                    fields=local_fields,
                )
                record = record.mark_synced(external_id=ext_id, synced_at=now)
                applied.append(record)

            return applied

        async def log_results(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            pushed: list[CRMRecord] = completed["push_to_crm"]
            applied: list[CRMRecord] = completed["apply_remote"]
            resolution = completed["resolve_auto_conflicts"]
            flagged: list[CRMRecord] = resolution["flagged"]

            all_events: list = []

            for record in pushed + applied + flagged:
                await self._sync_log_repository.save(record)
                all_events.extend(record.domain_events)

            if all_events:
                await self._event_bus.publish(tuple(all_events))

            return {
                "pushed": len(pushed),
                "pulled": len(applied),
                "conflicts_auto_resolved": len(resolution["auto_resolved"]),
                "conflicts_flagged": len(flagged),
            }

        # ------------------------------------------------------------------
        # Build the DAG and execute
        # ------------------------------------------------------------------

        steps = [
            WorkflowStep(name="pull_remote_changes", execute=pull_remote_changes),
            WorkflowStep(name="gather_local_changes", execute=gather_local_changes),
            WorkflowStep(
                name="detect_conflicts",
                execute=detect_conflicts,
                depends_on=("pull_remote_changes", "gather_local_changes"),
            ),
            WorkflowStep(
                name="resolve_auto_conflicts",
                execute=resolve_auto_conflicts,
                depends_on=("detect_conflicts",),
            ),
            WorkflowStep(
                name="push_to_crm",
                execute=push_to_crm,
                depends_on=("resolve_auto_conflicts",),
            ),
            WorkflowStep(
                name="apply_remote",
                execute=apply_remote,
                depends_on=("resolve_auto_conflicts",),
            ),
            WorkflowStep(
                name="log_results",
                execute=log_results,
                depends_on=("push_to_crm", "apply_remote"),
            ),
        ]

        orchestrator = DAGOrchestrator(steps)

        # We need provider in context for apply_remote step
        # Derive it from the field_mappings or default
        provider_value = (
            self._field_mappings[0].provider.value
            if self._field_mappings
            else "SALESFORCE"
        )

        ctx: dict[str, Any] = {
            "record_type": record_type,
            "since": since,
            "provider": provider_value,
        }

        results = await orchestrator.execute(ctx)
        return results["log_results"]
