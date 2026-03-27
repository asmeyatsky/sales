"""Command and handler for executing the next step in an outreach sequence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import MessageId, SequenceId

from searce_scout.outreach.application.dtos.outreach_dtos import OutreachSequenceDTO
from searce_scout.outreach.domain.ports.email_sender_port import (
    EmailSenderPort,
    SendResult,
)
from searce_scout.outreach.domain.ports.linkedin_messenger_port import (
    LinkedInMessengerPort,
)
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.ports.task_creator_port import TaskCreatorPort
from searce_scout.outreach.domain.value_objects.step_type import StepResult, StepType
from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)


@dataclass(frozen=True)
class ExecuteNextStepCommand:
    sequence_id: str


class ExecuteNextStepHandler:
    """Executes the current step of an outreach sequence by dispatching
    to the appropriate channel port.
    """

    def __init__(
        self,
        sequence_repository: SequenceRepositoryPort,
        message_repository: MessageRepositoryPort,
        email_sender: EmailSenderPort,
        linkedin_messenger: LinkedInMessengerPort,
        task_creator: TaskCreatorPort,
        event_bus: EventBusPort,
    ) -> None:
        self._sequence_repository = sequence_repository
        self._message_repository = message_repository
        self._email_sender = email_sender
        self._linkedin_messenger = linkedin_messenger
        self._task_creator = task_creator
        self._event_bus = event_bus

    async def execute(self, cmd: ExecuteNextStepCommand) -> OutreachSequenceDTO:
        """Load the sequence, execute its current step, and advance.

        Args:
            cmd: The command containing the sequence ID.

        Returns:
            An OutreachSequenceDTO reflecting the updated state.

        Raises:
            DomainError: If the sequence or current step is not found,
                or if the message content cannot be loaded.
        """
        sequence = await self._sequence_repository.get_by_id(
            SequenceId(cmd.sequence_id)
        )
        if sequence is None:
            raise DomainError(f"Sequence not found: {cmd.sequence_id}")

        current_step = sequence.current_step()
        if current_step is None:
            raise DomainError(
                f"No current step available for sequence: {cmd.sequence_id}"
            )

        # Load the message content for this step
        message = None
        if current_step.message_id:
            message = await self._message_repository.get_by_id(
                MessageId(current_step.message_id)
            )

        # Dispatch to the correct channel port
        result = await self._dispatch_to_channel(
            step_type=current_step.step_type,
            message=message,
            sequence=sequence,
        )

        # Complete the current step with the result
        step_result = StepResult(
            success=result.success,
            channel_message_id=result.message_id,
            error=result.error,
        )
        sequence = sequence.complete_current_step(step_result)

        # Advance to the next step
        sequence = sequence.advance_to_next_step()

        # Persist and publish
        await self._sequence_repository.save(sequence)
        if sequence.domain_events:
            await self._event_bus.publish(sequence.domain_events)

        return OutreachSequenceDTO.from_domain(sequence)

    async def _dispatch_to_channel(
        self,
        step_type: StepType,
        message: object | None,
        sequence: object,
    ) -> SendResult:
        """Route execution to the appropriate channel port.

        Args:
            step_type: The type of step to execute.
            message: The loaded Message entity (may be None for phone tasks).
            sequence: The OutreachSequence (for stakeholder context).

        Returns:
            A SendResult from the channel adapter.
        """
        from searce_scout.shared_kernel.value_objects import EmailAddress, URL

        if step_type in (StepType.EMAIL_1, StepType.EMAIL_2):
            if message is None:
                return SendResult(success=False, error="No message content for email step")
            return await self._email_sender.send(
                to=EmailAddress("placeholder@example.com"),
                subject=message.subject or "",  # type: ignore[union-attr]
                body=message.body,  # type: ignore[union-attr]
                from_alias="Searce Scout",
            )

        elif step_type == StepType.LINKEDIN_REQUEST:
            if message is None:
                return SendResult(success=False, error="No message content for LinkedIn request")
            return await self._linkedin_messenger.send_connection_request(
                profile_url=URL("https://linkedin.com/in/placeholder"),
                note=message.body[:300],  # type: ignore[union-attr]
            )

        elif step_type == StepType.LINKEDIN_MESSAGE:
            if message is None:
                return SendResult(success=False, error="No message content for LinkedIn message")
            return await self._linkedin_messenger.send_message(
                profile_url=URL("https://linkedin.com/in/placeholder"),
                body=message.body,  # type: ignore[union-attr]
            )

        elif step_type == StepType.PHONE_TASK:
            notes = message.body if message else "Follow up call"  # type: ignore[union-attr]
            task_id = await self._task_creator.create_phone_task(
                stakeholder_id=sequence.stakeholder_id,  # type: ignore[union-attr]
                notes=notes,
                due_date=datetime.now(),
            )
            return SendResult(success=True, message_id=task_id)

        return SendResult(success=False, error=f"Unknown step type: {step_type.value}")
