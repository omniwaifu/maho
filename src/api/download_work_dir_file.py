import base64
from io import BytesIO

from src.helpers.api import ApiHandler, Input, Output, Request, Response
from fastapi.responses import FileResponse

from src.helpers import files, runtime
from src.api import file_info
import os


class DownloadFile(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        file_path = request.query_params.get("path", input.get("path", ""))
        if not file_path:
            raise ValueError("No file path provided")
        if not file_path.startswith("/"):
            file_path = f"/{file_path}"

        file = await runtime.call_development_function(
            file_info.get_file_info, file_path
        )

        if not file["exists"]:
            raise Exception(f"File {file_path} not found")

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
        raise Exception(f"File {file_path} not found")


async def fetch_file(path):
    with open(path, "rb") as file:
        file_content = file.read()
        return base64.b64encode(file_content).decode("utf-8")
