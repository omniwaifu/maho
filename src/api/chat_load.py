from fastapi import APIRouter, HTTPException
from src.api.models import ChatLoadRequest, ChatLoadResponse
from src.helpers import persist_chat

router = APIRouter(prefix="/chat_load", tags=["chat"])

@router.post("", response_model=ChatLoadResponse)
async def load_chats(request: ChatLoadRequest) -> ChatLoadResponse:
    """Load chats from provided data"""
    if not request.chats:
        raise HTTPException(status_code=400, detail="No chats provided")

    ctxids = persist_chat.load_json_chats(request.chats)

    return ChatLoadResponse(
        message="Chats loaded.",
        ctxids=ctxids
    )
