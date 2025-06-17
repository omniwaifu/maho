#!/usr/bin/env python3
"""
Main UI entry point for the Agent Zero application.
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
from flask import Flask, request, Response
from flask_basicauth import BasicAuth

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

# initialize the internal Flask server
webapp = Flask("app", static_folder=get_abs_path("./webui"), static_url_path="/")
webapp.config["JSON_SORT_KEYS"] = False  # Disable key sorting in jsonify

lock = threading.Lock()

# Set up basic authentication for UI and API but not MCP
basic_auth = BasicAuth(webapp)


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


def requires_api_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        valid_api_key = dotenv.get_dotenv_value("API_KEY")
        if api_key := request.headers.get("X-API-KEY"):
            if api_key != valid_api_key:
                return Response("API key required", 401)
        elif request.json and request.json.get("api_key"):
            api_key = request.json.get("api_key")
            if api_key != valid_api_key:
                return Response("API key required", 401)
        else:
            return Response("API key required", 401)
        return await f(*args, **kwargs)

    return decorated


# allow only loopback addresses
def requires_loopback(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not is_loopback_address(request.remote_addr):
            return Response(
                "Access denied.",
                403,
                {},
            )
        return await f(*args, **kwargs)

    return decorated


# require authentication for handlers
def requires_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        user = dotenv.get_dotenv_value("AUTH_LOGIN")
        password = dotenv.get_dotenv_value("AUTH_PASSWORD")
        if user and password:
            auth = request.authorization
            if not auth or not (auth.username == user and auth.password == password):
                return Response(
                    "Could not verify your access level for that URL.\n"
                    "You have to login with proper credentials",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'},
                )
        return await f(*args, **kwargs)

    return decorated


# handle default address, load index
@webapp.route("/", methods=["GET"])
@requires_auth
async def serve_index():
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


def init_a0():
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


def run():
    PrintStyle().print("Initializing framework...")

    # Suppress only request logs but keep the startup messages
    from werkzeug.serving import WSGIRequestHandler
    from werkzeug.serving import make_server
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from a2wsgi import ASGIMiddleware, WSGIMiddleware

    PrintStyle().print("Starting server...")

    class NoRequestLoggingWSGIRequestHandler(WSGIRequestHandler):
        def log_request(self, code="-", size="-"):
            pass  # Override to suppress request logging

    # Get configuration from environment
    port = runtime.get_web_ui_port()
    host = (
        runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"
    )
    server = None

    def register_api_handler(app, handler: type[ApiHandler]):
        name = handler.__module__.split(".")[-1]
        instance = handler(app, lock)

        if handler.requires_loopback():

            @requires_loopback
            async def handle_request():
                return await instance.handle_request(request=request)

        elif handler.requires_auth():

            @requires_auth
            async def handle_request():
                return await instance.handle_request(request=request)

        elif handler.requires_api_key():

            @requires_api_key
            async def handle_request():
                return await instance.handle_request(request=request)

        else:
            # Fallback to requires_auth
            @requires_auth
            async def handle_request():
                return await instance.handle_request(request=request)

        app.add_url_rule(
            f"/{name}",
            f"/{name}",
            handle_request,
            methods=["POST", "GET"],
        )

    # initialize and register API handlers
    handlers = load_classes_from_folder("src/api", "*.py", ApiHandler)
    for handler in handlers:
        register_api_handler(webapp, handler)

    # MCP server
    # TODO: Implement MCP server registration
    # mcp_server.register_server(webapp)

    try:

        def signal_handler(sig, frame):
            PrintStyle().print("Received interrupt signal. Shutting down gracefully...")
            if server:
                server.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Create the server
        server = make_server(
            host,
            port,
            webapp,
            request_handler=NoRequestLoggingWSGIRequestHandler,
            threaded=True,
        )

        PrintStyle().print(f"Agent Zero Web UI running at http://{host}:{port}")

        # initialize A0 in background
        threading.Thread(target=init_a0, daemon=True).start()

        # Serve forever
        server.serve_forever()

    except Exception as e:
        PrintStyle().error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
