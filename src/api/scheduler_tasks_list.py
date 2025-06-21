from fastapi import APIRouter
from src.api.models import SchedulerTasksListRequest, SchedulerTasksListResponse
from src.helpers.task_scheduler import TaskScheduler
import traceback
from src.helpers.print_style import PrintStyle
from src.helpers.localization import Localization

router = APIRouter(prefix="/scheduler_tasks_list", tags=["scheduler"])

@router.post("", response_model=SchedulerTasksListResponse)
async def list_scheduler_tasks(request: SchedulerTasksListRequest) -> SchedulerTasksListResponse:
    """List all tasks in the scheduler with their types"""
    try:
        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if request.timezone:
            Localization.get().set_timezone(request.timezone)

        # Get task scheduler
        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Use the scheduler's convenience method for task serialization
        tasks_list = scheduler.serialize_all_tasks()

        return SchedulerTasksListResponse(
            tasks=tasks_list,
            message="Scheduler tasks retrieved successfully"
        )

    except Exception as e:
        PrintStyle.error(f"Failed to list tasks: {str(e)} {traceback.format_exc()}")
        return SchedulerTasksListResponse(
            success=False,
            tasks=[],
            message=f"Failed to list tasks: {str(e)}"
        )
