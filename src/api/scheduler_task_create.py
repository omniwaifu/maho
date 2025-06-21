from fastapi import APIRouter, HTTPException
from src.api.models import SchedulerTaskCreateRequest, SchedulerTaskCreateResponse
from src.helpers.task_scheduler import (
    TaskScheduler,
    ScheduledTask,
    AdHocTask,
    PlannedTask,
    TaskSchedule,
    serialize_task,
    parse_task_schedule,
    parse_task_plan,
    TaskType,
)
from src.helpers.localization import Localization
from src.helpers.print_style import PrintStyle
import random

router = APIRouter(prefix="/scheduler_task_create", tags=["scheduler"])

@router.post("", response_model=SchedulerTaskCreateResponse)
async def create_scheduler_task(request: SchedulerTaskCreateRequest) -> SchedulerTaskCreateResponse:
    """Create a new task in the scheduler"""
    printer = PrintStyle(italic=True, font_color="blue", padding=False)

    try:
        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if request.timezone:
            Localization.get().set_timezone(request.timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Validate required fields
        if not request.name or not request.prompt:
            raise HTTPException(status_code=400, detail="Missing required fields: name, prompt")

        # Handle token for ad-hoc tasks
        token = request.token or ""
        
        # Debug log the token value
        printer.print(
            f"Token received from frontend: '{token}' (type: {type(token)}, length: {len(token) if token else 0})"
        )

        # Generate a random token if empty or not provided (for ad-hoc tasks)
        if not token and not request.schedule and not request.plan:
            token = str(random.randint(1000000000000000000, 9999999999999999999))
            printer.print(f"Generated new token: '{token}'")

        task = None
        if request.schedule:
            # Create a scheduled task
            # Handle different schedule formats (string or object)
            if isinstance(request.schedule, str):
                # Parse the string schedule
                parts = request.schedule.split(" ")
                task_schedule = TaskSchedule(
                    minute=parts[0] if len(parts) > 0 else "*",
                    hour=parts[1] if len(parts) > 1 else "*",
                    day=parts[2] if len(parts) > 2 else "*",
                    month=parts[3] if len(parts) > 3 else "*",
                    weekday=parts[4] if len(parts) > 4 else "*",
                )
            else:
                # Use our standardized parsing function
                try:
                    if hasattr(request.schedule, 'model_dump'):
                        schedule_dict = request.schedule.model_dump()
                    else:
                        schedule_dict = dict(request.schedule)
                    task_schedule = parse_task_schedule(schedule_dict)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))

            task = ScheduledTask.create(
                name=request.name,
                system_prompt=request.system_prompt,
                prompt=request.prompt,
                schedule=task_schedule,
                attachments=request.attachments,
                context_id=request.context_id,
                timezone=request.timezone,
            )
        elif request.plan:
            # Create a planned task
            try:
                # Use our standardized parsing function
                if hasattr(request.plan, 'model_dump'):
                    plan_dict = request.plan.model_dump()
                else:
                    plan_dict = dict(request.plan)
                task_plan = parse_task_plan(plan_dict)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            task = PlannedTask.create(
                name=request.name,
                system_prompt=request.system_prompt,
                prompt=request.prompt,
                plan=task_plan,
                attachments=request.attachments,
                context_id=request.context_id,
            )
        else:
            # Create an ad-hoc task
            printer.print(f"Creating AdHocTask with token: '{token}'")
            task = AdHocTask.create(
                name=request.name,
                system_prompt=request.system_prompt,
                prompt=request.prompt,
                token=token,
                attachments=request.attachments,
                context_id=request.context_id,
            )
            # Verify token after creation
            if isinstance(task, AdHocTask):
                printer.print(f"AdHocTask created with token: '{task.token}'")

        # Add the task to the scheduler
        await scheduler.add_task(task)

        # Verify the task was added correctly - retrieve by UUID to check persistence
        saved_task = scheduler.get_task_by_uuid(task.uuid)
        if saved_task:
            if saved_task.type == TaskType.AD_HOC and isinstance(saved_task, AdHocTask):
                printer.print(f"Task verified after save, token: '{saved_task.token}'")
            else:
                printer.print("Task verified after save, not an adhoc task")
        else:
            printer.print("WARNING: Task not found after save!")

        # Return the created task using our standardized serialization function
        task_dict = serialize_task(task)

        # Debug log the serialized task
        if task_dict and task_dict.get("type") == "adhoc":
            printer.print(
                f"Serialized adhoc task, token in response: '{task_dict.get('token')}'"
            )

        return SchedulerTaskCreateResponse(
            task=task_dict,
            message="Task created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")
