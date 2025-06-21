from fastapi import APIRouter, HTTPException
from src.api.models import PollRequest, PollResponse
from src.core.context import AgentContext
from src.helpers.task_scheduler import TaskScheduler
from src.helpers.localization import Localization
from src.helpers.dotenv import get_dotenv_value

router = APIRouter(prefix="/poll", tags=["system"])

@router.post("", response_model=PollResponse)
async def poll_status(request: PollRequest) -> PollResponse:
    """Poll for current system status, contexts, and tasks"""
    try:
        ctxid = str(request.context) if request.context is not None else None

        # Get timezone from input (default to dotenv default or UTC if not provided)
        timezone = request.timezone or get_dotenv_value("DEFAULT_USER_TIMEZONE", "UTC")
        Localization.get().set_timezone(timezone)

        # context instance - get or create
        context = None
        if ctxid:
            context = AgentContext.get(ctxid)
        
        if not context:
            # Create a new context if none found - use default context
            contexts = AgentContext._contexts
            if contexts:
                context = list(contexts.values())[0]
            else:
                # Import config to create a new context
                from src.config.initialization import initialize_agent
                initialize_agent()
                if AgentContext._contexts:
                    context = list(AgentContext._contexts.values())[0]
        
        # If we still don't have a context, create one
        if not context:
            from src.config.initialization import initialize_agent
            config = initialize_agent()
            context = AgentContext(config=config)

        logs = context.log.output(start=request.log_from)

        # Get a task scheduler instance
        scheduler = TaskScheduler.get()

        # Always reload the scheduler on each poll to ensure we have the latest task state
        # await scheduler.reload() # does not seem to be needed

        # loop AgentContext._contexts and divide into contexts and tasks
        ctxs = []
        tasks = []
        processed_contexts = set()  # Track processed context IDs

        all_ctxs = list(AgentContext._contexts.values())
        # First, identify all tasks
        for ctx in all_ctxs:
            # Skip if already processed
            if ctx.id in processed_contexts:
                continue

            # Create the base context data that will be returned
            context_data = ctx.serialize()

            context_task = scheduler.get_task_by_uuid(ctx.id)
            # Determine if this is a task-dedicated context by checking if a task with this UUID exists
            is_task_context = (
                context_task is not None and context_task.context_id == ctx.id
            )

            if not is_task_context:
                ctxs.append(context_data)
            else:
                # If this is a task, get task details from the scheduler
                task_details = scheduler.serialize_task(ctx.id)
                if task_details:
                    # Add task details to context_data with the same field names
                    # as used in scheduler endpoints to maintain UI compatibility
                    context_data.update(
                        {
                            "task_name": task_details.get(
                                "name"
                            ),  # name is for context, task_name for the task name
                            "uuid": task_details.get("uuid"),
                            "state": task_details.get("state"),
                            "type": task_details.get("type"),
                            "system_prompt": task_details.get("system_prompt"),
                            "prompt": task_details.get("prompt"),
                            "last_run": task_details.get("last_run"),
                            "last_result": task_details.get("last_result"),
                            "attachments": task_details.get("attachments", []),
                            "context_id": task_details.get("context_id"),
                        }
                    )

                    # Add type-specific fields
                    if task_details.get("type") == "scheduled":
                        context_data["schedule"] = task_details.get("schedule")
                    elif task_details.get("type") == "planned":
                        context_data["plan"] = task_details.get("plan")
                    else:
                        context_data["token"] = task_details.get("token")

                tasks.append(context_data)

            # Mark as processed
            processed_contexts.add(ctx.id)

        # Sort tasks and chats by their creation date, descending
        ctxs.sort(key=lambda x: x["created_at"], reverse=True)
        tasks.sort(key=lambda x: x["created_at"], reverse=True)

        # Return data from this server
        return PollResponse(
            context=context.id,
            contexts=ctxs,
            tasks=tasks,
            logs=logs,
            log_guid=context.log.guid,
            log_version=len(context.log.updates),
            log_progress=context.log.progress if context.log.progress else 0.0,
            log_progress_active=bool(context.log.progress_active),
            paused=context.paused,
            message="Poll completed successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to poll status: {str(e)}")
