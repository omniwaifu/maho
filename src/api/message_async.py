from src.core.context import AgentContext
from src.helpers.api import ApiHandler
from flask import Request, Response

from src.helpers import files
import os
from werkzeug.utils import secure_filename
from src.api.message import Message


class MessageAsync(Message):
    async def respond(self, context: AgentContext):
        return {
            "message": "Message received",
            "context": context.id,
        }
