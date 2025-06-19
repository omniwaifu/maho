import anyio
import json
import time
from typing import Optional
from src.core.agent import Agent, InterventionException
from pathlib import Path
from anyio.from_thread import start_blocking_portal
import threading
from concurrent.futures import Future


from src import models
from src.helpers import files, persist_chat, strings
from src.helpers.browser_use import browser_use
from src.helpers.print_style import PrintStyle
from src.helpers.playwright import ensure_playwright_binary
from src.extensions.message_loop_start._10_iteration_no import get_iter_no
from pydantic import BaseModel
import uuid
from src.helpers.dirty_json import DirtyJson
from src.helpers.tool import Tool, Response

# Module-level portal for browser agent background tasks
_browser_portal_cm = None
_browser_portal = None


def _get_browser_portal():
    """Get or create the browser portal"""
    global _browser_portal_cm, _browser_portal
    if _browser_portal is None:
        _browser_portal_cm = start_blocking_portal(backend="asyncio")
        _browser_portal = _browser_portal_cm.__enter__()
    return _browser_portal


class State:
    @staticmethod
    async def create(agent: Agent):
        state = State(agent)
        return state

    def __init__(self, agent: Agent):
        self.agent = agent
        self.browser_session: Optional[browser_use.BrowserSession] = None
        self.task: Future | None = None
        self.use_agent: Optional[browser_use.Agent] = None
        self.iter_no = 0

    def __del__(self):
        self.kill_task()

    async def _initialize(self):
        if self.browser_session:
            return

        # for some reason we need to provide exact path to headless shell, otherwise it looks for headed browser
        pw_binary = ensure_playwright_binary()

        self.browser_session = browser_use.BrowserSession(
            browser_profile=browser_use.BrowserProfile(
                headless=True,
                disable_security=True,
                chromium_sandbox=False,
                accept_downloads=True,
                downloads_dir=files.get_abs_path("tmp/downloads"),
                downloads_path=files.get_abs_path("tmp/downloads"),
                executable_path=pw_binary,
                keep_alive=True,
                minimum_wait_page_load_time=1.0,
                wait_for_network_idle_page_load_time=2.0,
                maximum_wait_page_load_time=10.0,
                screen={"width": 1024, "height": 2048},
                viewport={"width": 1024, "height": 2048},
                args=["--headless=new"],
            )
        )

        await self.browser_session.start()
        # self.override_hooks()

        # Add init script to the browser session
        if self.browser_session.browser_context:
            js_override = files.get_abs_path("lib/browser/init_override.js")
            await self.browser_session.browser_context.add_init_script(path=js_override)

    def start_task(self, task: str):
        if self.task and not self.task.done():
            self.kill_task()

        portal = _get_browser_portal()
        self.task = portal.start_task_soon(self._run_task, task)
        return self.task

    def kill_task(self):
        if self.task and not self.task.done():
            self.task.cancel()
        self.task = None
        if self.browser_session:
            try:
                # Use sniffio to run the async close operation in a new event loop
                import sniffio

                try:
                    # If we're already in an async context, we can't use run_sync
                    sniffio.current_async_library()
                    # We're in an async context, so we need to handle this differently
                    # For now, just set browser_session to None and let it be garbage collected
                    pass
                except sniffio.AsyncLibraryNotFoundError:
                    # We're not in an async context, so we can use anyio.run
                    anyio.run(self.browser_session.close)
            except Exception as e:
                PrintStyle().error(f"Error closing browser session: {e}")
            finally:
                self.browser_session = None
        self.use_agent = None
        self.iter_no = 0

    async def _run_task(self, task: str):
        await self._initialize()

        class DoneResult(BaseModel):
            title: str
            response: str
            page_summary: str

        # Initialize controller
        controller = browser_use.Controller(output_model=DoneResult)

        # Register custom completion action with proper ActionResult fields
        @controller.registry.action("Complete task", param_model=DoneResult)
        async def complete_task(params: DoneResult):
            result = browser_use.ActionResult(
                is_done=True, success=True, extracted_content=params.model_dump_json()
            )
            return result

        model = models.get_model(
            type=models.ModelType.CHAT,
            provider=self.agent.config.browser_model.provider,
            name=self.agent.config.browser_model.name,
            **self.agent.config.browser_model.kwargs,
        )

        self.use_agent = browser_use.Agent(
            task=task,
            browser_session=self.browser_session,
            llm=model,
            use_vision=self.agent.config.browser_model.vision,
            extend_system_message=self.agent.read_prompt(
                "prompts/browser_agent.system.md"
            ),
            controller=controller,
            enable_memory=False,  # Disable memory to avoid state conflicts
            # available_file_paths=[],
        )

        self.iter_no = get_iter_no(self.agent)

        async def hook(agent: browser_use.Agent):
            await self.agent.wait_if_paused()
            if self.iter_no != get_iter_no(self.agent):
                raise InterventionException("Task cancelled")

        # try:
        result = await self.use_agent.run(
            max_steps=50, on_step_start=hook, on_step_end=hook
        )
        return result
        # finally:
        #     # if self.browser_session:
        #     #     try:
        #     #         await self.browser_session.close()
        #     #     except Exception as e:
        #     #         PrintStyle().error(f"Error closing browser session in task cleanup: {e}")
        #     #     finally:
        #     #         self.browser_session = None
        #     pass

    # def override_hooks(self):
    #     def override_hook(func):
    #         async def wrapper(*args, **kwargs):
    #             await self.agent.wait_if_paused()
    #             if self.iter_no != get_iter_no(self.agent):
    #                 raise InterventionException("Task cancelled")
    #             return await func(*args, **kwargs)

    #         return wrapper

    #     if self.browser_session and hasattr(self.browser_session, "remove_highlights"):
    #         self.browser_session.remove_highlights = override_hook(
    #             self.browser_session.remove_highlights
    #         )

    async def get_page(self):
        if self.use_agent and self.browser_session:
            try:
                return await self.use_agent.browser_session.get_current_page()
            except Exception:
                # Browser session might be closed or invalid
                return None
        return None

    async def get_selector_map(self):
        """Get the selector map for the current page state."""
        if self.use_agent:
            await self.use_agent.browser_session.get_state_summary(
                cache_clickable_elements_hashes=True
            )
            return await self.use_agent.browser_session.get_selector_map()
        return {}


class BrowserAgent(Tool):

    async def execute(self, message="", reset="", **kwargs):
        self.guid = str(uuid.uuid4())
        reset = str(reset).lower().strip() == "true"
        await self.prepare_state(reset=reset)
        task = self.state.start_task(message)

        # wait for browser agent to finish and update progress with timeout
        timeout_seconds = 300  # 5 minute timeout
        start_time = time.time()

        fail_counter = 0
        while not task.done():
            # Check for timeout to prevent infinite waiting
            if time.time() - start_time > timeout_seconds:
                PrintStyle().warning(
                    f"Browser agent task timeout after {timeout_seconds} seconds, forcing completion"
                )
                break

            await self.agent.handle_intervention()
            await anyio.sleep(1)
            try:
                if task.done():  # otherwise get_update hangs
                    break
                update = {}  # initialize to prevent unbound variable
                try:
                    with anyio.move_on_after(10) as cancel_scope:
                        update = await self.get_update()

                    if cancel_scope.cancelled_caught:
                        # Timeout occurred
                        fail_counter += 1
                        PrintStyle().warning(
                            f"browser_agent.get_update timed out ({fail_counter}/3)"
                        )
                        if fail_counter >= 3:
                            PrintStyle().warning(
                                "3 consecutive browser_agent.get_update timeouts, breaking loop"
                            )
                            break
                        continue
                    else:
                        fail_counter = 0  # reset on success
                        
                        log = update.get("log", get_use_agent_log(None))
                        self.update_progress("\n".join(log))
                        screenshot = update.get("screenshot", None)
                        if screenshot:
                            self.log.update(screenshot=screenshot)
                except Exception as e:
                    # If get_update() raised an exception
                    fail_counter += 1
                    PrintStyle().warning(
                        f"browser_agent.get_update failed with exception: {e} ({fail_counter}/3)"
                    )
                    if fail_counter >= 3:
                        PrintStyle().warning(
                            "3 consecutive browser_agent.get_update failures, breaking loop"
                        )
                        break
                    continue
            except Exception as e:
                PrintStyle().error(f"Error getting update: {str(e)}")

        if not task.done():
            PrintStyle().warning("browser_agent.get_update timed out, killing the task")
            self.state.kill_task()
            return Response(
                message="Browser agent task timed out, not output provided.",
                break_loop=False,
            )

        # final progress update
        if self.state.use_agent:
            log = get_use_agent_log(self.state.use_agent)
            self.update_progress("\n".join(log))

        # collect result with error handling
        try:
            result = await task.result()
        except Exception as e:
            PrintStyle().error(f"Error getting browser agent task result: {str(e)}")
            # Return a timeout response if task.result() fails
            answer_text = f"Browser agent task failed to return result: {str(e)}"
            self.log.update(answer=answer_text)
            return Response(message=answer_text, break_loop=False)
        # finally:
        #     # Stop any further browser access after task completion
        #     # self.state.kill_task()
        #     pass

        # Check if task completed successfully
        if result.is_done():
            answer = result.final_result()
            try:
                if answer and isinstance(answer, str) and answer.strip():
                    answer_data = DirtyJson.parse_string(answer)
                    answer_text = strings.dict_to_text(answer_data)  # type: ignore
                else:
                    answer_text = (
                        str(answer) if answer else "Task completed successfully"
                    )
            except Exception as e:
                answer_text = (
                    str(answer)
                    if answer
                    else f"Task completed with parse error: {str(e)}"
                )
        else:
            # Task hit max_steps without calling done()
            urls = result.urls()
            current_url = urls[-1] if urls else "unknown"
            answer_text = (
                f"Task reached step limit without completion. Last page: {current_url}. "
                f"The browser agent may need clearer instructions on when to finish."
            )

        # update the log (without screenshot path here, user can click)
        self.log.update(answer=answer_text)

        # add screenshot to the answer if we have it
        if (
            self.log.kvps
            and "screenshot" in self.log.kvps
            and self.log.kvps["screenshot"]
        ):
            path = self.log.kvps["screenshot"].split("//", 1)[-1].split("&", 1)[0]
            answer_text += f"\n\nScreenshot: {path}"

        # respond (with screenshot path)
        return Response(message=answer_text, break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="browser",
            heading=f"{self.agent.agent_name}: Using tool '{self.name}'",
            content="",
            kvps=self.args,
        )

    async def get_update(self):
        await self.prepare_state()

        result = {}
        agent = self.agent
        ua = self.state.use_agent
        page = await self.state.get_page()

        if ua and page:
            try:

                async def _get_update():

                    # await agent.wait_if_paused() # no need here

                    log = []

                    # for message in ua.message_manager.get_messages():
                    #     if message.type == "system":
                    #         continue
                    #     if message.type == "ai":
                    #         try:
                    #             data = json.loads(message.content)  # type: ignore
                    #             cs = data.get("current_state")
                    #             if cs:
                    #                 log.append("AI:" + cs["memory"])
                    #                 log.append("AI:" + cs["next_goal"])
                    #         except Exception:
                    #             pass
                    #     if message.type == "human":
                    #         content = str(message.content).strip()
                    #         part = content.split("\n", 1)[0].split(",", 1)[0]
                    #         if part:
                    #             if len(part) > 150:
                    #                 part = part[:150] + "..."
                    #             log.append("FW:" + part)

                    # for hist in ua.state.history.history:
                    #     for res in hist.result:
                    #         log.append(res.extracted_content)
                    # log = ua.state.history.extracted_content()
                    # short_log = []
                    # for item in log:
                    #     first_line = str(item).split("\n", 1)[0][:200]
                    #     short_log.append(first_line)
                    result["log"] = get_use_agent_log(ua)

                    path = files.get_abs_path(
                        persist_chat.get_chat_folder_path(agent.context.id),
                        "browser",
                        "screenshots",
                        f"{self.guid}.png",
                    )
                    files.make_dirs(path)
                    await page.screenshot(path=path, full_page=False, timeout=3000)
                    result["screenshot"] = f"img://{path}&t={str(time.time())}"

                if self.state.task and not self.state.task.done():
                    await _get_update()

            except Exception:
                pass

        return result

    async def prepare_state(self, reset=False):
        self.state = self.agent.get_data("_browser_agent_state")
        if reset and self.state:
            self.state.kill_task()
        if not self.state or reset:
            self.state = await State.create(self.agent)
        self.agent.set_data("_browser_agent_state", self.state)

    def update_progress(self, text):
        short = text.split("\n")[-1]
        if len(short) > 50:
            short = short[:50] + "..."
        progress = f"Browser: {short}"

        self.log.update(progress=text)
        self.agent.context.log.set_progress(progress)

    # def __del__(self):
    #     if self.state:
    #         self.state.kill_task()


def get_use_agent_log(use_agent: browser_use.Agent | None):
    result = ["🚦 Starting task"]
    if use_agent:
        action_results = use_agent.state.history.action_results()
        short_log = []
        for item in action_results:
            # final results
            if item.is_done:
                if item.success:
                    short_log.append("✅ Done")
                else:
                    short_log.append(
                        f"❌ Error: {item.error or item.extracted_content or 'Unknown error'}"
                    )

            # progress messages
            else:
                text = item.extracted_content
                if text:
                    first_line = text.split("\n", 1)[0][:200]
                    short_log.append(first_line)
        result.extend(short_log)
    return result
