from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


# Base response model
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


# Message API models
class MessageRequest(BaseModel):
    message: str = Field(..., description="The message content")
    attachments: List[str] = Field(default_factory=list, description="File attachment paths or URLs")
    context: Optional[str] = Field(None, description="Context ID for the conversation")


class MessageResponse(BaseResponse):
    context: str = Field(..., description="Context ID for the conversation")


# Settings API models  
class SettingsRequest(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Settings to update")


class SettingsResponse(BaseResponse):
    settings: Dict[str, Any] = Field(..., description="Current settings")


# File operations models
class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    type: str
    modified: Optional[str] = None


class GetWorkDirFilesRequest(BaseModel):
    path: Optional[str] = Field("", description="Directory path to list files from")


class WorkDirFilesResponse(BaseResponse):
    data: Dict[str, Any] = Field(..., description="File listing data")


class DeleteWorkDirFileRequest(BaseModel):
    path: str = Field(..., description="File path to delete")
    currentPath: str = Field("", description="Current directory path")


class FileListResponse(BaseResponse):
    files: List[FileInfo] = Field(default_factory=list)
    current_path: str = ""


class FileUploadResponse(BaseResponse):
    uploaded_files: List[str] = Field(default_factory=list)
    failed_files: List[str] = Field(default_factory=list)


class FileInfoRequest(BaseModel):
    path: str = Field(..., description="File path to get information about")


class FileInfoDetail(BaseModel):
    input_path: str
    abs_path: str
    exists: bool
    is_dir: bool
    is_file: bool
    is_link: bool
    size: int
    modified: float
    created: float
    permissions: int
    dir_path: str
    file_name: str
    file_ext: str
    message: str


class FileInfoResponse(BaseResponse):
    file_info: FileInfoDetail


class ImageGetRequest(BaseModel):
    path: str = Field(..., description="Path to the image file")


# Context and history models
class ContextRequest(BaseModel):
    context: Optional[str] = Field(None, description="Context ID")


class PauseRequest(BaseModel):
    paused: bool = Field(..., description="Whether to pause the agent")
    context: Optional[str] = Field(None, description="Context ID")


class PauseResponse(BaseResponse):
    paused: bool = Field(..., description="Current pause state")


class NudgeRequest(BaseModel):
    ctxid: str = Field(..., description="Context ID to nudge")


class NudgeResponse(BaseResponse):
    ctxid: str = Field(..., description="Context ID that was nudged")


class HistoryGetRequest(BaseModel):
    context: Optional[str] = Field(None, description="Context ID")


class HistoryGetResponse(BaseResponse):
    history: str = Field(..., description="Chat history as text")
    tokens: int = Field(..., description="Token count")


class ChatResetRequest(BaseModel):
    context: Optional[str] = Field(None, description="Context ID")


class ChatLoadRequest(BaseModel):
    chats: List[str] = Field(..., description="Chat JSON strings to load")


class ChatLoadResponse(BaseResponse):
    ctxids: List[str] = Field(..., description="Context IDs of loaded chats")


class ChatRemoveRequest(BaseModel):
    context: str = Field(..., description="Context ID to remove")


class ChatExportRequest(BaseModel):
    ctxid: str = Field(..., description="Context ID to export")


class ChatExportResponse(BaseResponse):
    ctxid: str = Field(..., description="Context ID that was exported")
    content: Dict[str, Any] = Field(..., description="Exported chat content")


class HistoryResponse(BaseResponse):
    history: List[Dict[str, Any]] = Field(default_factory=list)


# Scheduler models
class SchedulerTask(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    scheduled_time: str
    recurrence: Optional[str] = None
    enabled: bool = True


class SchedulerTaskRequest(BaseModel):
    task: SchedulerTask


class SchedulerTaskResponse(BaseResponse):
    task: SchedulerTask


class SchedulerTasksListRequest(BaseModel):
    timezone: Optional[str] = Field(None, description="Timezone for task display")


class SchedulerTasksListResponse(BaseResponse):
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="List of scheduler tasks")


class SchedulerTickRequest(BaseModel):
    timezone: Optional[str] = Field(None, description="Timezone for scheduler operations")


class SchedulerTickResponse(BaseResponse):
    scheduler: str = Field(..., description="Scheduler operation type")
    timestamp: str = Field(..., description="Timestamp of the operation")
    tasks_count: int = Field(..., description="Number of tasks")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="Serialized tasks")


class CtxWindowGetRequest(BaseModel):
    context: Optional[str] = Field(None, description="Context ID")


class CtxWindowGetResponse(BaseResponse):
    content: str = Field(..., description="Context window content")
    tokens: int = Field(..., description="Token count")


class SchedulerTasksResponse(BaseResponse):
    tasks: List[SchedulerTask] = Field(default_factory=list)


# Scheduler task creation models
class TaskScheduleModel(BaseModel):
    minute: str = Field("*", description="Minute field (0-59 or *)")
    hour: str = Field("*", description="Hour field (0-23 or *)")
    day: str = Field("*", description="Day field (1-31 or *)")
    month: str = Field("*", description="Month field (1-12 or *)")
    weekday: str = Field("*", description="Weekday field (0-7 or *)")


class TaskPlanModel(BaseModel):
    plan_type: str = Field(..., description="Type of plan")
    details: Dict[str, Any] = Field(default_factory=dict, description="Plan details")


class SchedulerTaskCreateRequest(BaseModel):
    name: str = Field(..., description="Task name")
    system_prompt: str = Field("", description="System prompt for the task")
    prompt: str = Field(..., description="Task prompt")
    attachments: List[str] = Field(default_factory=list, description="Task attachments")
    context_id: Optional[str] = Field(None, description="Context ID")
    schedule: Optional[Union[str, TaskScheduleModel]] = Field(None, description="Task schedule")
    plan: Optional[TaskPlanModel] = Field(None, description="Task plan")
    token: Optional[str] = Field(None, description="Token for ad-hoc tasks")
    timezone: Optional[str] = Field(None, description="Timezone for the task")


class SchedulerTaskCreateResponse(BaseResponse):
    task: Dict[str, Any] = Field(..., description="Created task details")


class SchedulerTaskUpdateRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to update")
    name: Optional[str] = Field(None, description="Task name")
    state: Optional[str] = Field(None, description="Task state")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    prompt: Optional[str] = Field(None, description="Task prompt")
    attachments: Optional[List[str]] = Field(None, description="Task attachments")
    schedule: Optional[Union[str, TaskScheduleModel]] = Field(None, description="Schedule for scheduled tasks")
    token: Optional[str] = Field(None, description="Token for ad-hoc tasks")
    plan: Optional[TaskPlanModel] = Field(None, description="Plan for planned tasks")
    timezone: Optional[str] = Field(None, description="Timezone")


class SchedulerTaskUpdateResponse(BaseResponse):
    task: Dict[str, Any] = Field(..., description="Updated task details")


class SchedulerTaskRunRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to run")
    timezone: Optional[str] = Field(None, description="Timezone")


class SchedulerTaskRunResponse(BaseResponse):
    success: bool = Field(..., description="Whether the task started successfully")
    task: Optional[Dict[str, Any]] = Field(None, description="Task details")


class SchedulerTaskDeleteRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to delete")
    timezone: Optional[str] = Field(None, description="Timezone")


class SchedulerTaskDeleteResponse(BaseResponse):
    success: bool = Field(..., description="Whether the task was deleted successfully")


# Poll endpoint models
class PollRequest(BaseModel):
    context: Optional[str] = Field(None, description="Context ID")
    log_from: int = Field(0, description="Log start position")
    timezone: Optional[str] = Field("UTC", description="Timezone")


class PollResponse(BaseResponse):
    context: str = Field(..., description="Context ID")
    contexts: List[Dict[str, Any]] = Field(default_factory=list, description="List of contexts")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="List of tasks")
    logs: List[Dict[str, Any]] = Field(default_factory=list, description="Log entries")
    log_guid: str = Field(..., description="Log GUID")
    log_version: int = Field(..., description="Log version")
    log_progress: Union[str, float] = Field(0.0, description="Log progress or status text")
    log_progress_active: bool = Field(False, description="Log progress active")
    paused: bool = Field(False, description="Context paused status")


# MCP models
class McpServerStatus(BaseModel):
    name: str
    status: str
    enabled: bool
    last_error: Optional[str] = None


class McpServersStatusResponse(BaseResponse):
    status: List[Dict[str, Any]] = Field(..., description="MCP servers status information")


class McpServersApplyRequest(BaseModel):
    mcp_servers: str = Field(..., description="MCP servers configuration JSON")


class McpServersApplyResponse(BaseResponse):
    status: List[Dict[str, Any]] = Field(..., description="Updated MCP servers status")


class McpServerGetDetailRequest(BaseModel):
    server_name: str = Field(..., description="Name of the MCP server")


class McpServerGetDetailResponse(BaseResponse):
    detail: Dict[str, Any] = Field(..., description="MCP server detail information")


class McpServerGetLogRequest(BaseModel):
    server_name: str = Field(..., description="Name of the MCP server")


class McpServerGetLogResponse(BaseResponse):
    log: str = Field(..., description="MCP server log content")


class TranscribeRequest(BaseModel):
    audio: str = Field(..., description="Audio data for transcription")
    ctxid: Optional[str] = Field("", description="Context ID")


class TranscribeResponse(BaseResponse):
    text: Optional[str] = Field(None, description="Transcribed text")
    data: Dict[str, Any] = Field(default_factory=dict, description="Transcription result data")


class DownloadWorkDirFileRequest(BaseModel):
    path: str = Field(..., description="File or directory path to download")


class McpServersResponse(BaseResponse):
    servers: List[McpServerStatus] = Field(default_factory=list)


# Tunnel models
class TunnelAction(str, Enum):
    CREATE = "create"
    STOP = "stop"
    GET = "get"
    HEALTH = "health"


class TunnelRequest(BaseModel):
    action: TunnelAction = TunnelAction.GET
    provider: Optional[str] = Field("serveo", description="Tunnel provider")


class TunnelResponse(BaseResponse):
    tunnel_url: Optional[str] = None
    is_running: bool = False


# Health check
class HealthResponse(BaseResponse):
    status: str = "healthy"
    uptime: Optional[int] = None


# RFC models
class RfcRequest(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict, description="RFC request data")


class RfcResponse(BaseResponse):
    data: Dict[str, Any] = Field(default_factory=dict, description="RFC response data")


# Generic API models
class GenericRequest(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class GenericResponse(BaseResponse):
    data: Dict[str, Any] = Field(default_factory=dict)


# Error response
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


# Common error responses for OpenAPI documentation
class BadRequestError(ErrorResponse):
    """400 Bad Request error response"""
    pass

class UnauthorizedError(ErrorResponse):
    """401 Unauthorized error response"""  
    pass

class ForbiddenError(ErrorResponse):
    """403 Forbidden error response"""
    pass

class NotFoundError(ErrorResponse):
    """404 Not Found error response"""
    pass

class InternalServerError(ErrorResponse):
    """500 Internal Server Error response"""
    pass

# Standard error responses for endpoints
COMMON_ERROR_RESPONSES = {
    400: {"model": BadRequestError, "description": "Bad Request"},
    401: {"model": UnauthorizedError, "description": "Unauthorized"}, 
    403: {"model": ForbiddenError, "description": "Forbidden"},
    404: {"model": NotFoundError, "description": "Not Found"},
    500: {"model": InternalServerError, "description": "Internal Server Error"}
}

# File upload models
class FileUploadBody(BaseModel):
    """Request body for file uploads"""
    uploaded_files: List[Any] = Field(..., description="Files to upload")
    path: str = Field(default="", description="Target directory path")


class KnowledgeUploadBody(BaseModel):
    """Request body for knowledge import uploads"""
    upload_files: List[Any] = Field(..., description="Files to import as knowledge")
    path: str = Field(default="", description="Knowledge base path") 