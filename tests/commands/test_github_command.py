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


from todopro_cli.commands.github_command import _get_priority_from_labels
import httpx


class TestGetPriorityFromLabels:
    def test_bug_label_returns_4(self):
        assert _get_priority_from_labels([{"name": "bug"}]) == 4

    def test_enhancement_label_returns_2(self):
        assert _get_priority_from_labels([{"name": "enhancement"}]) == 2

    def test_feature_label_returns_2(self):
        assert _get_priority_from_labels([{"name": "feature"}]) == 2

    def test_docs_label_returns_1(self):
        assert _get_priority_from_labels([{"name": "docs"}]) == 1

    def test_documentation_label_returns_1(self):
        assert _get_priority_from_labels([{"name": "documentation"}]) == 1

    def test_no_known_labels_returns_1(self):
        assert _get_priority_from_labels([{"name": "triage"}]) == 1

    def test_empty_labels(self):
        assert _get_priority_from_labels([]) == 1


class TestFetchIssuesErrorHandling:
    """Tests for _fetch_issues function error responses."""

    def test_connect_error_import(self):
        """ConnectError during import → exit 1 with message."""
        with patch(
            "todopro_cli.commands.github_command.httpx.AsyncClient",
        ) as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("conn refused"))
            mock_cls.return_value = mock_instance
            result = runner.invoke(app, ["import", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 1
        assert "connect" in result.output.lower() or "error" in result.output.lower()

    def test_connect_error_list_issues(self):
        """ConnectError during list-issues → exit 1 with message."""
        with patch(
            "todopro_cli.commands.github_command.httpx.AsyncClient",
        ) as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("conn refused"))
            mock_cls.return_value = mock_instance
            result = runner.invoke(app, ["list-issues", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 1


class TestImportDoImport:
    """Lines 148-168: _do_import function."""

    def test_import_filters_pull_requests(self):
        """PRs (with pull_request key) are filtered out."""
        issues_with_pr = [
            {"number": 1, "title": "Real issue", "body": "", "labels": [], "state": "open", "pull_request": None},
            {"number": 2, "title": "PR", "body": "", "labels": [], "state": "open", "pull_request": {"url": "..."}},
        ]
        mock_http_client = _make_mock_client(200, issues_with_pr)
        mock_tasks_api = MagicMock()
        mock_tasks_api.create_task = AsyncMock(return_value={"id": "t1"})
        mock_api_client = MagicMock()
        mock_api_client.close = AsyncMock()

        with patch("todopro_cli.commands.github_command.httpx.AsyncClient", return_value=mock_http_client):
            with patch("todopro_cli.commands.github_command.get_client", return_value=mock_api_client):
                with patch("todopro_cli.commands.github_command.TasksAPI", return_value=mock_tasks_api):
                    result = runner.invoke(app, ["import", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 0
        # Only 1 real issue imported (PR filtered)
        assert mock_tasks_api.create_task.call_count == 1

    def test_import_exception_in_do_import(self):
        """Exception in _do_import → exit 1 with error message."""
        mock_http_client = _make_mock_client(200, SAMPLE_ISSUES)
        mock_api_client = MagicMock()
        mock_api_client.close = AsyncMock()

        with patch("todopro_cli.commands.github_command.httpx.AsyncClient", return_value=mock_http_client):
            with patch("todopro_cli.commands.github_command.get_client", return_value=mock_api_client):
                with patch("todopro_cli.commands.github_command.TasksAPI", side_effect=Exception("api down")):
                    result = runner.invoke(app, ["import", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 1

    def test_list_issues_no_token(self):
        """Missing token on list-issues → exit 1."""
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            result = runner.invoke(app, ["list-issues", "--repo", "owner/repo"])
        assert result.exit_code == 1

    def test_list_issues_no_issues(self):
        """Empty list from API → 'No ... issues' message."""
        mock_http_client = _make_mock_client(200, [])
        with patch("todopro_cli.commands.github_command.httpx.AsyncClient", return_value=mock_http_client):
            result = runner.invoke(app, ["list-issues", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 0
        assert "No" in result.output

    def test_list_issues_generic_exception(self):
        """Generic exception in list-issues → exit 1."""
        with patch(
            "todopro_cli.commands.github_command.httpx.AsyncClient",
        ) as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=Exception("unexpected"))
            mock_cls.return_value = mock_instance
            result = runner.invoke(app, ["list-issues", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 1


class TestImportGenericException:
    """Lines 85-87: generic exception in import_issues fetch."""

    def test_import_generic_exception_exits_1(self):
        """Generic exception (non-ConnectError) exits 1 with error message."""
        with patch("todopro_cli.commands.github_command.httpx.AsyncClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=RuntimeError("unexpected error"))
            mock_cls.return_value = mock_instance
            result = runner.invoke(app, ["import", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "Error" in result.output


class TestListIssuesTyperExit:
    """Line 156: typer.Exit re-raised in list-issues."""

    def test_list_issues_401_reraises_exit(self):
        """401 response in list-issues → _fetch_issues raises typer.Exit → re-raised."""
        mock_client = _make_mock_client(401, {"message": "Bad credentials"})
        with patch("todopro_cli.commands.github_command.httpx.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["list-issues", "--repo", "o/r", "--token", "bad-token"])
        assert result.exit_code == 1
        assert "token" in result.output.lower() or "Invalid" in result.output

    def test_list_issues_404_reraises_exit(self):
        """404 response in list-issues → _fetch_issues raises typer.Exit → re-raised."""
        mock_client = _make_mock_client(404, {"message": "Not Found"})
        with patch("todopro_cli.commands.github_command.httpx.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["list-issues", "--repo", "o/missing", "--token", "tok"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_list_issues_generic_exception_exits_1(self):
        """Generic exception in list-issues fetch → exit 1."""
        with patch("todopro_cli.commands.github_command.httpx.AsyncClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=RuntimeError("connection lost"))
            mock_cls.return_value = mock_instance
            result = runner.invoke(app, ["list-issues", "--repo", "o/r", "--token", "tok"])
        assert result.exit_code == 1
