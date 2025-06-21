from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from src.api.models import MessageRequest, MessageResponse
from src.core.context import AgentContext
from src.core.models import UserMessage
from src.config.initialization import initialize_agent
from src.helpers import files
import os
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/message", tags=["chat"])

def get_context(context_id: str = "") -> AgentContext:
    """Get or create agent context"""
    if not context_id:
        first = AgentContext.first()
        if first:
            return first
        return AgentContext(config=initialize_agent())
    got = AgentContext.get(context_id)
    if got:
        return got
    return AgentContext(config=initialize_agent(), id=context_id)

@router.post("", response_model=MessageResponse)
async def send_message(request: MessageRequest) -> MessageResponse:
    """Send a message to the agent"""
    try:
        # get context
        context = get_context(request.context or "")

        # get user message
        user_message = UserMessage(message=request.message, attachments=request.attachments)

        # communicate with agent
        await context.communicate(user_message)

        return MessageResponse(
            context=context.id,
            message="Message received, processing in background."
        )
        
    except Exception as e:
        # Handle errors gracefully with proper JSON responses
        error_message = str(e)
        if "Cannot connect to host" in error_message:
            error_message = "Search service is not available. Message processed without search capability."
        elif "Connection refused" in error_message:
            error_message = "External service connection failed. Message processed with limited functionality."
        else:
            error_message = f"Error processing message: {error_message}"
            
        raise HTTPException(
            status_code=500,
            detail=error_message
        )
