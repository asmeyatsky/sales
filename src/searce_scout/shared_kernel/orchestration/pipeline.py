"""
Parallel Pipeline

Processes items through typed stages with concurrency control.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T_In = TypeVar("T_In")
T_Out = TypeVar("T_Out")


class PipelineStage(Generic[T_In, T_Out], ABC):
    @abstractmethod
    async def process(self, input_data: T_In) -> T_Out: ...


class ParallelPipeline:
    """Processes items through stages, parallelizing within each stage."""

    def __init__(self, stages: list[PipelineStage[Any, Any]], max_concurrency: int = 10) -> None:
        self.stages = stages
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def execute(self, items: list[Any]) -> list[Any]:
        results = items
        for stage in self.stages:
            results = list(
                await asyncio.gather(
                    *(self._run_with_limit(stage.process, item) for item in results)
                )
            )
        return results

    async def _run_with_limit(self, fn: Any, item: Any) -> Any:
        async with self.semaphore:
            return await fn(item)
