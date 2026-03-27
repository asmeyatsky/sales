"""Base error types for domain and validation errors."""


class DomainError(Exception):
    """Raised when a domain invariant is violated."""


class ValidationError(DomainError):
    """Raised when input validation fails at the domain boundary."""


class OrchestrationError(Exception):
    """Raised when a workflow orchestration step fails."""
