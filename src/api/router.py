"""
Main API router that collects all individual API routers.
This replaces the old ApiHandler system with proper FastAPI routers.
"""

from fastapi import APIRouter
from src.api import (
    health, settings_get, settings_set, message, message_async, restart, pause, nudge,
    history_get, chat_reset, chat_load, chat_remove, chat_export,
    tunnel, rfc, file_info, get_work_dir_files, delete_work_dir_file,
    mcp_servers_status, scheduler_tasks_list, image_get, ctx_window_get,
    mcp_servers_apply, mcp_server_get_detail, mcp_server_get_log,
    transcribe, download_work_dir_file, scheduler_tick, tunnel_proxy,
    upload, scheduler_task_create, scheduler_task_update, 
    scheduler_task_run, scheduler_task_delete, poll, upload_work_dir_files, import_knowledge, connection_test
)

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all individual routers
api_router.include_router(health.router)
api_router.include_router(settings_get.router)
api_router.include_router(settings_set.router)
api_router.include_router(message.router)
api_router.include_router(message_async.router)
api_router.include_router(restart.router)
api_router.include_router(pause.router)
api_router.include_router(nudge.router)
api_router.include_router(history_get.router)
api_router.include_router(chat_reset.router)
api_router.include_router(chat_load.router)
api_router.include_router(chat_remove.router)
api_router.include_router(chat_export.router)
api_router.include_router(tunnel.router)
api_router.include_router(rfc.router)
api_router.include_router(file_info.router)
api_router.include_router(get_work_dir_files.router)
api_router.include_router(delete_work_dir_file.router)
api_router.include_router(mcp_servers_status.router)
api_router.include_router(scheduler_tasks_list.router)
api_router.include_router(image_get.router)
api_router.include_router(ctx_window_get.router)
api_router.include_router(mcp_servers_apply.router)
api_router.include_router(mcp_server_get_detail.router)
api_router.include_router(mcp_server_get_log.router)
api_router.include_router(transcribe.router)
api_router.include_router(download_work_dir_file.router)
api_router.include_router(scheduler_tick.router)
api_router.include_router(tunnel_proxy.router)
api_router.include_router(upload.router)
api_router.include_router(scheduler_task_create.router)
api_router.include_router(scheduler_task_update.router)
api_router.include_router(scheduler_task_run.router)
api_router.include_router(scheduler_task_delete.router)
api_router.include_router(poll.router)
api_router.include_router(upload_work_dir_files.router)
api_router.include_router(import_knowledge.router)
api_router.include_router(connection_test.router)

# Export the main router
__all__ = ["api_router"] 