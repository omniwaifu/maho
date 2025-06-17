from src.helpers.extension import Extension
from src.core.agent import LoopData
from src.helpers import persist_chat


class SaveChat(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        persist_chat.save_tmp_chat(self.agent.context)
