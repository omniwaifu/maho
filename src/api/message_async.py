from fastapi import APIRouter, Form, File, UploadFile, Request, HTTPException
from fastapi.responses import JSONResponse
from src.api.models import MessageResponse
from src.core.context import AgentContext
from src.core.models import UserMessage
from src.config.initialization import initialize_agent
from src.helpers import files
from typing import List, Optional, Union
import os
import re
import json

router = APIRouter(prefix="/message_async", tags=["chat"])

def get_context(context_id: str = "") -> AgentContext:
    """Get or create agent context"""
    if not context_id:
        first = AgentContext.first()
        if first:
            return first
        return AgentContext(config=initialize_agent())
    got = AgentContext.get(context_id)
    if got:
        return got
    return AgentContext(config=initialize_agent(), id=context_id)

@router.post("", response_model=None)
async def send_message_async(request: Request) -> JSONResponse:
    """Send a message to the agent asynchronously"""
    try:
        content_type = request.headers.get("content-type", "")
        
        if content_type.startswith("multipart/form-data"):
            # Handle FormData (with attachments)
            form = await request.form()
            text = str(form.get("text") or "")
            context = str(form.get("context") or "") if form.get("context") else None
            message_id = str(form.get("message_id") or "") if form.get("message_id") else None
            
            if not text:
                raise HTTPException(status_code=400, detail="Text field is required")
            
            # Handle file uploads
            attachment_paths = []
            attachments = form.getlist("attachments")
            for file in attachments:
                if isinstance(file, UploadFile) and file.filename:
                    # Save uploaded file and add to attachments
                    file_path = files.get_abs_path(f"./tmp/{file.filename}")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    attachment_paths.append(file_path)
                    
        elif content_type.startswith("application/json"):
            # Handle JSON (without attachments)
            body = await request.body()
            data = json.loads(body)
            text = data.get("text")
            context = data.get("context")
            message_id = data.get("message_id")
            attachment_paths = []
            
            if not text:
                raise HTTPException(status_code=400, detail="text field is required")
                
        else:
            raise HTTPException(status_code=400, detail="Unsupported content type")

        # get context
        agent_context = get_context(context or "")

        # get user message
        user_message = UserMessage(message=text, attachments=attachment_paths)

        # communicate with agent
        await agent_context.communicate(user_message)

        return JSONResponse(content={
            "context": agent_context.id,
            "message": "Message received",
            "success": True
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        # Catch any other exceptions and return proper JSON error response
        error_message = str(e)
        if "Cannot connect to host" in error_message:
            error_message = "Search service is not available. Message processed without search capability."
        elif "Connection refused" in error_message:
            error_message = "External service connection failed. Message processed with limited functionality."
        else:
            error_message = f"Error processing message: {error_message}"
            
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_message,
                "detail": str(e)
            }
        )
