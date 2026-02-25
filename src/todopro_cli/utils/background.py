"""Background task runner with retry logic."""

import subprocess
import sys
import tempfile
from typing import Any

# Worker script template that will run in background
WORKER_SCRIPT_TEMPLATE = """
import asyncio
import os
import traceback
from typing import Dict, Any

def log_debug(msg):
    debug_log = os.path.expanduser("~/.local/share/todopro/logs/background_debug.log")
    os.makedirs(os.path.dirname(debug_log), exist_ok=True)
    with open(debug_log, "a") as f:
        import datetime
        f.write(f"{{datetime.datetime.now()}}: {{msg}}\\n")
        f.flush()

async def complete_task(context: Dict[str, Any]):
    from todopro_cli.services.api.client import get_client
    from todopro_cli.services.api.tasks import TasksAPI
    from .commands.tasks import resolve_task_id

    task_id = context["task_id"]

    client = get_client()
    tasks_api = TasksAPI(client)
    try:
        resolved_id = await resolve_task_id(tasks_api, task_id)
        await tasks_api.complete_task(resolved_id)
    finally:
        await client.close()

async def batch_complete_tasks(context: Dict[str, Any]):
    from todopro_cli.services.api.client import get_client
    from todopro_cli.services.api.tasks import TasksAPI
    from .commands.tasks import resolve_task_id

    task_ids = context["task_ids"]

    client = get_client()
    tasks_api = TasksAPI(client)
    try:
        # Resolve all IDs
        resolved_ids = []
        for task_id in task_ids:
            resolved_id = await resolve_task_id(tasks_api, task_id)
            resolved_ids.append(resolved_id)

        # Batch complete
        await tasks_api.batch_complete_tasks(resolved_ids)
    finally:
        await client.close()

async def run_with_retry(task_type: str, command: str, context: Dict[str, Any], max_retries: int):
    from .utils.error_logger import log_error
    from .utils.task_cache import get_background_cache

    last_error = None

    # Get task IDs for cache removal
    task_ids = []
    if task_type == "complete":
        task_ids = [context.get("task_id")]
    elif task_type == "batch_complete":
        task_ids = context.get("task_ids", [])

    try:
        for attempt in range(max_retries):
            try:
                if task_type == "complete":
                    await complete_task(context)
                elif task_type == "batch_complete":
                    await batch_complete_tasks(context)
                else:
                    raise ValueError(f"Unknown task type: {{task_type}}")

                # Success! Remove from cache
                cache = get_background_cache()
                for task_id in task_ids:
                    if task_id:
                        cache.remove_task(task_id)
                return  # Success
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue

        # All retries failed
        # Remove from cache even on failure (don't keep showing as "completing")
        cache = get_background_cache()
        for task_id in task_ids:
            if task_id:
                cache.remove_task(task_id)

        # Log error
        if last_error:
            log_error(
                command=command,
                error=last_error,
                context=context,
                retries=max_retries - 1,
            )
    except Exception:
        # Final safety net - ensure cache is cleaned even if something goes wrong
        try:
            cache = get_background_cache()
            for task_id in task_ids:
                if task_id:
                    cache.remove_task(task_id)
        except Exception:
            pass  # Best effort

if __name__ == "__main__":
    import json
    import sys

    # Read parameters from command line
    task_type = sys.argv[1]
    command = sys.argv[2]
    context = json.loads(sys.argv[3])
    max_retries = int(sys.argv[4])

    try:
        asyncio.run(run_with_retry(task_type, command, context, max_retries))
    except Exception:
        pass  # Errors are logged by run_with_retry
"""


def run_in_background(
    func=None,  # Deprecated, kept for compatibility
    command: str = "",
    context: dict[str, Any] | None = None,
    max_retries: int = 3,
    task_type: str | None = None,
) -> None:
    """
    Run a task in a background process with retry logic.

    Args:
        func: DEPRECATED - use task_type instead
        command: Command name for logging
        context: Context information (must include task_id)
        max_retries: Maximum number of retry attempts (default: 3)
        task_type: Type of task to run ("complete", etc.)
    """
    if context is None:
        context = {}

    # Determine task type from context if not provided
    if task_type is None:
        task_type = command  # Use command as task type

    # Write worker script to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(WORKER_SCRIPT_TEMPLATE)
        script_path = f.name

    # Prepare arguments
    import json

    args = [
        sys.executable,
        script_path,
        task_type,
        command,
        json.dumps(context),
        str(max_retries),
    ]

    # Start detached background process
    subprocess.Popen(
        args,
        start_new_session=True,  # Detach from parent session
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    # Process continues independently - no wait needed
