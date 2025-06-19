from src.helpers.extension import Extension
from src.core.models import LoopData


class LogFromStream(Extension):
    """Extension for logging from the agent response stream."""

    async def execute(
        self,
        loop_data: LoopData | None = None,
        text: str = "",
        parsed: dict | None = None,
        **kwargs
    ):
        try:
            # Log the generating process
            if hasattr(self.agent, 'context') and hasattr(self.agent.context, 'log'):
                self.agent.context.log.log(
                    type="agent",
                    heading=f"{self.agent.agent_name}: Generating",
                    content=text
                )
        except Exception:
            # Silently handle any errors to avoid breaking the response flow
            pass 