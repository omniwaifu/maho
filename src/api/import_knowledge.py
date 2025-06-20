from src.helpers.api import ApiHandler
from fastapi import Request, Response, UploadFile, File, Form
from typing import List

from src.helpers.file_browser import FileBrowser
from src.helpers import files, memory
import os
import re


class ImportKnowledge(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        # This endpoint should be called directly with FastAPI's file upload handling
        raise Exception("This endpoint should be called with proper file upload parameters")


# Create proper FastAPI endpoint function
async def import_knowledge_endpoint(
    files: List[UploadFile] = File(...),
    path: str = Form("")
) -> dict:
    """Proper FastAPI file upload endpoint for knowledge import"""
    
    if not files:
        raise Exception("No files uploaded")

    successful = []
    failed = []
    
    for file in files:
        try:
            if file.filename:
                # Read file content
                content = await file.read()
                
                # Save to temporary location for processing
                temp_path = f"/tmp/{file.filename}"
                with open(temp_path, "wb") as f:
                    f.write(content)
                
                # Process the file for knowledge import
                # This would typically involve parsing and indexing the content
                await memory.import_file(temp_path)
                
                successful.append(file.filename)
                
                # Clean up temp file
                os.remove(temp_path)
            else:
                failed.append("unnamed_file")
                
        except Exception as e:
            failed.append(file.filename or "unknown_file")

    return {
        "message": f"Imported {len(successful)} files successfully",
        "successful": successful,
        "failed": failed
    }
