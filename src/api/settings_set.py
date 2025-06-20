from src.helpers.api import ApiHandler
from fastapi import Request, Response

from src.helpers import settings

from typing import Any


class SetSettings(ApiHandler):
    async def process(
        self, input: dict[Any, Any], request: Request
    ) -> dict[Any, Any] | Response:
        set = settings.convert_in(input)
        settings.set_settings(set)
        # Return the updated settings via convert_out
        updated_settings = settings.convert_out(settings.get_settings())
        return {"settings": updated_settings.model_dump()}
