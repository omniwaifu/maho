from src.helpers.api import ApiHandler
from fastapi import Request, Response, UploadFile, File, Form
from typing import List

from src.helpers import files as file_helpers
import os


class Upload(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        # This endpoint should be called directly with FastAPI's file upload handling
        raise Exception("This endpoint should be called with proper file upload parameters")


# Create proper FastAPI endpoint function
async def upload_endpoint(
    files: List[UploadFile] = File(...)
) -> dict:
    """Proper FastAPI file upload endpoint"""
    
    if not files:
        raise Exception("No files uploaded")

    uploaded_files = []
    
    for file in files:
        if file.filename:
            # Save file to work directory
            work_dir = file_helpers.get_work_dir()
            file_path = os.path.join(work_dir, file.filename)
            
            # Read and save file content
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
                
            uploaded_files.append({
                "filename": file.filename,
                "size": len(content),
                "path": file_path
            })

    return {
        "message": f"Uploaded {len(uploaded_files)} files successfully",
        "files": uploaded_files
    }
