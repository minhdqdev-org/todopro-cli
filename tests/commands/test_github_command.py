"""Unit tests for github_command."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.github_command import app

runner = CliRunner()

SAMPLE_ISSUES = [
    {
        "number": 1,
        "title": "Bug in login",
        "body": "Login fails with wrong password",
        "labels": [{"name": "bug"}],
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/1",
    },
    {
        "number": 2,
        "title": "Add dark mode",
        "body": "Feature request for dark mode",
        "labels": [{"name": "enhancement"}],
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/2",
    },
]


def _make_mock_client(status_code: int, json_data):
    """Helper to build an async httpx mock client."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    if status_code < 400:
        mock_response.raise_for_status = MagicMock()
    else:
        from httpx import HTTPStatusError, Request, Response

        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "error", request=MagicMock(), response=mock_response
            )
        )

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    return mock_client_instance


def test_import_help():
    """Test that --help works for the import command."""
    result = runner.invoke(app, ["import", "--help"])
    assert result.exit_code == 0


def test_import_missing_token():
    """Test that missing token produces an error."""
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    with patch.dict(os.environ, env, clear=True):
        result = runner.invoke(app, ["import", "--repo", "owner/repo"])
    assert result.exit_code == 1
    assert "token" in result.output.lower()


def test_import_success():
    """Test successful import of GitHub issues."""
    mock_client = _make_mock_client(200, SAMPLE_ISSUES)
    mock_tasks_api = MagicMock()
    mock_tasks_api.create_task = AsyncMock(return_value={"id": "task-1"})
    mock_api_client = MagicMock()
    mock_api_client.close = AsyncMock()

    with patch(
        "todopro_cli.commands.github_command.httpx.AsyncClient",
        return_value=mock_client,
    ):
        with patch(
            "todopro_cli.commands.github_command.get_client",
            return_value=mock_api_client,
        ):
            with patch(
                "todopro_cli.commands.github_command.TasksAPI",
                return_value=mock_tasks_api,
            ):
                result = runner.invoke(
                    app,
                    ["import", "--repo", "owner/repo", "--token", "test-token"],
                )

    assert result.exit_code == 0
    assert "Imported" in result.output


def test_import_dry_run():
    """Test dry run does not create tasks."""
    mock_client = _make_mock_client(200, SAMPLE_ISSUES)
    mock_tasks_api = MagicMock()
    mock_tasks_api.create_task = AsyncMock(return_value={"id": "task-1"})
    mock_api_client = MagicMock()
    mock_api_client.close = AsyncMock()

    with patch(
        "todopro_cli.commands.github_command.httpx.AsyncClient",
        return_value=mock_client,
    ):
        with patch(
            "todopro_cli.commands.github_command.get_client",
            return_value=mock_api_client,
        ):
            with patch(
                "todopro_cli.commands.github_command.TasksAPI",
                return_value=mock_tasks_api,
            ):
                result = runner.invoke(
                    app,
                    [
                        "import",
                        "--repo",
                        "owner/repo",
                        "--token",
                        "test-token",
                        "--dry-run",
                    ],
                )

    assert result.exit_code == 0
    # dry run output should mention the issues or "dry"
    assert "dry" in result.output.lower() or "Bug in login" in result.output
    mock_tasks_api.create_task.assert_not_called()


def test_import_repo_not_found():
    """Test 404 response gives 'not found' error."""
    mock_client = _make_mock_client(404, {"message": "Not Found"})

    with patch(
        "todopro_cli.commands.github_command.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["import", "--repo", "owner/missing", "--token", "test-token"],
        )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_import_auth_error():
    """Test 401 response gives token error."""
    mock_client = _make_mock_client(401, {"message": "Bad credentials"})

    with patch(
        "todopro_cli.commands.github_command.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["import", "--repo", "owner/repo", "--token", "bad-token"],
        )

    assert result.exit_code == 1
    assert "token" in result.output.lower()


def test_import_no_issues():
    """Test empty issue list prints 'No ... issues' message."""
    mock_client = _make_mock_client(200, [])

    with patch(
        "todopro_cli.commands.github_command.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["import", "--repo", "owner/repo", "--token", "test-token"],
        )

    assert result.exit_code == 0
    assert "No" in result.output


def test_list_issues_success():
    """Test list-issues command displays a table."""
    mock_client = _make_mock_client(200, SAMPLE_ISSUES)

    with patch(
        "todopro_cli.commands.github_command.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["list-issues", "--repo", "owner/repo", "--token", "tok"],
        )

    assert result.exit_code == 0
