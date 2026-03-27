"""Port for creating tasks in external systems (e.g., CRM)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from searce_scout.shared_kernel.types import StakeholderId


class TaskCreatorPort(Protocol):
    """Driven port for creating phone call tasks.

    Infrastructure adapters implement this to integrate with CRM or
    task management systems.
    """

    async def create_phone_task(
        self,
        stakeholder_id: StakeholderId,
        notes: str,
        due_date: datetime,
    ) -> str:
        """Create a phone task for a sales representative.

        Args:
            stakeholder_id: The stakeholder to call.
            notes: Talking points or context for the call.
            due_date: When the call should be made.

        Returns:
            The identifier of the created task.
        """
        ...
