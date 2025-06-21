from fastapi import APIRouter, HTTPException
from src.api.models import McpServersStatusResponse
from src.helpers.mcp_handler import MCPConfig
from src.helpers.print_style import PrintStyle

router = APIRouter(prefix="/mcp_servers_status", tags=["mcp"])

@router.get("", response_model=McpServersStatusResponse)
async def get_mcp_servers_status() -> McpServersStatusResponse:
    """Get the status of all MCP servers"""
    try:
        mcp_config = MCPConfig.get_instance()
        if not mcp_config:
            raise HTTPException(status_code=503, detail="MCP configuration service not available")
            
        status = mcp_config.get_servers_status()
        
        # Ensure status is a list (handle the case where it might be a dict)
        if isinstance(status, dict):
            if not status:  # Empty dict
                status = []
            else:
                raise HTTPException(
                    status_code=500, 
                    detail="Invalid MCP servers status format received"
                )
        elif not isinstance(status, list):
            raise HTTPException(
                status_code=500, 
                detail="Invalid MCP servers status format received"
            )
        
        return McpServersStatusResponse(
            status=status,
            message="MCP servers status retrieved successfully"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, 
            detail="MCP configuration files not found"
        )
    except PermissionError:
        raise HTTPException(
            status_code=500, 
            detail="Insufficient permissions to access MCP configuration"
        )
    except Exception as e:
        PrintStyle.error(f"Failed to get MCP servers status: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving MCP servers status: {str(e)}"
        )
