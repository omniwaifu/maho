from fastapi import APIRouter
from src.api.models import CtxWindowGetRequest, CtxWindowGetResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent

router = APIRouter(prefix="/ctx_window_get", tags=["context"])

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

@router.post("", response_model=CtxWindowGetResponse)
async def get_ctx_window(request: CtxWindowGetRequest) -> CtxWindowGetResponse:
    """Get context window information for an agent"""
    context = get_context(request.context or "")
    agent = context.streaming_agent or context.agent0
    window = agent.get_data(agent.DATA_NAME_CTX_WINDOW)
    
    if not window or not isinstance(window, dict):
        return CtxWindowGetResponse(
            content="",
            tokens=0,
            message="No context window data available"
        )

    text = window["text"]
    tokens = window["tokens"]

    return CtxWindowGetResponse(
        content=text,
        tokens=tokens,
        message="Context window retrieved successfully"
    )
