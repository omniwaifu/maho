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
        # Create tasks for all three search methods
        tasks = [
            self.searxng_search(question),
            # self.perplexity_search(question),
            # self.duckduckgo_search(question),
            self.mem_search(question),
        ]

        # Run all tasks concurrently - simple replacement
        # Convert to anyio task group
        results = []
        async with anyio.create_task_group() as tg:

            async def run_task(task, index):
                try:
                    result = await task
                    while len(results) <= index:
                        results.append(None)
                    results[index] = result
                except Exception as e:
                    while len(results) <= index:
                        results.append(None)
                    results[index] = e

            for i, task in enumerate(tasks):
                tg.start_soon(run_task, task, i)

        # perplexity_result, duckduckgo_result, memory_result = results
        searxng_result, memory_result = results

        # Handle exceptions and format results
        # perplexity_result = self.format_result(perplexity_result, "Perplexity")
        # duckduckgo_result = self.format_result(duckduckgo_result, "DuckDuckGo")
        searxng_result = self.format_result_searxng(searxng_result, "Search Engine")
        memory_result = self.format_result(memory_result, "Memory")

        msg = self.agent.read_prompt(
            "tool.knowledge.response.md",
            #   online_sources = ((perplexity_result + "\n\n") if perplexity_result else "") + str(duckduckgo_result),
            online_sources=((searxng_result + "\n\n") if searxng_result else ""),
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

        outputs = []
        for item in result["results"]:
            outputs.append(f"{item['title']}\n{item['url']}\n{item['content']}")

        return "\n\n".join(outputs[:SEARCH_ENGINE_RESULTS]).strip()
