import os
from fastapi import APIRouter, HTTPException
from src.api.models import FileInfoRequest, FileInfoResponse, FileInfoDetail
from src.helpers import files, runtime
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/file_info", tags=["files"])

@router.post("", response_model=FileInfoResponse)
async def get_file_info_endpoint(request: FileInfoRequest) -> FileInfoResponse:
    """Get detailed information about a file or directory"""
    try:
        if not request.path:
            raise HTTPException(status_code=400, detail="No file path provided")
        
        # Sanitize path
        path = request.path.strip()
        if not path:
            raise HTTPException(status_code=400, detail="Empty file path provided")
        
        # Check for suspicious path patterns
        if '..' in path or path.startswith('/'):
            PrintStyle.warning(f"Suspicious file path requested: {path}")
        
        info = await runtime.call_development_function(get_file_info, path)
        
        if not info:
            raise HTTPException(status_code=500, detail="Failed to retrieve file information")
        
        return FileInfoResponse(
            file_info=FileInfoDetail(**info),
            message="File information retrieved successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid file path: {str(e)}")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Permission denied: {str(e)}")
    except Exception as e:
        PrintStyle.error(f"Failed to get file info for {request.path}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve file information: {str(e)}"
        )


async def get_file_info(path: str) -> dict:
    """Get file information for the given path"""
    try:
        abs_path = files.get_abs_path(path)
        exists = os.path.exists(abs_path)
        message = ""

        if not exists:
            message = f"File {path} not found."

        return {
            "input_path": path,
            "abs_path": abs_path,
            "exists": exists,
            "is_dir": os.path.isdir(abs_path) if exists else False,
            "is_file": os.path.isfile(abs_path) if exists else False,
            "is_link": os.path.islink(abs_path) if exists else False,
            "size": os.path.getsize(abs_path) if exists else 0,
            "modified": os.path.getmtime(abs_path) if exists else 0,
            "created": os.path.getctime(abs_path) if exists else 0,
            "permissions": os.stat(abs_path).st_mode if exists else 0,
            "dir_path": os.path.dirname(abs_path),
            "file_name": os.path.basename(abs_path),
            "file_ext": os.path.splitext(abs_path)[1],
            "message": message,
        }
    except PermissionError:
        return {
            "input_path": path,
            "abs_path": abs_path if 'abs_path' in locals() else "",
            "exists": False,
            "is_dir": False,
            "is_file": False,
            "is_link": False,
            "size": 0,
            "modified": 0,
            "created": 0,
            "permissions": 0,
            "dir_path": "",
            "file_name": "",
            "file_ext": "",
            "message": f"Permission denied accessing {path}",
        }
    except Exception as e:
        return {
            "input_path": path,
            "abs_path": abs_path if 'abs_path' in locals() else "",
            "exists": False,
            "is_dir": False,
            "is_file": False,
            "is_link": False,
            "size": 0,
            "modified": 0,
            "created": 0,
            "permissions": 0,
            "dir_path": "",
            "file_name": "",
            "file_ext": "",
            "message": f"Error accessing {path}: {str(e)}",
        }
