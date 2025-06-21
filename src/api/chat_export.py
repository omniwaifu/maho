from fastapi import APIRouter, HTTPException
from src.api.models import ChatExportRequest, ChatExportResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers import persist_chat
import json

router = APIRouter(prefix="/chat_export", tags=["chat"])

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

@router.post("", response_model=ChatExportResponse)
async def export_chat(request: ChatExportRequest) -> ChatExportResponse:
    """Export a chat context as JSON"""
    if not request.ctxid:
        raise HTTPException(status_code=400, detail="No context id provided")

    context = get_context(request.ctxid)
    content_json = persist_chat.export_json_chat(context)
    content = json.loads(content_json)
    
    return ChatExportResponse(
        message="Chat exported.",
        ctxid=context.id,
        content=content
    )
