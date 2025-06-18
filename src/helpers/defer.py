import asyncio
from dataclasses import dataclass
import threading
from concurrent.futures import Future
from typing import Any, Callable, Optional, Coroutine, TypeVar, Awaitable
from anyio.from_thread import start_blocking_portal, BlockingPortal

T = TypeVar("T")


class EventLoopThread:
    """Singleton managing a background AnyIO portal for a given *thread_name*."""

    _instances: dict[str, "EventLoopThread"] = {}
    _lock = threading.Lock()

    def __new__(cls, thread_name: str = "Background"):
        # Guarantee single instance per *thread_name*
        with cls._lock:
            if thread_name not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[thread_name] = instance
            return cls._instances[thread_name]

    def __init__(self, thread_name: str = "Background") -> None:  # type: ignore[override]
        # Prevent double-initialisation if the singleton already existed
        if getattr(self, "_initialised", False):
            return
        self.thread_name = thread_name
        self.portal: BlockingPortal | None = None
        self._portal_cm = None  # type: ignore
        self._start()
        self._initialised = True

    # ---------------------------------------------------------------------
    # Portal lifecycle helpers
    # ---------------------------------------------------------------------

    def _start(self) -> None:
        """Start the background AnyIO portal if it's not already running."""
        if self.portal is not None:
            return

        # start_blocking_portal() spins up a new thread that hosts an event-loop
        # (asyncio backend here for maximum compatibility with the existing
        # code-base that still uses asyncio primitives like asyncio.sleep()).
        #
        # Using the *context manager* form allows us to get a proper shutdown
        # implementation simply by calling __exit__() later.
        self._portal_cm = start_blocking_portal(backend="asyncio")
        self.portal = self._portal_cm.__enter__()

    def terminate(self) -> None:
        """Stop the portal and clean up the background thread."""
        if self.portal is None or self._portal_cm is None:
            return

        # __exit__ will ensure the portal is stopped and the event-loop thread
        # is joined.
        try:
            self._portal_cm.__exit__(None, None, None)
        finally:
            self.portal = None
            self._portal_cm = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def run_coroutine(self, coro):
        """Schedule *coro* on the background portal and return a Future."""
        self._start()
        if self.portal is None:
            raise RuntimeError("Portal is not initialized")

        async def _runner():  # noqa: D401 – simple helper
            return await coro

        # start_task_soon() gives us a concurrent.futures.Future that mirrors
        # the task's outcome which is exactly what run_coroutine_threadsafe()
        # previously returned.
        return self.portal.start_task_soon(_runner)


@dataclass
class ChildTask:
    task: "DeferredTask"
    terminate_thread: bool


class DeferredTask:
    def __init__(
        self,
        thread_name: str = "Background",
    ):
        self.event_loop_thread = EventLoopThread(thread_name)
        self._future: Optional[Future] = None
        self.children: list[ChildTask] = []

    def start_task(
        self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any
    ):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._start_task()
        return self

    def __del__(self):
        self.kill()

    def _start_task(self):
        self._future = self.event_loop_thread.run_coroutine(self._run())

    async def _run(self):
        return await self.func(*self.args, **self.kwargs)

    def is_ready(self) -> bool:
        return self._future.done() if self._future else False

    def result_sync(self, timeout: Optional[float] = None) -> Any:
        if not self._future:
            raise RuntimeError("Task hasn't been started")
        try:
            return self._future.result(timeout)
        except TimeoutError:
            raise TimeoutError(
                "The task did not complete within the specified timeout."
            )

    async def result(self, timeout: Optional[float] = None) -> Any:
        if not self._future:
            raise RuntimeError("Task hasn't been started")

        loop = asyncio.get_running_loop()

        def _get_result():
            try:
                result = self._future.result(timeout)  # type: ignore
                # self.kill()
                return result
            except TimeoutError:
                raise TimeoutError(
                    "The task did not complete within the specified timeout."
                )

        return await loop.run_in_executor(None, _get_result)

    def kill(self, terminate_thread: bool = False) -> None:
        """Kill the task and optionally terminate its thread."""
        self.kill_children()
        if self._future and not self._future.done():
            self._future.cancel()

        if terminate_thread and self.event_loop_thread.portal:
            # Gracefully stop the background portal which will, in turn,
            # cancel any remaining tasks.
            self.event_loop_thread.terminate()

    def kill_children(self) -> None:
        for child in self.children:
            child.task.kill(terminate_thread=child.terminate_thread)
        self.children = []

    def is_alive(self) -> bool:
        return self._future and not self._future.done()  # type: ignore

    def restart(self, terminate_thread: bool = False) -> None:
        self.kill(terminate_thread=terminate_thread)
        self._start_task()

    def add_child_task(
        self, task: "DeferredTask", terminate_thread: bool = False
    ) -> None:
        self.children.append(ChildTask(task, terminate_thread))

    async def _execute_in_task_context(
        self, func: Callable[..., T], *args, **kwargs
    ) -> T:
        """Execute a function in the task's context and return its result."""
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def execute_inside(self, func: Callable[..., T], *args, **kwargs) -> Awaitable[T]:
        if not self.event_loop_thread.portal:
            raise RuntimeError("Portal is not initialized")

        future: Future = Future()

        async def wrapped():
            if not self.event_loop_thread.portal:
                raise RuntimeError("Portal is not initialized")
            try:
                result = await self._execute_in_task_context(func, *args, **kwargs)
                # Keep awaiting until we get a concrete value
                while isinstance(result, Awaitable):
                    result = await result
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        self.event_loop_thread.portal.start_task_soon(wrapped)
        return asyncio.wrap_future(future)
