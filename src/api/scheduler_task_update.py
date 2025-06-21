from fastapi import APIRouter, HTTPException
from src.api.models import SchedulerTaskUpdateRequest, SchedulerTaskUpdateResponse
from src.helpers.task_scheduler import (
    TaskScheduler,
    ScheduledTask,
    AdHocTask,
    PlannedTask,
    TaskState,
    serialize_task,
    parse_task_schedule,
    parse_task_plan,
)
from src.helpers.localization import Localization

router = APIRouter(prefix="/scheduler_task_update", tags=["scheduler"])

@router.post("", response_model=SchedulerTaskUpdateResponse)
async def update_scheduler_task(request: SchedulerTaskUpdateRequest) -> SchedulerTaskUpdateResponse:
    """Update an existing task in the scheduler"""
    try:
        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if request.timezone:
            Localization.get().set_timezone(request.timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Get the task to update
        task = scheduler.get_task_by_uuid(request.task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task with ID {request.task_id} not found")

        # Update fields if provided using the task's update method
        update_params = {}

        if request.name is not None:
            update_params["name"] = request.name

        if request.state is not None:
            update_params["state"] = TaskState(request.state)

        if request.system_prompt is not None:
            update_params["system_prompt"] = request.system_prompt

        if request.prompt is not None:
            update_params["prompt"] = request.prompt

        if request.attachments is not None:
            update_params["attachments"] = request.attachments

        # Update schedule if this is a scheduled task and schedule is provided
        if isinstance(task, ScheduledTask) and request.schedule is not None:
            try:
                if isinstance(request.schedule, str):
                    # Parse the string schedule
                    parts = request.schedule.split(" ")
                    from src.helpers.task_scheduler import TaskSchedule
                    task_schedule = TaskSchedule(
                        minute=parts[0] if len(parts) > 0 else "*",
                        hour=parts[1] if len(parts) > 1 else "*",
                        day=parts[2] if len(parts) > 2 else "*",
                        month=parts[3] if len(parts) > 3 else "*",
                        weekday=parts[4] if len(parts) > 4 else "*",
                    )
                else:
                    # Parse the schedule with timezone handling
                    if hasattr(request.schedule, 'model_dump'):
                        schedule_dict = request.schedule.model_dump()
                    else:
                        schedule_dict = dict(request.schedule)
                    task_schedule = parse_task_schedule(schedule_dict)

                    # Set the timezone from the request if not already in schedule_data
                    if not schedule_dict.get("timezone", None) and request.timezone:
                        task_schedule.timezone = request.timezone

                update_params["schedule"] = task_schedule
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid schedule format: {str(e)}")
        elif isinstance(task, AdHocTask) and request.token is not None:
            if request.token:  # Only update if non-empty
                update_params["token"] = request.token
        elif isinstance(task, PlannedTask) and request.plan is not None:
            try:
                # Parse the plan data
                if hasattr(request.plan, 'model_dump'):
                    plan_dict = request.plan.model_dump()
                else:
                    plan_dict = dict(request.plan)
                task_plan = parse_task_plan(plan_dict)
                update_params["plan"] = task_plan
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid plan format: {str(e)}")

        # Use atomic update method to apply changes
        updated_task = await scheduler.update_task(request.task_id, **update_params)

        if not updated_task:
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID {request.task_id} not found or could not be updated"
            )

        # Return the updated task using our standardized serialization function
        task_dict = serialize_task(updated_task)

        return SchedulerTaskUpdateResponse(
            task=task_dict,
            message="Task updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")
