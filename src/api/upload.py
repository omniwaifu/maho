from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from src.api.models import FileUploadResponse
from src.helpers import files as file_helpers
from src.helpers.print_style import PrintStyle
import os

router = APIRouter(prefix="/upload", tags=["files"])

@router.post("", response_model=FileUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...)
) -> FileUploadResponse:
    """Upload files to the work directory"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Check if any files were actually sent
    if len(files) == 1 and not files[0].filename:
        raise HTTPException(status_code=400, detail="No files selected for upload")

    uploaded_files = []
    failed_files = []
    
    try:
        work_dir = file_helpers.get_abs_path("root")
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir, exist_ok=True)
            except PermissionError:
                raise HTTPException(
                    status_code=403, 
                    detail="Insufficient permissions to create work directory"
                )
        
        for file in files:
            try:
                if not file.filename:
                    failed_files.append("unnamed_file")
                    continue
                
                # Validate filename
                if any(char in file.filename for char in ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']):
                    failed_files.append(f"{file.filename} (invalid filename)")
                    continue
                
                # Check file size (limit to 100MB)
                if file.size and file.size > 100 * 1024 * 1024:
                    failed_files.append(f"{file.filename} (file too large)")
                    continue
                
                # Save file to work directory
                file_path = os.path.join(work_dir, file.filename)
                
                # Check if file already exists
                if os.path.exists(file_path):
                    PrintStyle.warning(f"Overwriting existing file: {file.filename}")
                
                # Read and save file content
                content = await file.read()
                if not content:
                    failed_files.append(f"{file.filename} (empty file)")
                    continue
                
                with open(file_path, "wb") as f:
                    f.write(content)
                    
                uploaded_files.append(file.filename)
                PrintStyle.info(f"Successfully uploaded: {file.filename}")
                
            except PermissionError:
                failed_files.append(f"{file.filename or 'unknown_file'} (permission denied)")
            except OSError as e:
                failed_files.append(f"{file.filename or 'unknown_file'} (disk error: {str(e)})")
            except Exception as e:
                PrintStyle.error(f"Failed to upload {file.filename}: {str(e)}")
                failed_files.append(f"{file.filename or 'unknown_file'} (upload error)")

        if not uploaded_files and failed_files:
            raise HTTPException(
                status_code=400, 
                detail=f"All file uploads failed. Failed files: {', '.join(failed_files)}"
            )

        return FileUploadResponse(
            uploaded_files=uploaded_files,
            failed_files=failed_files,
            message=f"Uploaded {len(uploaded_files)} files successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        PrintStyle.error(f"File upload operation failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"File upload operation failed: {str(e)}"
        )
