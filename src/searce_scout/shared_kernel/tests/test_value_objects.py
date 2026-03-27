"""Tests for shared kernel value objects."""

from __future__ import annotations

import pytest

from searce_scout.shared_kernel.errors import ValidationError
from searce_scout.shared_kernel.value_objects import (
    CompanyName,
    EmailAddress,
    PersonName,
    PhoneNumber,
    URL,
)


# ---------------------------------------------------------------------------
# EmailAddress
# ---------------------------------------------------------------------------


def test_email_valid():
    """A well-formed email address is accepted."""
    email = EmailAddress("user@example.com")
    assert email.value == "user@example.com"


def test_email_invalid_raises():
    """A string without a valid email format raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid email"):
        EmailAddress("notanemail")


def test_email_normalized_lowercase():
    """Mixed-case email addresses are normalized to lowercase."""
    email = EmailAddress("User@Example.COM")
    assert email.value == "user@example.com"


# ---------------------------------------------------------------------------
# PhoneNumber
# ---------------------------------------------------------------------------


def test_phone_valid_e164():
    """A valid E.164 phone number is accepted."""
    phone = PhoneNumber("+14155551234")
    assert phone.value == "+14155551234"


def test_phone_invalid_raises():
    """A non-E.164 number raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid E.164"):
        PhoneNumber("555-1234")


# ---------------------------------------------------------------------------
# URL
# ---------------------------------------------------------------------------


def test_url_valid():
    """A well-formed https URL is accepted."""
    url = URL("https://example.com")
    assert url.value == "https://example.com"


def test_url_invalid_raises():
    """A string that is not a valid URL raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid URL"):
        URL("not-a-url")


# ---------------------------------------------------------------------------
# CompanyName
# ---------------------------------------------------------------------------


def test_company_name_empty_raises():
    """An empty or whitespace-only company name raises ValidationError."""
    with pytest.raises(ValidationError, match="cannot be empty"):
        CompanyName(canonical="")


def test_company_name_matches():
    """Canonical name and aliases all match case-insensitively."""
    name = CompanyName(canonical="Acme Corp", aliases=("ACME", "Acme"))

    assert name.matches("Acme Corp") is True
    assert name.matches("acme corp") is True
    assert name.matches("ACME") is True
    assert name.matches("acme") is True
    assert name.matches("Other Corp") is False


# ---------------------------------------------------------------------------
# PersonName
# ---------------------------------------------------------------------------


def test_person_name_empty_raises():
    """Empty first or last name raises ValidationError."""
    with pytest.raises(ValidationError, match="First and last name are required"):
        PersonName(first_name="", last_name="Doe")

    with pytest.raises(ValidationError, match="First and last name are required"):
        PersonName(first_name="Jane", last_name="")


def test_person_name_full_name():
    """full_name property returns 'First Last'."""
    name = PersonName(first_name="Jane", last_name="Doe")
    assert name.full_name == "Jane Doe"
    assert str(name) == "Jane Doe"
