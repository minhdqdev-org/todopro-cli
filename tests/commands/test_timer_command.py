"""Tests for timer command.

This module tests the Pomodoro timer commands using CliRunner.
"""
# pylint: disable=redefined-outer-name

import re
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from todopro_cli.commands.timer import app


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

runner = CliRunner()


@pytest.fixture
def mock_api_client():
    """Mock APIClient for testing."""
    with patch("todopro_cli.commands.timer.APIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock async methods
        mock_client.post = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.close = AsyncMock()

        yield mock_client


class TestTimerHistory:
    """Tests for timer history command."""

    def test_history_no_sessions(self, mock_api_client):
        """Test history command with no sessions."""
        # Arrange
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {"sessions": []}
        mock_api_client.get.return_value = mock_response

        # Act
        result = runner.invoke(app, ["history"])

        # Assert
        assert result.exit_code == 0
        assert "No timer sessions found" in result.stdout
        mock_api_client.get.assert_called_once()
        mock_api_client.close.assert_called_once()

    def test_history_with_sessions(self, mock_api_client):
        """Test history command with sessions."""
        # Arrange
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "sessions": [
                {
                    "started_at": "2026-02-10T10:00:00Z",
                    "session_type": "work",
                    "task_content": "Write tests",
                    "actual_duration_minutes": 25,
                    "is_completed": True,
                    "is_interrupted": False,
                },
                {
                    "started_at": "2026-02-10T11:00:00Z",
                    "session_type": "short_break",
                    "task_content": None,
                    "actual_duration_minutes": 5,
                    "is_completed": True,
                    "is_interrupted": False,
                },
            ]
        }
        mock_api_client.get.return_value = mock_response

        # Act
        result = runner.invoke(app, ["history"], catch_exceptions=False)

        # Assert
        assert result.exit_code == 0
        assert "Recent Timer Sessions (2)" in result.stdout
        assert "Write tests" in result.stdout
        assert "Short Break" in result.stdout
        mock_api_client.get.assert_called_once()

    def test_history_with_task_filter(self, mock_api_client):
        """Test history command with task ID filter."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {"sessions": []}
        mock_api_client.get.return_value = mock_response

        result = runner.invoke(app, ["history", "--task-id", "task-123"])

        assert result.exit_code == 0
        # Verify task_id was passed in params
        call_args = mock_api_client.get.call_args
        assert call_args[1]["params"]["task_id"] == "task-123"

    def test_history_with_limit(self, mock_api_client):
        """Test history command with custom limit."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {"sessions": []}
        mock_api_client.get.return_value = mock_response

        result = runner.invoke(app, ["history", "--limit", "50"])

        assert result.exit_code == 0
        call_args = mock_api_client.get.call_args
        assert call_args[1]["params"]["limit"] == 50

    def test_history_api_error(self, mock_api_client):
        """Test history command handles API errors."""
        mock_api_client.get.side_effect = Exception("API error")

        result = runner.invoke(app, ["history"])

        # Should handle error and exit with code 1
        assert result.exit_code == 1
        assert "Error" in result.stdout


class TestTimerStats:
    """Tests for timer stats command."""

    def test_stats_success(self, mock_api_client):
        """Test stats command with successful response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "total_sessions": 10,
            "completed_sessions": 8,
            "interrupted_sessions": 2,
            "completion_rate": 80,
            "total_work_hours": 5.0,
            "total_work_minutes": 300,
        }
        mock_api_client.get.return_value = mock_response

        result = runner.invoke(app, ["stats"])

        assert result.exit_code == 0
        assert "Pomodoro Statistics" in result.stdout
        assert "Total Sessions: 10" in result.stdout
        assert "Completed: 8" in result.stdout
        assert "Completion Rate: 80%" in result.stdout
        assert "5.0 hours" in result.stdout

    def test_stats_with_task_filter(self, mock_api_client):
        """Test stats command with task ID filter."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "total_sessions": 5,
            "completed_sessions": 5,
            "interrupted_sessions": 0,
            "completion_rate": 100,
            "total_work_hours": 2.0,
            "total_work_minutes": 120,
        }
        mock_api_client.get.return_value = mock_response

        result = runner.invoke(app, ["stats", "--task-id", "task-123"])

        assert result.exit_code == 0
        call_args = mock_api_client.get.call_args
        assert call_args[1]["params"]["task_id"] == "task-123"

    def test_stats_with_custom_days(self, mock_api_client):
        """Test stats command with custom days."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.return_value = {
            "total_sessions": 20,
            "completed_sessions": 18,
            "interrupted_sessions": 2,
            "completion_rate": 90,
            "total_work_hours": 10.0,
            "total_work_minutes": 600,
        }
        mock_api_client.get.return_value = mock_response

        result = runner.invoke(app, ["stats", "--days", "30"])

        assert result.exit_code == 0
        assert "Last 30 days" in result.stdout
        call_args = mock_api_client.get.call_args
        assert call_args[1]["params"]["days"] == 30

    def test_stats_api_error(self, mock_api_client):
        """Test stats command handles API errors."""
        mock_api_client.get.side_effect = Exception("API error")

        result = runner.invoke(app, ["stats"])

        # Should handle error and exit with code 1
        assert result.exit_code == 1
        assert "Error" in result.stdout


class TestTimerStart:
    """Tests for timer start command."""

    @patch("todopro_cli.commands.timer.time")
    def test_start_basic(self, mock_time, mock_api_client):
        """Test basic timer start (mocked to finish immediately)."""
        # Mock the timer to finish immediately
        mock_time.time.side_effect = [0, 1501]  # Start and end after duration
        mock_time.sleep = MagicMock()  # Don't actually sleep

        # Mock start response
        start_response = MagicMock(spec=httpx.Response)
        start_response.json.return_value = {
            "id": "session-123",
            "session_type": "work",
            "duration": 25,
        }

        # Mock complete response
        complete_response = MagicMock(spec=httpx.Response)
        complete_response.json.return_value = {"success": True}

        mock_api_client.post.side_effect = [start_response, complete_response]

        result = runner.invoke(app, ["start", "--duration", "25"])

        assert result.exit_code == 0
        assert (
            "Starting Work Session" in result.stdout
            or "Session Complete" in result.stdout
        )
        assert mock_api_client.post.call_count >= 1

    def test_start_invalid_type(self, mock_api_client):
        """Test start command with invalid session type."""
        result = runner.invoke(app, ["start", "--type", "invalid"])

        assert result.exit_code == 1
        assert "Invalid type" in result.stdout
        # Should not call API
        mock_api_client.post.assert_not_called()

    def test_start_with_task_id(self, mock_api_client):
        """Test start command with task ID."""
        mock_time_module = MagicMock()
        mock_time_module.time.side_effect = [0, 1501]

        start_response = MagicMock(spec=httpx.Response)
        start_response.json.return_value = {
            "id": "session-123",
            "session_type": "work",
            "duration": 25,
            "task_content": "Write tests",
        }

        complete_response = MagicMock(spec=httpx.Response)
        complete_response.json.return_value = {"success": True}

        mock_api_client.post.side_effect = [start_response, complete_response]

        with patch("todopro_cli.commands.timer.time", mock_time_module):
            result = runner.invoke(
                app, ["start", "--task-id", "task-123", "--duration", "1"]
            )

        assert result.exit_code == 0
        # Verify task_id was passed in request
        call_args = mock_api_client.post.call_args_list[0]
        assert call_args[1]["json"]["task_id"] == "task-123"

    def test_start_api_error(self, mock_api_client):
        """Test start command handles API errors."""
        mock_api_client.post.side_effect = Exception("API error")

        result = runner.invoke(app, ["start"])

        # Should handle error and exit with code 1
        assert result.exit_code == 1
        assert "Error" in result.stdout


class TestTimerQuick:
    """Tests for quick timer command."""

    @patch("todopro_cli.commands.timer.time")
    def test_quick_timer_default_duration(self, mock_time):
        """Test quick timer with default 25 minutes."""
        # Mock time to finish immediately
        mock_time.time.side_effect = [0, 1501]
        mock_time.sleep = MagicMock()

        result = runner.invoke(app, ["quick"])

        # Should complete without API calls
        assert result.exit_code == 0 or "Timer running" in result.stdout

    @patch("todopro_cli.commands.timer.time")
    def test_quick_timer_custom_duration(self, mock_time):
        """Test quick timer with custom duration."""
        mock_time.time.side_effect = [0, 601]
        mock_time.sleep = MagicMock()

        result = runner.invoke(app, ["quick", "10"])

        assert result.exit_code == 0 or "Timer running" in result.stdout


class TestTimerIntegration:
    """Integration tests for timer commands."""

    def test_help_command(self):
        """Test timer help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Pomodoro timer for focus sessions" in result.stdout
        assert "start" in result.stdout
        assert "history" in result.stdout
        assert "stats" in result.stdout
        assert "quick" in result.stdout

    def test_start_help(self):
        """Test timer start help."""
        result = runner.invoke(app, ["start", "--help"])
        clean_output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Start a Pomodoro timer session" in clean_output
        assert "--task-id" in clean_output
        assert "--duration" in clean_output
        assert "--type" in clean_output

    def test_history_help(self):
        """Test timer history help."""
        result = runner.invoke(app, ["history", "--help"])
        clean_output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Show Pomodoro session history" in clean_output
        assert "--task-id" in clean_output
        assert "--limit" in clean_output

    def test_stats_help(self):
        """Test timer stats help."""
        result = runner.invoke(app, ["stats", "--help"])
        clean_output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "Show Pomodoro statistics" in clean_output
        assert "--days" in clean_output
