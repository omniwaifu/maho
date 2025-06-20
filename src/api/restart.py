from src.helpers.api import ApiHandler
from fastapi import Request, Response

from src.helpers import process


class Restart(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        process.reload()
        return Response(status_code=200)
