"""
Pydantic models for API request and response payloads.

These schemas define the public contract for the Searce Scout REST API.
They are intentionally decoupled from the internal DTOs used by the
application layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class PaginationParams(BaseModel):
    offset: int = 0
    limit: int = 50


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Account Research
# ---------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "company_name": "Acme Corp",
                    "website": "https://acme.com",
                    "ticker": "ACME",
                }
            ]
        }
    )

    company_name: str = Field(..., description="Name of the target company")
    website: str | None = Field(default=None, description="Company website URL")
    ticker: str | None = Field(default=None, description="Stock ticker symbol")


class ResearchResponse(BaseModel):
    account_id: str
    company_name: str
    migration_score: float
    signal_count: int
    stakeholders_found: int


# ---------------------------------------------------------------------------
# Outreach
# ---------------------------------------------------------------------------


class OutreachRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "account_id": "acc_12345",
                    "tone": "PROFESSIONAL_CONSULTANT",
                }
            ]
        }
    )

    account_id: str = Field(..., description="Account to start outreach for")
    tone: str = Field(
        default="PROFESSIONAL_CONSULTANT",
        description="Message tone: PROFESSIONAL_CONSULTANT or WITTY_TECH_PARTNER",
    )


# ---------------------------------------------------------------------------
# Presentations
# ---------------------------------------------------------------------------


class DeckRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "account_id": "acc_12345",
                    "offering": "Cloud Migration",
                }
            ]
        }
    )

    account_id: str = Field(..., description="Account to generate a deck for")
    offering: str | None = Field(
        default=None, description="Searce offering to focus on"
    )


# ---------------------------------------------------------------------------
# Sequence Status
# ---------------------------------------------------------------------------


class SequenceStatusResponse(BaseModel):
    sequence_id: str
    account_id: str
    stakeholder_id: str
    status: str
    current_step_index: int
    total_steps: int
    started_at: datetime | None
    stopped_at: datetime | None
    stop_reason: str | None


# ---------------------------------------------------------------------------
# Message Preview
# ---------------------------------------------------------------------------


class MessagePreviewRequest(BaseModel):
    account_id: str
    stakeholder_id: str
    channel: str = Field(default="EMAIL", description="EMAIL, LINKEDIN_REQUEST, etc.")
    tone: str = Field(default="PROFESSIONAL_CONSULTANT")


class MessagePreviewResponse(BaseModel):
    message_id: str
    channel: str
    tone: str
    subject: str | None
    body: str
    call_to_action: str
    quality_score: float | None


# ---------------------------------------------------------------------------
# Message Tone Adjustment
# ---------------------------------------------------------------------------


class AdjustToneRequest(BaseModel):
    new_tone: str = Field(..., description="Target tone for the message")


# ---------------------------------------------------------------------------
# Stakeholder Discovery
# ---------------------------------------------------------------------------


class DiscoverStakeholdersRequest(BaseModel):
    account_id: str
    company_name: str


# ---------------------------------------------------------------------------
# Stakeholder Validation
# ---------------------------------------------------------------------------


class ValidateContactRequest(BaseModel):
    stakeholder_id: str


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------


class CRMPushRequest(BaseModel):
    local_id: str
    record_type: str
    provider: str = "salesforce"
    fields: dict[str, str] = Field(default_factory=dict)


class CRMPullRequest(BaseModel):
    provider: str = "salesforce"
    record_type: str = "LEAD"
    since: str = Field(..., description="ISO datetime string")


class CRMResolveConflictRequest(BaseModel):
    strategy: str = Field(
        ..., description="Resolution strategy: LOCAL_WINS, REMOTE_WINS, MERGE"
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
