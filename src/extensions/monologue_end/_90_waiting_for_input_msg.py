from src.helpers.extension import Extension
from src.core.agent import LoopData


class WaitingForInputMsg(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # show temp info message
        if self.agent.number == 0:
            self.agent.context.log.set_initial_progress()
