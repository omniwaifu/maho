"""
Configuration and initialization logic for Agent Zero.
This replaces the old initialize.py file.
"""

from src.core.models import AgentConfig, ModelConfig
from src.providers.base import ModelProvider
from src.helpers import runtime, settings, defer
from src.helpers.print_style import PrintStyle


def initialize_agent():
    """Initialize agent configuration from user settings"""
    current_settings = settings.get_settings()

    # chat model from user settings
    chat_llm = ModelConfig(
        provider=ModelProvider[current_settings["chat_model_provider"]],
        name=current_settings["chat_model_name"],
        ctx_length=current_settings["chat_model_ctx_length"],
        vision=current_settings["chat_model_vision"],
        limit_requests=current_settings["chat_model_rl_requests"],
        limit_input=current_settings["chat_model_rl_input"],
        limit_output=current_settings["chat_model_rl_output"],
        kwargs=current_settings["chat_model_kwargs"],
    )

    # utility model from user settings
    utility_llm = ModelConfig(
        provider=ModelProvider[current_settings["util_model_provider"]],
        name=current_settings["util_model_name"],
        ctx_length=current_settings["util_model_ctx_length"],
        limit_requests=current_settings["util_model_rl_requests"],
        limit_input=current_settings["util_model_rl_input"],
        limit_output=current_settings["util_model_rl_output"],
        kwargs=current_settings["util_model_kwargs"],
    )
    
    # embedding model from user settings
    embedding_llm = ModelConfig(
        provider=ModelProvider[current_settings["embed_model_provider"]],
        name=current_settings["embed_model_name"],
        limit_requests=current_settings["embed_model_rl_requests"],
        kwargs=current_settings["embed_model_kwargs"],
    )
    
    # browser model from user settings
    browser_llm = ModelConfig(
        provider=ModelProvider[current_settings["browser_model_provider"]],
        name=current_settings["browser_model_name"],
        vision=current_settings["browser_model_vision"],
        kwargs=current_settings["browser_model_kwargs"],
    )
    
    # agent configuration
    config = AgentConfig(
        chat_model=chat_llm,
        utility_model=utility_llm,
        embeddings_model=embedding_llm,
        browser_model=browser_llm,
        prompts_subdir=current_settings["agent_prompts_subdir"],
        memory_subdir=current_settings["agent_memory_subdir"],
        knowledge_subdirs=["default", current_settings["agent_knowledge_subdir"]],
        mcp_servers=current_settings["mcp_servers"],
        code_exec_docker_enabled=False,
    )

    # update SSH and docker settings
    _set_runtime_config(config, current_settings)

    # update config with runtime args
    _args_override(config)

    return config


def initialize_chats():
    """Initialize chat persistence in background"""
    from src.helpers import persist_chat
    
    async def initialize_chats_async():
        persist_chat.load_tmp_chats()
    
    return defer.DeferredTask().start_task(initialize_chats_async)


def initialize_mcp():
    """Initialize MCP (Model Context Protocol) in background"""
    set = settings.get_settings()
    
    async def initialize_mcp_async():
        from src.helpers.mcp_handler import initialize_mcp as _initialize_mcp
        return _initialize_mcp(set["mcp_servers"])
    
    return defer.DeferredTask().start_task(initialize_mcp_async)


def initialize_job_loop():
    """Initialize the background job loop"""
    from src.helpers.job_loop import run_loop
    return defer.DeferredTask("JobLoop").start_task(run_loop)


def _args_override(config):
    """Update config with runtime arguments"""
    for key, value in runtime.args.items():
        if hasattr(config, key):
            # conversion based on type of config[key]
            if isinstance(getattr(config, key), bool):
                value = value.lower().strip() == "true"
            elif isinstance(getattr(config, key), int):
                value = int(value)
            elif isinstance(getattr(config, key), float):
                value = float(value)
            elif isinstance(getattr(config, key), str):
                value = str(value)
            else:
                raise Exception(
                    f"Unsupported argument type of '{key}': {type(getattr(config, key))}"
                )

            setattr(config, key, value)


def _set_runtime_config(config: AgentConfig, set: settings.Settings):
    """Set runtime configuration from settings"""
    ssh_conf = settings.get_runtime_config(set)
    for key, value in ssh_conf.items():
        if hasattr(config, key):
            setattr(config, key, value) 