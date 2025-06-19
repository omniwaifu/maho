from src.helpers import files, memory
from src.helpers.tool import Tool, Response
from src.core.agent import Agent
from src.helpers.log import LogItem
from src.helpers.prompt_engine import get_prompt_engine


class UpdateBehaviour(Tool):

    async def execute(self, adjustments="", **kwargs):

        # stringify adjustments if needed
        if not isinstance(adjustments, str):
            adjustments = str(adjustments)

        await update_behaviour(self.agent, self.log, adjustments)
        return Response(
            message=get_prompt_engine().render("components/behaviors/behavior_updated.j2"), break_loop=False
        )

    # async def before_execution(self, **kwargs):
    #     pass

    # async def after_execution(self, response, **kwargs):
    #     pass


async def update_behaviour(agent: Agent, log_item: LogItem, adjustments: str):

    # get system message and current ruleset
    system = get_prompt_engine().render("components/behaviors/behavior_merge_system.j2")
    current_rules = read_rules(agent)

    # log query streamed by LLM
    async def log_callback(content):
        log_item.stream(ruleset=content)

    engine = get_prompt_engine()
    msg = engine.render(
        "components/behaviors/behavior_merge_message.j2", current_rules=current_rules, adjustments=adjustments
    )

    # call util llm to find solutions in history
    adjustments_merge = await agent.call_utility_model(
        system=system,
        message=msg,
        callback=log_callback,
    )

    # update rules file
    rules_file = get_custom_rules_file(agent)
    files.write_file(rules_file, adjustments_merge)
    log_item.update(result="Behaviour updated")


def get_custom_rules_file(agent: Agent):
    return memory.get_memory_subdir_abs(agent) + "/behaviour.md"


def read_rules(agent: Agent):
    rules_file = get_custom_rules_file(agent)
    if files.exists(rules_file):
        rules = files.read_file(rules_file)
        return get_prompt_engine().render("components/behaviors/behavior_system.j2", rules=rules)
    else:
        engine = get_prompt_engine()
        rules = engine.render("components/behaviors/behavior_default.j2")
        return engine.render("components/behaviors/behavior_system.j2", rules=rules)
