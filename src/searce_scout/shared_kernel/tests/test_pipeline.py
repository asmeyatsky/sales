"""Tests for the Parallel Pipeline."""

from __future__ import annotations

import asyncio

import pytest

from searce_scout.shared_kernel.orchestration.pipeline import (
    ParallelPipeline,
    PipelineStage,
)


# ---------------------------------------------------------------------------
# Concrete stage implementations for testing
# ---------------------------------------------------------------------------


class DoubleStage(PipelineStage[int, int]):
    """Doubles the input value."""

    async def process(self, input_data: int) -> int:
        return input_data * 2


class AddOneStage(PipelineStage[int, int]):
    """Adds one to the input value."""

    async def process(self, input_data: int) -> int:
        return input_data + 1


class RecordingStage(PipelineStage[int, int]):
    """Records concurrency level to detect semaphore behaviour."""

    def __init__(self) -> None:
        self.max_concurrent = 0
        self._current = 0
        self._lock = asyncio.Lock()

    async def process(self, input_data: int) -> int:
        async with self._lock:
            self._current += 1
            if self._current > self.max_concurrent:
                self.max_concurrent = self._current
        # Yield control so other tasks can enter
        await asyncio.sleep(0.01)
        async with self._lock:
            self._current -= 1
        return input_data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_single_stage():
    """Items processed through a single stage produce expected results."""
    pipeline = ParallelPipeline(stages=[DoubleStage()])

    result = await pipeline.execute([1, 2, 3])

    assert result == [2, 4, 6]


@pytest.mark.asyncio
async def test_pipeline_multiple_stages():
    """Items processed through chained stages produce expected results."""
    pipeline = ParallelPipeline(stages=[DoubleStage(), AddOneStage()])

    result = await pipeline.execute([1, 2, 3])

    # Each item is doubled, then incremented: (1*2)+1=3, (2*2)+1=5, (3*2)+1=7
    assert result == [3, 5, 7]


@pytest.mark.asyncio
async def test_pipeline_concurrency_limit():
    """The semaphore caps how many items run concurrently within a stage."""
    stage = RecordingStage()
    pipeline = ParallelPipeline(stages=[stage], max_concurrency=2)

    await pipeline.execute(list(range(10)))

    # The max observed concurrency should not exceed the limit
    assert stage.max_concurrent <= 2
