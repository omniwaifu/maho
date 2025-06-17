"""
Model provider factory and utilities.
This replaces the model provider logic from the old models.py file.
"""

from typing import Any
from src.providers.base import ModelType, ModelProvider, parse_chunk
from src.helpers import dotenv, runtime
from src.helpers.dotenv import load_dotenv
from src.helpers.rate_limiter import RateLimiter

# environment variables
load_dotenv()

rate_limiters: dict[str, RateLimiter] = {}


# Utility function to get API keys from environment variables
def get_api_key(service):
    return (
        dotenv.get_dotenv_value(f"API_KEY_{service.upper()}")
        or dotenv.get_dotenv_value(f"{service.upper()}_API_KEY")
        or dotenv.get_dotenv_value(
            f"{service.upper()}_API_TOKEN"
        )  # Added for CHUTES_API_TOKEN
        or "None"
    )


def get_model(type: ModelType, provider: ModelProvider, name: str, **kwargs):
    """Get a model instance from the specified provider"""
    fnc_name = f"get_{provider.name.lower()}_{type.name.lower()}"  # function name of model getter

    # Fallback to the root models.py for now until provider modules are implemented
    import models
    return models.get_model(type, provider, name, **kwargs)


def get_rate_limiter(
    provider: ModelProvider, name: str, requests: int, input: int, output: int
) -> RateLimiter:
    """Get or create a rate limiter for the specified provider and model"""
    # get or create
    key = f"{provider.name}\\{name}"
    rate_limiters[key] = limiter = rate_limiters.get(key, RateLimiter(seconds=60))
    # always update
    limiter.limits["requests"] = requests or 0
    limiter.limits["input"] = input or 0
    limiter.limits["output"] = output or 0
    return limiter
 