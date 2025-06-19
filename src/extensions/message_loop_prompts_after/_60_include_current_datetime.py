from datetime import datetime, timezone
from src.helpers.extension import Extension
from src.core.agent import LoopData
from src.helpers.localization import Localization


class IncludeCurrentDatetime(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # get current datetime
        current_datetime = Localization.get().utc_dt_to_localtime_str(
            datetime.now(timezone.utc), sep=" ", timespec="seconds"
        )
        # remove timezone offset
        if current_datetime and "+" in current_datetime:
            current_datetime = current_datetime.split("+")[0]

        # read prompt (this will automatically use Jinja2 if available, fallback to old system)
        from src.helpers.prompt_engine import get_prompt_engine
        datetime_prompt = get_prompt_engine().render(
            "components/behaviors/datetime.j2", date_time=current_datetime
        )

        # add current datetime to the loop data
        loop_data.extras_temporary["current_datetime"] = datetime_prompt
