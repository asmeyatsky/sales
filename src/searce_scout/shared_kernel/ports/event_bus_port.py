"""Event bus port for cross-context domain event communication."""

from collections.abc import Callable
from typing import Protocol

from searce_scout.shared_kernel.domain_event import DomainEvent


class EventBusPort(Protocol):
    async def publish(self, events: tuple[DomainEvent, ...]) -> None: ...

    async def subscribe(
        self, event_type: type[DomainEvent], handler: Callable
    ) -> None: ...
