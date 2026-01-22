"""Final tests to complete formatter coverage."""

import pytest
from io import StringIO
from unittest.mock import patch
from datetime import datetime, timedelta
from todopro_cli.ui.formatters import format_table, format_pretty


def test_format_table_with_simple_list():
    """Test formatting a simple list (not dict)."""
    data = ["item1", "item2", "item3"]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)


def test_format_table_with_string():
    """Test formatting a string."""
    data = "simple string"
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)


def test_format_pretty_with_string():
    """Test pretty format with a string."""
    data = "simple string"
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_pretty_with_non_dict_list():
    """Test pretty format with non-dict list items."""
    data = ["item1", "item2"]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_pretty(data)


def test_format_task_item_compact_completed():
    """Test formatting completed task in compact mode."""
    now = datetime.now()
    task = {
        "id": "1",
        "content": "Completed task",
        "is_completed": True,
        "completed_at": now.isoformat(),
        "priority": 2,
        "labels": [],
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        from todopro_cli.ui.formatters import format_task_item
        format_task_item(task, compact=True)


def test_format_task_item_compact_with_overdue():
    """Test formatting overdue task in compact mode."""
    past = datetime.now() - timedelta(days=1)
    task = {
        "id": "1",
        "content": "Overdue task",
        "is_completed": False,
        "due_date": past.isoformat(),
        "priority": 2,
        "labels": ["work", "urgent", "critical"],
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        from todopro_cli.ui.formatters import format_task_item
        format_task_item(task, compact=True)


def test_format_task_item_without_project_name():
    """Test formatting task without project name to show created_at."""
    now = datetime.now()
    task = {
        "id": "1",
        "content": "Task without project",
        "is_completed": False,
        "priority": 2,
        "labels": [],
        "created_at": (now - timedelta(hours=2)).isoformat(),
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        from todopro_cli.ui.formatters import format_task_item
        format_task_item(task, compact=False)


def test_format_project_item_with_updated_at():
    """Test formatting project with updated_at instead of due_date."""
    now = datetime.now()
    project = {
        "id": "1",
        "name": "Project",
        "color": "#FF0000",
        "is_favorite": False,
        "is_archived": False,
        "updated_at": (now - timedelta(hours=3)).isoformat(),
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        from todopro_cli.ui.formatters import format_project_item
        format_project_item(project, compact=False)


def test_format_project_item_without_color():
    """Test formatting project without color."""
    project = {
        "id": "1",
        "name": "Project",
        "color": "#808080",
        "is_favorite": False,
        "is_archived": False,
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        from todopro_cli.ui.formatters import format_project_item
        format_project_item(project, compact=False)


def test_format_project_item_compact_without_color():
    """Test formatting project in compact mode without custom color."""
    project = {
        "id": "1",
        "name": "Project",
        "color": "#808080",
    }
    with patch('sys.stdout', new=StringIO()) as fake_out:
        from todopro_cli.ui.formatters import format_project_item
        format_project_item(project, compact=True)


def test_is_overdue_invalid():
    """Test is_overdue with invalid date string."""
    from todopro_cli.ui.formatters import is_overdue
    result = is_overdue("invalid_date")
    assert result is False


def test_format_relative_time_invalid():
    """Test format_relative_time with invalid date."""
    from todopro_cli.ui.formatters import format_relative_time
    result = format_relative_time("invalid_date")
    assert result == ""


def test_get_project_icon_launch():
    """Test getting icon for launch project."""
    from todopro_cli.ui.formatters import get_project_icon
    assert get_project_icon("Sprint Launch") == "🚀"


def test_get_project_icon_mobile():
    """Test getting icon for mobile project."""
    from todopro_cli.ui.formatters import get_project_icon
    assert get_project_icon("Mobile App") == "📱"


def test_get_project_icon_analytics():
    """Test getting icon for analytics project."""
    from todopro_cli.ui.formatters import get_project_icon
    assert get_project_icon("Data Analytics") == "📊"
