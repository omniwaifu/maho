import time
from fastapi import APIRouter, HTTPException
from src.api.models import McpServersApplyRequest, McpServersApplyResponse
from src.helpers.mcp_handler import MCPConfig
from src.helpers.settings import set_settings_delta
from src.helpers.print_style import PrintStyle
import json
from typing import List, Dict, Any

router = APIRouter(prefix="/mcp_servers_apply", tags=["mcp"])

@router.post("", response_model=McpServersApplyResponse)
async def apply_mcp_servers(request: McpServersApplyRequest) -> McpServersApplyResponse:
    """Apply MCP servers configuration"""
    try:
        if not request.mcp_servers:
            raise HTTPException(status_code=400, detail="No MCP servers configuration provided")
        
        # Validate JSON format
        try:
            json.loads(request.mcp_servers)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid JSON format in MCP servers configuration: {str(e)}"
            )
        
        # Apply configuration changes
        try:
            # MCPConfig.update(mcp_servers) # done in settings automatically
            set_settings_delta({"mcp_servers": "[]"})  # to force reinitialization
            set_settings_delta({"mcp_servers": request.mcp_servers})
        except PermissionError:
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to update MCP configuration"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to apply MCP configuration: {str(e)}"
            )

        time.sleep(1)  # wait at least a second
        
        # Get updated status
        status: List[Dict[str, Any]] = []
        try:
            mcp_config = MCPConfig.get_instance()
            if not mcp_config:
                raise HTTPException(
                    status_code=503, 
                    detail="MCP configuration service not available after update"
                )
                
            # MCPConfig.wait_for_lock() # wait until config lock is released
            raw_status = mcp_config.get_servers_status()
            
            # Ensure status is a list of dicts
            if isinstance(raw_status, list):
                # Validate each item is a dict
                status = [item for item in raw_status if isinstance(item, dict)]
            elif isinstance(raw_status, dict):
                if raw_status:  # Non-empty dict
                    PrintStyle.warning("MCP status returned dict instead of list, converting")
                    status = [raw_status]
                # Empty dict case - status remains empty list
            else:
                PrintStyle.warning(f"MCP status returned unexpected type: {type(raw_status)}")
                # status remains empty list
                
        except Exception as e:
            PrintStyle.error(f"Failed to get updated MCP status: {str(e)}")
            # Don't fail the whole operation if we can't get status
            # status remains empty list
        
        return McpServersApplyResponse(
            status=status,
            message="MCP servers configuration applied successfully"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        PrintStyle.error(f"Failed to apply MCP servers configuration: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to apply MCP servers configuration: {str(e)}"
        )
