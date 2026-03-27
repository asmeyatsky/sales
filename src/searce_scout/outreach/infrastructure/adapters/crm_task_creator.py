"""Infrastructure adapter for creating phone tasks in a CRM system.

Implements TaskCreatorPort by delegating to a :class:`CRMClientPort`
instance (from the crm_sync bounded context).  This adapter translates
the outreach domain's phone-task concept into a generic CRM activity
record.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from searce_scout.shared_kernel.types import StakeholderId
from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.outreach.domain.ports.task_creator_port import TaskCreatorPort

logger = logging.getLogger(__name__)


class CRMTaskCreator:
    """CRM task adapter implementing :class:`TaskCreatorPort`.

    Delegates to an existing :class:`CRMClientPort` implementation (e.g., a
    Salesforce or HubSpot adapter from the ``crm_sync`` context) to persist
    phone call tasks.

    Parameters
    ----------
    crm_client:
        An implementation of the CRMClientPort protocol that handles the
        actual CRM communication.
    default_owner_id:
        Fallback CRM owner / user ID to assign the task to when no
        specific owner is determined.
    """

    def __init__(
        self,
        crm_client: CRMClientPort,
        *,
        default_owner_id: str = "",
    ) -> None:
        self._crm_client = crm_client
        self._default_owner_id = default_owner_id

    # -- TaskCreatorPort interface ------------------------------------------

    async def create_phone_task(
        self,
        stakeholder_id: StakeholderId,
        notes: str,
        due_date: datetime,
    ) -> str:
        """Create a CRM phone-call task for the given stakeholder.

        Maps the domain request to a CRM ``ACTIVITY`` record with
        appropriate fields and returns the external task identifier
        assigned by the CRM.
        """
        fields: dict[str, str] = {
            "subject": f"Phone call - stakeholder {stakeholder_id}",
            "type": "phone_call",
            "stakeholder_id": str(stakeholder_id),
            "notes": notes,
            "due_date": due_date.isoformat(),
            "status": "open",
        }

        if self._default_owner_id:
            fields["owner_id"] = self._default_owner_id

        try:
            task_id = await self._crm_client.create_record(
                record_type=RecordType.ACTIVITY,
                fields=fields,
            )
            logger.info(
                "CRM phone task created. task_id=%s, stakeholder=%s, due=%s",
                task_id,
                stakeholder_id,
                due_date.isoformat(),
            )
            return task_id

        except Exception as exc:
            logger.error(
                "Failed to create CRM phone task for stakeholder %s: %s",
                stakeholder_id,
                exc,
            )
            raise


# Structural compatibility check with the port Protocol.
_check: type[TaskCreatorPort] = CRMTaskCreator  # type: ignore[assignment]
