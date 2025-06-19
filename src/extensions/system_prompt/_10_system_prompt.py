from datetime import datetime, timezone
from typing import Any
from src.helpers.extension import Extension
from src.helpers.mcp_handler import MCPConfig
from src.core.agent import Agent, LoopData
from src.helpers.localization import Localization
from src.helpers.prompt_engine import get_prompt_engine


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
            if "hacker" in self.agent.config.prompts_subdir:
                agent_type = "hacker"
            elif "research" in self.agent.config.prompts_subdir:
                agent_type = "research"
        
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
        
        # Template variables
        template_vars = {
            "agent_name": self.agent.agent_name,
            "datetime": current_datetime,
            "environment": "Kali Linux docker container with full root access",
            "tools": local_tools,
            "mcp_tools": mcp_tools if mcp_tools else "",
        }
        
        # Render the agent template
        template_path = f"agents/{agent_type}/system.j2"
        main_prompt = engine.render(template_path, **template_vars)
        system_prompt.append(main_prompt)


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
