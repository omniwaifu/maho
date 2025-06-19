from src.helpers.memory import Memory
from src.helpers.tool import Tool, Response


class MemorySave(Tool):

    async def execute(self, text="", area="", **kwargs):

        if not area:
            area = Memory.Area.MAIN.value

        metadata = {"area": area, **kwargs}

        db = await Memory.get(self.agent)
        id = await db.insert_text(text, metadata)

        from src.helpers.prompt_engine import get_prompt_engine
        engine = get_prompt_engine()
        result = engine.render("components/frameworks/memory_saved.j2", memory_id=id)
        return Response(message=result, break_loop=False)
