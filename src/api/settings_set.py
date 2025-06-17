from src.helpers.api import ApiHandler
from flask import Request, Response

from src.helpers import settings

from typing import Any


class SetSettings(ApiHandler):
    async def process(
        self, input: dict[Any, Any], request: Request
    ) -> dict[Any, Any] | Response:
        set = settings.convert_in(input)
        set = settings.set_settings(set)
        return {"settings": set}
