from fastapi import APIRouter
from src.api.models import ChatRemoveRequest, BaseResponse
from src.core.context import AgentContext
from src.helpers import persist_chat
from src.helpers.task_scheduler import TaskScheduler

router = APIRouter(prefix="/chat_remove", tags=["chat"])

@router.post("", response_model=BaseResponse)
async def remove_chat(request: ChatRemoveRequest) -> BaseResponse:
    """Remove a chat context and its tasks"""
    context = AgentContext.get(request.context)
    if context:
        # stop processing any tasks
        context.reset()

    AgentContext.remove(request.context)
    persist_chat.remove_chat(request.context)

    scheduler = TaskScheduler.get()
    await scheduler.reload()

    tasks = scheduler.get_tasks_by_context_id(request.context)
    for task in tasks:
        await scheduler.remove_task_by_uuid(task.uuid)

    return BaseResponse(message="Context removed.")
