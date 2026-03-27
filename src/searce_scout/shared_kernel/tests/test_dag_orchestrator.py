"""Tests for the DAG-based Workflow Orchestrator."""

from __future__ import annotations

import asyncio

import pytest

from searce_scout.shared_kernel.errors import OrchestrationError
from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _constant_step(value):
    """Return a step function that ignores its args and returns *value*."""
    async def _fn(context, completed):
        return value
    return _fn


def _make_step_fn(value):
    """Return a coroutine-function that always returns *value*."""
    async def _fn(context, completed):
        return value
    return _fn


def _make_recording_step(name: str, call_order: list[str], value=None):
    """Return a step function that records its invocation order."""
    async def _fn(context, completed):
        call_order.append(name)
        return value
    return _fn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_single_step():
    """A single step with no dependencies returns its result."""
    step = WorkflowStep(name="only", execute=_make_step_fn(42))
    orchestrator = DAGOrchestrator([step])

    result = await orchestrator.execute({})

    assert result == {"only": 42}


@pytest.mark.asyncio
async def test_execute_parallel_steps():
    """Two independent steps both run and return results."""
    call_order: list[str] = []
    step_a = WorkflowStep(
        name="a", execute=_make_recording_step("a", call_order, "result_a")
    )
    step_b = WorkflowStep(
        name="b", execute=_make_recording_step("b", call_order, "result_b")
    )
    orchestrator = DAGOrchestrator([step_a, step_b])

    result = await orchestrator.execute({})

    assert result["a"] == "result_a"
    assert result["b"] == "result_b"
    # Both must have been called
    assert set(call_order) == {"a", "b"}


@pytest.mark.asyncio
async def test_execute_respects_dependencies():
    """Step B depends on step A, so A must complete first."""
    call_order: list[str] = []

    step_a = WorkflowStep(
        name="a", execute=_make_recording_step("a", call_order, "done_a")
    )
    step_b = WorkflowStep(
        name="b",
        execute=_make_recording_step("b", call_order, "done_b"),
        depends_on=("a",),
    )
    orchestrator = DAGOrchestrator([step_a, step_b])

    result = await orchestrator.execute({})

    assert call_order.index("a") < call_order.index("b")
    assert result == {"a": "done_a", "b": "done_b"}


def test_cycle_detection_raises():
    """Two mutually dependent steps cause OrchestrationError at construction."""
    step_a = WorkflowStep(
        name="a", execute=_make_step_fn(None), depends_on=("b",)
    )
    step_b = WorkflowStep(
        name="b", execute=_make_step_fn(None), depends_on=("a",)
    )

    with pytest.raises(OrchestrationError, match="Circular dependency"):
        DAGOrchestrator([step_a, step_b])


def test_unknown_dependency_raises():
    """A step that depends on a nonexistent step raises OrchestrationError."""
    step = WorkflowStep(
        name="orphan", execute=_make_step_fn(None), depends_on=("ghost",)
    )

    with pytest.raises(OrchestrationError, match="unknown step"):
        DAGOrchestrator([step])


@pytest.mark.asyncio
async def test_critical_step_failure_raises():
    """A critical step that throws propagates OrchestrationError."""

    async def _exploding(context, completed):
        raise RuntimeError("boom")

    step = WorkflowStep(name="bomb", execute=_exploding, is_critical=True)
    orchestrator = DAGOrchestrator([step])

    with pytest.raises(OrchestrationError, match="Critical step 'bomb' failed"):
        await orchestrator.execute({})


@pytest.mark.asyncio
async def test_non_critical_step_failure_continues():
    """A non-critical step failure records None and lets other steps proceed."""

    async def _exploding(context, completed):
        raise RuntimeError("oops")

    step_bad = WorkflowStep(
        name="bad", execute=_exploding, is_critical=False
    )
    step_good = WorkflowStep(
        name="good",
        execute=_make_step_fn("ok"),
        depends_on=("bad",),
    )
    orchestrator = DAGOrchestrator([step_bad, step_good])

    result = await orchestrator.execute({})

    assert result["bad"] is None
    assert result["good"] == "ok"


@pytest.mark.asyncio
async def test_timeout_raises():
    """A step that exceeds its timeout_seconds triggers asyncio.TimeoutError
    which is wrapped in OrchestrationError for critical steps."""

    async def _slow(context, completed):
        await asyncio.sleep(10)

    step = WorkflowStep(
        name="slow",
        execute=_slow,
        timeout_seconds=0.01,
        is_critical=True,
    )
    orchestrator = DAGOrchestrator([step])

    with pytest.raises(OrchestrationError, match="Critical step 'slow' failed"):
        await orchestrator.execute({})


@pytest.mark.asyncio
async def test_step_receives_context_and_completed():
    """The step function receives the context dict and a dict of completed results."""
    received_args: dict = {}

    async def _capturing(context, completed):
        received_args["context"] = context
        received_args["completed"] = completed
        return "captured"

    step_first = WorkflowStep(name="first", execute=_make_step_fn("first_done"))
    step_second = WorkflowStep(
        name="second", execute=_capturing, depends_on=("first",)
    )
    orchestrator = DAGOrchestrator([step_first, step_second])

    ctx = {"key": "value"}
    await orchestrator.execute(ctx)

    assert received_args["context"] is ctx
    assert received_args["completed"] == {"first": "first_done"}


@pytest.mark.asyncio
async def test_empty_steps():
    """An orchestrator with no steps returns an empty dict."""
    orchestrator = DAGOrchestrator([])

    result = await orchestrator.execute({})

    assert result == {}
