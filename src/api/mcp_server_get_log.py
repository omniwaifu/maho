from fastapi import APIRouter, HTTPException
from src.api.models import McpServerGetLogRequest, McpServerGetLogResponse
from src.helpers.mcp_handler import MCPConfig

router = APIRouter(prefix="/mcp_server_get_log", tags=["mcp"])

@router.post("", response_model=McpServerGetLogResponse)
async def get_mcp_server_log(request: McpServerGetLogRequest) -> McpServerGetLogResponse:
    """Get log content for a specific MCP server"""
    try:
        if not request.server_name:
            raise HTTPException(status_code=400, detail="Missing server_name")
        
        log = MCPConfig.get_instance().get_server_log(request.server_name)
        
        return McpServerGetLogResponse(
            log=log,
            message="MCP server log retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        return McpServerGetLogResponse(
            success=False,
            log="",
            message=f"Failed to get MCP server log: {str(e)}"
        )
