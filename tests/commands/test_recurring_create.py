"""Unit tests for MVP2.2 recurring task creation options in create_command."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.create_command import app
from todopro_cli.models import Task

runner = CliRunner()


@pytest.fixture
def mock_task():
    """Sample recurring task."""
    return Task(
        id="task-recurring-1",
        content="Daily standup",
        description=None,
        project_id=None,
        due_date=None,
        priority=1,
        is_completed=False,
        labels=[],
        contexts=[],
        is_recurring=True,
        recurrence_rule="FREQ=DAILY",
        recurrence_end=None,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def mock_strategy():
    """Mock task service via get_task_service."""
    service_mock = MagicMock()
    with patch(
        "todopro_cli.commands.create_command.get_task_service",
        return_value=service_mock,
    ) as mock:
        yield mock, service_mock


class TestCreateTaskRecurrence:
    """Tests for --recur and --recur-end options on 'create task'."""

    def test_create_task_recur_help(self):
        """create task --help should mention --recur and --recur-end."""
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "--recur" in result.stdout
        assert "--recur-end" in result.stdout

    def test_create_task_daily_recur(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(app, ["task", "Daily standup", "--recur", "daily"])
        assert result.exit_code == 0
        service_mock.add_task.assert_awaited_once()
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("is_recurring") is True
        assert call_kwargs.get("recurrence_rule") == "FREQ=DAILY"

    def test_create_task_weekly_recur(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(app, ["task", "Weekly review", "--recur", "weekly"])
        assert result.exit_code == 0
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("recurrence_rule") == "FREQ=WEEKLY"

    def test_create_task_weekdays_recur(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(app, ["task", "Standup", "--recur", "weekdays"])
        assert result.exit_code == 0
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("recurrence_rule") == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"

    def test_create_task_biweekly_recur(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(
            app, ["task", "Biweekly sync", "--recur", "bi-weekly"]
        )
        assert result.exit_code == 0
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("recurrence_rule") == "FREQ=WEEKLY;INTERVAL=2"

    def test_create_task_monthly_recur(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(
            app, ["task", "Monthly report", "--recur", "monthly"]
        )
        assert result.exit_code == 0
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("recurrence_rule") == "FREQ=MONTHLY"

    def test_create_task_invalid_recur_exits(self, mock_strategy):
        """Invalid --recur value should exit with non-zero and error message."""
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock()
        result = runner.invoke(app, ["task", "Test", "--recur", "hourly"])
        assert result.exit_code != 0
        assert "hourly" in result.stdout

    def test_create_task_recur_with_end_date(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(
            app,
            [
                "task",
                "Daily standup",
                "--recur",
                "daily",
                "--recur-end",
                "2025-12-31",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("recurrence_end") == "2025-12-31"

    def test_create_task_no_recur_defaults_to_false(self, mock_strategy, mock_task):
        mock_strat_ctx, service_mock = mock_strategy
        service_mock.add_task = AsyncMock(return_value=mock_task)
        result = runner.invoke(app, ["task", "Regular task"])
        assert result.exit_code == 0
        call_kwargs = service_mock.add_task.call_args.kwargs
        assert call_kwargs.get("is_recurring") is False
        assert call_kwargs.get("recurrence_rule") is None


class TestCreateFilter:
    """Tests for 'create filter' command."""

    def test_create_filter_help(self):
        """create filter --help should document options."""
        result = runner.invoke(app, ["filter", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.stdout or "NAME" in result.stdout
        assert "--color" in result.stdout
        assert "--priority" in result.stdout
        assert "--due-within" in result.stdout

    def test_create_filter_basic(self):
        """create filter should call FiltersAPI.create_filter."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        filter_resp = {
            "id": "f-1",
            "name": "urgent",
            "color": "#FF0000",
            "criteria": {},
        }
        mock_api = MagicMock()
        mock_api.create_filter = AsyncMock(return_value=filter_resp)
        with patch(
            "todopro_cli.commands.create_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.create_command.FiltersAPI", return_value=mock_api
            ):
                result = runner.invoke(app, ["filter", "urgent"])
        assert result.exit_code == 0
        mock_api.create_filter.assert_awaited_once()
        assert "urgent" in result.stdout

    def test_create_filter_with_priority(self):
        """create filter --priority should parse as list of ints."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        filter_resp = {
            "id": "f-2",
            "name": "high-prio",
            "color": "#0066CC",
            "criteria": {"priority": [3, 4]},
        }
        mock_api = MagicMock()
        mock_api.create_filter = AsyncMock(return_value=filter_resp)
        with patch(
            "todopro_cli.commands.create_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.create_command.FiltersAPI", return_value=mock_api
            ):
                result = runner.invoke(
                    app, ["filter", "high-prio", "--priority", "3,4"]
                )
        assert result.exit_code == 0
        call_kwargs = mock_api.create_filter.call_args.kwargs
        assert call_kwargs.get("priority") == [3, 4]

    def test_create_filter_invalid_priority_exits(self):
        """Non-integer priority should fail gracefully."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.create_filter = AsyncMock()
        with patch(
            "todopro_cli.commands.create_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.create_command.FiltersAPI", return_value=mock_api
            ):
                result = runner.invoke(app, ["filter", "test", "--priority", "high"])
        assert result.exit_code != 0

    def test_create_filter_with_due_within(self):
        """create filter --due-within should pass due_within_days."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        filter_resp = {
            "id": "f-3",
            "name": "soon",
            "color": "#0066CC",
            "criteria": {"due_within_days": 7},
        }
        mock_api = MagicMock()
        mock_api.create_filter = AsyncMock(return_value=filter_resp)
        with patch(
            "todopro_cli.commands.create_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.create_command.FiltersAPI", return_value=mock_api
            ):
                result = runner.invoke(app, ["filter", "soon", "--due-within", "7"])
        assert result.exit_code == 0
        call_kwargs = mock_api.create_filter.call_args.kwargs
        assert call_kwargs.get("due_within_days") == 7
