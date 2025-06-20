#!/usr/bin/env python3
"""
Tunnel API server entry point for Maho.
This replaces the old run_tunnel.py file.
"""

import os
import sys
from fastapi import FastAPI, Request
import uvicorn
import anyio

# Add the project root to Python path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.helpers import runtime, dotenv, process
from src.helpers.print_style import PrintStyle
from src.api.tunnel import Tunnel


async def main():
    """Initializes and runs the tunnel server."""
    PrintStyle().print("Starting tunnel server...")

    app = FastAPI()
    tunnel = Tunnel(app)

    # handle api request
    @app.post("/")
    async def handle_request(request: Request):
        return await tunnel.handle_request_async(request=request)

    try:
        host = "127.0.0.1"
        port = runtime.get_tunnel_api_port()
        print(f"Tunnel API server running at http://{host}:{port}")
        
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        print("Server stopped.")
    except Exception as e:
        PrintStyle().error(f"Failed to start tunnel server: {e}")


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        pass
