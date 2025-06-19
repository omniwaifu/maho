from src.core.context import AgentContext
from src.core.models import UserMessage
from src.helpers.api import ApiHandler
from flask import Request, Response

from src.helpers import files
import os
from werkzeug.utils import secure_filename
from src.helpers.print_style import PrintStyle


class Message(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        context = await self.communicate(input=input, request=request)
        return await self.respond(context)

    async def respond(self, context: AgentContext):
        return {
            "message": "Message received, processing in background.",
            "context": context.id,
        }

    async def communicate(self, input: dict, request: Request):
        # get context
        context = self.get_context(input.get("context", ""))

        # get message from input
        message = input.get("message", "")

        # get attachments from input
        attachments = input.get("attachments", [])

        # get user message
        user_message = UserMessage(message=message, attachments=attachments)

        # communicate with agent
        await context.communicate(user_message)

        return context
