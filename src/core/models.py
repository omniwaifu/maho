from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict
from enum import Enum
from collections import OrderedDict

from src.helpers import files, history
from src.providers.base import ModelProvider


class AgentContextType(Enum):
    USER = "user"
    TASK = "task"
    MCP = "mcp"


@dataclass
class ModelConfig:
    provider: ModelProvider
    name: str
    ctx_length: int = 0
    limit_requests: int = 0
    limit_input: int = 0
    limit_output: int = 0
    vision: bool = False
    kwargs: dict = field(default_factory=dict)


@dataclass
class AgentConfig:
    chat_model: ModelConfig
    utility_model: ModelConfig
    embeddings_model: ModelConfig
    browser_model: ModelConfig
    mcp_servers: str
    prompts_subdir: str = ""
    memory_subdir: str = ""
    knowledge_subdirs: list[str] = field(default_factory=lambda: ["default", "custom"])
    code_exec_docker_enabled: bool = False
    code_exec_docker_name: str = "maho-dev"
    code_exec_docker_image: str = "maho:latest"
    code_exec_docker_ports: dict[str, int] = field(
        default_factory=lambda: {"22/tcp": 55022, "80/tcp": 55080}
    )
    code_exec_docker_volumes: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            files.get_base_dir(): {"bind": "/maho", "mode": "rw"},
            files.get_abs_path("work_dir"): {"bind": "/root", "mode": "rw"},
        }
    )
    code_exec_ssh_enabled: bool = False
    code_exec_ssh_addr: str = "localhost"
    code_exec_ssh_port: int = 55022
    code_exec_ssh_user: str = "root"
    code_exec_ssh_pass: str = ""
    additional: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserMessage:
    message: str
    attachments: list[str] = field(default_factory=list[str])
    system_message: list[str] = field(default_factory=list[str])


class LoopData:
    def __init__(self, **kwargs):
        self.iteration = -1
        self.system = []
        self.user_message: history.Message | None = None
        self.history_output: list[history.OutputMessage] = []
        self.extras_temporary: OrderedDict[str, history.MessageContent] = OrderedDict()
        self.extras_persistent: OrderedDict[str, history.MessageContent] = OrderedDict()
        self.last_response = ""

        # override values with kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


# Exception classes
class InterventionException(Exception):
    """Intervention exception class - skips rest of message loop iteration"""

    pass


class RepairableException(Exception):
    """Killer exception class - not forwarded to LLM, cannot be fixed on its own, ends message loop"""

    pass


class HandledException(Exception):
    pass
