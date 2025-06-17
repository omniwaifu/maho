from src.helpers.api import ApiHandler
from flask import Request, Response

from src.helpers import settings


class GetSettings(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        set = settings.convert_out(settings.get_settings())
        return {"settings": set}
