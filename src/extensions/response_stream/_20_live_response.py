from src.helpers.extension import Extension
from src.core.models import LoopData


class LiveResponse(Extension):
    """Extension for live response streaming during agent responses."""

    async def execute(
        self,
        loop_data: LoopData | None = None,
        text: str = "",
        parsed: dict | None = None,
        **kwargs,
    ):
        try:
            if not parsed or parsed.get("tool_name") != "response":
                return  # not a response
            
            tool_args = parsed.get("tool_args", {})
            response_text = tool_args.get("text", "")
            
            if not response_text:
                return
                
            # Log the response for live streaming
            if hasattr(self.agent, 'context') and hasattr(self.agent.context, 'log'):
                self.agent.context.log.log(
                    type="response",
                    heading=f"{self.agent.agent_name}: Responding",
                    content=response_text
                )
        except Exception:
            # Silently handle any errors to avoid breaking the response flow
            pass 