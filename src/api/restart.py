from fastapi import APIRouter, Response, HTTPException
from src.helpers import process
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/restart", tags=["system"])

@router.post("", status_code=200)
async def restart_system() -> Response:
    """Restart the system"""
    try:
        PrintStyle.info("System restart requested via API")
        process.reload()
        return Response(status_code=200)
    except PermissionError:
        raise HTTPException(
            status_code=403, 
            detail="Insufficient permissions to restart the system"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, 
            detail="System restart command not found"
        )
    except Exception as e:
        PrintStyle.error(f"Failed to restart system: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to restart system: {str(e)}"
        )
