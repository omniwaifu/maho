from abc import abstractmethod
import json
import threading
from typing import Union, TypedDict, Dict, Any
from attr import dataclass
from flask import Request, Response, jsonify, Flask
from src.core.context import AgentContext
from src.config.initialization import initialize_agent
from src.helpers.print_style import PrintStyle
from src.helpers.errors import format_error
from werkzeug.serving import make_server
from anyio.from_thread import start_blocking_portal


Input = dict
Output = Union[Dict[str, Any], Response, TypedDict]  # type: ignore


class ApiHandler:
    def __init__(self, app: Flask, thread_lock: threading.Lock):
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

    def handle_request(self, request: Request) -> Response:
        try:
            with start_blocking_portal() as portal:
                return portal.call(self._handle_request_async, request)
        except Exception as e:
            error = format_error(e)
            PrintStyle.error(f"API error: {error}")
            return Response(response=error, status=500, mimetype="text/plain")

    async def _handle_request_async(self, request: Request) -> Response:
        # input data from request based on type
        input_data: Input = {}
        if request.is_json:
            try:
                if request.data:  # Check if there's any data
                    input_data = request.get_json()
                # If empty or not valid JSON, use empty dict
            except Exception as e:
                # Just log the error and continue with empty input
                PrintStyle().print(f"Error parsing JSON: {str(e)}")
                input_data = {}
        else:
            input_data = {"data": request.get_data(as_text=True)}

        # process via handler
        output = await self.process(input_data, request)

        # return output based on type
        if isinstance(output, Response):
            return output
        else:
            # Handle Pydantic models in JSON serialization
            try:
                if hasattr(output, 'model_dump'):
                    response_json = json.dumps(output.model_dump())  # type: ignore
                elif hasattr(output, 'dict'):
                    response_json = json.dumps(output.dict())  # type: ignore
                else:
                    response_json = json.dumps(output)
            except TypeError:
                # If all else fails, try model_dump anyway
                try:
                    response_json = json.dumps(output.model_dump())  # type: ignore
                except:
                    response_json = json.dumps(str(output))
            return Response(
                response=response_json, status=200, mimetype="application/json"
            )

    # get context to run maho in
    def get_context(self, ctxid: str):
        with self.thread_lock:
            if not ctxid:
                first = AgentContext.first()
                if first:
                    return first
                return AgentContext(config=initialize_agent())
            got = AgentContext.get(ctxid)
            if got:
                return got
            return AgentContext(config=initialize_agent(), id=ctxid)
