"""
Shared Value Objects

Cross-cutting value objects used by multiple bounded contexts.
All are immutable (frozen dataclasses) with validation on construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from searce_scout.shared_kernel.errors import ValidationError

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")
_URL_RE = re.compile(r"^https?://\S+$")


@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        object.__setattr__(self, "value", normalized)
        if not _EMAIL_RE.match(normalized):
            raise ValidationError(f"Invalid email address: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PhoneNumber:
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        object.__setattr__(self, "value", cleaned)
        if not _E164_RE.match(cleaned):
            raise ValidationError(f"Invalid E.164 phone number: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class URL:
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not _URL_RE.match(stripped):
            raise ValidationError(f"Invalid URL: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CompanyName:
    canonical: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.canonical.strip():
            raise ValidationError("Company name cannot be empty")

    def matches(self, name: str) -> bool:
        lower = name.lower()
        if self.canonical.lower() == lower:
            return True
        return any(a.lower() == lower for a in self.aliases)

    def __str__(self) -> str:
        return self.canonical


@dataclass(frozen=True)
class PersonName:
    first_name: str
    last_name: str

    def __post_init__(self) -> None:
        if not self.first_name.strip() or not self.last_name.strip():
            raise ValidationError("First and last name are required")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return self.full_name
