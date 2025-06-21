from fastapi import APIRouter, HTTPException
from src.api.models import ChatResetRequest, BaseResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers import persist_chat
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/chat_reset", tags=["chat"])

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

@router.post("", response_model=BaseResponse)
async def reset_chat(request: ChatResetRequest) -> BaseResponse:
    """Reset a chat context"""
    try:
        context_id = request.context or ""
        
        # Log the reset action
        PrintStyle.info(f"Resetting chat context: {context_id if context_id else 'default'}")
        
        # context instance - get or create
        try:
            context = get_context(context_id)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to get context for reset: {str(e)}"
            )
        
        if not context:
            raise HTTPException(status_code=500, detail="Failed to get agent context")
        
        # Log to context before reset
        context.log.log(type="info", content="Chat reset requested via API")
        
        # Reset the context
        try:
            context.reset()
            PrintStyle.info(f"Context {context.id} reset successfully")
        except Exception as e:
            PrintStyle.error(f"Failed to reset context {context.id}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to reset context: {str(e)}"
            )
        
        # Save the reset context
        try:
            persist_chat.save_tmp_chat(context)
            PrintStyle.info(f"Context {context.id} saved after reset")
        except PermissionError:
            PrintStyle.error(f"Permission denied saving context {context.id}")
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to save chat after reset"
            )
        except Exception as e:
            PrintStyle.error(f"Failed to save context {context.id} after reset: {str(e)}")
            # Don't fail the operation if save fails, just log the warning
            PrintStyle.warning("Chat reset completed but failed to save - changes may be lost")

        return BaseResponse(message="Agent restarted.")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        PrintStyle.error(f"Failed to reset chat: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to reset chat: {str(e)}"
        )
