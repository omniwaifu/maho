from fastapi import APIRouter, HTTPException
from src.api.models import TunnelRequest, TunnelResponse
from src.helpers import runtime
from src.helpers.tunnel_manager import TunnelManager
from src.helpers.print_style import PrintStyle
import time

router = APIRouter(prefix="/tunnel", tags=["tunnel"])

@router.post("", response_model=TunnelResponse)
async def tunnel_control(request: TunnelRequest) -> TunnelResponse:
    """Control tunnel operations (create, stop, get status, health)"""
    try:
        tunnel_manager = TunnelManager.get_instance()
        if not tunnel_manager:
            raise HTTPException(status_code=503, detail="Tunnel manager service not available")

        if request.action == "health":
            return TunnelResponse(message="Tunnel service healthy")

        elif request.action == "create":
            try:
                port = runtime.get_web_ui_port()
                if not port or port <= 0:
                    raise HTTPException(status_code=500, detail="Invalid web UI port configuration")
                    
                provider = request.provider or "serveo"
                PrintStyle.info(f"Creating tunnel on port {port} using provider {provider}")
                
                tunnel_url = tunnel_manager.start_tunnel(port, provider)
                
                if tunnel_url is None:
                    # Add a little delay and check again - tunnel might be starting
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
            except ConnectionError as e:
                raise HTTPException(status_code=503, detail=f"Failed to connect to tunnel service: {str(e)}")
            except TimeoutError as e:
                raise HTTPException(status_code=504, detail=f"Tunnel creation timed out: {str(e)}")
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=f"Insufficient permissions for tunnel creation: {str(e)}")

        elif request.action == "stop":
            try:
                tunnel_manager.stop_tunnel()
                PrintStyle.info("Tunnel stopped successfully")
                return TunnelResponse(message="Tunnel stopped successfully")
            except Exception as e:
                PrintStyle.error(f"Failed to stop tunnel: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to stop tunnel: {str(e)}")

        elif request.action == "get":
            try:
                tunnel_url = tunnel_manager.get_tunnel_url()
                is_running = tunnel_manager.is_running
                return TunnelResponse(
                    tunnel_url=tunnel_url,
                    is_running=is_running,
                    message="Tunnel status retrieved"
                )
            except Exception as e:
                PrintStyle.error(f"Failed to get tunnel status: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to get tunnel status: {str(e)}")

        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid action. Use 'create', 'stop', 'get', or 'health'."
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        PrintStyle.error(f"Tunnel operation failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Tunnel operation failed: {str(e)}"
        )
