import base64
from io import BytesIO
import os
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from src.helpers import files, runtime
from src.api import file_info
from typing import Annotated, Union

router = APIRouter(prefix="/download_work_dir_file", tags=["files"])

@router.get("", response_model=None)
async def download_work_dir_file(
    path: Annotated[str, Query(description="File or directory path to download")]
) -> Union[FileResponse, Response]:
    """Download a file or directory (as zip) from the work directory"""
    if not path:
        raise HTTPException(status_code=400, detail="No file path provided")
    
    file_path = path
    if not file_path.startswith("/"):
        file_path = f"/{file_path}"

    file = await runtime.call_development_function(
        file_info.get_file_info, file_path
    )

    if not file["exists"]:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")

    if file["is_dir"]:
        zip_file = await runtime.call_development_function(
            files.zip_dir, file["abs_path"]
        )
        if runtime.is_development():
            b64 = await runtime.call_development_function(fetch_file, zip_file)
            file_data = BytesIO(base64.b64decode(b64))
            return Response(
                content=file_data.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={os.path.basename(zip_file)}"}
            )
        else:
            return FileResponse(
                path=zip_file,
                media_type="application/zip",
                filename=f"{os.path.basename(file_path)}.zip"
            )
    elif file["is_file"]:
        if runtime.is_development():
            b64 = await runtime.call_development_function(
                fetch_file, file["abs_path"]
            )
            file_data = BytesIO(base64.b64decode(b64))
            return Response(
                content=file_data.getvalue(),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
            )
        else:
            return FileResponse(
                path=file["abs_path"],
                media_type="application/octet-stream", 
                filename=os.path.basename(file["file_name"])
            )
    
    raise HTTPException(status_code=404, detail=f"File {file_path} not found")


async def fetch_file(path):
    """Helper function to fetch file content as base64"""
    with open(path, "rb") as file:
        file_content = file.read()
        return base64.b64encode(file_content).decode("utf-8")
