from fastapi import APIRouter, HTTPException
from src.api.models import TranscribeRequest, TranscribeResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers import runtime, settings, whisper
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/transcribe", tags=["audio"])

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

@router.post("", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest) -> TranscribeResponse:
    """Transcribe audio to text using Whisper"""
    try:
        if not request.audio:
            raise HTTPException(status_code=400, detail="No audio data provided")
            
        context = get_context(request.ctxid or "")
        
        if await whisper.is_downloading():
            context.log.log(
                type="info",
                content="Whisper model is currently being downloaded, please wait...",
            )
            raise HTTPException(
                status_code=503, 
                detail="Whisper model is downloading, please wait and try again"
            )

        try:
            set = settings.get_settings()
            stt_model = set.get("stt_model_size")
            if not stt_model:
                raise HTTPException(status_code=500, detail="Speech-to-text model not configured")
                
            result = await whisper.transcribe(stt_model, request.audio)  # type: ignore
        except FileNotFoundError:
            raise HTTPException(
                status_code=500, 
                detail="Whisper model files not found. Please check configuration."
            )
        except PermissionError:
            raise HTTPException(
                status_code=500, 
                detail="Insufficient permissions to access Whisper model files"
            )
        
        # Handle different result formats
        if isinstance(result, dict):
            raw_text = result.get("text", "")
            text = str(raw_text) if raw_text is not None else ""
            return TranscribeResponse(
                text=text,
                data=result,
                message="Audio transcribed successfully"
            )
        else:
            return TranscribeResponse(
                text=str(result),
                data={"raw_result": result},
                message="Audio transcribed successfully"
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {str(e)}")
    except Exception as e:
        PrintStyle.error(f"Transcription failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Transcription failed: {str(e)}"
        )
