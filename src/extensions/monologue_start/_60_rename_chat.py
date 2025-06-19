from src.helpers import persist_chat, tokens
from src.helpers.extension import Extension
from src.core.agent import LoopData
from src.helpers.prompt_engine import get_prompt_engine
import anyio


class RenameChat(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Use task group for background task execution
        async with anyio.create_task_group() as tg:
            tg.start_soon(self.change_name)
            # Task completes in background with proper cancellation handling

    async def change_name(self):
        try:
            # prepare history
            history_text = self.agent.history.output_text()
            ctx_length = int(self.agent.config.utility_model.ctx_length * 0.3)
            history_text = tokens.trim_to_tokens(history_text, ctx_length, "start")
            # prepare system and user prompt
            engine = get_prompt_engine()
            system = engine.render("components/frameworks/rename_chat_system.j2")
            current_name = self.agent.context.name
            message = engine.render(
                "components/frameworks/rename_chat_message.j2", current_name=current_name, history=history_text
            )
            # call utility model
            new_name = await self.agent.call_utility_model(
                system=system, message=message, background=True
            )
            # update name
            if new_name:
                # trim name to max length if needed
                if len(new_name) > 40:
                    new_name = new_name[:40] + "..."
                # apply to context and save
                self.agent.context.name = new_name
                persist_chat.save_tmp_chat(self.agent.context)
        except Exception as e:
            pass  # non-critical
