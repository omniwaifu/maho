import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Coroutine, Callable
import anyio
from anyio.abc import TaskGroup

if TYPE_CHECKING:
    from src.core.agent import Agent

from src.core.models import AgentConfig, AgentContextType, UserMessage
from src.helpers import log as Log
from src.helpers.localization import Localization


class AgentContext:
    """Manages agent execution context and state"""

    _contexts: dict[str, "AgentContext"] = {}
    _counter: int = 0

    def __init__(
        self,
        config: AgentConfig,
        id: str | None = None,
        name: str | None = None,
        agent0: "Agent|None" = None,  # type: ignore
        log: Log.Log | None = None,
        paused: bool = False,
        streaming_agent: "Agent|None" = None,  # type: ignore
        created_at: datetime | None = None,
        type: AgentContextType = AgentContextType.USER,
        last_message: datetime | None = None,
    ):
        # build context
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.config = config
        self.log = log or Log.Log()
        # Avoid circular import by importing Agent here
        from src.core.agent import Agent

        self.agent0 = agent0 or Agent(0, self.config, self)
        self.paused = paused
        self.streaming_agent = streaming_agent
        self._task_group: TaskGroup | None = None
        self._cancel_scope: anyio.CancelScope | None = None
        self.created_at = created_at or datetime.now(timezone.utc)
        self.type = type
        AgentContext._counter += 1
        self.no = AgentContext._counter
        # set to start of unix epoch
        self.last_message = last_message or datetime.now(timezone.utc)

        existing = self._contexts.get(self.id, None)
        if existing:
            AgentContext.remove(self.id)
        self._contexts[self.id] = self

    @staticmethod
    def get(id: str):
        return AgentContext._contexts.get(id, None)

    @staticmethod
    def first():
        if not AgentContext._contexts:
            return None
        return list(AgentContext._contexts.values())[0]

    @staticmethod
    def all():
        return list(AgentContext._contexts.values())

    @staticmethod
    def remove(id: str):
        context = AgentContext._contexts.pop(id, None)
        if context:
            context.kill_process()
        return context

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": (
                Localization.get().serialize_datetime(self.created_at)
                if self.created_at
                else Localization.get().serialize_datetime(datetime.fromtimestamp(0))
            ),
            "no": self.no,
            "log_guid": self.log.guid,
            "log_version": len(self.log.updates),
            "log_length": len(self.log.logs),
            "paused": self.paused,
            "last_message": (
                Localization.get().serialize_datetime(self.last_message)
                if self.last_message
                else Localization.get().serialize_datetime(datetime.fromtimestamp(0))
            ),
            "type": self.type.value,
        }

    @staticmethod
    def log_to_all(
        type: Log.Type,
        heading: str | None = None,
        content: str | None = None,
        kvps: dict | None = None,
        temp: bool | None = None,
        update_progress: Log.ProgressUpdate | None = None,
        id: str | None = None,  # Add id parameter
        **kwargs,
    ) -> list[Log.LogItem]:
        items: list[Log.LogItem] = []
        for context in AgentContext.all():
            items.append(
                context.log.log(
                    type, heading, content, kvps, temp, update_progress, id, **kwargs
                )
            )
        return items

    def kill_process(self):
        if self._cancel_scope and not self._cancel_scope.cancelled_caught:
            self._cancel_scope.cancel()

    def reset(self):
        self.kill_process()
        self.log.reset()
        # Avoid circular import by importing Agent here
        from src.core.agent import Agent

        self.agent0 = Agent(0, self.config, self)
        self.streaming_agent = None
        self.paused = False

    async def nudge(self):
        self.kill_process()
        self.paused = False
        await self.run_task(self.get_agent().monologue)

    def get_agent(self):
        return self.streaming_agent or self.agent0

    async def communicate(self, msg: UserMessage, broadcast_level: int = 1):
        self.paused = False  # unpause if paused

        current_agent = self.get_agent()

        if self._task_group:
            # set intervention messages to agent(s):
            intervention_agent = current_agent
            while intervention_agent and broadcast_level != 0:
                intervention_agent.intervention = msg
                broadcast_level -= 1
                # Avoid circular import by importing Agent here
                from src.core.agent import Agent

                intervention_agent = intervention_agent.data.get(
                    Agent.DATA_NAME_SUPERIOR, None
                )
        else:
            await self.run_task(self._process_chain, current_agent, msg)

    async def run_task(
        self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any
    ):
        async def task_wrapper():
            try:
                async with anyio.create_task_group() as tg:
                    self._task_group = tg
                    await func(*args, **kwargs)
            finally:
                self._task_group = None

        if not self._cancel_scope or self._cancel_scope.cancelled_caught:
             # Create a new cancel scope for the entire context's lifecycle
            with anyio.CancelScope() as scope:
                self._cancel_scope = scope
                async with anyio.create_task_group() as tg:
                    tg.start_soon(task_wrapper)
        else:
            # We are already inside a running task group, just start the new task
            if self._task_group:
                self._task_group.start_soon(task_wrapper)
            else:
                 # This case should ideally not be reached if logic is correct
                async with anyio.create_task_group() as tg:
                    tg.start_soon(task_wrapper)

    # this wrapper ensures that superior agents are called back if the chat was loaded from file and original callstack is gone
    async def _process_chain(self, agent: "Agent", msg: "UserMessage|str", user=True):  # type: ignore
        try:
            msg_template = (
                agent.hist_add_user_message(msg)  # type: ignore
                if user
                else agent.hist_add_tool_result(
                    tool_name="call_subordinate", tool_result=msg  # type: ignore
                )
            )
            response = await agent.monologue()  # type: ignore
            # Avoid circular import by importing Agent here
            from src.core.agent import Agent

            superior = agent.data.get(Agent.DATA_NAME_SUPERIOR, None)
            if superior:
                response = await self._process_chain(superior, response, False)  # type: ignore
            return response
        except Exception as e:
            agent.handle_critical_exception(e)
