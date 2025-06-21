from fastapi import APIRouter, HTTPException
from src.api.models import NudgeRequest, NudgeResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent

router = APIRouter(prefix="/nudge", tags=["control"])

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

@router.post("", response_model=NudgeResponse)
async def nudge_agent(request: NudgeRequest) -> NudgeResponse:
    """Nudge an agent to reset its process"""
    if not request.ctxid:
        raise HTTPException(status_code=400, detail="No context id provided")

    context = get_context(request.ctxid)
    await context.nudge()

    msg = "Process reset, agent nudged."
    context.log.log(type="info", content=msg)

    return NudgeResponse(
        message=msg,
        ctxid=context.id
    )
