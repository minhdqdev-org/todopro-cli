"""Background task runner with retry logic."""

import asyncio
import multiprocessing
import sys
from typing import Any, Callable, Dict, Optional

from todopro_cli.utils.error_logger import log_error


def _background_task_worker(
    task_type: str,
    command: str,
    context: Dict[str, Any],
    max_retries: int,
) -> None:
    """
    Worker function that runs in background process.
    This must be a top-level function for multiprocessing to work.
    """
    import asyncio
    from todopro_cli.api.client import get_client
    from todopro_cli.api.tasks import TasksAPI
    from todopro_cli.commands.tasks import resolve_task_id
    
    async def _complete_task():
        """Complete a task (runs in background)."""
        profile = context.get("profile", "default")
        task_id = context["task_id"]
        
        client = get_client(profile)
        tasks_api = TasksAPI(client)
        try:
            resolved_id = await resolve_task_id(tasks_api, task_id)
            await tasks_api.complete_task(resolved_id)
        finally:
            await client.close()
    
    async def _run_with_retry():
        """Run the task with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if task_type == "complete":
                    await _complete_task()
                else:
                    raise ValueError(f"Unknown task type: {task_type}")
                return  # Success
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
                continue
        
        # All retries failed, log error
        if last_error:
            log_error(
                command=command,
                error=last_error,
                context=context,
                retries=max_retries - 1,
            )
    
    # Run the async function
    try:
        asyncio.run(_run_with_retry())
    except Exception:
        # Silently fail - error is already logged
        pass


def run_in_background(
    func: Callable = None,  # Deprecated, kept for compatibility
    command: str = "",
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    task_type: Optional[str] = None,
) -> None:
    """
    Run a task in a background process with retry logic.
    
    Args:
        func: DEPRECATED - use task_type instead
        command: Command name for logging
        context: Context information (must include task_id, profile)
        max_retries: Maximum number of retry attempts (default: 3)
        task_type: Type of task to run ("complete", etc.)
    """
    if context is None:
        context = {}
    
    # Determine task type from context if not provided
    if task_type is None:
        task_type = command  # Use command as task type
    
    # Start background process
    process = multiprocessing.Process(
        target=_background_task_worker,
        args=(task_type, command, context, max_retries),
        daemon=True
    )
    process.start()
    # Don't wait for it to finish
