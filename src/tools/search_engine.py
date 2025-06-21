import os
import anyio.to_thread
from src.helpers import dotenv, memory, perplexity_search, duckduckgo_search, brave_search
from src.helpers.tool import Tool, Response
from src.helpers.print_style import PrintStyle
from src.helpers.errors import handle_error
from src.helpers.searxng import search as searxng

SEARCH_ENGINE_RESULTS = 10


class SearchEngine(Tool):
    async def execute(self, query="", **kwargs):
        # Try SearxNG first
        searxng_result = await self.searxng_search(query)
        
        # Check if SearxNG failed or returned no results
        if (isinstance(searxng_result, Exception) or 
            "search failed" in str(searxng_result).lower() or
            not searxng_result.strip()):
            
            PrintStyle.hint("SearxNG failed, falling back to DuckDuckGo...")
            # Fallback to DuckDuckGo
            try:
                duckduckgo_result = await self.duckduckgo_search(query)
                final_result = self.format_result_duckduckgo(duckduckgo_result, "DuckDuckGo Search")
            except Exception as e:
                if "ratelimit" in str(e).lower():
                    PrintStyle.hint("DuckDuckGo rate limited, falling back to Brave Search...")
                    # Fallback to Brave Search
                    try:
                        brave_result = await self.brave_search(query)
                        final_result = self.format_result_brave(brave_result, "Brave Search")
                    except Exception as brave_e:
                        PrintStyle.hint("Brave Search failed, falling back to Perplexity...")
                        # Final fallback to Perplexity
                        perplexity_result = await self.perplexity_search(query)
                        final_result = self.format_result_perplexity(perplexity_result, "Perplexity AI")
                else:
                    handle_error(e)
                    final_result = f"DuckDuckGo search failed: {str(e)}"
        else:
            final_result = searxng_result

        await self.agent.handle_intervention(
            final_result
        )  # wait for intervention and handle it, if paused

        return Response(message=final_result, break_loop=False)

    async def searxng_search(self, question):
        try:
            results = await searxng(question)
            return self.format_result_searxng(results, "Search Engine")
        except Exception as e:
            handle_error(e)
            return f"Search Engine search failed: {str(e)}"

    async def duckduckgo_search(self, question):
        return await anyio.to_thread.run_sync(duckduckgo_search.search, question)

    async def brave_search(self, question):
        return await brave_search.search(question, results=SEARCH_ENGINE_RESULTS)

    async def perplexity_search(self, question):
        if dotenv.get_dotenv_value("API_KEY_PERPLEXITY"):
            return await anyio.to_thread.run_sync(
                perplexity_search.perplexity_search, question
            )
        else:
            raise Exception("No API key provided for Perplexity. Set API_KEY_PERPLEXITY in your environment.")

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

    def format_result_duckduckgo(self, result, source):
        if isinstance(result, Exception):
            handle_error(result)
            return f"{source} search failed: {str(result)}"
        
        if not result:
            return f"{source} search returned no results"

        outputs = []
        for item in result[:SEARCH_ENGINE_RESULTS]:
            # DuckDuckGo returns string representations of dict objects
            try:
                # Try to extract title and URL from the string representation
                item_str = str(item)
                if "'title':" in item_str and "'href':" in item_str:
                    outputs.append(item_str)
                else:
                    outputs.append(f"Result: {item_str}")
            except Exception:
                outputs.append(f"Result: {str(item)}")

        return "\n\n".join(outputs).strip()

    def format_result_brave(self, result, source):
        if isinstance(result, Exception):
            handle_error(result)
            return f"{source} search failed: {str(result)}"
        
        if not result:
            return f"{source} search returned no results"

        # Brave search returns a list of formatted strings
        return "\n\n".join(result[:SEARCH_ENGINE_RESULTS]).strip()

    def format_result_perplexity(self, result, source):
        if isinstance(result, Exception):
            handle_error(result)
            return f"{source} search failed: {str(result)}"
        
        if not result:
            return f"{source} search returned no results"

        # Perplexity returns a text response
        return f"**{source} Results:**\n\n{result}"
