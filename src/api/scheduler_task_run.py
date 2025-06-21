from fastapi import APIRouter, HTTPException
from src.api.models import SchedulerTaskRunRequest, SchedulerTaskRunResponse
from src.helpers.task_scheduler import TaskScheduler, TaskState
from src.helpers.print_style import PrintStyle
from src.helpers.localization import Localization

router = APIRouter(prefix="/scheduler_task_run", tags=["scheduler"])

_printer: PrintStyle = PrintStyle(italic=True, font_color="green", padding=False)

@router.post("", response_model=SchedulerTaskRunResponse)
async def run_scheduler_task(request: SchedulerTaskRunRequest) -> SchedulerTaskRunResponse:
    """Manually run a task from the scheduler by ID"""
    try:
        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if request.timezone:
            Localization.get().set_timezone(request.timezone)

        _printer.print(f"SchedulerTaskRun: On-Demand running task {request.task_id}")

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Check if the task exists first
        task = scheduler.get_task_by_uuid(request.task_id)
        if not task:
            _printer.error(f"SchedulerTaskRun: Task with ID '{request.task_id}' not found")
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID '{request.task_id}' not found"
            )

        # Check if task is already running
        if task.state == TaskState.RUNNING:
            # Return task details along with error for better frontend handling
            serialized_task = scheduler.serialize_task(request.task_id)
            _printer.error(
                f"SchedulerTaskRun: Task '{request.task_id}' is in state '{task.state}' and cannot be run"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Task '{request.task_id}' is in state '{task.state}' and cannot be run"
            )

        # Run the task, which now includes atomic state checks and updates
        try:
            await scheduler.run_task_by_uuid(request.task_id)
            _printer.print(
                f"SchedulerTaskRun: Task '{request.task_id}' started successfully"
            )
            # Get updated task after run starts
            serialized_task = scheduler.serialize_task(request.task_id)
            return SchedulerTaskRunResponse(
                success=True,
                message=f"Task '{request.task_id}' started successfully",
                task=serialized_task
            )
        except ValueError as e:
            _printer.error(
                f"SchedulerTaskRun: Task '{request.task_id}' failed to start: {str(e)}"
            )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            _printer.error(
                f"SchedulerTaskRun: Task '{request.task_id}' failed to start: {str(e)}"
            )
            raise HTTPException(status_code=500, detail=f"Failed to run task '{request.task_id}': {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run task: {str(e)}")
