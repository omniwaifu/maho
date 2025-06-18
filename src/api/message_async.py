from src.core.context import AgentContext
from src.helpers.api import ApiHandler
from flask import Request, Response

from src.helpers import files
import os
from werkzeug.utils import secure_filename
from src.helpers.defer import DeferredTask
from src.api.message import Message


class MessageAsync(Message):
    async def respond(self, task: DeferredTask, context: AgentContext):
        return {
            "message": "Message received.",
            "context": context.id,
        }
