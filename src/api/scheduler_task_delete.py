from fastapi import APIRouter, HTTPException
from src.api.models import SchedulerTaskDeleteRequest, SchedulerTaskDeleteResponse
from src.helpers.task_scheduler import TaskScheduler, TaskState
from src.helpers.localization import Localization
from src.core.context import AgentContext
from src.helpers import persist_chat

router = APIRouter(prefix="/scheduler_task_delete", tags=["scheduler"])

@router.post("", response_model=SchedulerTaskDeleteResponse)
async def delete_scheduler_task(request: SchedulerTaskDeleteRequest) -> SchedulerTaskDeleteResponse:
    """Delete a task from the scheduler by ID"""
    try:
        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if request.timezone:
            Localization.get().set_timezone(request.timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Check if the task exists first
        task = scheduler.get_task_by_uuid(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task with ID {request.task_id} not found")

        context = None
        if task.context_id:
            context = AgentContext.get(task.context_id)

        # If the task is running, update its state to IDLE first
        if task.state == TaskState.RUNNING:
            if context:
                context.reset()
            # Update the state to IDLE so any ongoing processes know to terminate
            await scheduler.update_task(request.task_id, state=TaskState.IDLE)
            # Force a save to ensure the state change is persisted
            await scheduler.save()

        # This is a dedicated context for the task, so we remove it
        if context and context.id == task.uuid:
            AgentContext.remove(context.id)
            persist_chat.remove_chat(context.id)

        # Remove the task
        await scheduler.remove_task_by_uuid(request.task_id)

        return SchedulerTaskDeleteResponse(
            success=True,
            message=f"Task {request.task_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")
