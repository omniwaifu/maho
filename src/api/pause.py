from fastapi import APIRouter, HTTPException
from src.api.models import PauseRequest, PauseResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/pause", tags=["control"])

def get_context(context_id: str = "") -> AgentContext:
    """Get or create agent context"""
    try:
        if not context_id:
            first = AgentContext.first()
            if first:
                return first
            return AgentContext(config=initialize_agent())
        got = AgentContext.get(context_id)
        if got:
            return got
        return AgentContext(config=initialize_agent(), id=context_id)
    except Exception as e:
        PrintStyle.error(f"Failed to get or create context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get or create context: {str(e)}")

@router.post("", response_model=PauseResponse)
async def pause_agent(request: PauseRequest) -> PauseResponse:
    """Pause or unpause an agent"""
    try:
        # Validate request
        if request.paused is None:
            raise HTTPException(status_code=400, detail="'paused' field is required")
        
        # context instance - get or create
        context = get_context(request.context or "")
        
        if not context:
            raise HTTPException(status_code=500, detail="Failed to get agent context")
        
        # Log the pause/unpause action
        action = "paused" if request.paused else "unpaused"
        PrintStyle.info(f"Agent {context.id} is being {action}")
        
        # Set pause state
        context.paused = request.paused
        
        # Log to context
        message = f"Agent {action} via API"
        context.log.log(type="info", content=message)
        
        return PauseResponse(
            message=f"Agent {action}.",
            paused=request.paused
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        PrintStyle.error(f"Failed to pause/unpause agent: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to pause/unpause agent: {str(e)}"
        )
