"""Task helper utilities."""

from todopro_cli.services.task_service import TaskService


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


async def resolve_task_id(task_service: TaskService, task_id_or_suffix: str) -> str:
    """
    Resolve a task ID or suffix to a full task ID.

    If the input is already a valid task ID, returns it as-is.
    If it's a suffix, searches for matching tasks and returns the full ID.

    Args:
        task_service: The task service instance
        task_id_or_suffix: Full task ID or suffix to resolve

    Returns:
        The full task ID

    Raises:
        ValueError: If no matching task is found or multiple matches exist
    """
    # First, check cached suffix mapping from recent display
    from .task_cache import get_suffix_mapping

    suffix_mapping = get_suffix_mapping()
    if task_id_or_suffix in suffix_mapping:
        return suffix_mapping[task_id_or_suffix]

    # Second, try to get the task directly (maybe it's already a full ID)
    try:
        await task_service.get_task(task_id_or_suffix)
        return task_id_or_suffix
    except Exception:
        # Not a valid full ID, try to resolve as suffix
        pass

    # Search for tasks matching the suffix
    tasks_response = await task_service.list_tasks(limit=100)

    # Handle both dict response with 'items' key and direct list
    if isinstance(tasks_response, dict):
        tasks = tasks_response.get("items", tasks_response.get("tasks", []))
    else:
        tasks = tasks_response

    # Handle both dict and object tasks
    if tasks and isinstance(tasks[0], dict):
        matching_tasks = [
            task for task in tasks if task.get("id", "").endswith(task_id_or_suffix)
        ]
    else:
        matching_tasks = [task for task in tasks if task.id.endswith(task_id_or_suffix)]

    if not matching_tasks:
        raise ValueError(f"No task found with ID or suffix '{task_id_or_suffix}'")

    if len(matching_tasks) > 1:
        # Find suggested unique suffixes and format with task content
        suggestions = []
        for task in matching_tasks:
            # Handle both dict and object
            task_id = task.get("id") if isinstance(task, dict) else task.id
            task_content = (
                task.get("content") if isinstance(task, dict) else task.content
            )

            # Get all task IDs for comparison
            all_task_ids = [t.get("id") if isinstance(t, dict) else t.id for t in tasks]

            unique_suffix = _find_shortest_unique_suffix(all_task_ids, task_id)
            content = task_content
            # Truncate long content
            if len(content) > 70:
                content = content[:67] + "..."
            suggestions.append(f"  [{unique_suffix}] {content}")

        raise ValueError(
            f"Multiple tasks match suffix '{task_id_or_suffix}':\n"
            + "\n".join(suggestions)
            + "\n\nUse the suffix in brackets to select a specific task."
        )

    return (
        matching_tasks[0].get("id")
        if isinstance(matching_tasks[0], dict)
        else matching_tasks[0].id
    )
