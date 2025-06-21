from datetime import datetime, timezone
from typing import Any
import os
from src.helpers.extension import Extension
from src.helpers.mcp_handler import MCPConfig
from src.core.agent import Agent, LoopData
from src.helpers.localization import Localization
from src.helpers.prompt_engine import get_prompt_engine
from src.helpers import runtime


class SystemPrompt(Extension):

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ):
        # Determine agent type based on prompts_subdir
        agent_type = "default"
        if self.agent.config.prompts_subdir:
            # Check if the specified agent type exists as a directory
            engine = get_prompt_engine()
            available_agents = self._get_available_agent_types()
            
            # Use the prompts_subdir directly if it's a valid agent type
            if self.agent.config.prompts_subdir in available_agents:
                agent_type = self.agent.config.prompts_subdir
            else:
                # Fallback: check if any available agent type is mentioned in the subdir
                for available_agent in available_agents:
                    if available_agent in self.agent.config.prompts_subdir:
                        agent_type = available_agent
                        break
        
        # Use new Jinja2 agent templates
        engine = get_prompt_engine()
        
        # Get current datetime
        current_datetime = Localization.get().utc_dt_to_localtime_str(
            datetime.now(timezone.utc), sep=" ", timespec="seconds"
        )
        if current_datetime and "+" in current_datetime:
            current_datetime = current_datetime.split("+")[0]
        
        # Get MCP tools
        mcp_tools = get_mcp_tools_prompt(self.agent)

        # Get local tools
        local_tools = engine.render("components/tools/tools_summary.j2")
        
        # Set environment based on agent type and runtime
        environment = self._get_environment_description(agent_type)
        
        # Template variables
        template_vars = {
            "agent_name": self.agent.agent_name,
            "datetime": current_datetime,
            "environment": environment,
            "tools": local_tools,
            "mcp_tools": mcp_tools if mcp_tools else "",
        }
        
        # Render the agent template
        template_path = f"agents/{agent_type}/system.j2"
        main_prompt = engine.render(template_path, **template_vars)
        system_prompt.append(main_prompt)

    def _get_available_agent_types(self) -> list[str]:
        """Discover available agent types by scanning the prompts/agents directory"""
        agents_dir = os.path.join("prompts", "agents")
        if not os.path.exists(agents_dir):
            return ["default"]
        
        agent_types = []
        for item in os.listdir(agents_dir):
            agent_path = os.path.join(agents_dir, item)
            # Check if it's a directory and has a system.j2 file
            if os.path.isdir(agent_path) and os.path.exists(os.path.join(agent_path, "system.j2")):
                agent_types.append(item)
        
        # Ensure 'default' is always included
        if "default" not in agent_types:
            agent_types.insert(0, "default")
            
        return agent_types

    def _get_environment_description(self, agent_type: str) -> str:
        """Get environment description based on agent type and runtime"""
        # Define environment overrides for specific agent types
        env_overrides = {
            "hacker": {
                "dockerized": "Kali Linux docker container with full root access and penetration testing tools",
                "local": "Local development environment with access to security tools"
            },
            "engineer": {
                "dockerized": "Debian Linux docker container with development tools and full root access",
                "local": "Local development environment with development tools and system access"
            }
        }
        
        # Check if agent type has specific environment override
        if agent_type in env_overrides:
            override = env_overrides[agent_type]
            return override["dockerized"] if runtime.is_dockerized() else override["local"]
        
        # Default environment description
        if runtime.is_dockerized():
            return "Debian Linux docker container with full root access"
        else:
            return "Local development environment with full system access"


def get_mcp_tools_prompt(agent: Agent):
    """Get MCP tools prompt."""
    mcp_config = MCPConfig.get_instance()
    if mcp_config.servers:
        pre_progress = agent.context.log.progress
        agent.context.log.set_progress("Collecting MCP tools")
        tools = MCPConfig.get_instance().get_tools_prompt()
        agent.context.log.set_progress(pre_progress)
        return tools
    return ""
