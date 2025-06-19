from src.helpers.tool import Tool, Response


class Unknown(Tool):
    async def execute(self, **kwargs):
        from src.helpers.prompt_engine import get_prompt_engine
        
        # Get available tools list
        tools_prompt = get_prompt_engine().render("components/tools/tools_summary.j2")
        
        # Use the template with proper context
        message = get_prompt_engine().render(
            "components/frameworks/tool_not_found.j2",
            tool_name=self.name,
            tools_prompt=tools_prompt
        )
        
        return Response(message=message, break_loop=False)
