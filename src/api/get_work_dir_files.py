from fastapi import APIRouter, Query, HTTPException
from src.api.models import WorkDirFilesResponse
from src.helpers.file_browser import FileBrowser
from src.helpers import files, runtime
from src.helpers.print_style import PrintStyle
from typing import Annotated

router = APIRouter(prefix="/get_work_dir_files", tags=["files"])

@router.get("", response_model=WorkDirFilesResponse)
async def get_work_dir_files(
    path: Annotated[str, Query(description="Directory path to list files from")] = ""
) -> WorkDirFilesResponse:
    """Get files and directories in the work directory"""
    try:
        current_path = path
        
        # Handle special path cases
        if current_path == "$WORK_DIR":
            current_path = "root"
        
        # Sanitize path
        if current_path:
            current_path = current_path.strip()
            
            # Check for suspicious path patterns
            if '..' in current_path:
                PrintStyle.warning(f"Suspicious directory path requested: {current_path}")
                # Still allow it but log the warning - file browser should handle security
        
        try:
            result = await runtime.call_development_function(get_files, current_path)
        except PermissionError:
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions to access directory: {current_path}"
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, 
                detail=f"Directory not found: {current_path}"
            )
        except Exception as e:
            PrintStyle.error(f"Failed to get files for path {current_path}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to retrieve directory contents: {str(e)}"
            )

        if not result:
            raise HTTPException(
                status_code=500, 
                detail="No file listing data returned"
            )

        return WorkDirFilesResponse(
            data=result,
            message="Files retrieved successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        PrintStyle.error(f"Failed to get work directory files: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve work directory files: {str(e)}"
        )


async def get_files(path):
    """Helper function to get files in a directory"""
    try:
        browser = FileBrowser()
        return browser.get_files(path)
    except PermissionError:
        raise PermissionError(f"Permission denied accessing directory: {path}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Directory not found: {path}")
    except Exception as e:
        PrintStyle.error(f"FileBrowser.get_files failed for {path}: {str(e)}")
        raise
