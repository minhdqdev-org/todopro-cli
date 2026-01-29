"""Tests for UI formatters."""

import pytest
from io import StringIO
from unittest.mock import patch
from datetime import datetime
from todopro_cli.ui.formatters import (
    format_output,
    format_table,
    format_pretty,
    format_quiet,
    format_error,
    format_success,
    format_warning,
    format_info,
    is_today,
    is_overdue,
    format_due_date,
    format_relative_time,
    get_project_icon,
    get_progress_bar,
    get_completion_color,
)


def test_format_error():
    """Test formatting error messages."""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_error("Test error")
        # Just verify no exception is raised


def test_format_success():
    """Test formatting success messages."""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_success("Test success")
        # Just verify no exception is raised


def test_format_warning():
    """Test formatting warning messages."""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_warning("Test warning")
        # Just verify no exception is raised


def test_format_info():
    """Test formatting info messages."""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_info("Test info")
        # Just verify no exception is raised


def test_format_output_json():
    """Test JSON output format."""
    data = {"key": "value", "number": 42}
    with patch('builtins.print') as mock_print:
        format_output(data, "json")
        mock_print.assert_called_once()


def test_format_output_yaml():
    """Test YAML output format."""
    data = {"key": "value", "number": 42}
    with patch('builtins.print') as mock_print:
        format_output(data, "yaml")
        mock_print.assert_called_once()


def test_format_output_quiet():
    """Test quiet output format."""
    data = [{"id": "123"}, {"id": "456"}]
    with patch('builtins.print') as mock_print:
        format_output(data, "quiet")
        assert mock_print.call_count == 2


def test_format_output_table():
    """Test table output format."""
    data = [{"id": "123", "name": "Test"}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_output(data, "table")
        # Just verify no exception is raised


def test_format_output_pretty():
    """Test pretty output format."""
    data = [{"id": "123", "name": "Test"}]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_output(data, "pretty")
        # Just verify no exception is raised


def test_format_table_empty_data():
    """Test formatting empty data as table."""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table([])
        # Just verify no exception is raised


def test_format_table_with_dict_list():
    """Test formatting list of dicts as table."""
    data = [
        {"id": "1", "name": "Task 1", "is_completed": True},
        {"id": "2", "name": "Task 2", "is_completed": False},
    ]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)
        # Just verify no exception is raised


def test_format_table_with_single_dict():
    """Test formatting single dict as table."""
    data = {"id": "1", "name": "Task 1", "is_completed": True}
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)
        # Just verify no exception is raised


def test_format_table_with_items_key():
    """Test formatting dict with items key."""
    data = {"items": [{"id": "1", "name": "Task 1"}]}
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_table(data)
        # Just verify no exception is raised


def test_format_pretty_empty_data():
    """Test formatting empty data in pretty format."""
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_pretty([])
        # Just verify no exception is raised


def test_format_pretty_with_tasks():
    """Test formatting tasks in pretty format."""
    now = datetime.now()
    tasks = [
        {
            "id": "1",
            "content": "Test task",
            "is_completed": False,
            "priority": 2,
            "labels": ["work"],
            "created_at": now.isoformat(),
        }
    ]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_pretty(tasks)
        # Just verify no exception is raised


def test_format_pretty_with_projects():
    """Test formatting projects in pretty format."""
    now = datetime.now()
    projects = [
        {
            "id": "1",
            "name": "Test Project",
            "color": "#FF0000",
            "is_favorite": True,
            "is_archived": False,
            "created_at": now.isoformat(),
        }
    ]
    with patch('sys.stdout', new=StringIO()) as fake_out:
        format_pretty(projects)
        # Just verify no exception is raised


def test_format_quiet_with_list():
    """Test quiet format with list of items."""
    data = [{"id": "123"}, {"id": "456"}]
    with patch('builtins.print') as mock_print:
        format_quiet(data)
        assert mock_print.call_count == 2


def test_format_quiet_with_dict():
    """Test quiet format with single dict."""
    data = {"id": "123"}
    with patch('builtins.print') as mock_print:
        format_quiet(data)
        mock_print.assert_called_once_with("123")


def test_is_today_with_today_date():
    """Test is_today with today's date."""
    now = datetime.now()
    assert is_today(now.isoformat()) is True


def test_is_today_with_old_date():
    """Test is_today with old date."""
    from datetime import timedelta
    old_date = datetime.now() - timedelta(days=1)
    assert is_today(old_date.isoformat()) is False


def test_is_today_with_none():
    """Test is_today with None."""
    assert is_today(None) is False


def test_is_overdue_with_past_date():
    """Test is_overdue with past date."""
    from datetime import timedelta
    past_date = datetime.now() - timedelta(days=1)
    assert is_overdue(past_date.isoformat()) is True


def test_is_overdue_with_future_date():
    """Test is_overdue with future date."""
    from datetime import timedelta
    future_date = datetime.now() + timedelta(days=1)
    assert is_overdue(future_date.isoformat()) is False


def test_is_overdue_with_none():
    """Test is_overdue with None."""
    assert is_overdue(None) is False


def test_format_due_date_today():
    """Test formatting due date for today."""
    now = datetime.now()
    result = format_due_date(now.isoformat())
    # New format: HH:MM DD/MM DayOfWeek
    assert "/" in result  # Contains date separator
    assert ":" in result  # Contains time separator


def test_format_due_date_tomorrow():
    """Test formatting due date for tomorrow."""
    from datetime import timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    result = format_due_date(tomorrow.isoformat())
    # New format: HH:MM DD/MM DayOfWeek
    assert "/" in result  # Contains date separator
    assert ":" in result  # Contains time separator


def test_format_due_date_past():
    """Test formatting past due date."""
    from datetime import timedelta
    yesterday = datetime.now() - timedelta(days=1)
    result = format_due_date(yesterday.isoformat())
    # New format: HH:MM DD/MM DayOfWeek
    assert "/" in result  # Contains date separator
    assert ":" in result  # Contains time separator


def test_format_relative_time_just_now():
    """Test formatting relative time for recent timestamp."""
    now = datetime.now()
    result = format_relative_time(now.isoformat())
    assert result == "just now"


def test_format_relative_time_minutes():
    """Test formatting relative time for minutes ago."""
    from datetime import timedelta
    past = datetime.now() - timedelta(minutes=5)
    result = format_relative_time(past.isoformat())
    assert "5m ago" in result


def test_format_relative_time_hours():
    """Test formatting relative time for hours ago."""
    from datetime import timedelta
    past = datetime.now() - timedelta(hours=2)
    result = format_relative_time(past.isoformat())
    assert "2h ago" in result


def test_format_relative_time_days():
    """Test formatting relative time for days ago."""
    from datetime import timedelta
    past = datetime.now() - timedelta(days=3)
    result = format_relative_time(past.isoformat())
    assert "3d ago" in result


def test_format_relative_time_none():
    """Test formatting relative time with None."""
    result = format_relative_time(None)
    assert result == ""


def test_get_project_icon_work():
    """Test getting icon for work project."""
    assert get_project_icon("Work Project") == "💼"


def test_get_project_icon_personal():
    """Test getting icon for personal project."""
    assert get_project_icon("Personal Tasks") == "🏠"


def test_get_project_icon_tech():
    """Test getting icon for tech project."""
    assert get_project_icon("Tech Development") == "🔧"


def test_get_project_icon_default():
    """Test getting default icon."""
    assert get_project_icon("Random Project") == "📁"


def test_get_progress_bar_empty():
    """Test progress bar for 0%."""
    result = get_progress_bar(0)
    assert result == "░" * 10


def test_get_progress_bar_half():
    """Test progress bar for 50%."""
    result = get_progress_bar(50)
    assert result == "▓" * 5 + "░" * 5


def test_get_progress_bar_full():
    """Test progress bar for 100%."""
    result = get_progress_bar(100)
    assert result == "▓" * 10


def test_get_completion_color_high():
    """Test completion color for high percentage."""
    assert get_completion_color(90) == "green"


def test_get_completion_color_medium():
    """Test completion color for medium percentage."""
    assert get_completion_color(50) == "yellow"


def test_get_completion_color_low():
    """Test completion color for low percentage."""
    assert get_completion_color(20) == "red"
