import base64
import hashlib
import json
import os
import re
import subprocess
from typing import Any, Literal, Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict

from src import models
from src.helpers import runtime, whisper
from . import files, dotenv
from src.helpers.print_style import PrintStyle
from anyio.from_thread import start_blocking_portal


class Settings(BaseModel):
    """Main settings configuration using Pydantic for validation and type safety"""
    model_config = ConfigDict(extra='forbid')
    
    # Chat model settings
    chat_model_provider: str = "OPENAI"
    chat_model_name: str = "gpt-4"
    chat_model_kwargs: Dict[str, str] = Field(default_factory=dict)
    chat_model_ctx_length: int = 100000
    chat_model_ctx_history: float = 0.7
    chat_model_vision: bool = True
    chat_model_rl_requests: int = 0
    chat_model_rl_input: int = 0
    chat_model_rl_output: int = 0

    # Utility model settings
    util_model_provider: str = "OPENAI"
    util_model_name: str = "gpt-4-mini"
    util_model_kwargs: Dict[str, str] = Field(default_factory=dict)
    util_model_ctx_length: int = 100000
    util_model_ctx_input: float = 0.7
    util_model_rl_requests: int = 0
    util_model_rl_input: int = 0
    util_model_rl_output: int = 0

    # Embedding model settings
    embed_model_provider: str = "HUGGINGFACE"
    embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embed_model_kwargs: Dict[str, str] = Field(default_factory=dict)
    embed_model_rl_requests: int = 0
    embed_model_rl_input: int = 0

    # Browser model settings
    browser_model_provider: str = "OPENAI"
    browser_model_name: str = "gpt-4"
    browser_model_vision: bool = True
    browser_model_kwargs: Dict[str, str] = Field(default_factory=dict)

    # Agent settings
    agent_prompts_subdir: str = "default"
    agent_memory_subdir: str = "default"
    agent_knowledge_subdir: str = "custom"

    # API keys
    api_keys: Dict[str, str] = Field(default_factory=dict)

    # Authentication
    auth_login: str = ""
    auth_password: str = ""
    root_password: str = ""

    # RFC settings
    rfc_auto_docker: bool = True
    rfc_url: str = "localhost"
    rfc_password: str = ""
    rfc_port_http: int = 55080
    rfc_port_ssh: int = 55022

    # Speech-to-text settings
    stt_model_size: str = "base"
    stt_language: str = "en"
    stt_silence_threshold: float = 0.3
    stt_silence_duration: int = 1000
    stt_waiting_timeout: int = 2000

    # MCP settings
    mcp_servers: str = '{\n    "mcpServers": {}\n}'
    mcp_client_init_timeout: int = 5
    mcp_client_tool_timeout: int = 120
    mcp_server_enabled: bool = False
    mcp_server_token: str = ""

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access for backwards compatibility"""
        return getattr(self, key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-style assignment for backwards compatibility"""
        setattr(self, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Allow dict-style .get() for backwards compatibility"""
        return getattr(self, key, default)
    
    def copy(self) -> "Settings":
        """Return a copy of the settings"""
        return self.model_copy()


class FieldOption(BaseModel):
    """Field option for select fields"""
    value: str
    label: str


class SettingsField(BaseModel):
    """Settings field definition"""
    model_config = ConfigDict(extra='forbid')
    
    id: str
    title: str
    description: str = ""
    type: Literal[
        "text", "number", "select", "range", "textarea", "password", "switch", "button"
    ]
    value: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    hidden: bool = False
    options: List[FieldOption] = Field(default_factory=list)


class SettingsSection(BaseModel):
    """Settings section definition"""
    model_config = ConfigDict(extra='forbid')
    
    id: str
    title: str
    description: str = ""
    fields: List[SettingsField]
    tab: str = "agent"


class SettingsOutput(BaseModel):
    """Settings output structure"""
    sections: List[SettingsSection]


PASSWORD_PLACEHOLDER = "****PSWD****"

SETTINGS_FILE = files.get_abs_path("tmp/settings.json")
_settings: Settings | None = None

# Module-level portal for settings background tasks
_settings_portal_cm = None
_settings_portal = None

# Flag to prevent Docker message spam
_docker_message_shown = False


def _get_settings_portal():
    """Get or create the settings portal"""
    global _settings_portal_cm, _settings_portal
    if _settings_portal is None:
        _settings_portal_cm = start_blocking_portal(backend="asyncio")
        _settings_portal = _settings_portal_cm.__enter__()
    return _settings_portal


def _create_field(**kwargs) -> SettingsField:
    """Helper to create SettingsField with proper types"""
    if 'options' in kwargs and isinstance(kwargs['options'], list):
        kwargs['options'] = [
            FieldOption(value=opt['value'], label=opt['label']) 
            if isinstance(opt, dict) else opt 
            for opt in kwargs['options']
        ]
    return SettingsField(**kwargs)

def _create_section(**kwargs) -> SettingsSection:
    """Helper to create SettingsSection with proper types"""
    return SettingsSection(**kwargs)

def _get_available_agent_types() -> list[dict[str, str]]:
    """Discover available agent types by scanning the prompts/agents directory"""
    agents_dir = os.path.join("prompts", "agents")
    if not os.path.exists(agents_dir):
        return [{"value": "default", "label": "Default - General purpose agent"}]
    
    # Predefined descriptions for known agent types
    agent_descriptions = {
        "default": "General purpose agent",
        "hacker": "Cybersecurity focused agent", 
        "research": "Research and analysis focused agent",
        "engineer": "Software development focused agent"
    }
    
    options = []
    for item in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, item)
        # Check if it's a directory and has a system.j2 file
        if os.path.isdir(agent_path) and os.path.exists(os.path.join(agent_path, "system.j2")):
            # Use predefined description if available, otherwise generate one
            description = agent_descriptions.get(item, f"{item.title()} agent")
            options.append({
                "value": item,
                "label": f"{item.title()} - {description}"
            })
    
    # Ensure default is always first if it exists
    options.sort(key=lambda x: (x["value"] != "default", x["value"]))
    return options

def convert_out(settings: Settings) -> SettingsOutput:
    from src.models import ModelProvider

    # main model section
    chat_model_fields: list[SettingsField] = []
    chat_model_fields.append(
        SettingsField(
            id="chat_model_provider",
            title="Chat model provider",
            description="Select provider for main chat model used by Maho",
            type="select",
            value=settings["chat_model_provider"],
            options=[FieldOption(value=p.name, label=p.value) for p in ModelProvider],
        )
    )
    chat_model_fields.append(
        _create_field(
            id="chat_model_name",
            title="Chat model name",
            description="Exact name of model from selected provider",
            type="text",
            value=settings["chat_model_name"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_ctx_length",
            title="Chat model context length",
            description="Maximum number of tokens in the context window for LLM. System prompt, chat history, RAG and response all count towards this limit.",
            type="number",
            value=settings["chat_model_ctx_length"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_ctx_history",
            title="Context window space for chat history",
            description="Portion of context window dedicated to chat history visible to the agent. Chat history will automatically be optimized to fit. Smaller size will result in shorter and more summarized history. The remaining space will be used for system prompt, RAG and response.",
            type="range",
            min=0.01,
            max=1,
            step=0.01,
            value=settings["chat_model_ctx_history"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_vision",
            title="Supports Vision",
            description="Models capable of Vision can for example natively see the content of image attachments.",
            type="switch",
            value=settings["chat_model_vision"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_rl_requests",
            title="Requests per minute limit",
            description="Limits the number of requests per minute to the chat model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["chat_model_rl_requests"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_rl_input",
            title="Input tokens per minute limit",
            description="Limits the number of input tokens per minute to the chat model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["chat_model_rl_input"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_rl_output",
            title="Output tokens per minute limit",
            description="Limits the number of output tokens per minute to the chat model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["chat_model_rl_output"],
        )
    )

    chat_model_fields.append(
        _create_field(
            id="chat_model_kwargs",
            title="Chat model additional parameters",
            description="Any other parameters supported by the model. Format is KEY=VALUE on individual lines, just like .env file.",
            type="textarea",
            value=_dict_to_env(settings["chat_model_kwargs"]),
        )
    )

    chat_model_section = _create_section(
        id="chat_model",
        title="Chat Model",
        description="Selection and settings for main chat model used by Maho",
        fields=chat_model_fields,
        tab="agent",
    )

    # main model section
    util_model_fields: list[SettingsField] = []
    util_model_fields.append(
        _create_field(
            id="util_model_provider",
            title="Utility model provider",
            description="Select provider for utility model used by the framework",
            type="select",
            value=settings["util_model_provider"],
            options=[{"value": p.name, "label": p.value} for p in ModelProvider],
        )
    )
    util_model_fields.append(
        _create_field(
            id="util_model_name",
            title="Utility model name",
            description="Exact name of model from selected provider",
            type="text",
            value=settings["util_model_name"],
        )
    )

    util_model_fields.append(
        _create_field(
            id="util_model_rl_requests",
            title="Requests per minute limit",
            description="Limits the number of requests per minute to the utility model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["util_model_rl_requests"],
        )
    )

    util_model_fields.append(
        _create_field(
            id="util_model_rl_input",
            title="Input tokens per minute limit",
            description="Limits the number of input tokens per minute to the utility model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["util_model_rl_input"],
        )
    )

    util_model_fields.append(
        _create_field(
            id="util_model_rl_output",
            title="Output tokens per minute limit",
            description="Limits the number of output tokens per minute to the utility model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["util_model_rl_output"],
        )
    )

    util_model_fields.append(
        _create_field(
            id="util_model_kwargs",
            title="Utility model additional parameters",
            description="Any other parameters supported by the model. Format is KEY=VALUE on individual lines, just like .env file.",
            type="textarea",
            value=_dict_to_env(settings["util_model_kwargs"]),
        )
    )

    util_model_section = _create_section(
        id="util_model",
        title="Utility model",
        description="Smaller, cheaper, faster model for handling utility tasks like organizing memory, preparing prompts, summarizing.",
        fields=util_model_fields,
        tab="agent",
    )

    # embedding model section
    embed_model_fields: list[SettingsField] = []
    embed_model_fields.append(
        _create_field(
            id="embed_model_provider",
            title="Embedding model provider",
            description="Select provider for embedding model used by the framework",
            type="select",
            value=settings["embed_model_provider"],
            options=[{"value": p.name, "label": p.value} for p in ModelProvider],
        )
    )
    embed_model_fields.append(
        _create_field(
            id="embed_model_name",
            title="Embedding model name",
            description="Exact name of model from selected provider",
            type="text",
            value=settings["embed_model_name"],
        )
    )

    embed_model_fields.append(
        _create_field(
            id="embed_model_rl_requests",
            title="Requests per minute limit",
            description="Limits the number of requests per minute to the embedding model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["embed_model_rl_requests"],
        )
    )

    embed_model_fields.append(
        _create_field(
            id="embed_model_rl_input",
            title="Input tokens per minute limit",
            description="Limits the number of input tokens per minute to the embedding model. Waits if the limit is exceeded. Set to 0 to disable rate limiting.",
            type="number",
            value=settings["embed_model_rl_input"],
        )
    )

    embed_model_fields.append(
        _create_field(
            id="embed_model_kwargs",
            title="Embedding model additional parameters",
            description="Any other parameters supported by the model. Format is KEY=VALUE on individual lines, just like .env file.",
            type="textarea",
            value=_dict_to_env(settings["embed_model_kwargs"]),
        )
    )

    embed_model_section = _create_section(
        id="embed_model",
        title="Embedding Model",
        description="Settings for the embedding model used by Maho.",
        fields=embed_model_fields,
        tab="agent",
    )

    # browser model section
    browser_model_fields: list[SettingsField] = []
    browser_model_fields.append(
        _create_field(
            id="browser_model_provider",
            title="Web Browser model provider",
            description="Select provider for web browser model used by <a href='https://github.com/browser-use/browser-use' target='_blank'>browser-use</a> framework",
            type="select",
            value=settings["browser_model_provider"],
            options=[{"value": p.name, "label": p.value} for p in ModelProvider],
        )
    )
    browser_model_fields.append(
        _create_field(
            id="browser_model_name",
            title="Web Browser model name",
            description="Exact name of model from selected provider",
            type="text",
            value=settings["browser_model_name"],
        )
    )

    browser_model_fields.append(
        _create_field(
            id="browser_model_vision",
            title="Use Vision",
            description="Models capable of Vision can use it to analyze web pages from screenshots. Increases quality but also token usage.",
            type="switch",
            value=settings["browser_model_vision"],
        )
    )

    browser_model_fields.append(
        _create_field(
            id="browser_model_kwargs",
            title="Web Browser model additional parameters",
            description="Any other parameters supported by the model. Format is KEY=VALUE on individual lines, just like .env file.",
            type="textarea",
            value=_dict_to_env(settings["browser_model_kwargs"]),
        )
    )

    browser_model_section = _create_section(
        id="browser_model",
        title="Web Browser Model",
        description="Settings for the web browser model. Maho uses <a href='https://github.com/browser-use/browser-use' target='_blank'>browser-use</a> agentic framework to handle web interactions.",
        fields=browser_model_fields,
        tab="agent",
    )

    # # Memory settings section
    # memory_fields: list[SettingsField] = []
    # memory_fields.append(
    #     {
    #         "id": "memory_settings",
    #         "title": "Memory Settings",
    #         "description": "<settings for memory>",
    #         "type": "text",
    #         "value": "",
    #     }
    # )

    # memory_section: SettingsSection = {
    #     "id": "memory",
    #     "title": "Memory Settings",
    #     "description": "<settings for memory management here>",
    #     "fields": memory_fields,
    # }

    # basic auth section
    auth_fields: list[SettingsField] = []

    auth_fields.append(
        _create_field(
            id="auth_login",
            title="UI Login",
            description="Set user name for web UI",
            type="text",
            value=dotenv.get_dotenv_value(dotenv.KEY_AUTH_LOGIN) or "",
        )
    )

    auth_fields.append(
        _create_field(
            id="auth_password",
            title="UI Password",
            description="Set user password for web UI",
            type="password",
            value=(
                PASSWORD_PLACEHOLDER
                if dotenv.get_dotenv_value(dotenv.KEY_AUTH_PASSWORD)
                else ""
            ),
        )
    )

    if runtime.is_dockerized():
        auth_fields.append(
            _create_field(
                id="root_password",
                title="root Password",
                description="Change linux root password in docker container. This password can be used for SSH access. Original password was randomly generated during setup.",
                type="password",
                value="",
            )
        )

    auth_section = _create_section(
        id="auth",
        title="Authentication",
        description="Settings for authentication to use Maho Web UI.",
        fields=auth_fields,
        tab="external",
    )

    # api keys model section
    api_keys_fields: list[SettingsField] = []
    api_keys_fields.append(_get_api_key_field(settings, "openai", "OpenAI API Key"))
    api_keys_fields.append(
        _get_api_key_field(settings, "anthropic", "Anthropic API Key")
    )
    api_keys_fields.append(_get_api_key_field(settings, "chutes", "Chutes API Key"))
    api_keys_fields.append(_get_api_key_field(settings, "deepseek", "DeepSeek API Key"))
    api_keys_fields.append(_get_api_key_field(settings, "google", "Google API Key"))
    api_keys_fields.append(_get_api_key_field(settings, "groq", "Groq API Key"))
    api_keys_fields.append(
        _get_api_key_field(settings, "huggingface", "HuggingFace API Key")
    )
    api_keys_fields.append(_get_api_key_field(settings, "iointel", "IOIntel API Key"))
    api_keys_fields.append(
        _get_api_key_field(settings, "mistralai", "MistralAI API Key")
    )
    api_keys_fields.append(
        _get_api_key_field(settings, "openrouter", "OpenRouter API Key")
    )
    api_keys_fields.append(
        _get_api_key_field(settings, "sambanova", "Sambanova API Key")
    )

    api_keys_section = _create_section(
        id="api_keys",
        title="API Keys",
        description="API keys for model providers and services used by Maho.",
        fields=api_keys_fields,
        tab="external",
    )

    # Agent config section
    agent_fields: list[SettingsField] = []

    agent_fields.append(
        _create_field(
            id="agent_prompts_subdir",
            title="Agent Type",
            description="Choose the agent personality/behavior type. Each agent type has specialized prompts and capabilities.",
            type="select",
            value=settings["agent_prompts_subdir"],
            options=_get_available_agent_types(),
        )
    )

    agent_fields.append(
        _create_field(
            id="agent_memory_subdir",
            title="Memory Subdirectory",
            description="Subdirectory of /memory folder to use for agent memory storage. Used to separate memory storage between different instances.",
            type="text",
            value=settings["agent_memory_subdir"],
            # "options": [
            #     {"value": subdir, "label": subdir}
            #     for subdir in files.get_subdirectories("memory", exclude="embeddings")
            # ],
        )
    )

    agent_fields.append(
        _create_field(
            id="agent_knowledge_subdir",
            title="Knowledge subdirectory",
            description="Subdirectory of /knowledge folder to use for agent knowledge import. 'default' subfolder is always imported and contains framework knowledge.",
            type="select",
            value=settings["agent_knowledge_subdir"],
            options=[
                {"value": subdir, "label": subdir}
                for subdir in files.get_subdirectories("knowledge", exclude="default")
            ],
        )
    )

    agent_section = _create_section(
        id="agent",
        title="Agent Config",
        description="Agent parameters.",
        fields=agent_fields,
        tab="agent",
    )

    dev_fields: list[SettingsField] = []

    if runtime.is_development():
        # dev_fields.append(
        #     {
        #         "id": "rfc_auto_docker",
        #         "title": "RFC Auto Docker Management",
        #         "description": "Automatically create dockerized instance of Maho for RFCs using this instance's code base and, settings and .env.",
        #         "type": "text",
        #         "value": settings["rfc_auto_docker"],
        #     }
        # )

        dev_fields.append(
            _create_field(
                id="rfc_url",
                title="RFC Destination URL",
                description="URL of dockerized Maho instance for remote function calls. Do not specify port here.",
                type="text",
                value=settings["rfc_url"],
            )
        )

    dev_fields.append(
        _create_field(
            id="rfc_password",
            title="RFC Password",
            description="Password for remote function calls. Passwords must match on both instances. RFCs can not be used with empty password.",
            type="password",
            value=(
                PASSWORD_PLACEHOLDER
                if dotenv.get_dotenv_value(dotenv.KEY_RFC_PASSWORD)
                else ""
            ),
        )
    )

    if runtime.is_development():
        dev_fields.append(
            _create_field(
                id="rfc_port_http",
                title="RFC HTTP port",
                description="HTTP port for dockerized instance of Maho.",
                type="text",
                value=settings["rfc_port_http"],
            )
        )

        dev_fields.append(
            _create_field(
                id="rfc_port_ssh",
                title="RFC SSH port",
                description="SSH port for dockerized instance of Maho.",
                type="text",
                value=settings["rfc_port_ssh"],
            )
        )

    dev_section = _create_section(
        id="dev",
        title="Development",
        description="Parameters for Maho framework development. RFCs (remote function calls) are used to call functions on another Maho instance. You can develop and debug Maho natively on your local system while redirecting some functions to Maho instance in docker. This is crucial for development as Maho needs to run in standardized environment to support all features.",
        fields=dev_fields,
        tab="developer",
    )

    # Speech to text section
    stt_fields: list[SettingsField] = []

    stt_fields.append(
        _create_field(
            id="stt_model_size",
            title="Model Size",
            description="Select the speech recognition model size",
            type="select",
            value=settings["stt_model_size"],
            options=[
                {"value": "tiny", "label": "Tiny (39M, English)"},
                {"value": "base", "label": "Base (74M, English)"},
                {"value": "small", "label": "Small (244M, English)"},
                {"value": "medium", "label": "Medium (769M, English)"},
                {"value": "large", "label": "Large (1.5B, Multilingual)"},
                {"value": "turbo", "label": "Turbo (Multilingual)"},
            ],
        )
    )

    stt_fields.append(
        _create_field(
            id="stt_language",
            title="Language Code",
            description="Language code (e.g. en, fr, it)",
            type="text",
            value=settings["stt_language"],
        )
    )

    stt_fields.append(
        _create_field(
            id="stt_silence_threshold",
            title="Silence threshold",
            description="Silence detection threshold. Lower values are more sensitive.",
            type="range",
            min=0,
            max=1,
            step=0.01,
            value=settings["stt_silence_threshold"],
        )
    )

    stt_fields.append(
        _create_field(
            id="stt_silence_duration",
            title="Silence duration (ms)",
            description="Duration of silence before the server considers speaking to have ended.",
            type="text",
            value=settings["stt_silence_duration"],
        )
    )

    stt_fields.append(
        _create_field(
            id="stt_waiting_timeout",
            title="Waiting timeout (ms)",
            description="Duration before the server closes the microphone.",
            type="text",
            value=settings["stt_waiting_timeout"],
        )
    )

    stt_section = _create_section(
        id="stt",
        title="Speech to Text",
        description="Voice transcription preferences and server turn detection settings.",
        fields=stt_fields,
        tab="agent",
    )

    # MCP section
    mcp_client_fields: list[SettingsField] = []

    mcp_client_fields.append(
        _create_field(
            id="mcp_servers_config",
            title="MCP Servers Configuration",
            description="External MCP servers can be configured here.",
            type="button",
            value="Open",
        )
    )

    mcp_client_fields.append(
        _create_field(
            id="mcp_servers",
            title="MCP Servers",
            description="(JSON list of) >> RemoteServer <<: [name, url, headers, timeout (opt), sse_read_timeout (opt), disabled (opt)] / >> Local Server <<: [name, command, args, env, encoding (opt), encoding_error_handler (opt), disabled (opt)]",
            type="textarea",
            value=settings["mcp_servers"],
            hidden=True,
        )
    )

    mcp_client_fields.append(
        _create_field(
            id="mcp_client_init_timeout",
            title="MCP Client Init Timeout",
            description="Timeout for MCP client initialization (in seconds). Higher values might be required for complex MCPs, but might also slowdown system startup.",
            type="number",
            value=settings["mcp_client_init_timeout"],
        )
    )

    mcp_client_fields.append(
        _create_field(
            id="mcp_client_tool_timeout",
            title="MCP Client Tool Timeout",
            description="Timeout for MCP client tool execution. Higher values might be required for complex tools, but might also result in long responses with failing tools.",
            type="number",
            value=settings["mcp_client_tool_timeout"],
        )
    )

    mcp_client_section = _create_section(
        id="mcp_client",
        title="External MCP Servers",
        description="Maho can use external MCP servers, local or remote as tools.",
        fields=mcp_client_fields,
        tab="mcp",
    )

    mcp_server_fields: list[SettingsField] = []

    mcp_server_fields.append(
        _create_field(
            id="mcp_server_enabled",
            title="Enable Maho MCP Server",
            description="Expose Maho as an SSE MCP server. This will make this Maho instance available to MCP clients.",
            type="switch",
            value=settings["mcp_server_enabled"],
        )
    )

    mcp_server_fields.append(
        _create_field(
            id="mcp_server_token",
            title="MCP Server Token",
            description="Token for MCP server authentication.",
            type="text",
            hidden=True,
            value=settings["mcp_server_token"],
        )
    )

    mcp_server_section = _create_section(
        id="mcp_server",
        title="Maho MCP Server",
        description="Maho can be exposed as an SSE MCP server. See <a href=\"javascript:openModal('settings/mcp/server/example.html')\">connection example</a>.",
        fields=mcp_server_fields,
        tab="mcp",
    )

    # Add the section to the result
    return SettingsOutput(
        sections=[
            agent_section,
            chat_model_section,
            util_model_section,
            embed_model_section,
            browser_model_section,
            # memory_section,
            stt_section,
            api_keys_section,
            auth_section,
            mcp_client_section,
            mcp_server_section,
            dev_section,
        ]
    )


def _get_api_key_field(settings: Settings, provider: str, title: str) -> SettingsField:
    key = settings["api_keys"].get(provider, models.get_api_key(provider))
    return _create_field(
        id=f"api_key_{provider}",
        title=title,
        type="password",
        value=(PASSWORD_PLACEHOLDER if key and key != "None" else ""),
    )


def convert_in(settings: dict) -> Settings:
    current = get_settings()
    current_dict = current.model_dump()  # Convert to dict for easier manipulation
    
    for section in settings["sections"]:
        if "fields" in section:
            for field in section["fields"]:
                # Skip fields without an id (like button fields)
                if "id" not in field:
                    continue
                if field["value"] != PASSWORD_PLACEHOLDER:
                    if field["id"].endswith("_kwargs"):
                        current_dict[field["id"]] = _env_to_dict(field["value"])
                    elif field["id"].startswith("api_key_"):
                        current_dict["api_keys"][field["id"]] = field["value"]
                    else:
                        current_dict[field["id"]] = field["value"]
    
    # Create new Settings instance from the modified dict
    return Settings(**current_dict)


def get_settings() -> Settings:
    global _settings
    if not _settings:
        _settings = _read_settings_file()
    if not _settings:
        _settings = get_default_settings()
    norm = normalize_settings(_settings)
    return norm


def set_settings(settings: Settings, apply: bool = True):
    global _settings
    previous = _settings
    _settings = normalize_settings(settings)
    _write_settings_file(_settings)
    if apply:
        _apply_settings(previous)


def set_settings_delta(delta: dict, apply: bool = True):
    current = get_settings()
    current_dict = current.model_dump()
    new_dict = {**current_dict, **delta}
    new_settings = Settings(**new_dict)
    set_settings(new_settings, apply)


def normalize_settings(settings: Settings | dict) -> Settings:
    # Handle both Settings objects and dicts for backwards compatibility
    if isinstance(settings, dict):
        settings_dict = settings
    else:
        settings_dict = settings.model_dump()
    
    default_dict = get_default_settings().model_dump()

    # remove keys that are not in default
    keys_to_remove = [key for key in settings_dict if key not in default_dict]
    for key in keys_to_remove:
        del settings_dict[key]

    # add missing keys and normalize types
    for key, value in default_dict.items():
        if key not in settings_dict:
            settings_dict[key] = value
        else:
            try:
                settings_dict[key] = type(value)(settings_dict[key])  # type: ignore
            except (ValueError, TypeError):
                settings_dict[key] = value  # make default instead

    # mcp server token is set automatically
    settings_dict["mcp_server_token"] = create_auth_token()

    return Settings(**settings_dict)


def _read_settings_file() -> Settings | None:
    if os.path.exists(SETTINGS_FILE):
        content = files.read_file(SETTINGS_FILE)
        parsed = json.loads(content)
        # Convert dict to Settings object, then normalize
        try:
            settings_obj = Settings(**parsed)
            return normalize_settings(settings_obj)
        except Exception:
            # If conversion fails, use defaults
            return None


def _write_settings_file(settings: Settings):
    _write_sensitive_settings(settings)
    
    # Create a copy for writing (so we don't modify the original)
    settings_copy = settings.model_copy()
    _remove_sensitive_settings(settings_copy)

    # write settings
    content = json.dumps(settings_copy.model_dump(), indent=4)
    files.write_file(SETTINGS_FILE, content)


def _remove_sensitive_settings(settings: Settings):
    settings["api_keys"] = {}
    settings["auth_login"] = ""
    settings["auth_password"] = ""
    settings["rfc_password"] = ""
    settings["root_password"] = ""
    settings["mcp_server_token"] = ""


def _write_sensitive_settings(settings: Settings):
    for key, val in settings["api_keys"].items():
        dotenv.save_dotenv_value(key.upper(), val)

    dotenv.save_dotenv_value(dotenv.KEY_AUTH_LOGIN, settings["auth_login"])
    if settings["auth_password"]:
        dotenv.save_dotenv_value(dotenv.KEY_AUTH_PASSWORD, settings["auth_password"])
    if settings["rfc_password"]:
        dotenv.save_dotenv_value(dotenv.KEY_RFC_PASSWORD, settings["rfc_password"])

    if settings["root_password"]:
        dotenv.save_dotenv_value(dotenv.KEY_ROOT_PASSWORD, settings["root_password"])
    if settings["root_password"]:
        set_root_password(settings["root_password"])


def get_default_settings() -> Settings:
    from src.models import ModelProvider

    return Settings(
        chat_model_provider=ModelProvider.OPENAI.name,
        chat_model_name="gpt-4.1",
        chat_model_kwargs={"temperature": "0"},
        chat_model_ctx_length=100000,
        chat_model_ctx_history=0.7,
        chat_model_vision=True,
        chat_model_rl_requests=0,
        chat_model_rl_input=0,
        chat_model_rl_output=0,
        util_model_provider=ModelProvider.OPENAI.name,
        util_model_name="gpt-4.1-nano",
        util_model_ctx_length=100000,
        util_model_ctx_input=0.7,
        util_model_kwargs={"temperature": "0"},
        util_model_rl_requests=0,
        util_model_rl_input=0,
        util_model_rl_output=0,
        embed_model_provider=ModelProvider.HUGGINGFACE.name,
        embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embed_model_kwargs={},
        embed_model_rl_requests=0,
        embed_model_rl_input=0,
        browser_model_provider=ModelProvider.OPENAI.name,
        browser_model_name="gpt-4.1",
        browser_model_vision=True,
        browser_model_kwargs={"temperature": "0"},
        api_keys={},
        auth_login="",
        auth_password="",
        root_password="",
        agent_prompts_subdir="default",
        agent_memory_subdir="default",
        agent_knowledge_subdir="custom",
        rfc_auto_docker=True,
        rfc_url="localhost",
        rfc_password="",
        rfc_port_http=55080,
        rfc_port_ssh=55022,
        stt_model_size="base",
        stt_language="en",
        stt_silence_threshold=0.3,
        stt_silence_duration=1000,
        stt_waiting_timeout=2000,
        mcp_servers='{\n    "mcpServers": {}\n}',
        mcp_client_init_timeout=5,
        mcp_client_tool_timeout=120,
        mcp_server_enabled=False,
        mcp_server_token=create_auth_token(),
    )


def _apply_settings(previous: Settings | None):
    global _settings
    if _settings:
        from src.core.context import AgentContext
        from src.config.initialization import initialize_agent

        config = initialize_agent()
        for ctx in AgentContext._contexts.values():
            ctx.config = config  # reinitialize context config with new settings
            # apply config to agents
            agent = ctx.agent0
            while agent:
                agent.config = ctx.config
                agent = agent.get_data(agent.DATA_NAME_SUBORDINATE)

        # reload whisper model if necessary
        if not previous or _settings["stt_model_size"] != previous["stt_model_size"]:
            # Use AnyIO portal for background whisper preload
            portal = _get_settings_portal()
            portal.start_task_soon(whisper.preload, _settings["stt_model_size"])

        # force memory reload on embedding model change
        if not previous or (
            _settings["embed_model_name"] != previous["embed_model_name"]
            or _settings["embed_model_provider"] != previous["embed_model_provider"]
            or _settings["embed_model_kwargs"] != previous["embed_model_kwargs"]
        ):
            from src.helpers.memory import reload as memory_reload

            memory_reload()

        # update mcp settings if necessary
        if not previous or _settings["mcp_servers"] != previous["mcp_servers"]:
            from src.helpers.mcp_handler import MCPConfig

            async def update_mcp_settings(mcp_servers: str):
                PrintStyle(
                    background_color="black", font_color="white", padding=True
                ).print("Updating MCP config...")
                AgentContext.log_to_all(
                    type="info", content="Updating MCP settings...", temp=True
                )

                mcp_config = MCPConfig.get_instance()
                try:
                    MCPConfig.update(mcp_servers)
                except Exception as e:
                    AgentContext.log_to_all(
                        type="error",
                        content=f"Failed to update MCP settings: {e}",
                        temp=False,
                    )
                    (
                        PrintStyle(
                            background_color="red", font_color="black", padding=True
                        ).print("Failed to update MCP settings")
                    )
                    (
                        PrintStyle(
                            background_color="black", font_color="red", padding=True
                        ).print(f"{e}")
                    )

                PrintStyle(
                    background_color="#6734C3", font_color="white", padding=True
                ).print("Parsed MCP config:")
                (
                    PrintStyle(
                        background_color="#334455", font_color="white", padding=False
                    ).print(mcp_config.model_dump_json())
                )
                AgentContext.log_to_all(
                    type="info", content="Finished updating MCP settings.", temp=True
                )

            # Use AnyIO portal for background MCP settings update
            portal = _get_settings_portal()
            portal.start_task_soon(update_mcp_settings, config.mcp_servers)

        # update token in mcp server
        current_token = (
            create_auth_token()
        )  # TODO - ugly, token in settings is generated from dotenv and does not always correspond
        if not previous or current_token != previous["mcp_server_token"]:

            async def update_mcp_token(token: str):
                from src.helpers.mcp_server import DynamicMcpProxy

                DynamicMcpProxy.get_instance().reconfigure(token=token)

            # Use AnyIO portal for background MCP token update
            portal = _get_settings_portal()
            portal.start_task_soon(update_mcp_token, current_token)


def _env_to_dict(data: str):
    env_dict = {}
    line_pattern = re.compile(r"\s*([^#][^=]*)\s*=\s*(.*)")
    for line in data.splitlines():
        match = line_pattern.match(line)
        if match:
            key, value = match.groups()
            # Remove optional surrounding quotes (single or double)
            value = value.strip().strip('"').strip("'")
            env_dict[key.strip()] = value
    return env_dict


def _dict_to_env(data_dict):
    lines = []
    for key, value in data_dict.items():
        if "\n" in value:
            value = f"'{value}'"
        elif " " in value or value == "" or any(c in value for c in "\"'"):
            value = f'"{value}"'
        lines.append(f"{key}={value}")
    return "\n".join(lines)


def set_root_password(password: str):
    if not runtime.is_dockerized():
        raise Exception("root password can only be set in dockerized environments")
    subprocess.run(f"echo 'root:{password}' | chpasswd", shell=True, check=True)
    dotenv.save_dotenv_value(dotenv.KEY_ROOT_PASSWORD, password)


def get_runtime_config(set: Settings):
    if runtime.is_dockerized():
        return {
            "code_exec_ssh_addr": "localhost",
            "code_exec_ssh_port": 22,
            "code_exec_http_port": 80,
            "code_exec_ssh_user": "root",
        }
    else:
        host = set["rfc_url"]
        if "//" in host:
            host = host.split("//")[1]
        if ":" in host:
            host, port = host.split(":")
        if host.endswith("/"):
            host = host[:-1]
        return {
            "code_exec_ssh_addr": host,
            "code_exec_ssh_port": set["rfc_port_ssh"],
            "code_exec_http_port": set["rfc_port_http"],
            "code_exec_ssh_user": "root",
        }


def create_auth_token() -> str:
    username = dotenv.get_dotenv_value(dotenv.KEY_AUTH_LOGIN) or ""
    password = dotenv.get_dotenv_value(dotenv.KEY_AUTH_PASSWORD) or ""
    if not username or not password:
        return "0"
    # use base64 encoding for a more compact token with alphanumeric chars
    hash_bytes = hashlib.sha256(f"{username}:{password}".encode()).digest()
    # encode as base64 and remove any non-alphanumeric chars (like +, /, =)
    b64_token = base64.urlsafe_b64encode(hash_bytes).decode().replace("=", "")
    return b64_token[:16]
