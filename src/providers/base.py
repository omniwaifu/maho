from enum import Enum
from typing import Any
from abc import ABC, abstractmethod


class ModelType(Enum):
    CHAT = "Chat"
    EMBEDDING = "Embedding"


class ModelProvider(Enum):
    ANTHROPIC = "Anthropic"
    CHUTES = "Chutes"
    DEEPSEEK = "DeepSeek"
    GOOGLE = "Google"
    GROQ = "Groq"
    HUGGINGFACE = "HuggingFace"
    IOINTEL = "io.net"
    LMSTUDIO = "LM Studio"
    MISTRALAI = "Mistral AI"
    OLLAMA = "Ollama"
    OPENAI = "OpenAI"
    OPENAI_AZURE = "OpenAI Azure"
    OPENROUTER = "OpenRouter"
    SAMBANOVA = "Sambanova"
    OTHER = "Other"


class BaseModelProvider(ABC):
    """Base class for all model providers"""

    @abstractmethod
    def get_chat_model(self, model_name: str, **kwargs):
        """Get a chat model instance"""
        pass

    @abstractmethod
    def get_embedding_model(self, model_name: str, **kwargs):
        """Get an embedding model instance"""
        pass

    @abstractmethod
    def get_api_key(self) -> str:
        """Get the API key for this provider"""
        pass


def parse_chunk(chunk: Any) -> str:
    """Parse a chunk from any model provider into a string"""
    if isinstance(chunk, str):
        content = chunk
    elif hasattr(chunk, "content"):
        content = str(chunk.content)
    else:
        content = str(chunk)
    
    # Removed debug logging - HTML entity issue traced and handled in extract_tools.py
    return content
