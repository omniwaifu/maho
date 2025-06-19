from src.helpers.memory import Memory
from src.helpers.tool import Tool, Response
from src.tools.memory_load import DEFAULT_THRESHOLD


class MemoryForget(Tool):

    async def execute(self, query="", threshold=DEFAULT_THRESHOLD, filter="", **kwargs):
        db = await Memory.get(self.agent)
        dels = await db.delete_documents_by_query(
            query=query, threshold=threshold, filter=filter
        )

        from src.helpers.prompt_engine import get_prompt_engine
        result = get_prompt_engine().render(
            "components/frameworks/memories_deleted.j2", memory_count=len(dels)
        )
        return Response(message=result, break_loop=False)
