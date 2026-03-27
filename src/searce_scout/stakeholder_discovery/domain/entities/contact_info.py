"""ContactInfo entity representing validated contact details for a stakeholder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from searce_scout.shared_kernel.value_objects import EmailAddress, PhoneNumber

from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    ValidationStatus,
)


@dataclass(frozen=True)
class ContactInfo:
    email: EmailAddress | None
    phone: PhoneNumber | None
    email_status: ValidationStatus
    phone_status: ValidationStatus
    source: str
    validated_at: datetime
