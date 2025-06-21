from fastapi import APIRouter
from src.api.models import HistoryGetRequest, HistoryGetResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers import tokens

router = APIRouter(prefix="/history_get", tags=["chat"])

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

@router.post("", response_model=HistoryGetResponse)
async def get_history(request: HistoryGetRequest) -> HistoryGetResponse:
    """Get chat history for a context"""
    context = get_context(request.context or "")
    agent = context.streaming_agent or context.agent0
    history = agent.history.output_text()
    size = agent.history.get_tokens()

    return HistoryGetResponse(
        history=history,
        tokens=size,
        message="History retrieved successfully"
    )
