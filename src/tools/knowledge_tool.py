import os
import anyio
import anyio.to_thread
from src.helpers import dotenv, memory, perplexity_search, duckduckgo_search
from src.helpers.tool import Tool, Response
from src.helpers.print_style import PrintStyle
from src.helpers.errors import handle_error
from src.helpers.searxng import search as searxng
from src.tools.memory_load import DEFAULT_THRESHOLD as DEFAULT_MEMORY_THRESHOLD

SEARCH_ENGINE_RESULTS = 10


class Knowledge(Tool):
    async def execute(self, question="", **kwargs):
        # Try searxng first, fallback to duckduckgo if it fails
        searxng_result = await self.searxng_search(question)
        
        # Check if searxng failed or returned no results
        if (isinstance(searxng_result, Exception) or 
            not searxng_result or 
            not isinstance(searxng_result, dict) or 
            "results" not in searxng_result or 
            not searxng_result["results"]):
            
            # Fallback to DuckDuckGo
            duckduckgo_result = await self.duckduckgo_search(question)
            online_result = self.format_result(duckduckgo_result, "DuckDuckGo")
        else:
            online_result = self.format_result_searxng(searxng_result, "SearXNG")
        
        # Get memory results
        memory_result = await self.mem_search(question)
        memory_result = self.format_result(memory_result, "Memory")

        msg = self.agent.read_prompt(
            "tool.knowledge.response.md",
            online_sources=online_result,
            memory=memory_result,
        )

        await self.agent.handle_intervention(
            msg
        )  # wait for intervention and handle it, if paused

        return Response(message=msg, break_loop=False)

    async def perplexity_search(self, question):
        if dotenv.get_dotenv_value("API_KEY_PERPLEXITY"):
            return await anyio.to_thread.run_sync(
                perplexity_search.perplexity_search, question
            )
        else:
            PrintStyle.hint(
                "No API key provided for Perplexity. Skipping Perplexity search."
            )
            self.agent.context.log.log(
                type="hint",
                content="No API key provided for Perplexity. Skipping Perplexity search.",
            )
            return None

    async def duckduckgo_search(self, question):
        return await anyio.to_thread.run_sync(duckduckgo_search.search, question)

    async def searxng_search(self, question):
        return await searxng(question)

    async def mem_search(self, question: str):
        db = await memory.Memory.get(self.agent)
        docs = await db.search_similarity_threshold(
            query=question, limit=5, threshold=DEFAULT_MEMORY_THRESHOLD
        )
        text = memory.Memory.format_docs_plain(docs)
        return "\n\n".join(text)

    def format_result(self, result, source):
        if isinstance(result, Exception):
            handle_error(result)
            return f"{source} search failed: {str(result)}"
        return result if result else ""

    def format_result_searxng(self, result, source):
        if isinstance(result, Exception):
            handle_error(result)
            return f"{source} search failed: {str(result)}"

        if not result or not isinstance(result, dict) or "results" not in result:
            return f"{source} search returned no results"

        outputs = []
        for item in result["results"]:
            title = item.get("title", "No title")
            url = item.get("url", "No URL")
            content = item.get("content", "No content")
            outputs.append(f"{title}\n{url}\n{content}")

        return "\n\n".join(outputs[:SEARCH_ENGINE_RESULTS]).strip()
