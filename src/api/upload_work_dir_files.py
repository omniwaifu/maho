import base64
from src.helpers.api import ApiHandler
from fastapi import Request, Response, UploadFile, File, Form, APIRouter
from typing import List, Optional

from src.helpers.file_browser import FileBrowser
from src.helpers import files, runtime
from src.api import get_work_dir_files
import os

# Create router for this endpoint
router = APIRouter()

class UploadWorkDirFiles(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        # This endpoint should be called directly with FastAPI's file upload handling
        # The input dict won't contain files - they come through FastAPI's dependency injection
        raise Exception("This endpoint should be called with proper file upload parameters")


# Create proper FastAPI endpoint function that will be registered
@router.post("/upload_work_dir_files")
async def upload_files_endpoint(
    uploaded_files: List[UploadFile] = File(...),
    path: str = Form("")
) -> dict:
    """Proper FastAPI file upload endpoint"""
    
    if not uploaded_files:
        raise Exception("No files uploaded")

    current_path = path
    
    successful, failed = await upload_files(uploaded_files, current_path)

    if not successful and failed:
        raise Exception("All uploads failed")

    result = await runtime.call_development_function(
        get_work_dir_files.get_files, current_path
    )

    return {
        "message": (
            "Files uploaded successfully"
            if not failed
            else "Some files failed to upload"
        ),
        "data": result,
        "successful": successful,
        "failed": failed,
    }


async def upload_files(uploaded_files: List[UploadFile], current_path: str):
    if runtime.is_development():
        successful = []
        failed = []
        for file in uploaded_files:
            file_content = await file.read()
            base64_content = base64.b64encode(file_content).decode("utf-8")
            if await runtime.call_development_function(
                upload_file, current_path, file.filename, base64_content
            ):
                successful.append(file.filename)
            else:
                failed.append(file.filename)
    else:
        browser = FileBrowser()
        successful, failed = browser.save_files(uploaded_files, current_path)

    return successful, failed


async def upload_file(current_path: str, filename: str, base64_content: str):
    browser = FileBrowser()
    return browser.save_file_b64(current_path, filename, base64_content)
