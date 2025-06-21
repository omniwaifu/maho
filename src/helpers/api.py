from abc import abstractmethod
import json
import threading
from typing import Union, TypedDict, Dict, Any, Optional
from attr import dataclass
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers.print_style import PrintStyle
from src.helpers.errors import format_error


Input = dict
Output = Union[Dict[str, Any], Response, TypedDict]  # type: ignore


class ApiHandler:
    def __init__(self, app, thread_lock: Optional[threading.Lock] = None):
        self.app = app
        self.thread_lock = thread_lock

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @abstractmethod
    async def process(self, input: Input, request: Request) -> Output:
        pass

    async def handle_request_async(self, request: Request) -> Response:
        """Handle FastAPI request asynchronously"""
        try:
            # input data from request based on method
            input_data: Input = {}
            
            if request.method == "POST":
                try:
                    body = await request.body()
                    if body:
                        input_data = json.loads(body)
                except Exception as e:
                    PrintStyle().print(f"Error parsing JSON: {str(e)}")
                    input_data = {}
            else:
                # GET request - use query parameters
                input_data = dict(request.query_params)

            # process via handler
            output = await self.process(input_data, request)

            # return output based on type
            if isinstance(output, (Response, JSONResponse, FileResponse)):
                return output
            else:
                # Handle Pydantic models in JSON serialization
                try:
                    if hasattr(output, 'model_dump'):
                        return JSONResponse(content=output.model_dump())  # type: ignore
                    elif hasattr(output, 'dict'):
                        return JSONResponse(content=output.dict())  # type: ignore
                    else:
                        return JSONResponse(content=output)
                except TypeError:
                    # If all else fails, try model_dump anyway
                    try:
                        return JSONResponse(content=output.model_dump())  # type: ignore
                    except Exception:
                        return JSONResponse(content={"result": str(output)})
                        
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            error = format_error(e)
            PrintStyle.error(f"API error: {error}")
            raise HTTPException(status_code=500, detail=error)

    # Backward compatibility method
    def handle_request(self, request: Request) -> Response:
        """Backward compatibility - should not be used with FastAPI"""
        import asyncio
        return asyncio.run(self.handle_request_async(request))

    # get context to run maho in
    def get_context(self, ctxid: str):
        # Thread lock is optional in FastAPI async context
        if self.thread_lock:
            with self.thread_lock:
                return self._get_context_impl(ctxid)
        else:
            return self._get_context_impl(ctxid)
    
    def _get_context_impl(self, ctxid: str):
        if not ctxid:
            first = AgentContext.first()
            if first:
                return first
            return AgentContext(config=initialize_agent())
        got = AgentContext.get(ctxid)
        if got:
            return got
        return AgentContext(config=initialize_agent(), id=ctxid)
