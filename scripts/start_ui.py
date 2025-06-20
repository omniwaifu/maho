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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    version="1.0.0"
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
app.mount("/css", StaticFiles(directory=get_abs_path("./webui/css")), name="css")
app.mount("/js", StaticFiles(directory=get_abs_path("./webui/js")), name="js") 
app.mount("/public", StaticFiles(directory=get_abs_path("./webui/public")), name="public")
app.mount("/components", StaticFiles(directory=get_abs_path("./webui/components")), name="components")

# Add specific favicon routes to ensure they work properly
@app.get("/favicon.ico")
async def get_favicon_ico():
    from fastapi.responses import FileResponse
    return FileResponse(get_abs_path("./webui/public/favicon.ico"))

@app.get("/favicon.png")
async def get_favicon_png():
    from fastapi.responses import FileResponse
    return FileResponse(get_abs_path("./webui/public/favicon.png"))

@app.get("/favicon-16x16.png")
async def get_favicon_16():
    from fastapi.responses import FileResponse
    return FileResponse(get_abs_path("./webui/public/favicon-16x16.png"))

@app.get("/favicon-32x32.png")
async def get_favicon_32():
    from fastapi.responses import FileResponse
    return FileResponse(get_abs_path("./webui/public/favicon-32x32.png"))

@app.get("/favicon-48x48.png")
async def get_favicon_48():
    from fastapi.responses import FileResponse
    return FileResponse(get_abs_path("./webui/public/favicon-48x48.png"))

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
@app.get("/", response_class=HTMLResponse)
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
    from src.api.upload import upload_endpoint
    from src.api.import_knowledge import import_knowledge_endpoint
    
    # Register file upload endpoints with proper FastAPI patterns
    app.add_api_route(
        "/upload_work_dir_files",
        upload_files_endpoint,
        methods=["POST"],
        dependencies=[Depends(verify_auth)]
    )
    
    app.add_api_route(
        "/upload",
        upload_endpoint,
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

    # Initialize and register API handlers
    handlers = load_classes_from_folder("src/api", "*.py", ApiHandler)
    for handler in handlers:
        register_api_handler(app, handler)

    # Register file upload endpoints
    register_file_upload_endpoints(app)
    
    # Add individual file routes for main CSS/JS files
    from fastapi.responses import FileResponse
    
    @app.get("/index.css")
    async def serve_index_css():
        return FileResponse(get_abs_path("./webui/index.css"))
    
    @app.get("/index.js")
    async def serve_index_js():
        return FileResponse(get_abs_path("./webui/index.js"))

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
 