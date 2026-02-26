"""Additional tests for UI formatters to improve coverage."""

from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from todopro_cli.utils.ui.formatters import (
    calculate_unique_suffixes,
    format_dict_table,
    format_due_date,
    format_generic_list_pretty,
    format_next_task,
    format_output,
    format_pretty,
    format_project_item,
    format_projects_pretty,
    format_relative_time,
    format_single_item,
    format_single_item_pretty,
    format_table,
    format_task_item,
    format_tasks_pretty,
    is_overdue,
    is_today,
)


def test_format_output_default():
    """Test output format defaults to pretty."""
    data = [{"id": "123"}]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_output(data, "unknown_format")
        # Should use pretty format as default


def test_format_output_json_pretty():
    """Test JSON pretty output format."""
    data = {"key": "value"}
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_output(data, "json-pretty")
        mock_console.print.assert_called_once()


def test_format_output_wide():
    """Test wide table output format."""
    data = [{"id": "123", "name": "Test"}]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_output(data, "wide")


def test_format_dict_table_with_boolean():
    """Test formatting table with boolean values."""
    data = [{"id": "1", "completed": True}, {"id": "2", "completed": False}]
    # format_dict_table uses rich console - just verify no exception
    format_dict_table(data)


def test_format_dict_table_with_list_values():
    """Test formatting table with list values."""
    data = [{"id": "1", "labels": ["work", "urgent"]}]
    format_dict_table(data)


def test_format_dict_table_with_none_values():
    """Test formatting table with None values."""
    data = [{"id": "1", "description": None}]
    format_dict_table(data)


def test_format_single_item_with_various_types():
    """Test formatting single item with various value types."""
    data = {
        "id": "123",
        "name": "Test",
        "is_active": True,
        "tags": ["a", "b"],
        "description": None,
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_single_item(data)


def test_format_table_with_tasks_key():
    """Test formatting dict with tasks key."""
    data = {"tasks": [{"id": "1", "content": "Task 1"}]}
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_table(data)


def test_format_table_with_projects_key():
    """Test formatting dict with projects key."""
    data = {"projects": [{"id": "1", "name": "Project 1"}]}
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_table(data)


def test_format_pretty_with_dict_items():
    """Test pretty format with dict containing items."""
    data = {"items": [{"id": "1", "content": "Test"}]}
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_pretty_with_dict_tasks():
    """Test pretty format with dict containing tasks."""
    now = datetime.now()
    data = {
        "tasks": [
            {
                "id": "1",
                "content": "Test task",
                "is_completed": False,
                "priority": 3,
                "labels": ["urgent"],
                "created_at": now.isoformat(),
            }
        ]
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_pretty_with_dict_projects():
    """Test pretty format with dict containing projects."""
    now = datetime.now()
    data = {
        "projects": [
            {
                "id": "1",
                "name": "Test Project",
                "color": "#FF0000",
                "is_favorite": True,
                "is_archived": False,
                "created_at": now.isoformat(),
            }
        ]
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_pretty_single_item():
    """Test pretty format with single item dict."""
    data = {"id": "123", "content": "Test task", "is_completed": False}
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_tasks_pretty_with_completed():
    """Test formatting tasks with completed ones."""
    now = datetime.now()
    tasks = [
        {
            "id": "1",
            "content": "Completed task",
            "is_completed": True,
            "completed_at": now.isoformat(),
            "priority": 2,
            "labels": [],
        },
        {
            "id": "2",
            "content": "Active task",
            "is_completed": False,
            "priority": 1,
            "labels": ["work"],
        },
    ]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_tasks_pretty(tasks)


def test_format_tasks_pretty_with_overdue():
    """Test formatting tasks with overdue ones."""
    past = datetime.now() - timedelta(days=2)
    tasks = [
        {
            "id": "1",
            "content": "Overdue task",
            "is_completed": False,
            "due_date": past.isoformat(),
            "priority": 2,
            "labels": [],
        }
    ]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_tasks_pretty(tasks)


def test_format_tasks_pretty_compact():
    """Test formatting tasks - standard call."""
    now = datetime.now()
    future = now + timedelta(days=1)
    tasks = [
        {
            "id": "1",
            "content": "Task with due date",
            "is_completed": False,
            "due_date": future.isoformat(),
            "priority": 2,
            "labels": ["work", "urgent", "important"],
        }
    ]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_tasks_pretty(tasks)


def test_format_task_item_recurring():
    """Test formatting a recurring task."""
    now = datetime.now()
    task = {
        "id": "1",
        "content": "Recurring task",
        "is_completed": False,
        "is_recurring": True,
        "priority": 2,
        "labels": [],
        "next_occurrence": (now + timedelta(days=1)).isoformat(),
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_task_item(task, compact=False)


def test_format_task_item_with_metadata():
    """Test formatting task with various metadata."""
    now = datetime.now()
    task = {
        "id": "1",
        "content": "Task with metadata",
        "is_completed": False,
        "priority": 3,
        "labels": ["work"],
        "due_date": (now + timedelta(hours=2)).isoformat(),
        "assigned_to": "user123",
        "comments_count": 5,
        "project_name": "Project Alpha",
        "created_at": (now - timedelta(hours=1)).isoformat(),
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_task_item(task, compact=False)


def test_format_projects_pretty_with_archived():
    """Test formatting projects with archived ones."""
    now = datetime.now()
    projects = [
        {
            "id": "1",
            "name": "Active Project",
            "color": "#FF0000",
            "is_favorite": False,
            "is_archived": False,
        },
        {
            "id": "2",
            "name": "Archived Project",
            "color": "#00FF00",
            "is_favorite": False,
            "is_archived": True,
        },
    ]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_projects_pretty(projects, compact=False)


def test_format_projects_pretty_with_favorites():
    """Test formatting projects with favorites."""
    projects = [
        {
            "id": "1",
            "name": "Favorite Project",
            "color": "#FF0000",
            "is_favorite": True,
            "is_archived": False,
        }
    ]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_projects_pretty(projects, compact=False)


def test_format_project_item_with_stats():
    """Test formatting project with statistics."""
    now = datetime.now()
    project = {
        "id": "1",
        "name": "Project with stats",
        "color": "#FF0000",
        "is_favorite": False,
        "is_archived": False,
        "tasks_active": 10,
        "tasks_done": 5,
        "completion_percentage": 75.5,
        "shared_with": ["user1", "user2", "user3", "user4"],
        "due_date": (now + timedelta(days=7)).isoformat(),
        "overdue_count": 3,
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_project_item(project, compact=False)


def test_format_project_item_compact():
    """Test formatting project in compact mode."""
    project = {
        "id": "1",
        "name": "Compact Project",
        "color": "#00FF00",
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_project_item(project, compact=True)


def test_format_generic_list_pretty():
    """Test formatting generic list."""
    items = [
        {"id": "1", "name": "Item 1"},
        {"content": "Item 2"},
        {"other": "value"},
    ]
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_generic_list_pretty(items, compact=False)


def test_format_single_item_pretty_task():
    """Test formatting single task in pretty mode."""
    task = {
        "id": "1",
        "content": "Single task",
        "is_completed": False,
        "priority": 2,
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_single_item_pretty(task)


def test_format_single_item_pretty_project():
    """Test formatting single project in pretty mode."""
    project = {
        "id": "1",
        "name": "Single project",
        "color": "#FF0000",
        "is_favorite": True,
    }
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_single_item_pretty(project)


def test_format_single_item_pretty_generic():
    """Test formatting single generic item in pretty mode."""
    item = {"id": "1", "other_field": "value"}
    with patch("sys.stdout", new=StringIO()) as fake_out:
        format_single_item_pretty(item)


def test_format_due_date_this_week():
    """Test formatting due date for this week."""
    future = datetime.now() + timedelta(days=3)
    result = format_due_date(future.isoformat())
    # Should return day name


def test_format_due_date_multiple_days_ago():
    """Test formatting date multiple days ago."""
    past = datetime.now() - timedelta(days=10)
    result = format_due_date(past.isoformat())
    # Should return formatted date


def test_format_due_date_invalid():
    """Test formatting invalid due date."""
    result = format_due_date("invalid_date")
    assert result == "invalid_date"


def test_is_today_invalid_date():
    """Test is_today with invalid date."""
    result = is_today("invalid_date")
    assert result is False


def test_format_quiet_with_items_key():
    """Test quiet format with items key in dict."""
    data = {"items": [{"id": "123"}, {"id": "456"}]}
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        from todopro_cli.utils.ui.formatters import format_quiet

        format_quiet(data)
        assert mock_console.print.call_count == 2


# ===========================================================================
# calculate_unique_suffixes — else branch (line 48)
# ===========================================================================

def test_calculate_unique_suffixes_else_branch():
    """When a task ID is always a suffix of another, the else branch fires."""
    # "ab" is a proper suffix of "aab": every length suffix of "ab" matches "aab"
    result = calculate_unique_suffixes(["ab", "aab"])
    # "ab" can only be fully distinguished by its full 2-char length
    assert result["ab"] == 2
    # "aab" gets a unique suffix at length 3
    assert result["aab"] == 3


def test_calculate_unique_suffixes_empty_returns_empty():
    assert calculate_unique_suffixes([]) == {}


def test_calculate_unique_suffixes_single_id():
    result = calculate_unique_suffixes(["abc123"])
    assert result["abc123"] == 1  # single item, length 1 is unique


# ===========================================================================
# format_dict_table — empty items (lines 115-116)
# ===========================================================================

def test_format_dict_table_empty_items():
    """Directly calling format_dict_table([]) must print 'No items found'."""
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_dict_table([])
    mock_console.print.assert_called_once()
    call_args = str(mock_console.print.call_args)
    assert "No items" in call_args or "found" in call_args.lower()


# ===========================================================================
# is_today — timezone-aware datetime (line 616)
# ===========================================================================

def test_is_today_with_timezone_aware_datetime():
    """is_today must handle a timezone-aware datetime string (line 616)."""
    from datetime import timezone

    # Use a UTC datetime for today
    today_utc = datetime.now(tz=timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    date_str = today_utc.isoformat()
    # The result may be True or False depending on TZ offset, but must not raise
    result = is_today(date_str)
    assert isinstance(result, bool)


def test_is_today_with_z_suffix():
    """Datetime with 'Z' suffix should be parsed and handled correctly."""
    today_z = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    result = is_today(today_z)
    assert isinstance(result, bool)


# ===========================================================================
# format_relative_time — timezone-aware datetime (line 690)
# ===========================================================================

def test_format_relative_time_with_timezone_aware_datetime():
    """format_relative_time with tz-aware input triggers the UTC now branch (line 690)."""
    from datetime import timezone

    # A timezone-aware datetime 2 hours ago
    two_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    result = format_relative_time(two_hours_ago)
    assert "ago" in result.lower() or "h ago" in result

    # 5 minutes ago
    five_min_ago = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    result2 = format_relative_time(five_min_ago)
    assert "ago" in result2.lower() or "m ago" in result2


def test_format_relative_time_with_z_suffix_string():
    """format_relative_time with a Z-suffix string also uses UTC branch."""
    # 3 hours ago as ISO string with Z
    three_hours_ago = datetime.utcnow() - timedelta(hours=3)
    date_str = three_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
    result = format_relative_time(date_str)
    assert result  # non-empty


# ===========================================================================
# format_next_task (lines 762-821)
# ===========================================================================

def test_format_next_task_minimal():
    """format_next_task with only required fields must not raise."""
    task = {"id": "abc123def456", "content": "Write unit tests"}
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called


def test_format_next_task_with_due_date():
    task = {
        "id": "abc123def456",
        "content": "Ship feature",
        "due_date": "2025-01-15T10:00:00Z",
    }
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called


def test_format_next_task_with_project():
    task = {
        "id": "abc123def456",
        "content": "Review PR",
        "project": {"name": "Work"},
    }
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called


def test_format_next_task_with_eisenhower_quadrant():
    task = {
        "id": "abc123def456",
        "content": "Fix critical bug",
        "eisenhower_quadrant": "Q1",
    }
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called


def test_format_next_task_with_description():
    task = {
        "id": "abc123def456",
        "content": "Design new feature",
        "description": "Detailed description of the feature work.",
    }
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called


def test_format_next_task_with_recurring():
    task = {
        "id": "abc123def456",
        "content": "Daily standup",
        "is_recurring": True,
    }
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called


def test_format_next_task_full_metadata():
    """All metadata fields combined."""
    task = {
        "id": "abc123def456",
        "content": "Deploy to production",
        "due_date": "2025-06-01T14:00:00Z",
        "project": {"name": "Infrastructure"},
        "eisenhower_quadrant": "Q2",
        "is_recurring": False,
        "description": "Deploy the new release to prod servers.",
    }
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    # Should have printed at least: header, task line, meta line, description, newline
    assert mock_console.print.call_count >= 4


def test_format_next_task_no_id():
    """Task without an 'id' must not raise."""
    task = {"content": "Task without id"}
    with patch("todopro_cli.utils.ui.formatters.console") as mock_console:
        format_next_task(task)
    assert mock_console.print.called
