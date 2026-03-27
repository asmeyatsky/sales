"""DAG-based workflow for executing a single outreach step.

Architectural Intent:
- Parallelism-first: sequence and message loading run in parallel (Step 1)
- Sequential: channel dispatch depends on loaded data, result update depends on send
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from searce_scout.shared_kernel.errors import DomainError, OrchestrationError
from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import MessageId, SequenceId

from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)
from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
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


class OutreachExecutionWorkflow:
    """Orchestrates a single step execution through a DAG of dependent steps.

    Steps:
        1. load_sequence + load_message (parallel) - loads sequence and message
        2. send_via_channel (depends on 1) - dispatches to email/linkedin/phone
        3. update_results (depends on 2) - completes step, advances, saves
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

    async def execute(
        self,
        sequence_id: str,
        message_id: str | None = None,
    ) -> OutreachSequence:
        """Run the step execution workflow.

        Args:
            sequence_id: The outreach sequence to execute a step for.
            message_id: Optional explicit message ID; if not provided,
                the message ID from the current step is used.

        Returns:
            The updated OutreachSequence after step execution.
        """
        dag = DAGOrchestrator(
            steps=[
                WorkflowStep(
                    name="load_sequence",
                    execute=self._load_sequence,
                    timeout_seconds=10.0,
                ),
                WorkflowStep(
                    name="load_message",
                    execute=self._load_message,
                    timeout_seconds=10.0,
                    is_critical=False,
                ),
                WorkflowStep(
                    name="send_via_channel",
                    execute=self._send_via_channel,
                    depends_on=("load_sequence", "load_message"),
                    timeout_seconds=30.0,
                ),
                WorkflowStep(
                    name="update_results",
                    execute=self._update_results,
                    depends_on=("send_via_channel",),
                ),
            ]
        )

        context: dict[str, Any] = {
            "sequence_id": sequence_id,
            "message_id": message_id,
        }

        results = await dag.execute(context)
        return results["update_results"]

    async def _load_sequence(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> OutreachSequence:
        """Step 1a: Load the outreach sequence."""
        sequence = await self._sequence_repository.get_by_id(
            SequenceId(context["sequence_id"])
        )
        if sequence is None:
            raise DomainError(f"Sequence not found: {context['sequence_id']}")
        return sequence

    async def _load_message(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> Any:
        """Step 1b: Load the message content for the current step.

        If an explicit message_id is provided in context, use that.
        Otherwise, this returns None and the actual message_id will be
        resolved from the sequence's current step after load_sequence completes.
        Note: since load_sequence and load_message run in parallel and
        load_message is non-critical, a None result is acceptable.
        """
        explicit_id = context.get("message_id")
        if explicit_id:
            return await self._message_repository.get_by_id(MessageId(explicit_id))
        return None

    async def _send_via_channel(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> SendResult:
        """Step 2: Dispatch to the appropriate channel port."""
        from searce_scout.shared_kernel.value_objects import EmailAddress, URL

        sequence: OutreachSequence = completed["load_sequence"]
        current_step = sequence.current_step()
        if current_step is None:
            raise OrchestrationError("No current step to execute")

        # Resolve message: prefer pre-loaded, fall back to loading by step's message_id
        message = completed.get("load_message")
        if message is None and current_step.message_id:
            message = await self._message_repository.get_by_id(
                MessageId(current_step.message_id)
            )

        step_type = current_step.step_type

        if step_type in (StepType.EMAIL_1, StepType.EMAIL_2):
            if message is None:
                return SendResult(success=False, error="No message content for email step")
            return await self._email_sender.send(
                to=EmailAddress("placeholder@example.com"),
                subject=message.subject or "",
                body=message.body,
                from_alias="Searce Scout",
            )

        elif step_type == StepType.LINKEDIN_REQUEST:
            if message is None:
                return SendResult(
                    success=False, error="No message content for LinkedIn request"
                )
            return await self._linkedin_messenger.send_connection_request(
                profile_url=URL("https://linkedin.com/in/placeholder"),
                note=message.body[:300],
            )

        elif step_type == StepType.LINKEDIN_MESSAGE:
            if message is None:
                return SendResult(
                    success=False, error="No message content for LinkedIn message"
                )
            return await self._linkedin_messenger.send_message(
                profile_url=URL("https://linkedin.com/in/placeholder"),
                body=message.body,
            )

        elif step_type == StepType.PHONE_TASK:
            notes = message.body if message else "Follow up call"
            task_id = await self._task_creator.create_phone_task(
                stakeholder_id=sequence.stakeholder_id,
                notes=notes,
                due_date=datetime.now(),
            )
            return SendResult(success=True, message_id=task_id)

        return SendResult(success=False, error=f"Unknown step type: {step_type.value}")

    async def _update_results(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> OutreachSequence:
        """Step 3: Complete the step with the send result, advance, and save."""
        sequence: OutreachSequence = completed["load_sequence"]
        send_result: SendResult = completed["send_via_channel"]

        step_result = StepResult(
            success=send_result.success,
            channel_message_id=send_result.message_id,
            error=send_result.error,
        )

        sequence = sequence.complete_current_step(step_result)
        sequence = sequence.advance_to_next_step()

        await self._sequence_repository.save(sequence)
        if sequence.domain_events:
            await self._event_bus.publish(sequence.domain_events)

        return sequence
