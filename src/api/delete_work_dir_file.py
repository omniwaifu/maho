from fastapi import APIRouter, HTTPException
from src.api.models import DeleteWorkDirFileRequest, WorkDirFilesResponse
from src.helpers.file_browser import FileBrowser
from src.helpers import files, runtime
from src.api import get_work_dir_files

router = APIRouter(prefix="/delete_work_dir_file", tags=["files"])

@router.post("", response_model=WorkDirFilesResponse)
async def delete_work_dir_file(request: DeleteWorkDirFileRequest) -> WorkDirFilesResponse:
    """Delete a file from the work directory and return updated file list"""
    file_path = request.path
    if not file_path.startswith("/"):
        file_path = f"/{file_path}"

    res = await runtime.call_development_function(delete_file, file_path)

    if res:
        # Get updated file list
        result = await runtime.call_development_function(
            get_work_dir_files.get_files, request.currentPath
        )
        return WorkDirFilesResponse(
            data=result,
            message="File deleted successfully"
        )
    else:
        raise HTTPException(status_code=404, detail="File not found or could not be deleted")


async def delete_file(file_path: str):
    """Helper function to delete a file"""
    browser = FileBrowser()
    return browser.delete_file(file_path)
