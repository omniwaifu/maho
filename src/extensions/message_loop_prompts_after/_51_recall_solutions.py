import anyio
from src.helpers.extension import Extension
from src.helpers.memory import Memory
from src.core.agent import LoopData

DATA_NAME_TASK = "_recall_solutions_task"


class RecallSolutions(Extension):

    INTERVAL = 3
    HISTORY = 10000
    SOLUTIONS_COUNT = 2
    INSTRUMENTS_COUNT = 2
    THRESHOLD = 0.6

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):

        # every 3 iterations (or the first one) recall memories
        if loop_data.iteration % RecallSolutions.INTERVAL == 0:
            # Use anyio task group for structured concurrency
            async with anyio.create_task_group() as tg:
                tg.start_soon(self.search_solutions, loop_data, **kwargs)

        # No need to store task reference with anyio task groups
        self.agent.set_data(DATA_NAME_TASK, None)

    async def search_solutions(self, loop_data: LoopData, **kwargs):

        # cleanup
        extras = loop_data.extras_persistent
        if "solutions" in extras:
            del extras["solutions"]

        # try:
        # show temp info message
        self.agent.context.log.log(
            type="info", content="Searching memory for solutions...", temp=True
        )

        # show full util message, this will hide temp message immediately if turned on
        log_item = self.agent.context.log.log(
            type="util",
            heading="Searching memory for solutions...",
        )

        # get system message and chat history for util llm
        # msgs_text = self.agent.concat_messages(
        #     self.agent.history[-RecallSolutions.HISTORY :]
        # )  # only last X messages
        # msgs_text = self.agent.history.current.output_text()
        msgs_text = self.agent.history.output_text()[-RecallSolutions.HISTORY :]

        from src.helpers.prompt_engine import get_prompt_engine
        system = get_prompt_engine().render(
            "components/memory/solutions_query_system.j2", history=msgs_text
        )

        # log query streamed by LLM
        async def log_callback(content):
            log_item.stream(query=content)

        # call util llm to summarize conversation
        query = await self.agent.call_utility_model(
            system=system,
            message=(
                loop_data.user_message.output_text() if loop_data.user_message else ""
            ),
            callback=log_callback,
        )

        # get solutions database
        db = await Memory.get(self.agent)

        solutions = await db.search_similarity_threshold(
            query=query,
            limit=RecallSolutions.SOLUTIONS_COUNT,
            threshold=RecallSolutions.THRESHOLD,
            filter=f"area == '{Memory.Area.SOLUTIONS.value}'",
        )
        instruments = await db.search_similarity_threshold(
            query=query,
            limit=RecallSolutions.INSTRUMENTS_COUNT,
            threshold=RecallSolutions.THRESHOLD,
            filter=f"area == '{Memory.Area.INSTRUMENTS.value}'",
        )

        log_item.update(
            heading=f"{len(instruments)} instruments, {len(solutions)} solutions found",
        )

        if instruments:
            instruments_text = ""
            for instrument in instruments:
                instruments_text += instrument.page_content + "\n\n"
            instruments_text = instruments_text.strip()
            log_item.update(instruments=instruments_text)
            engine = get_prompt_engine()
            instruments_prompt = engine.render(
                "components/memory/instruments_system.j2", instruments=instruments_text
            )
            loop_data.system.append(instruments_prompt)

        if solutions:
            solutions_text = ""
            for solution in solutions:
                solutions_text += solution.page_content + "\n\n"
            solutions_text = solutions_text.strip()
            log_item.update(solutions=solutions_text)
            engine = get_prompt_engine()
            result = engine.render("components/memory/solutions_system.j2", solutions=solutions_text)
            # Parse as JSON if needed for compatibility
            try:
                import json
                solutions_prompt = json.loads(result)
            except (json.JSONDecodeError, ValueError):
                solutions_prompt = result

            # append to prompt
            extras["solutions"] = solutions_prompt

    # except Exception as e:
    #     err = errors.format_error(e)
    #     self.agent.context.log.log(
    #         type="error", heading="Recall solutions extension error:", content=err
    #     )
