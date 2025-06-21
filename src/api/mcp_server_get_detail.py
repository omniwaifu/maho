from fastapi import APIRouter, HTTPException
from src.api.models import McpServerGetDetailRequest, McpServerGetDetailResponse
from src.helpers.mcp_handler import MCPConfig

router = APIRouter(prefix="/mcp_server_get_detail", tags=["mcp"])

@router.post("", response_model=McpServerGetDetailResponse)
async def get_mcp_server_detail(request: McpServerGetDetailRequest) -> McpServerGetDetailResponse:
    """Get detailed information about a specific MCP server"""
    try:
        if not request.server_name:
            raise HTTPException(status_code=400, detail="Missing server_name")
        
        detail = MCPConfig.get_instance().get_server_detail(request.server_name)
        
        return McpServerGetDetailResponse(
            detail=detail,
            message="MCP server detail retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        return McpServerGetDetailResponse(
            success=False,
            detail={},
            message=f"Failed to get MCP server detail: {str(e)}"
        )
