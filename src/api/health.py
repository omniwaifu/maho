from src.helpers.api import ApiHandler
from flask import Request, Response
from src.helpers import errors

from src.helpers import git


class HealthCheck(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        gitinfo = None
        error = None
        try:
            gitinfo = git.get_git_info()
        except Exception as e:
            error = errors.error_text(e)

        return {"gitinfo": gitinfo, "error": error}
