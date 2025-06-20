"""
Configuration and initialization logic for Maho (forked from Maho).
This replaces the old initialize.py file.
"""

from src.core.models import AgentConfig, ModelConfig
from src.providers.base import ModelProvider
from src.helpers import runtime, settings
from src.helpers.print_style import PrintStyle
from anyio.from_thread import start_blocking_portal
from concurrent.futures import Future

# Module-level portals for background tasks
_init_portal_cm = None
_init_portal = None
_job_loop_portal_cm = None
_job_loop_portal = None

# Flag to prevent spam messages
_ssh_message_shown = False


def _get_init_portal():
    """Get or create the initialization portal"""
    global _init_portal_cm, _init_portal
    if _init_portal is None:
        _init_portal_cm = start_blocking_portal(backend="asyncio")
        _init_portal = _init_portal_cm.__enter__()
    return _init_portal


def _get_job_loop_portal():
    """Get or create the job loop portal"""
    global _job_loop_portal_cm, _job_loop_portal
    if _job_loop_portal is None:
        _job_loop_portal_cm = start_blocking_portal(backend="asyncio")
        _job_loop_portal = _job_loop_portal_cm.__enter__()
    return _job_loop_portal


def initialize_agent():
    """Initialize agent configuration using the existing settings system"""
    global _ssh_message_shown
    
    # Use the existing settings system that user's configuration is in
    set = settings.get_settings()
    runtime_config = settings.get_runtime_config(set)
    
    # Convert to AgentConfig format
    chat_llm = ModelConfig(
        provider=ModelProvider[set["chat_model_provider"]],
        name=set["chat_model_name"],
        ctx_length=set["chat_model_ctx_length"],
        vision=set["chat_model_vision"],
        limit_requests=set["chat_model_rl_requests"],
        limit_input=set["chat_model_rl_input"],
        limit_output=set["chat_model_rl_output"],
        kwargs=set["chat_model_kwargs"],
    )

    utility_llm = ModelConfig(
        provider=ModelProvider[set["util_model_provider"]],
        name=set["util_model_name"],
        ctx_length=set["util_model_ctx_length"],
        limit_requests=set["util_model_rl_requests"],
        limit_input=set["util_model_rl_input"],
        limit_output=set["util_model_rl_output"],
        kwargs=set["util_model_kwargs"],
    )

    embedding_llm = ModelConfig(
        provider=ModelProvider[set["embed_model_provider"]],
        name=set["embed_model_name"],
        limit_requests=set["embed_model_rl_requests"],
        limit_input=set["embed_model_rl_input"],
        kwargs=set["embed_model_kwargs"],
    )

    browser_llm = ModelConfig(
        provider=ModelProvider[set["browser_model_provider"]],
        name=set["browser_model_name"],
        vision=set["browser_model_vision"],
        kwargs=set["browser_model_kwargs"],
    )

    # Determine SSH settings - force local execution when in Docker
    if runtime.is_dockerized():
        ssh_enabled = False
        if not _ssh_message_shown:
            PrintStyle.standard("Docker runtime detected: forcing local code execution")
            _ssh_message_shown = True
    else:
        ssh_enabled = True

    config = AgentConfig(
        chat_model=chat_llm,
        utility_model=utility_llm,
        embeddings_model=embedding_llm,
        browser_model=browser_llm,
        prompts_subdir=set["agent_prompts_subdir"],
        memory_subdir=set["agent_memory_subdir"],
        knowledge_subdirs=[set["agent_knowledge_subdir"]],
        mcp_servers=set["mcp_servers"],
        code_exec_docker_enabled=False,  # Simplified for now
        code_exec_ssh_enabled=ssh_enabled,
        code_exec_ssh_addr=runtime_config["code_exec_ssh_addr"],
        code_exec_ssh_port=runtime_config["code_exec_ssh_port"],
        code_exec_ssh_user=runtime_config["code_exec_ssh_user"],
        code_exec_ssh_pass=set["root_password"],
    )

    if not _ssh_message_shown:
        PrintStyle.standard(f"🔧 Code execution: {'SSH' if config.code_exec_ssh_enabled else 'Local'}")
        _ssh_message_shown = True
    
    return config


def initialize_chats():
    """Initialize chat persistence in background"""
    from src.helpers import persist_chat

    async def initialize_chats_async():
        persist_chat.load_tmp_chats()

    # Use persistent portal and return a Future for compatibility
    portal = _get_init_portal()
    return portal.start_task_soon(initialize_chats_async)


def initialize_mcp():
    """Initialize MCP (Model Context Protocol) in background"""
    set = settings.get_settings()

    async def initialize_mcp_async():
        from src.helpers.mcp_handler import initialize_mcp as _initialize_mcp

        return _initialize_mcp(set["mcp_servers"])

    # Use persistent portal and return a Future for compatibility
    portal = _get_init_portal()
    return portal.start_task_soon(initialize_mcp_async)


def initialize_job_loop():
    """Initialize the background job loop"""
    from src.helpers.job_loop import run_loop

    # JobLoop gets its own dedicated portal since it runs indefinitely
    portal = _get_job_loop_portal()
    return portal.start_task_soon(run_loop)
