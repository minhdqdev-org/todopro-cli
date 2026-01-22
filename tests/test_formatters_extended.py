"""Additional tests for UI formatters to improve coverage."""

import pytest
from io import StringIO
from unittest.mock import patch
from datetime import datetime, timedelta
from todopro_cli.ui.formatters import (
    format_output,
    format_table,
    format_dict_table,
    format_single_item,
    format_pretty,
    format_tasks_pretty,
    format_task_item,
    format_projects_pretty,
    format_project_item,
    format_generic_list_pretty,
    format_single_item_pretty,
    is_today,
    format_due_date,
)


def test_format_output_default():
    """Test output format defaults to pretty."""
    data = [{"id": "123"}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_output(data, "unknown_format")
        # Should use pretty format as default


def test_format_output_json_pretty():
    """Test JSON pretty output format."""
    data = {"key": "value"}
    with patch('builtins.print') as mock_print:
        format_output(data, "json-pretty")
        mock_print.assert_called_once()


def test_format_output_wide():
    """Test wide table output format."""
    data = [{"id": "123", "name": "Test"}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_output(data, "wide")


def test_format_dict_table_with_boolean():
    """Test formatting table with boolean values."""
    data = [{"id": "1", "completed": True}, {"id": "2", "completed": False}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_dict_table(data, wide=False)


def test_format_dict_table_with_list_values():
    """Test formatting table with list values."""
    data = [{"id": "1", "labels": ["work", "urgent"]}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_dict_table(data, wide=False)


def test_format_dict_table_with_none_values():
    """Test formatting table with None values."""
    data = [{"id": "1", "description": None}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_dict_table(data, wide=False)


def test_format_single_item_with_various_types():
    """Test formatting single item with various value types."""
    data = {
        "id": "123",
        "name": "Test",
        "is_active": True,
        "tags": ["a", "b"],
        "description": None,
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_single_item(data)


def test_format_table_with_tasks_key():
    """Test formatting dict with tasks key."""
    data = {"tasks": [{"id": "1", "content": "Task 1"}]}
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)


def test_format_table_with_projects_key():
    """Test formatting dict with projects key."""
    data = {"projects": [{"id": "1", "name": "Project 1"}]}
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)


def test_format_pretty_with_dict_items():
    """Test pretty format with dict containing items."""
    data = {"items": [{"id": "1", "content": "Test"}]}
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_pretty_single_item():
    """Test pretty format with single item dict."""
    data = {"id": "123", "content": "Test task", "is_completed": False}
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_tasks_pretty(tasks, compact=False)


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
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_tasks_pretty(tasks, compact=False)


def test_format_tasks_pretty_compact():
    """Test formatting tasks in compact mode."""
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_tasks_pretty(tasks, compact=True)


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
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_project_item(project, compact=False)


def test_format_project_item_compact():
    """Test formatting project in compact mode."""
    project = {
        "id": "1",
        "name": "Compact Project",
        "color": "#00FF00",
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_project_item(project, compact=True)


def test_format_generic_list_pretty():
    """Test formatting generic list."""
    items = [
        {"id": "1", "name": "Item 1"},
        {"content": "Item 2"},
        {"other": "value"},
    ]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_generic_list_pretty(items, compact=False)


def test_format_single_item_pretty_task():
    """Test formatting single task in pretty mode."""
    task = {
        "id": "1",
        "content": "Single task",
        "is_completed": False,
        "priority": 2,
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_single_item_pretty(task)


def test_format_single_item_pretty_project():
    """Test formatting single project in pretty mode."""
    project = {
        "id": "1",
        "name": "Single project",
        "color": "#FF0000",
        "is_favorite": True,
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_single_item_pretty(project)


def test_format_single_item_pretty_generic():
    """Test formatting single generic item in pretty mode."""
    item = {"id": "1", "other_field": "value"}
    with patch('sys.stdout', new=StringIO()) as fake_out:
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
    with patch('builtins.print') as mock_print:
        from todopro_cli.ui.formatters import format_quiet
        format_quiet(data)
        assert mock_print.call_count == 2
