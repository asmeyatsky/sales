"""Workflow for monitoring inboxes, classifying replies, and applying actions.

Architectural Intent:
- Step 1: Check inboxes for new replies
- Step 2: Fan-out classification of each reply via asyncio.gather
- Step 3: Apply stop/pause/continue actions to matching sequences
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
from typing import Any

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import SequenceId

from searce_scout.outreach.domain.events.outreach_events import ReplyReceivedEvent
from searce_scout.outreach.domain.ports.ai_classifier_port import AIClassifierPort
from searce_scout.outreach.domain.ports.inbox_reader_port import InboxReaderPort, RawReply
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.services.reply_classification_service import (
    ReplyClassificationService,
)
from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)


class InboxMonitoringWorkflow:
    """Orchestrates inbox monitoring: check replies, classify, and act.

    Steps:
        1. check_inboxes - polls the inbox reader for new replies
        2. classify_replies (depends on 1) - fan-out classification via asyncio.gather
        3. apply_actions (depends on 2) - applies stop/pause/continue to sequences
    """

    def __init__(
        self,
        inbox_reader: InboxReaderPort,
        ai_classifier: AIClassifierPort,
        reply_classification_service: ReplyClassificationService,
        sequence_repository: SequenceRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._inbox_reader = inbox_reader
        self._ai_classifier = ai_classifier
        self._reply_classification_service = reply_classification_service
        self._sequence_repository = sequence_repository
        self._event_bus = event_bus

    async def execute(self, since: datetime) -> dict[str, Any]:
        """Run the full inbox monitoring workflow.

        Args:
            since: Only process replies received after this timestamp.

        Returns:
            A summary dict with keys:
                - replies_found: number of raw replies fetched
                - classified: list of dicts with reply_id, classification, confidence
                - actions_taken: list of dicts with sequence_id and action performed
        """
        dag = DAGOrchestrator(
            steps=[
                WorkflowStep(
                    name="check_inboxes",
                    execute=self._check_inboxes,
                    timeout_seconds=30.0,
                ),
                WorkflowStep(
                    name="classify_replies",
                    execute=self._classify_replies,
                    depends_on=("check_inboxes",),
                    timeout_seconds=60.0,
                ),
                WorkflowStep(
                    name="apply_actions",
                    execute=self._apply_actions,
                    depends_on=("classify_replies",),
                ),
            ]
        )

        context: dict[str, Any] = {"since": since}
        results = await dag.execute(context)
        return results["apply_actions"]

    async def _check_inboxes(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> tuple[RawReply, ...]:
        """Step 1: Check inboxes for new replies."""
        since: datetime = context["since"]
        return await self._inbox_reader.check_replies(since)

    async def _classify_replies(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Step 2: Fan-out classification of each reply via asyncio.gather."""
        raw_replies: tuple[RawReply, ...] = completed["check_inboxes"]

        if not raw_replies:
            return []

        async def classify_single(reply: RawReply) -> dict[str, Any]:
            classification, confidence = await self._ai_classifier.classify_reply(
                reply.content
            )
            return {
                "reply": reply,
                "classification": classification,
                "confidence": confidence,
            }

        results = await asyncio.gather(
            *(classify_single(reply) for reply in raw_replies),
            return_exceptions=True,
        )

        classified = []
        for result in results:
            if isinstance(result, Exception):
                continue
            classified.append(result)

        return classified

    async def _apply_actions(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 3: Apply stop/pause/continue actions based on classifications."""
        classified_replies: list[dict[str, Any]] = completed["classify_replies"]

        summary: dict[str, Any] = {
            "replies_found": len(completed["check_inboxes"]),
            "classified": [],
            "actions_taken": [],
        }

        for item in classified_replies:
            reply: RawReply = item["reply"]
            classification: ReplyClassification = item["classification"]
            confidence: float = item["confidence"]

            summary["classified"].append({
                "reply_id": reply.reply_id,
                "classification": classification.value,
                "confidence": confidence,
            })

            # Look up the matching sequence by thread_id
            # The thread_id from the reply maps to a sequence_id
            sequence = await self._sequence_repository.get_by_id(
                SequenceId(reply.thread_id)
            )
            if sequence is None:
                continue

            # Record the reply event
            reply_event = ReplyReceivedEvent(
                aggregate_id=sequence.sequence_id,
                classification=classification.value,
                confidence=confidence,
            )

            action = "continue"

            if self._reply_classification_service.should_stop_sequence(classification):
                reason = (
                    f"Reply classified as {classification.value} "
                    f"(confidence: {confidence:.2f})"
                )
                sequence = sequence.stop(reason)
                action = "stopped"

            elif self._reply_classification_service.should_pause_sequence(
                classification
            ):
                sequence = sequence.pause()
                action = "paused"

            # Append the reply event
            sequence = replace(
                sequence,
                domain_events=sequence.domain_events + (reply_event,),
            )

            await self._sequence_repository.save(sequence)
            if sequence.domain_events:
                await self._event_bus.publish(sequence.domain_events)

            summary["actions_taken"].append({
                "sequence_id": sequence.sequence_id,
                "action": action,
                "classification": classification.value,
            })

        return summary
