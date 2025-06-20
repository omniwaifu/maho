from src.core.context import AgentContext
from src.helpers.api import ApiHandler
from fastapi import Request, Response

from src.helpers import files
import os
import re
from src.api.message import Message


class MessageAsync(Message):
    async def respond(self, context: AgentContext):
        return {
            "message": "Message received",
            "context": context.id,
        }
