from fastapi import APIRouter, HTTPException
from src.api.models import RfcRequest, RfcResponse
from src.helpers import runtime
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/rfc", tags=["system"])

@router.post("", response_model=RfcResponse)
async def handle_rfc(request: RfcRequest) -> RfcResponse:
    """Handle RFC (Remote Function Call) requests"""
    try:
        if not request.data:
            raise HTTPException(status_code=400, detail="No RFC data provided")
            
        result = await runtime.handle_rfc(request.data)  # type: ignore
        
        if isinstance(result, dict):
            return RfcResponse(
                data=result,
                message="RFC handled successfully"
            )
        else:
            return RfcResponse(
                data={"result": result},
                message="RFC handled successfully"
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid RFC request: {str(e)}")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"RFC service unavailable: {str(e)}")
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"RFC request timed out: {str(e)}")
    except Exception as e:
        PrintStyle.error(f"RFC handling failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to handle RFC request: {str(e)}"
        )
