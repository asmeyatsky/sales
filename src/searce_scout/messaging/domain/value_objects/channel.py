"""Channel value object for message delivery."""

from enum import Enum


class Channel(Enum):
    """The delivery channel for an outreach message."""

    EMAIL = "email"
    LINKEDIN_REQUEST = "linkedin_request"
    LINKEDIN_MESSAGE = "linkedin_message"
    PHONE_SCRIPT = "phone_script"
