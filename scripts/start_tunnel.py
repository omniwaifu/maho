#!/usr/bin/env python3
"""
Tunnel API server entry point for Agent Zero.
This replaces the old run_tunnel.py file.
"""

import os
import sys
from flask import Flask, request, Response
from werkzeug.serving import make_server
import threading
import anyio
import anyio.to_thread

# Add the project root to Python path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.helpers import runtime, dotenv, process
from src.helpers.print_style import PrintStyle
from src.api.tunnel import Tunnel


async def main():
    """Initializes and runs the tunnel server."""
    PrintStyle().print("Starting tunnel server...")

    app = Flask(__name__)
    lock = threading.Lock()
    tunnel = Tunnel(app, lock)

    # handle api request
    @app.route("/", methods=["POST"])
    async def handle_request():
        return tunnel.handle_request(request=request)

    try:
        host = "127.0.0.1"
        port = runtime.get_tunnel_api_port()
        server = make_server(
            host=host,
            port=port,
            app=app,
            threaded=False,
        )
        print(f"Tunnel API server running at http://{host}:{port}")
        await anyio.to_thread.run_sync(server.serve_forever)
    except KeyboardInterrupt:
        print("Server stopped.")
    except Exception as e:
        PrintStyle().error(f"Failed to start tunnel server: {e}")


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        pass
