import anyio
from src.helpers.extension import Extension
from src.core.agent import LoopData

DATA_NAME_TASK = "_organize_history_task"


class OrganizeHistory(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Check if there's already a compression running
        task = self.agent.get_data(DATA_NAME_TASK)
        if task and not task.done():
            return

        # Use anyio task group for structured concurrency
        async with anyio.create_task_group() as tg:
            tg.start_soon(self.agent.history.compress)
        
        # Mark that compression has been handled
        self.agent.set_data(DATA_NAME_TASK, None)
