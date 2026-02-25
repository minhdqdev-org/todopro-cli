"""Unit tests for ramble_command."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from todopro_cli.commands.ramble_command import app

runner = CliRunner()


def _mock_api_get(return_value):
    return patch("todopro_cli.commands.ramble_command._api_get", new=AsyncMock(return_value=return_value))


def _mock_api_post(return_value):
    return patch("todopro_cli.commands.ramble_command._api_post", new=AsyncMock(return_value=return_value))


def _mock_api_put(return_value):
    return patch("todopro_cli.commands.ramble_command._api_put", new=AsyncMock(return_value=return_value))


# Help tests
def test_ramble_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_history_help():
    result = runner.invoke(app, ["history", "--help"])
    assert result.exit_code == 0


def test_config_help():
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0


def test_usage_help():
    result = runner.invoke(app, ["usage", "--help"])
    assert result.exit_code == 0


# ramble --text (skips mic recording)
def test_ramble_text_success():
    with _mock_api_post({
        "tasks_created": 2,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [
            {"success": True, "title": "Buy milk"},
            {"success": True, "title": "Call doctor"},
        ],
        "transcript": "Buy milk and call doctor",
        "errors": [],
    }):
        result = runner.invoke(app, ["--text", "Buy milk and call doctor"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_ramble_text_error():
    with _mock_api_post({"error": "LLM not configured"}):
        result = runner.invoke(app, ["--text", "some text"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_ramble_text_dry_run():
    with _mock_api_post({
        "tasks_created": 1,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [],
        "transcript": "Buy milk",
        "errors": [],
        "dry_run": True,
    }):
        result = runner.invoke(app, ["--text", "Buy milk", "--dry-run"])
    assert result.exit_code == 0
    assert "dry" in result.output.lower() or "1" in result.output


def test_ramble_no_audio_deps():
    """Without sounddevice, should print helpful message and exit."""
    with patch("todopro_cli.commands.ramble_command.check_dependencies", return_value=(False, "sounddevice not installed")):
        result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "sounddevice" in result.output or "Audio" in result.output


# history
def test_history_empty():
    with _mock_api_get({"sessions": []}):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "No Ramble sessions" in result.output


def test_history_with_sessions():
    sessions = [
        {
            "id": "abc12345-1234-1234-1234-123456789012",
            "started_at": "2027-01-01T10:00:00Z",
            "ended_at": "2027-01-01T10:01:00Z",
            "duration_seconds": 30.5,
            "stt_provider": "whisper",
            "llm_provider": "gemini",
            "tasks_created": 3,
            "tasks_updated": 0,
            "tasks_deleted": 0,
            "source": "cli",
        }
    ]
    with _mock_api_get({"sessions": sessions}):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "whisper" in result.output


def test_history_error():
    with _mock_api_get({"error": "Unauthorized"}):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 1


# config
def test_config_show():
    with _mock_api_get({
        "default_stt_provider": "whisper",
        "default_llm_provider": "gemini",
        "silence_timeout_seconds": 3,
        "default_language": "auto",
        "sessions_per_day_limit": 5,
        "max_session_duration": 30,
    }):
        result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "whisper" in result.output


def test_config_update_stt():
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--stt", "gemini"])
    assert result.exit_code == 0
    assert "saved" in result.output.lower() or "Configuration" in result.output


def test_config_update_silence_timeout():
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--silence-timeout", "5"])
    assert result.exit_code == 0


def test_config_error():
    with _mock_api_put({"error": "Server error"}):
        result = runner.invoke(app, ["config", "--stt", "gemini"])
    assert result.exit_code == 1


# usage
def test_usage_success():
    with _mock_api_get({
        "sessions_today": 2,
        "sessions_limit": 5,
        "sessions_remaining": 3,
        "max_session_duration": 30,
    }):
        result = runner.invoke(app, ["usage"])
    assert result.exit_code == 0
    assert "2" in result.output
    assert "5" in result.output


def test_usage_error():
    with _mock_api_get({"error": "Unauthorized"}):
        result = runner.invoke(app, ["usage"])
    assert result.exit_code == 1
