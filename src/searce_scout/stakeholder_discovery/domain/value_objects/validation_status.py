"""Validation status, seniority, and department enumerations."""

from __future__ import annotations

from enum import Enum


class ValidationStatus(Enum):
    UNVALIDATED = "UNVALIDATED"
    VALID = "VALID"
    INVALID = "INVALID"
    CATCH_ALL = "CATCH_ALL"
    UNKNOWN = "UNKNOWN"


class Seniority(Enum):
    C_SUITE = "C_SUITE"
    VP = "VP"
    DIRECTOR = "DIRECTOR"
    HEAD = "HEAD"
    MANAGER = "MANAGER"
    IC = "IC"


class Department(Enum):
    ENGINEERING = "ENGINEERING"
    IT_INFRASTRUCTURE = "IT_INFRASTRUCTURE"
    DATA = "DATA"
    INNOVATION = "INNOVATION"
    HR = "HR"
    OPERATIONS = "OPERATIONS"
    EXECUTIVE = "EXECUTIVE"
