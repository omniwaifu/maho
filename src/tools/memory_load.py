from src.helpers.memory import Memory
from src.helpers.tool import Tool, Response

DEFAULT_THRESHOLD = 0.7
DEFAULT_LIMIT = 10


class MemoryLoad(Tool):

    async def execute(
        self,
        query="",
        threshold=DEFAULT_THRESHOLD,
        limit=DEFAULT_LIMIT,
        filter="",
        **kwargs,
    ):
        db = await Memory.get(self.agent)
        docs = await db.search_similarity_threshold(
            query=query, limit=limit, threshold=threshold, filter=filter
        )

        if len(docs) == 0:
            from src.helpers.prompt_engine import get_prompt_engine
            engine = get_prompt_engine()
            result = engine.render("components/frameworks/memories_not_found.j2", query=query)
        else:
            text = "\n\n".join(Memory.format_docs_plain(docs))
            result = str(text)

        return Response(message=result, break_loop=False)
