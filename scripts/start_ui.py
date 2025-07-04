#!/usr/bin/env python3
"""
Main UI entry point for the Maho application.
This replaces the old run_ui.py file.
"""

import os
import sys
import time
import socket
import struct
from functools import wraps
import threading
import signal
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import anyio

# Add the project root to Python path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.initialization import initialize_agent
from src.helpers import errors, files, git, mcp_server
from src.helpers.files import get_abs_path
from src.helpers import runtime, dotenv, process
from src.helpers.extract_tools import load_classes_from_folder
from src.helpers.api import ApiHandler
from src.helpers.print_style import PrintStyle


# Set the new timezone to 'UTC'
os.environ["TZ"] = "UTC"
# Apply the timezone change
time.tzset()

# Initialize FastAPI app
app = FastAPI(
    title="Maho Agent API",
    description="AI Agent with tools, memory, and scheduling",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and status endpoints"
        },
        {
            "name": "chat",
            "description": "Chat and messaging operations"
        },
        {
            "name": "files",
            "description": "File management and operations"
        },
        {
            "name": "settings",
            "description": "Configuration and settings management"
        },
        {
            "name": "mcp",
            "description": "Model Context Protocol server operations"
        },
        {
            "name": "scheduler",
            "description": "Task scheduling and automation"
        },
        {
            "name": "tunnel",
            "description": "Tunnel management for remote access"
        },
        {
            "name": "system",
            "description": "System control and management"
        },
        {
            "name": "audio",
            "description": "Audio processing and transcription"
        },
        {
            "name": "control",
            "description": "Agent control and intervention"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files properly - individual directories first
app.mount("/styles", StaticFiles(directory=get_abs_path("./webui/styles")), name="styles")
app.mount("/js", StaticFiles(directory=get_abs_path("./webui/js")), name="js")
app.mount("/public", StaticFiles(directory=get_abs_path("./webui/public")), name="public")
app.mount("/components", StaticFiles(directory=get_abs_path("./webui/components")), name="components")
app.mount("/dist", StaticFiles(directory=get_abs_path("./webui/dist")), name="dist")

# Add specific favicon routes to ensure they work properly
@app.get("/favicon.ico", response_class=FileResponse, responses={
    200: {"description": "Favicon icon file"},
    404: {"description": "Favicon not found"}
})
async def get_favicon_ico():
    return FileResponse(get_abs_path("./webui/public/favicon.ico"), media_type="image/x-icon")

@app.get("/favicon.png", response_class=FileResponse, responses={
    200: {"description": "Favicon PNG file"},
    404: {"description": "Favicon not found"}
})
async def get_favicon_png():
    return FileResponse(get_abs_path("./webui/public/favicon.png"), media_type="image/png")

@app.get("/favicon-16x16.png", response_class=FileResponse, responses={
    200: {"description": "16x16 favicon PNG file"},
    404: {"description": "Favicon not found"}
})
async def get_favicon_16():
    return FileResponse(get_abs_path("./webui/public/favicon-16x16.png"), media_type="image/png")

@app.get("/favicon-32x32.png", response_class=FileResponse, responses={
    200: {"description": "32x32 favicon PNG file"},
    404: {"description": "Favicon not found"}
})
async def get_favicon_32():
    return FileResponse(get_abs_path("./webui/public/favicon-32x32.png"), media_type="image/png")

@app.get("/favicon-48x48.png", response_class=FileResponse, responses={
    200: {"description": "48x48 favicon PNG file"},
    404: {"description": "Favicon not found"}
})
async def get_favicon_48():
    return FileResponse(get_abs_path("./webui/public/favicon-48x48.png"), media_type="image/png")

# Add specific routes for root-level files
@app.get("/index.css", response_class=FileResponse, responses={
    200: {"description": "Main CSS stylesheet"},
    404: {"description": "CSS file not found"}
})
async def serve_index_css():
    return FileResponse(get_abs_path("./webui/index.css"), media_type="text/css")

@app.get("/index.js", response_class=FileResponse, responses={
    200: {"description": "Main JavaScript file"},
    404: {"description": "JavaScript file not found"}
})
async def serve_index_js():
    return FileResponse(get_abs_path("./webui/index.js"), media_type="text/javascript")

@app.get("/ascii-art.txt", response_class=FileResponse, responses={
    200: {"description": "ASCII art text file"},
    404: {"description": "ASCII art file not found"}
})
async def serve_ascii_art():
    return FileResponse(get_abs_path("./webui/ascii-art.txt"), media_type="text/plain")

# Security
security = HTTPBasic()


def is_loopback_address(address):
    loopback_checker = {
        socket.AF_INET: lambda x: struct.unpack("!I", socket.inet_aton(x))[0]
        >> (32 - 8)
        == 127,
        socket.AF_INET6: lambda x: x == "::1",
    }
    address_type = "hostname"
    try:
        socket.inet_pton(socket.AF_INET6, address)
        address_type = "ipv6"
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET, address)
            address_type = "ipv4"
        except socket.error:
            address_type = "hostname"

    if address_type == "ipv4":
        return loopback_checker[socket.AF_INET](address)
    elif address_type == "ipv6":
        return loopback_checker[socket.AF_INET6](address)
    else:
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                r = socket.getaddrinfo(address, None, family, socket.SOCK_STREAM)
            except socket.gaierror:
                return False
            for family, _, _, _, sockaddr in r:
                if not loopback_checker[family](sockaddr[0]):
                    return False
        return True


async def verify_api_key(request: Request):
    """Verify API key from headers only (don't consume request body)"""
    valid_api_key = dotenv.get_dotenv_value("API_KEY")
    if not valid_api_key:
        return True  # No API key configured
        
    # Check headers only - don't consume request body
    api_key = request.headers.get("X-API-KEY")
    
    if api_key != valid_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return True


async def verify_loopback(request: Request):
    """Verify request comes from loopback address"""
    client_host = request.client.host if request.client else "127.0.0.1"
    if not is_loopback_address(client_host):
        raise HTTPException(status_code=403, detail="Access denied")
    return True


async def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication"""
    user = dotenv.get_dotenv_value("AUTH_LOGIN")
    password = dotenv.get_dotenv_value("AUTH_PASSWORD")
    
    if not user or not password:
        return True  # No auth configured
        
    if credentials.username != user or credentials.password != password:
        raise HTTPException(
            status_code=401,
            detail="Could not verify your access level",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


# Handle default address, load index
@app.get("/", response_class=HTMLResponse, responses={
    200: {"description": "Web UI index page"},
    401: {"description": "Authentication required"},
    403: {"description": "Access forbidden"}
})
async def serve_index(auth: bool = Depends(verify_auth)):
    gitinfo = None
    try:
        gitinfo = git.get_git_info()
    except Exception:
        gitinfo = {
            "version": "unknown",
            "commit_time": "unknown",
        }
    return files.read_file(
        "./webui/index.html",
        version_no=gitinfo["version"],
        version_time=gitinfo["commit_time"],
    )


def init_maho():
    """Initialize contexts and MCP"""
    from src.config.initialization import (
        initialize_chats,
        initialize_mcp,
        initialize_job_loop,
    )

    # initialize chats
    initialize_chats()

    # initialize MCP
    initialize_mcp()

    # initialize job loop
    initialize_job_loop()


def register_api_handler(app: FastAPI, handler: type[ApiHandler]):
    """Register an API handler with appropriate security"""
    name = handler.__module__.split(".")[-1]
    
    async def create_endpoint(request: Request):
        instance = handler(app, None)  # No thread lock needed in async
        return await instance.handle_request_async(request)
    
    # Determine dependencies based on handler requirements
    dependencies = []
    if handler.requires_loopback():
        dependencies.append(Depends(verify_loopback))
    elif handler.requires_api_key():
        dependencies.append(Depends(verify_api_key))
    elif handler.requires_auth():
        dependencies.append(Depends(verify_auth))
    else:
        # Fallback to auth
        dependencies.append(Depends(verify_auth))
    
    # Register GET and POST separately with unique operation IDs
    app.add_api_route(
        f"/{name}",
        create_endpoint,
        methods=["GET"],
        dependencies=dependencies,
        operation_id=f"{name}_get"
    )
    
    app.add_api_route(
        f"/{name}",
        create_endpoint,
        methods=["POST"],
        dependencies=dependencies,
        operation_id=f"{name}_post"
    )


def register_file_upload_endpoints(app: FastAPI):
    """Register proper FastAPI file upload endpoints"""
    from src.api.upload_work_dir_files import upload_files_endpoint
    from src.api.import_knowledge import import_knowledge_endpoint
    
    # Register file upload endpoints with proper FastAPI patterns
    app.add_api_route(
        "/upload_work_dir_files",
        upload_files_endpoint,
        methods=["POST"],
        dependencies=[Depends(verify_auth)]
    )
    
    app.add_api_route(
        "/import_knowledge",
        import_knowledge_endpoint,
        methods=["POST"],
        dependencies=[Depends(verify_auth)]
    )


async def run():
    # Initialize runtime to parse command line arguments
    runtime.initialize()
    
    # Suppress httpx cleanup warnings during shutdown
    runtime.suppress_httpx_cleanup_warnings()
    
    PrintStyle().print("Initializing framework...")
    PrintStyle().print("Starting FastAPI server...")

    # Get configuration from environment
    port = runtime.get_web_ui_port()
    host = (
        runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "0.0.0.0"
    )

    # Include the new FastAPI router system
    from src.api.router import api_router
    app.include_router(api_router)

    # Initialize and register remaining API handlers (to be migrated)
    handlers = load_classes_from_folder("src/api", "*.py", ApiHandler)
    for handler in handlers:
        # Skip the ones we've already converted to routers
        module_name = handler.__module__.split(".")[-1]
        converted_modules = [
            "health", "settings_get", "settings_set", "message", "message_async",
            "restart", "pause", "nudge", "history_get", "chat_reset", "chat_load", 
            "chat_remove", "chat_export", "tunnel", "rfc", "file_info", 
            "get_work_dir_files", "delete_work_dir_file", "mcp_servers_status", 
            "scheduler_tasks_list", "image_get", "ctx_window_get", "mcp_servers_apply",
            "mcp_server_get_detail", "mcp_server_get_log", "transcribe", "download_work_dir_file",
            "scheduler_tick", "tunnel_proxy", "upload", "scheduler_task_create",
            "scheduler_task_update", "scheduler_task_run", "scheduler_task_delete", "poll",
            "upload_work_dir_files", "import_knowledge", "test_connection"
        ]
        if module_name not in converted_modules:
            register_api_handler(app, handler)

    # File upload endpoints are now part of the API router
    # register_file_upload_endpoints(app)
    
    # MCP server
    # TODO: Implement MCP server registration
    # mcp_server.register_server(app)

    try:
        PrintStyle().print(f"Maho Web UI running at http://{host}:{port}")
        PrintStyle().print(f"API documentation available at http://{host}:{port}/docs")

        # Initialize Maho in background
        threading.Thread(target=init_maho, daemon=True).start()

        # Configure uvicorn
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,  # Disable access logs for cleaner output
        )
        server = uvicorn.Server(config)
        
        # Run with anyio
        await server.serve()

    except Exception as e:
        PrintStyle().error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    anyio.run(run)
 