"""Unit tests for import commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.import_command import app
from todopro_cli.services.todoist.models import TodoistImportResult

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_import_service(result: TodoistImportResult | None = None, error=None):
    """Context manager that replaces TodoistImportService.import_all."""
    mock_service = MagicMock()
    mock_service.import_all = AsyncMock(
        return_value=result or TodoistImportResult(projects_created=1, tasks_created=5),
        side_effect=error,
    )
    mock_service_cls = MagicMock(return_value=mock_service)
    return (
        patch("todopro_cli.commands.import_command.TodoistImportService", mock_service_cls),
        patch("todopro_cli.commands.import_command.TodoistClient", MagicMock()),
        patch(
            "todopro_cli.commands.import_command.get_storage_strategy_context",
            return_value=MagicMock(),
            create=True,
        ),
        mock_service,
    )


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------


class TestImportHelp:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_data_subcommand_help(self):
        result = runner.invoke(app, ["data", "--help"])
        assert result.exit_code == 0

    def test_todoist_subcommand_help(self):
        result = runner.invoke(app, ["todoist", "--help"])
        assert result.exit_code == 0
        assert "--api-key" in result.output

    def test_todoist_help_mentions_env_var(self):
        result = runner.invoke(app, ["todoist", "--help"])
        assert "TODOIST_API_KEY" in result.output


# ---------------------------------------------------------------------------
# todoist subcommand — authentication
# ---------------------------------------------------------------------------


class TestImportTodoistAuth:
    def test_exits_nonzero_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["todoist"])
        assert result.exit_code != 0

    def test_accepts_api_key_via_option(self):
        ctx1, ctx2, ctx3, mock_svc = _patch_import_service()
        with ctx1, ctx2, ctx3:
            result = runner.invoke(app, ["todoist", "--api-key", "secret"])
        assert result.exit_code == 0

    def test_reads_api_key_from_env_var(self):
        ctx1, ctx2, ctx3, mock_svc = _patch_import_service()
        with ctx1, ctx2, ctx3:
            with patch.dict("os.environ", {"TODOIST_API_KEY": "env-secret"}):
                result = runner.invoke(app, ["todoist"])
        assert result.exit_code == 0

    def test_invalid_api_key_exits_nonzero(self):
        with patch("todopro_cli.commands.import_command.TodoistClient", MagicMock()):
            with patch(
                "todopro_cli.commands.import_command.TodoistImportService",
                MagicMock(return_value=MagicMock(
                    import_all=AsyncMock(side_effect=ValueError("Invalid Todoist API key"))
                )),
            ):
                with patch(
                    "todopro_cli.commands.import_command.get_storage_strategy_context",
                    return_value=MagicMock(),
                    create=True,
                ):
                    result = runner.invoke(app, ["todoist", "--api-key", "bad"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# todoist subcommand — options
# ---------------------------------------------------------------------------


class TestImportTodoistOptions:
    def _invoke(self, args, result=None):
        ctx1, ctx2, ctx3, mock_svc = _patch_import_service(result=result)
        with ctx1, ctx2, ctx3:
            return runner.invoke(app, ["todoist", "--api-key", "key"] + args), mock_svc

    def test_dry_run_shown_in_output(self):
        inv_result, _ = self._invoke(["--dry-run"])
        assert "dry" in inv_result.output.lower() or inv_result.exit_code == 0

    def test_passes_project_prefix_to_options(self):
        _, mock_svc = self._invoke(["--project-prefix", "[T]"])
        options = mock_svc.import_all.call_args[0][0]
        assert options.project_name_prefix == "[T]"

    def test_passes_max_tasks_to_options(self):
        _, mock_svc = self._invoke(["--max-tasks", "100"])
        options = mock_svc.import_all.call_args[0][0]
        assert options.max_tasks_per_project == 100

    def test_passes_dry_run_flag_to_options(self):
        _, mock_svc = self._invoke(["--dry-run"])
        options = mock_svc.import_all.call_args[0][0]
        assert options.dry_run is True


# ---------------------------------------------------------------------------
# todoist subcommand — output
# ---------------------------------------------------------------------------


class TestImportTodoistOutput:
    def test_shows_success_message_on_clean_import(self):
        ctx1, ctx2, ctx3, _ = _patch_import_service(
            TodoistImportResult(projects_created=2, labels_created=5, tasks_created=10)
        )
        with ctx1, ctx2, ctx3:
            result = runner.invoke(app, ["todoist", "--api-key", "key"])
        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "✓" in result.output

    def test_exits_nonzero_on_import_errors(self):
        import_result = TodoistImportResult(errors=["Project 'X': DB error"])
        ctx1, ctx2, ctx3, _ = _patch_import_service(import_result)
        with ctx1, ctx2, ctx3:
            result = runner.invoke(app, ["todoist", "--api-key", "key"])
        assert result.exit_code != 0

    def test_shows_results_table(self):
        import_result = TodoistImportResult(
            projects_created=3, labels_created=10, tasks_created=50
        )
        ctx1, ctx2, ctx3, _ = _patch_import_service(import_result)
        with ctx1, ctx2, ctx3:
            result = runner.invoke(app, ["todoist", "--api-key", "key"])
        # Table should contain the numbers
        assert "3" in result.output
        assert "10" in result.output
        assert "50" in result.output


# ---------------------------------------------------------------------------
# Legacy: data subcommand
# ---------------------------------------------------------------------------


class TestImportDataCommand:
    def _invoke_import_data(self, args, service_side_effect=None):
        mock_data_service = MagicMock()
        mock_data_service.import_data = AsyncMock(side_effect=service_side_effect)
        fake_module = MagicMock()
        fake_module.DataService = MagicMock(return_value=mock_data_service)

        with patch.dict("sys.modules", {"todopro_cli.services.data_service": fake_module}):
            with patch(
                "todopro_cli.commands.import_command.get_storage_strategy_context",
                return_value=MagicMock(),
                create=True,
            ):
                return runner.invoke(app, ["data"] + args), mock_data_service

    def test_import_data_success(self):
        result, mock_service = self._invoke_import_data(["input.json"])
        assert result.exit_code == 0
        mock_service.import_data.assert_awaited_once_with("input.json", merge=False)

    def test_import_data_with_merge(self):
        result, mock_service = self._invoke_import_data(["input.json", "--merge"])
        assert result.exit_code == 0
        mock_service.import_data.assert_awaited_once_with("input.json", merge=True)

    def test_import_data_missing_file_arg_exits_nonzero(self):
        result = runner.invoke(app, ["data"])
        assert result.exit_code != 0

    def test_import_data_service_error_exits_nonzero(self):
        result, _ = self._invoke_import_data(
            ["input.json"], service_side_effect=Exception("parse error")
        )
        assert result.exit_code != 0

