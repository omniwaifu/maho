from fastapi import APIRouter, HTTPException
from src.api.models import HealthResponse
from src.helpers import errors, git
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/health", tags=["health"])

@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Get API health status with git information"""
    try:
        gitinfo = None
        error = None
        
        try:
            gitinfo = git.get_git_info()
            if gitinfo:
                PrintStyle.info(f"Git info retrieved: {gitinfo}")
        except FileNotFoundError:
            error = "Git repository not found or Git not installed"
            PrintStyle.warning(error)
        except PermissionError:
            error = "Insufficient permissions to access Git repository"
            PrintStyle.warning(error)
        except Exception as e:
            error = errors.error_text(e)
            PrintStyle.warning(f"Failed to get Git info: {error}")

        # Perform additional health checks
        health_status = "healthy"
        health_message = ""
        
        try:
            # Check if we can access the file system
            import os
            import tempfile
            test_file = os.path.join(tempfile.gettempdir(), "health_check_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            health_status = "degraded"
            health_message = f"File system access limited: {str(e)}"
            PrintStyle.warning(health_message)

        # Build final message
        if gitinfo:
            final_message = f"Git: {gitinfo}"
        elif error:
            final_message = f"Git Error: {error}"
        else:
            final_message = "Git status unknown"
            
        if health_message:
            final_message += f" | {health_message}"

        return HealthResponse(
            status=health_status,
            message=final_message
        )
        
    except Exception as e:
        PrintStyle.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Health check failed: {str(e)}"
        )
