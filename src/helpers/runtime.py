import argparse
import inspect
from typing import TypeVar, Callable, Awaitable, Union, overload, cast, Any
from src.helpers import dotenv, rfc, settings
import anyio
import threading
import queue
import os
import sys
import importlib.util
T = TypeVar("T")
R = TypeVar("R")

parser = argparse.ArgumentParser()
args = {}
dockerman = None


def initialize():
    global args
    if args:
        return
    parser.add_argument("--port", type=int, default=None, help="Web UI port")
    parser.add_argument("--host", type=str, default=None, help="Web UI host")
    parser.add_argument(
        "--cloudflare_tunnel",
        type=bool,
        default=False,
        help="Use cloudflare tunnel for public URL",
    )
    parser.add_argument(
        "--development", type=bool, default=False, help="Development mode"
    )

    known, unknown = parser.parse_known_args()
    args = vars(known)
    for arg in unknown:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lstrip("-")
            args[key] = value


def get_arg(name: str):
    global args
    return args.get(name, None)


def has_arg(name: str):
    global args
    return name in args


def is_dockerized() -> bool:
    return bool(get_arg("dockerized"))


def is_development() -> bool:
    return not is_dockerized()


def get_local_url():
    if is_dockerized():
        return "host.docker.internal"
    return "127.0.0.1"


@overload
async def call_development_function(
    func: Callable[..., Awaitable[T]], *args, **kwargs
) -> T: ...


@overload
async def call_development_function(func: Callable[..., T], *args, **kwargs) -> T: ...


async def call_development_function(
    func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs
) -> T:
    if is_development():
        url = _get_rfc_url()
        password = _get_rfc_password()
        result = await rfc.call_rfc(
            url=url,
            password=password,
            module=func.__module__,
            function_name=func.__name__,
            args=list(args),
            kwargs=kwargs,
        )
        return cast(T, result)
    else:
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)  # type: ignore


async def handle_rfc(rfc_call: rfc.RFCCall):
    return await rfc.handle_rfc(rfc_call=rfc_call, password=_get_rfc_password())


def _get_rfc_password() -> str:
    password = dotenv.get_dotenv_value(dotenv.KEY_RFC_PASSWORD)
    if not password:
        raise Exception("No RFC password, cannot handle RFC calls.")
    return password


def _get_rfc_url() -> str:
    set = settings.get_settings()
    url = set["rfc_url"]
    if "://" not in url:
        url = "http://" + url
    if url.endswith("/"):
        url = url[:-1]
    url = url + ":" + str(set["rfc_port_http"])
    url += "/rfc"
    return url


def call_development_function_sync(
    func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs
) -> T:
    # run async function in sync manner
    result_queue = queue.Queue()

    def run_in_thread():
        result = anyio.run(call_development_function, func, *args, **kwargs)
        result_queue.put(result)

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join(timeout=30)  # wait for thread with timeout

    if thread.is_alive():
        raise TimeoutError("Function call timed out after 30 seconds")

    result = result_queue.get_nowait()
    return cast(T, result)


def get_web_ui_port():
    web_ui_port = (
        get_arg("port") or int(dotenv.get_dotenv_value("WEB_UI_PORT", 0)) or 5000
    )
    return web_ui_port


def get_tunnel_api_port():
    tunnel_api_port = (
        get_arg("tunnel_api_port")
        or int(dotenv.get_dotenv_value("TUNNEL_API_PORT", 0))
        or 55520
    )
    return tunnel_api_port


def suppress_httpx_cleanup_warnings():
    """
    Suppress the asyncio task exception reporting for httpx AsyncClient cleanup
    that occurs when the event loop is closed during shutdown.
    These are harmless cleanup exceptions and don't affect functionality.
    """
    import asyncio
    import io
    
    # Store the original exception handler
    original_exception_handler = None
    
    def custom_exception_handler(loop, context):
        # Check if this is an httpx cleanup exception we want to suppress
        exception = context.get('exception')
        message = context.get('message', '')
        
        # Suppress httpx AsyncClient cleanup exceptions
        if (exception and isinstance(exception, RuntimeError) and 
            str(exception) == 'Event loop is closed' and
            ('AsyncClient.aclose' in message or 'httpx' in message)):
            return  # Suppress this exception
            
        # Suppress general "Task exception was never retrieved" for httpx
        if ('Task exception was never retrieved' in message and
            ('AsyncClient.aclose' in message or 'Event loop is closed' in str(exception))):
            return  # Suppress this exception
            
        # For all other exceptions, use the original handler
        if original_exception_handler:
            original_exception_handler(loop, context)
        else:
            # Default behavior if no original handler
            loop.default_exception_handler(context)
    
    # Get the current event loop and set our custom exception handler
    try:
        loop = asyncio.get_event_loop()
        original_exception_handler = loop.get_exception_handler()
        loop.set_exception_handler(custom_exception_handler)
    except RuntimeError:
        # No event loop running yet, set it later
        pass
    
    # Also redirect stderr temporarily to suppress direct prints
    original_stderr = sys.stderr
    
    class FilteredStderr:
        def __init__(self, original_stderr):
            self.original_stderr = original_stderr
            
        def write(self, text):
            # Filter out the specific httpx cleanup messages
            if ('Task exception was never retrieved' in text and 
                ('AsyncClient.aclose' in text or 'Event loop is closed' in text)):
                return  # Don't write this
            if ('RuntimeError: Event loop is closed' in text and 
                'httpx' in text):
                return  # Don't write this
            self.original_stderr.write(text)
            
        def flush(self):
            self.original_stderr.flush()
            
        def __getattr__(self, name):
            return getattr(self.original_stderr, name)
    
    sys.stderr = FilteredStderr(original_stderr)



