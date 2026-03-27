"""
Scout-wide configuration settings.

Uses pydantic-settings to load from environment variables with a SCOUT_ prefix.
All adapter credentials and operational parameters are centralised here so that
the Container can wire dependencies without leaking config across layers.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class ScoutSettings(BaseSettings):
    """Central settings for the Searce Scout application."""

    # -- Database ---------------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./scout.db"

    # -- Vertex AI / GCP -------------------------------------------------------
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    vertex_ai_model: str = "gemini-1.5-pro"

    # -- LinkedIn ---------------------------------------------------------------
    linkedin_api_key: str = ""
    linkedin_api_secret: str = ""

    # -- Apollo / ZoomInfo ------------------------------------------------------
    apollo_api_key: str = ""
    zoominfo_api_key: str = ""

    # -- Gmail ------------------------------------------------------------------
    gmail_credentials_path: str = ""
    sender_email: str = ""
    sender_name: str = "Searce Scout"

    # -- CRM --------------------------------------------------------------------
    crm_provider: str = "salesforce"
    salesforce_client_id: str = ""
    salesforce_client_secret: str = ""
    salesforce_instance_url: str = ""
    hubspot_api_key: str = ""

    # -- Google Slides ----------------------------------------------------------
    slides_template_id: str = ""
    google_credentials_path: str = ""

    # -- Messaging / Tone -------------------------------------------------------
    default_tone: str = "PROFESSIONAL_CONSULTANT"
    step_delays_hours: list[int] = [0, 48, 72, 96, 120]

    # -- Business-hours scheduling ----------------------------------------------
    business_hours_start: int = 9
    business_hours_end: int = 17

    # -- Concurrency limits -----------------------------------------------------
    max_concurrent_research: int = 3
    max_concurrent_outreach: int = 5

    # -- API key for the presentation layer -------------------------------------
    api_key: str = ""

    # -- CORS allowed origins ---------------------------------------------------
    allowed_origins: list[str] = []

    model_config = {"env_prefix": "SCOUT_"}
