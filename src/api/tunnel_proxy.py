from fastapi import APIRouter
from src.api.models import TunnelRequest, TunnelResponse
from src.helpers import dotenv, runtime
from src.helpers.tunnel_manager import TunnelManager
import requests
import time

router = APIRouter(prefix="/tunnel_proxy", tags=["tunnel"])

@router.post("", response_model=TunnelResponse)
async def tunnel_proxy(request: TunnelRequest) -> TunnelResponse:
    """Proxy tunnel requests to external service or handle locally"""
    # Get configuration from environment
    tunnel_api_port = (
        runtime.get_arg("tunnel_api_port")
        or int(dotenv.get_dotenv_value("TUNNEL_API_PORT", 0))
        or 55520
    )

    # first verify the service is running:
    service_ok = False
    try:
        response = requests.post(
            f"http://localhost:{tunnel_api_port}/", json={"action": "health"}
        )
        if response.status_code == 200:
            service_ok = True
    except Exception:
        service_ok = False

    # forward this request to the tunnel service if OK
    if service_ok:
        try:
            response = requests.post(
                f"http://localhost:{tunnel_api_port}/", 
                json=request.model_dump()
            )
            response_data = response.json()
            
            # Convert response to TunnelResponse format
            return TunnelResponse(
                tunnel_url=response_data.get("tunnel_url"),
                is_running=response_data.get("is_running", False),
                message=response_data.get("message", "Tunnel operation completed")
            )
        except Exception as e:
            return TunnelResponse(
                success=False,
                message=f"Tunnel proxy error: {str(e)}"
            )
    else:
        # forward to local tunnel handler directly
        tunnel_manager = TunnelManager.get_instance()

        if request.action == "health":
            return TunnelResponse(message="Tunnel proxy service healthy")

        elif request.action == "create":
            port = runtime.get_web_ui_port()
            provider = request.provider or "serveo"
            tunnel_url = tunnel_manager.start_tunnel(port, provider)
            if tunnel_url is None:
                time.sleep(2)
                tunnel_url = tunnel_manager.get_tunnel_url()

            return TunnelResponse(
                tunnel_url=tunnel_url,
                is_running=tunnel_url is not None,
                message=(
                    "Tunnel creation in progress"
                    if tunnel_url is None
                    else "Tunnel created successfully"
                )
            )

        elif request.action == "stop":
            tunnel_manager.stop_tunnel()
            return TunnelResponse(message="Tunnel stopped successfully")

        elif request.action == "get":
            tunnel_url = tunnel_manager.get_tunnel_url()
            return TunnelResponse(
                tunnel_url=tunnel_url,
                is_running=tunnel_manager.is_running,
                message="Tunnel status retrieved"
            )

        else:
            return TunnelResponse(
                success=False,
                message="Invalid action. Use 'create', 'stop', 'get', or 'health'."
            )
