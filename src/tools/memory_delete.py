from src.helpers.memory import Memory
from src.helpers.tool import Tool, Response


class MemoryDelete(Tool):

    async def execute(self, ids="", **kwargs):
        db = await Memory.get(self.agent)
        ids = [id.strip() for id in ids.split(",") if id.strip()]
        dels = await db.delete_documents_by_ids(ids=ids)

        from src.helpers.prompt_engine import get_prompt_engine
        result = get_prompt_engine().render(
            "components/frameworks/memories_deleted.j2", memory_count=len(dels)
        )
        return Response(message=result, break_loop=False)
