"""
Async compatibility layer for gradual asyncio -> anyio/trio migration.

This module provides drop-in replacements for common asyncio patterns
using anyio, allowing gradual migration to trio's structured concurrency.
"""

import asyncio
from typing import Any, Awaitable, Callable, Sequence, TypeVar
import anyio
from anyio import create_task_group, sleep
from contextlib import asynccontextmanager

T = TypeVar("T")


async def gather(*tasks: Awaitable[T], return_exceptions: bool = False) -> list[T]:
    """
    Drop-in replacement for asyncio.gather using anyio task groups.
    Provides structured concurrency instead of fire-and-forget tasks.
    
    :param return_exceptions: If True, exceptions are returned as results instead of raised
    """
    results: list[Any] = [None] * len(tasks)
    exceptions: list[Exception | None] = [None] * len(tasks)
    
    async with create_task_group() as tg:
        async def _run_task(task: Awaitable[T], index: int) -> None:
            try:
                result = await task
                results[index] = result
            except Exception as e:
                if return_exceptions:
                    results[index] = e
                else:
                    exceptions[index] = e
                    raise
            
        for i, task in enumerate(tasks):
            tg.start_soon(_run_task, task, i)
    
    # If not returning exceptions, check for any that occurred
    if not return_exceptions:
        for exc in exceptions:
            if exc:
                raise exc
    
    return results


async def sleep_compat(delay: float) -> None:
    """Drop-in replacement for asyncio.sleep."""
    await sleep(delay)


@asynccontextmanager
async def task_group():
    """
    Context manager for structured concurrency.
    Use this instead of asyncio.create_task() for better cancellation.
    """
    async with create_task_group() as tg:
        yield tg


class TaskGroup:
    """
    Wrapper for anyio task groups to provide a more familiar interface
    for gradual migration from asyncio patterns.
    """
    
    def __init__(self):
        self._tg = None
        
    async def __aenter__(self):
        self._tg = create_task_group()
        await self._tg.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._tg:
            return await self._tg.__aexit__(exc_type, exc_val, exc_tb)
            
    def start_soon(self, func: Callable[..., Awaitable[Any]], *args: Any) -> None:
        """Start a task in the group."""
        if self._tg:
            self._tg.start_soon(func, *args)


def run_with_trio(main: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    """
    Run an async function with trio backend.
    Use this instead of asyncio.run() for new code.
    """
    return anyio.run(main, *args, backend="trio", **kwargs)


def run_with_asyncio(main: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    """
    Run an async function with asyncio backend for compatibility.
    Fallback during migration period.
    """
    return anyio.run(main, *args, backend="asyncio", **kwargs)


# Compatibility aliases for gradual migration
create_task_group_compat = create_task_group
sleep_async = sleep_compat
