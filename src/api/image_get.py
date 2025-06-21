import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from src.helpers import files
from src.helpers.print_style import PrintStyle
from typing import Annotated

router = APIRouter(prefix="/image_get", tags=["files"])

@router.get("")
async def get_image(
    path: Annotated[str, Query(description="Path to the image file")]
) -> FileResponse:
    """Get an image file"""
    try:
        if not path:
            raise HTTPException(status_code=400, detail="No path provided")

        # Sanitize path
        path = path.strip()
        if not path:
            raise HTTPException(status_code=400, detail="Empty path provided")

        # check if path is within base directory
        if not files.is_in_base_dir(path):
            PrintStyle.warning(f"Attempted access to path outside base directory: {path}")
            raise HTTPException(status_code=403, detail="Path is outside of allowed directory")

        # check if file has an image extension
        # list of allowed image extensions
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"]
        # get file extension
        file_ext = os.path.splitext(path)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        # check if file exists
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        # check if it's actually a file (not a directory)
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # check file size (limit to 50MB for images)
        try:
            file_size = os.path.getsize(path)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(status_code=413, detail="Image file too large")
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Image file is empty")
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Unable to access file: {str(e)}")

        # check file permissions
        if not os.access(path, os.R_OK):
            raise HTTPException(status_code=403, detail="Insufficient permissions to read file")

        # send file
        return FileResponse(
            path=path,
            media_type=f"image/{file_ext[1:]}" if file_ext != ".svg" else "image/svg+xml"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied accessing image file")
    except Exception as e:
        PrintStyle.error(f"Failed to serve image {path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")
