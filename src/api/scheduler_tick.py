from datetime import datetime
from fastapi import APIRouter, Depends
from src.api.models import SchedulerTickRequest, SchedulerTickResponse
from src.helpers.print_style import PrintStyle
from src.helpers.task_scheduler import TaskScheduler
from src.helpers.localization import Localization

router = APIRouter(prefix="/scheduler_tick", tags=["scheduler"])

async def verify_loopback():
    """Verify request comes from loopback (placeholder for now)"""
    # TODO: Implement proper loopback verification if needed
    return True

@router.post("", response_model=SchedulerTickResponse, dependencies=[Depends(verify_loopback)])
async def scheduler_tick(request: SchedulerTickRequest) -> SchedulerTickResponse:
    """Execute a scheduler tick operation"""
    # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
    if request.timezone:
        Localization.get().set_timezone(request.timezone)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    printer = PrintStyle(font_color="green", padding=False)
    printer.print(f"Scheduler tick - API: {timestamp}")

    # Get the task scheduler instance and print detailed debug info
    scheduler = TaskScheduler.get()
    await scheduler.reload()

    tasks = scheduler.get_tasks()
    tasks_count = len(tasks)

    # Log information about the tasks
    printer.print(f"Scheduler has {tasks_count} task(s)")
    if tasks_count > 0:
        for task in tasks:
            printer.print(
                f"Task: {task.name} (UUID: {task.uuid}, State: {task.state})"
            )

    # Run the scheduler tick
    await scheduler.tick()

    # Get updated tasks after tick
    serialized_tasks = scheduler.serialize_all_tasks()

    return SchedulerTickResponse(
        scheduler="tick",
        timestamp=timestamp,
        tasks_count=tasks_count,
        tasks=serialized_tasks,
        message="Scheduler tick completed successfully"
    )
