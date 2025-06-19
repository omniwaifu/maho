import aiohttp
import anyio
from src.helpers import runtime

# Port candidates for searxng service discovery
SEARXNG_PORT_CANDIDATES = [55510, 55520, 55530, 55540]


async def _discover_searxng_port() -> str:
    """Discover which port searxng is actually running on."""
    host = "localhost"
    
    for port in SEARXNG_PORT_CANDIDATES:
        try:
            url = f"http://{host}:{port}/search"
            async with aiohttp.ClientSession() as session:
                # Quick health check with minimal query
                with anyio.move_on_after(2):  # 2 second timeout
                    async with session.post(
                        url, 
                        data={"q": "test", "format": "json"}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Verify it's actually searxng by checking response structure
                            if isinstance(data, dict) and ("results" in data or "query" in data):
                                return url
        except (aiohttp.ClientError, Exception):
            continue
    
    # Fallback to configured port if discovery fails
    return "http://localhost:55510/search"


# Cache the discovered URL to avoid repeated discovery
_cached_url = None


async def _get_searxng_url() -> str:
    """Get the searxng URL, using cached value or discovering it."""
    global _cached_url
    if _cached_url is None:
        _cached_url = await _discover_searxng_port()
    return _cached_url


def _invalidate_cache():
    """Invalidate the cached URL to force rediscovery."""
    global _cached_url
    _cached_url = None


async def search(query: str):
    return await runtime.call_development_function(_search, query=query)


async def _search(query: str):
    url = await _get_searxng_url()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data={"q": query, "format": "json"}) as response:
                result = await response.json()
                
                # Check if result is valid
                if isinstance(result, dict) and "results" in result:
                    return result
                else:
                    # Invalid response, try cache invalidation and retry once
                    _invalidate_cache()
                    url = await _get_searxng_url()
                    async with session.post(url, data={"q": query, "format": "json"}) as response:
                        return await response.json()
                        
    except (aiohttp.ClientError, asyncio.TimeoutError):
        # Connection failed, invalidate cache and retry once
        _invalidate_cache()
        url = await _get_searxng_url()
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data={"q": query, "format": "json"}) as response:
                return await response.json()
