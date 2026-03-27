"""Command and handler for starting a new outreach sequence."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.outreach.application.dtos.outreach_dtos import OutreachSequenceDTO
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.services.sequence_engine import (
    SequenceEngineService,
)
from searce_scout.outreach.domain.value_objects.step_type import StepType


@dataclass(frozen=True)
class StartSequenceCommand:
    account_id: str
    stakeholder_id: str
    message_ids: dict[str, str]


class StartSequenceHandler:
    """Builds and starts an outreach sequence via the domain engine."""

    def __init__(
        self,
        sequence_engine: SequenceEngineService,
        sequence_repository: SequenceRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._sequence_engine = sequence_engine
        self._sequence_repository = sequence_repository
        self._event_bus = event_bus

    async def execute(self, cmd: StartSequenceCommand) -> OutreachSequenceDTO:
        """Build, start, persist, and publish an outreach sequence.

        Args:
            cmd: The start command containing account/stakeholder IDs
                and a mapping from step type names to message IDs.

        Returns:
            An OutreachSequenceDTO representing the newly started sequence.
        """
        # Convert string step type names to StepType enum -> MessageId mapping
        typed_message_ids: dict[StepType, MessageId] = {
            StepType(step_type_name): MessageId(msg_id)
            for step_type_name, msg_id in cmd.message_ids.items()
        }

        # Build the default sequence via the domain engine
        sequence = self._sequence_engine.build_default_sequence(
            account_id=AccountId(cmd.account_id),
            stakeholder_id=StakeholderId(cmd.stakeholder_id),
            message_ids=typed_message_ids,
        )

        # Start the sequence (DRAFT -> ACTIVE)
        sequence = sequence.start()

        # Persist and publish domain events
        await self._sequence_repository.save(sequence)
        if sequence.domain_events:
            await self._event_bus.publish(sequence.domain_events)

        return OutreachSequenceDTO.from_domain(sequence)
