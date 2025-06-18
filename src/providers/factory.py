"""
Model provider factory and utilities.
This replaces the model provider logic from the old models.py file.
"""

from typing import Any
from pydantic import SecretStr
from src.providers.base import ModelType, ModelProvider, parse_chunk
from src.helpers import dotenv, runtime
from src.helpers.dotenv import load_dotenv
from src.helpers.rate_limiter import RateLimiter

# Import model classes
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint, HuggingFaceEmbeddings
from langchain_mistralai import ChatMistralAI

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

def get_openai_chat(model_name: str, **kwargs):
    api_key = get_api_key("openai")
    return ChatOpenAI(model=model_name, api_key=SecretStr(api_key), **kwargs)

def get_openai_embedding(model_name: str, **kwargs):
    api_key = get_api_key("openai")
    return OpenAIEmbeddings(model=model_name, api_key=SecretStr(api_key), **kwargs)

def get_iointel_chat(model_name: str, **kwargs):
    api_key = get_api_key("iointel")
    return ChatOpenAI(model=model_name, api_key=SecretStr(api_key), **kwargs)

def get_anthropic_chat(model_name: str, **kwargs):
    api_key = get_api_key("anthropic")
    return ChatAnthropic(model_name=model_name, api_key=SecretStr(api_key), **kwargs)


def get_groq_chat(model_name: str, **kwargs):
    api_key = get_api_key("groq")
    return ChatGroq(model=model_name, api_key=SecretStr(api_key), **kwargs)


def get_ollama_chat(model_name: str, **kwargs):
    base_url = dotenv.get_dotenv_value("OLLAMA_BASE_URL") or "http://localhost:11434"
    return ChatOllama(model=model_name, base_url=base_url, **kwargs)


def get_ollama_embedding(model_name: str, **kwargs):
    base_url = dotenv.get_dotenv_value("OLLAMA_BASE_URL") or "http://localhost:11434"
    return OllamaEmbeddings(model=model_name, base_url=base_url, **kwargs)


def get_google_chat(model_name: str, **kwargs):
    api_key = get_api_key("google")
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=SecretStr(api_key),
        safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        },
        **kwargs,
    )


def get_huggingface_chat(model_name: str, **kwargs):
    token = get_api_key("huggingface") or dotenv.get_dotenv_value("HF_TOKEN")
    endpoint = HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=token,
        **kwargs
    )
    return ChatHuggingFace(llm=endpoint)


def get_huggingface_embedding(model_name: str, **kwargs):
    return HuggingFaceEmbeddings(model_name=model_name, **kwargs)


def get_mistralai_chat(model_name: str, **kwargs):
    api_key = get_api_key("mistral")
    return ChatMistralAI(model=model_name, api_key=SecretStr(api_key), **kwargs) 


def get_model(type: ModelType, provider: ModelProvider, name: str, **kwargs):
    """Get a model instance from the specified provider"""
    fnc_name = f"get_{provider.name.lower()}_{type.name.lower()}"  # function name of model getter
    model = globals()[fnc_name](name, **kwargs)  # call function by name
    return model


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
 