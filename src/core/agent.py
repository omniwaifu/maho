import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from src.core.context import AgentContext

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from src.core.models import (
    AgentConfig,
    ModelConfig,
    UserMessage,
    LoopData,
    InterventionException,
    RepairableException,
    HandledException,
)
from src.helpers import extract_tools, files, errors, history, tokens
from src.helpers import dirty_json
from src.helpers.print_style import PrintStyle
from src.helpers.dirty_json import DirtyJson
import src.helpers.log as Log


class Agent:
    """Main Agent class that handles conversation loops and tool execution"""

    DATA_NAME_SUPERIOR = "_superior"
    DATA_NAME_SUBORDINATE = "_subordinate"
    DATA_NAME_CTX_WINDOW = "ctx_window"

    def __init__(
        self, number: int, config: AgentConfig, context: "AgentContext | None" = None  # type: ignore
    ):
        # agent config
        self.config = config

        # agent context - avoid circular import
        if context:
            self.context = context
        else:
            from src.core.context import AgentContext

            self.context = AgentContext(config)

        # non-config vars
        self.number = number
        self.agent_name = f"Agent {self.number}"

        self.history = history.History(self)
        self.last_user_message: history.Message | None = None
        self.intervention: UserMessage | None = None
        self.data = {}  # free data object all the tools can use

    async def monologue(self):
        while True:
            try:
                # loop data dictionary to pass to extensions
                self.loop_data = LoopData(user_message=self.last_user_message)
                # call monologue_start extensions
                await self.call_extensions("monologue_start", loop_data=self.loop_data)

                printer = PrintStyle(italic=True, font_color="#b3ffd9", padding=False)

                # let the agent run message loop until he stops it with a response tool
                while True:

                    self.context.streaming_agent = self  # mark self as current streamer
                    self.loop_data.iteration += 1

                    # call message_loop_start extensions
                    await self.call_extensions(
                        "message_loop_start", loop_data=self.loop_data
                    )

                    try:
                        # prepare LLM chain (model, system, history)
                        prompt = await self.prepare_prompt(loop_data=self.loop_data)

                        # output that the agent is starting
                        PrintStyle(
                            bold=True,
                            font_color="green",
                            padding=True,
                            background_color="white",
                        ).print(f"{self.agent_name}: Generating")
                        log = self.context.log.log(
                            type="agent", heading=f"{self.agent_name}: Generating"
                        )

                        async def stream_callback(chunk: str, full: str):
                            # output the agent response stream
                            if chunk:
                                printer.stream(chunk)
                                self.log_from_stream(full, log)

                        agent_response = await self.call_chat_model(
                            prompt, callback=stream_callback
                        )  # type: ignore

                        await self.handle_intervention(agent_response)

                        if (
                            self.loop_data.last_response == agent_response
                        ):  # if assistant_response is the same as last message in history, let him know
                            # Append the assistant's response to the history
                            self.hist_add_ai_response(agent_response)
                            # Append warning message to the history
                            warning_msg = self.read_prompt("fw.msg_repeat.md")
                            self.hist_add_warning(message=warning_msg)
                            PrintStyle(font_color="orange", padding=True).print(
                                warning_msg
                            )
                            self.context.log.log(type="warning", content=warning_msg)

                        else:  # otherwise proceed with tool
                            # Append the assistant's response to the history
                            self.hist_add_ai_response(agent_response)
                            # process tools requested in agent message
                            tools_result = await self.process_tools(agent_response)
                            if tools_result:  # final response of message loop available
                                return tools_result  # break the execution if the task is done

                    # exceptions inside message loop:
                    except InterventionException as e:
                        pass  # intervention message has been handled in handle_intervention(), proceed with conversation loop
                    except RepairableException as e:
                        # Forward repairable errors to the LLM, maybe it can fix them
                        error_message = errors.format_error(e)
                        self.hist_add_warning(error_message)
                        PrintStyle(font_color="red", padding=True).print(error_message)
                        self.context.log.log(type="error", content=error_message)
                    except Exception as e:
                        # Other exception kill the loop
                        self.handle_critical_exception(e)

                    finally:
                        # call message_loop_end extensions
                        await self.call_extensions(
                            "message_loop_end", loop_data=self.loop_data
                        )

            # exceptions outside message loop:
            except InterventionException as e:
                pass  # just start over
            except Exception as e:
                self.handle_critical_exception(e)
            finally:
                self.context.streaming_agent = None  # unset current streamer
                # call monologue_end extensions
                await self.call_extensions("monologue_end", loop_data=self.loop_data)  # type: ignore

    async def prepare_prompt(self, loop_data: LoopData) -> ChatPromptTemplate:
        self.context.log.set_progress("Building prompt")

        # call extensions before setting prompts
        await self.call_extensions("message_loop_prompts_before", loop_data=loop_data)

        # set system prompt and message history
        loop_data.system = await self.get_system_prompt(self.loop_data)
        loop_data.history_output = self.history.output()

        # and allow extensions to edit them
        await self.call_extensions("message_loop_prompts_after", loop_data=loop_data)

        # extras (memory etc.)
        extras = history.Message(
            False,
            content=self.read_prompt(
                "agent.context.extras.md",
                extras=dirty_json.stringify(
                    {**loop_data.extras_persistent, **loop_data.extras_temporary}
                ),
            ),
        ).output()
        loop_data.extras_temporary.clear()

        # convert history + extras to LLM format
        history_langchain: list[BaseMessage] = history.output_langchain(
            loop_data.history_output + extras
        )

        # build chain from system prompt, message history and model
        system_text = "\n\n".join(loop_data.system)
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_text),
                *history_langchain,
            ]
        )

        # store as last context window content
        self.set_data(
            Agent.DATA_NAME_CTX_WINDOW,
            {
                "text": prompt.format(),
                "tokens": self.history.get_tokens()
                + tokens.approximate_tokens(system_text)
                + tokens.approximate_tokens(history.output_text(extras)),
            },
        )

        return prompt

    def handle_critical_exception(self, exception: Exception):
        if isinstance(exception, HandledException):
            raise exception  # Re-raise the exception to kill the loop
        elif isinstance(exception, asyncio.CancelledError):
            # Handling for asyncio.CancelledError
            PrintStyle(font_color="white", background_color="red", padding=True).print(
                f"Context {self.context.id} terminated during message loop"
            )
            raise HandledException(
                exception
            )  # Re-raise the exception to cancel the loop
        else:
            # Handling for general exceptions
            error_text = errors.error_text(exception)
            error_message = errors.format_error(exception)
            PrintStyle(font_color="red", padding=True).print(error_message)
            self.context.log.log(
                type="error",
                heading="Error",
                content=error_message,
                kvps={"text": error_text},
            )
            raise HandledException(exception)  # Re-raise the exception to kill the loop

    async def get_system_prompt(self, loop_data: LoopData) -> list[str]:
        system_prompt = []
        await self.call_extensions(
            "system_prompt", system_prompt=system_prompt, loop_data=loop_data
        )
        return system_prompt

    def parse_prompt(self, file: str, **kwargs):
        prompt_dir = files.get_abs_path("prompts/default")
        backup_dir = []
        if (
            self.config.prompts_subdir
        ):  # if agent has custom folder, use it and use default as backup
            prompt_dir = files.get_abs_path("prompts", self.config.prompts_subdir)
            backup_dir.append(files.get_abs_path("prompts/default"))
        prompt = files.parse_file(
            files.get_abs_path(prompt_dir, file), _backup_dirs=backup_dir, **kwargs
        )
        return prompt

    def read_prompt(self, file: str, **kwargs) -> str:
        prompt_dir = files.get_abs_path("prompts/default")
        backup_dir = []
        if (
            self.config.prompts_subdir
        ):  # if agent has custom folder, use it and use default as backup
            prompt_dir = files.get_abs_path("prompts", self.config.prompts_subdir)
            backup_dir.append(files.get_abs_path("prompts/default"))
        prompt = files.read_file(
            files.get_abs_path(prompt_dir, file), _backup_dirs=backup_dir, **kwargs
        )
        prompt = files.remove_code_fences(prompt)
        return prompt

    def get_data(self, field: str):
        return self.data.get(field, None)

    def set_data(self, field: str, value):
        self.data[field] = value

    def hist_add_message(
        self, ai: bool, content: history.MessageContent, tokens: int = 0
    ):
        self.last_message = datetime.now(timezone.utc)
        return self.history.add_message(ai=ai, content=content, tokens=tokens)

    def hist_add_user_message(self, message: UserMessage, intervention: bool = False):
        self.history.new_topic()  # user message starts a new topic in history

        # load message template based on intervention
        if intervention:
            content = self.parse_prompt(
                "fw.intervention.md",
                message=message.message,
                attachments=message.attachments,
                system_message=message.system_message,
            )
        else:
            content = self.parse_prompt(
                "fw.user_message.md",
                message=message.message,
                attachments=message.attachments,
                system_message=message.system_message,
            )

        # remove empty parts from template
        if isinstance(content, dict):
            content = {k: v for k, v in content.items() if v}

        # add to history
        msg = self.hist_add_message(False, content=content)  # type: ignore
        self.last_user_message = msg
        return msg

    def hist_add_ai_response(self, message: str):
        self.loop_data.last_response = message
        content = self.parse_prompt("fw.ai_response.md", message=message)
        return self.hist_add_message(True, content=content)

    def hist_add_warning(self, message: history.MessageContent):
        content = self.parse_prompt("fw.warning.md", message=message)
        return self.hist_add_message(False, content=content)

    def hist_add_tool_result(self, tool_name: str, tool_result: str):
        content = self.parse_prompt(
            "fw.tool_result.md", tool_name=tool_name, tool_result=tool_result
        )
        return self.hist_add_message(False, content=content)

    def concat_messages(
        self, messages
    ):  # TODO add param for message range, topic, history
        return self.history.output_text(human_label="user", ai_label="assistant")

    def get_chat_model(self):
        # Import here to avoid circular dependency
        import models

        return models.get_model(
            models.ModelType.CHAT,
            self.config.chat_model.provider,
            self.config.chat_model.name,
            **self.config.chat_model.kwargs,
        )

    def get_utility_model(self):
        # Import here to avoid circular dependency
        import models

        return models.get_model(
            models.ModelType.CHAT,
            self.config.utility_model.provider,
            self.config.utility_model.name,
            **self.config.utility_model.kwargs,
        )

    def get_embedding_model(self):
        # Import here to avoid circular dependency
        import models

        return models.get_model(
            models.ModelType.EMBEDDING,
            self.config.embeddings_model.provider,
            self.config.embeddings_model.name,
            **self.config.embeddings_model.kwargs,
        )

    async def call_utility_model(
        self,
        system: str,
        message: str,
        callback: Callable[[str], Awaitable[None]] | None = None,
        background: bool = False,
    ):
        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=system), HumanMessage(content=message)]
        )

        response = ""

        # model class
        model = self.get_utility_model()

        # rate limiter
        limiter = await self.rate_limiter(
            self.config.utility_model, prompt.format(), background
        )

        async for chunk in (prompt | model).astream({}):
            await self.handle_intervention()  # wait for intervention and handle it, if paused

            # Import here to avoid circular dependency
            import models

            content = models.parse_chunk(chunk)
            limiter.add(output=tokens.approximate_tokens(content))
            response += content

            if callback:
                await callback(content)

        return response

    async def call_chat_model(
        self,
        prompt: ChatPromptTemplate,
        callback: Callable[[str, str], Awaitable[None]] | None = None,
    ):
        response = ""

        # model class
        model = self.get_chat_model()

        # rate limiter
        limiter = await self.rate_limiter(self.config.chat_model, prompt.format())

        async for chunk in (prompt | model).astream({}):
            await self.handle_intervention()  # wait for intervention and handle it, if paused

            # Import here to avoid circular dependency
            import models

            content = models.parse_chunk(chunk)
            limiter.add(output=tokens.approximate_tokens(content))
            response += content

            if callback:
                await callback(content, response)

        return response

    async def rate_limiter(
        self, model_config: ModelConfig, input: str, background: bool = False
    ):
        # rate limiter log
        wait_log = None

        async def wait_callback(msg: str, key: str, total: int, limit: int):
            nonlocal wait_log
            if not wait_log:
                wait_log = self.context.log.log(
                    type="util",
                    update_progress="none",
                    heading=msg,
                    model=f"{model_config.provider.value}\\{model_config.name}",
                )
            wait_log.update(heading=msg, key=key, value=total, limit=limit)
            if not background:
                self.context.log.set_progress(msg, -1)

        # rate limiter - Import here to avoid circular dependency
        import models

        limiter = models.get_rate_limiter(
            model_config.provider,
            model_config.name,
            model_config.limit_requests,
            model_config.limit_input,
            model_config.limit_output,
        )
        limiter.add(input=tokens.approximate_tokens(input))
        limiter.add(requests=1)
        await limiter.wait(callback=wait_callback)
        return limiter

    async def handle_intervention(self, progress: str = ""):
        while self.context.paused:
            await asyncio.sleep(0.1)  # wait if paused
        if (
            self.intervention
        ):  # if there is an intervention message, but not yet processed
            msg = self.intervention
            self.intervention = None  # reset the intervention message
            if progress.strip():
                self.hist_add_ai_response(progress)
            # append the intervention message
            self.hist_add_user_message(msg, intervention=True)
            raise InterventionException(msg)

    async def wait_if_paused(self):
        while self.context.paused:
            await asyncio.sleep(0.1)

    async def process_tools(self, msg: str):
        # search for tool usage requests in agent message
        tool_request = extract_tools.json_parse_dirty(msg)

        if tool_request is not None:
            raw_tool_name = tool_request.get("tool_name", "")  # Get the raw tool name
            tool_args = tool_request.get("tool_args", {})

            tool_name = raw_tool_name  # Initialize tool_name with raw_tool_name
            tool_method = None  # Initialize tool_method

            # Split raw_tool_name into tool_name and tool_method if applicable
            if ":" in raw_tool_name:
                tool_name, tool_method = raw_tool_name.split(":", 1)

            tool = None  # Initialize tool to None

            # Try getting tool from MCP first
            try:
                import python.helpers.mcp_handler as mcp_helper

                mcp_tool_candidate = mcp_helper.MCPConfig.get_instance().get_tool(
                    self, tool_name
                )
                if mcp_tool_candidate:
                    tool = mcp_tool_candidate
            except ImportError:
                PrintStyle(
                    background_color="black", font_color="yellow", padding=True
                ).print("MCP helper module not found. Skipping MCP tool lookup.")
            except Exception as e:
                PrintStyle(
                    background_color="black", font_color="red", padding=True
                ).print(f"Failed to get MCP tool '{tool_name}': {e}")

            # Fallback to local get_tool if MCP tool was not found or MCP lookup failed
            if not tool:
                tool = self.get_tool(
                    name=tool_name, method=tool_method, args=tool_args, message=msg
                )

            if tool:
                await self.handle_intervention()
                await tool.before_execution(**tool_args)
                await self.handle_intervention()
                response = await tool.execute(**tool_args)
                await self.handle_intervention()
                await tool.after_execution(response)
                await self.handle_intervention()
                if response.break_loop:
                    return response.message
            else:
                error_detail = (
                    f"Tool '{raw_tool_name}' not found or could not be initialized."
                )
                self.hist_add_warning(error_detail)
                PrintStyle(font_color="red", padding=True).print(error_detail)
                self.context.log.log(
                    type="error", content=f"{self.agent_name}: {error_detail}"
                )
        else:
            warning_msg_misformat = self.read_prompt("fw.msg_misformat.md")
            self.hist_add_warning(warning_msg_misformat)
            PrintStyle(font_color="red", padding=True).print(warning_msg_misformat)
            self.context.log.log(
                type="error",
                content=f"{self.agent_name}: Message misformat, no valid tool request found.",
            )

    def log_from_stream(self, stream: str, logItem: Log.LogItem):
        try:
            if len(stream) < 25:
                return  # no reason to try
            response = DirtyJson.parse_string(stream)
            if isinstance(response, dict):
                # log if result is a dictionary already
                logItem.update(content=stream, kvps=response)
        except Exception as e:
            pass

    def get_tool(
        self, name: str, method: str | None, args: dict, message: str, **kwargs
    ):
        from python.tools.unknown import Unknown
        from python.helpers.tool import Tool

        classes = extract_tools.load_classes_from_folder(
            "python/tools", name + ".py", Tool
        )
        tool_class = classes[0] if classes else Unknown
        return tool_class(
            agent=self, name=name, method=method, args=args, message=message, **kwargs
        )

    async def call_extensions(self, folder: str, **kwargs) -> Any:
        from python.helpers.extension import Extension

        classes = extract_tools.load_classes_from_folder(
            "python/extensions/" + folder, "*", Extension
        )
        for cls in classes:
            await cls(agent=self).execute(**kwargs)
