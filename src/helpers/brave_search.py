import aiohttp
from src.helpers import dotenv


async def search(query: str, results=10):
    """
    Search using Brave Search API
    Requires API_KEY_BRAVE in environment
    """
    api_key = dotenv.get_dotenv_value("API_KEY_BRAVE")
    
    if not api_key:
        raise Exception("No API key provided for Brave Search. Set API_KEY_BRAVE in your environment.")
    
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
    }
    
    params = {
        "q": query,
        "count": results,
        "result_filter": "web",  # Focus on web results
        "freshness": "pd",  # Past day for recent news
        "text_decorations": "false",  # No markdown formatting (must be string)
        "search_lang": "en",
        "country": "us",
    }
    
    url = "https://api.search.brave.com/res/v1/web/search"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return format_brave_results(data)
            elif response.status == 429:
                raise Exception("Brave Search rate limit exceeded")
            else:
                error_text = await response.text()
                raise Exception(f"Brave Search API error {response.status}: {error_text}")


def format_brave_results(data):
    """Format Brave search results into readable text"""
    if not data or "web" not in data or "results" not in data["web"]:
        return []
    
    results = []
    for item in data["web"]["results"]:
        title = item.get("title", "No title")
        url = item.get("url", "No URL")
        description = item.get("description", "No description")
        results.append(f"{title}\n{url}\n{description}")
    
    return results 