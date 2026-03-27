"""
DAG-based Workflow Orchestrator

Architectural Intent:
- Parallelism-first design per skill2026 Principle 6
- Executes workflow steps respecting dependency order
- Independent steps run concurrently via asyncio.gather
- Supports timeout per step and error propagation
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from searce_scout.shared_kernel.errors import OrchestrationError


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    execute: Callable[..., Coroutine[Any, Any, Any]]
    depends_on: tuple[str, ...] = ()
    timeout_seconds: float | None = None
    is_critical: bool = True


class DAGOrchestrator:
    """Executes workflow steps respecting dependency order, parallelizing independent steps."""

    def __init__(self, steps: list[WorkflowStep]) -> None:
        self.steps = {s.name: s for s in steps}
        self._validate_no_cycles()

    def _validate_no_cycles(self) -> None:
        visited: set[str] = set()
        in_stack: set[str] = set()

        def _dfs(name: str) -> None:
            if name in in_stack:
                raise OrchestrationError(f"Circular dependency detected at step: {name}")
            if name in visited:
                return
            in_stack.add(name)
            for dep in self.steps[name].depends_on:
                if dep not in self.steps:
                    raise OrchestrationError(f"Step '{name}' depends on unknown step '{dep}'")
                _dfs(dep)
            in_stack.discard(name)
            visited.add(name)

        for step_name in self.steps:
            _dfs(step_name)

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        completed: dict[str, Any] = {}
        pending = set(self.steps.keys())

        while pending:
            ready = [
                name
                for name in pending
                if all(dep in completed for dep in self.steps[name].depends_on)
            ]
            if not ready:
                raise OrchestrationError("Deadlock: no steps are ready but pending remains")

            results = await asyncio.gather(
                *(self._run_step(name, context, completed) for name in ready),
                return_exceptions=True,
            )

            for name, result in zip(ready, results):
                if isinstance(result, Exception):
                    if self.steps[name].is_critical:
                        raise OrchestrationError(
                            f"Critical step '{name}' failed: {result}"
                        ) from result
                    completed[name] = None
                else:
                    completed[name] = result
                pending.discard(name)

        return completed

    async def _run_step(
        self, name: str, context: dict[str, Any], completed: dict[str, Any]
    ) -> Any:
        step = self.steps[name]
        coro = step.execute(context, completed)
        if step.timeout_seconds:
            return await asyncio.wait_for(coro, timeout=step.timeout_seconds)
        return await coro
