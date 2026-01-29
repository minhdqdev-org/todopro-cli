"""Task helper utilities."""

from typing import Optional

from todopro_cli.api.tasks import TasksAPI


def _find_shortest_unique_suffix(task_ids: list[str], target_id: str) -> str:
    """
    Find the shortest suffix of target_id that uniquely identifies it.
    
    Args:
        task_ids: List of all task IDs
        target_id: The task ID to find a unique suffix for
        
    Returns:
        The shortest unique suffix
    """
    # Try increasingly longer suffixes from the end
    for length in range(1, len(target_id) + 1):
        suffix = target_id[-length:]
        matches = [tid for tid in task_ids if tid.endswith(suffix)]
        if len(matches) == 1:
            return suffix
    return target_id  # Fallback to full ID


async def resolve_task_id(tasks_api: TasksAPI, task_id_or_suffix: str) -> str:
    """
    Resolve a task ID or suffix to a full task ID.
    
    If the input is already a valid task ID, returns it as-is.
    If it's a suffix, searches for matching tasks and returns the full ID.
    
    Args:
        tasks_api: The tasks API client
        task_id_or_suffix: Full task ID or suffix to resolve
        
    Returns:
        The full task ID
        
    Raises:
        ValueError: If no matching task is found or multiple matches exist
    """
    # First, try to get the task directly (maybe it's already a full ID)
    try:
        await tasks_api.get_task(task_id_or_suffix)
        return task_id_or_suffix
    except Exception:
        # Not a valid full ID, try to resolve as suffix
        pass
    
    # Search for tasks matching the suffix
    result = await tasks_api.list_tasks(limit=100)
    
    # Handle different response formats
    if isinstance(result, list):
        tasks = result
    elif isinstance(result, dict):
        tasks = result.get("items", result.get("tasks", []))
    else:
        raise ValueError(f"Unexpected API response format: {type(result)}")
    
    matching_tasks = [
        task for task in tasks 
        if task.get("id", "").endswith(task_id_or_suffix)
    ]
    
    if not matching_tasks:
        raise ValueError(
            f"No task found with ID or suffix '{task_id_or_suffix}'"
        )
    
    if len(matching_tasks) > 1:
        task_ids = [task["id"] for task in matching_tasks]
        
        # Find suggested unique suffixes and format with task content
        suggestions = []
        for task in matching_tasks:
            tid = task["id"]
            unique_suffix = _find_shortest_unique_suffix(
                [t["id"] for t in tasks], 
                tid
            )
            content = task.get("content", "No content")
            # Truncate long content
            if len(content) > 70:
                content = content[:67] + "..."
            suggestions.append(f"  [{unique_suffix}] {content}")
        
        raise ValueError(
            f"Multiple tasks match suffix '{task_id_or_suffix}':\n" +
            "\n".join(suggestions) +
            "\n\nUse the suffix in brackets to select a specific task."
        )
    
    return matching_tasks[0]["id"]
