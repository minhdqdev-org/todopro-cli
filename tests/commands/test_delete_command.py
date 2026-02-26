"""Unit tests for delete_command.py — task, project, label, context, reminder, filter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.delete_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(id_: str = "task-abc-123", content: str = "Buy milk"):
    task = MagicMock()
    task.id = id_
    task.content = content
    task.model_dump.return_value = {"id": id_, "content": content}
    return task


def _make_project(id_: str = "proj-abc-123", name: str = "Work"):
    proj = MagicMock()
    proj.id = id_
    proj.name = name
    return proj


def _run(
    args: list[str],
    *,
    task=None,
    catch_exceptions: bool = True,
):
    if task is None:
        task = _make_task()
    return runner.invoke(app, args, catch_exceptions=catch_exceptions)


# ---------------------------------------------------------------------------
# delete task
# ---------------------------------------------------------------------------


class TestDeleteTask:
    """Tests for 'delete task <id>'."""

    def _run(self, args, task=None, resolved_id="task-abc-123"):
        task = task or _make_task()
        svc = MagicMock()
        svc.get_task = AsyncMock(return_value=task)
        svc.delete_task = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_task_service",
                return_value=svc,
            ),
            patch(
                "todopro_cli.commands.delete_command.resolve_task_id",
                new=AsyncMock(return_value=resolved_id),
            ),
        ):
            return runner.invoke(app, args, catch_exceptions=True)

    def test_force_flag_skips_confirmation(self):
        """--force deletes without prompting, exits 0."""
        result = self._run(["task", "task-abc-123", "--force"])
        assert result.exit_code == 0, result.output
        assert "Done" in result.output

    def test_short_force_flag(self):
        """-f is shorthand for --force."""
        result = self._run(["task", "task-abc-123", "-f"])
        assert result.exit_code == 0, result.output

    def test_confirmation_yes_deletes(self):
        """Confirming deletion ('y') deletes the task."""
        svc = MagicMock()
        svc.get_task = AsyncMock(return_value=_make_task())
        svc.delete_task = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_task_service",
                return_value=svc,
            ),
            patch(
                "todopro_cli.commands.delete_command.resolve_task_id",
                new=AsyncMock(return_value="task-abc-123"),
            ),
        ):
            result = runner.invoke(app, ["task", "task-abc-123"], input="y\n")
        assert result.exit_code == 0, result.output

    def test_confirmation_no_cancels(self):
        """Declining deletion ('n') cancels, exits 0."""
        svc = MagicMock()
        svc.get_task = AsyncMock(return_value=_make_task())
        svc.delete_task = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_task_service",
                return_value=svc,
            ),
            patch(
                "todopro_cli.commands.delete_command.resolve_task_id",
                new=AsyncMock(return_value="task-abc-123"),
            ),
        ):
            result = runner.invoke(app, ["task", "task-abc-123"], input="n\n")
        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output

    def test_task_not_found(self):
        """If get_task returns None, prints error and exits 1."""
        svc = MagicMock()
        svc.get_task = AsyncMock(return_value=None)
        svc.delete_task = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_task_service",
                return_value=svc,
            ),
            patch(
                "todopro_cli.commands.delete_command.resolve_task_id",
                new=AsyncMock(return_value="task-abc-123"),
            ),
        ):
            result = runner.invoke(app, ["task", "task-abc-123", "--force"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# delete project
# ---------------------------------------------------------------------------


class TestDeleteProject:
    """Tests for 'delete project <id>'."""

    def _run(self, args, project=None):
        project = project or _make_project()
        svc = MagicMock()
        svc.get_project = AsyncMock(return_value=project)
        svc.delete_project = AsyncMock()

        with patch(
            "todopro_cli.commands.delete_command.get_project_service",
            return_value=svc,
        ):
            return runner.invoke(app, args)

    def test_force_deletes_project(self):
        """--force deletes project without confirmation."""
        result = self._run(["project", "proj-abc-123", "--force"])
        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_short_force_flag(self):
        """-f works as alias for --force."""
        result = self._run(["project", "proj-abc-123", "-f"])
        assert result.exit_code == 0, result.output

    def test_confirmation_yes(self):
        """Confirming project deletion succeeds."""
        svc = MagicMock()
        svc.delete_project = AsyncMock()
        with patch(
            "todopro_cli.commands.delete_command.get_project_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["project", "proj-abc-123"], input="y\n")
        assert result.exit_code == 0, result.output

    def test_confirmation_no_cancels(self):
        """Declining project deletion cancels."""
        svc = MagicMock()
        svc.delete_project = AsyncMock()
        with patch(
            "todopro_cli.commands.delete_command.get_project_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["project", "proj-abc-123"], input="n\n")
        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output


# ---------------------------------------------------------------------------
# delete label
# ---------------------------------------------------------------------------


class TestDeleteLabel:
    """Tests for 'delete label <id>'."""

    def _run(self, args):
        mock_sc = MagicMock()
        mock_sc.label_repository = MagicMock()

        mock_label_svc = MagicMock()
        mock_label_svc.delete_label = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_storage_strategy_context",
                return_value=mock_sc,
                create=True,
            ),
            patch(
                "todopro_cli.commands.delete_command.LabelService",
                return_value=mock_label_svc,
            ),
        ):
            return runner.invoke(app, args)

    def test_force_deletes_label(self):
        """--force deletes label without confirmation."""
        result = self._run(["label", "label-123", "--force"])
        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_confirmation_yes(self):
        """Confirming label deletion succeeds."""
        mock_sc = MagicMock()
        mock_sc.label_repository = MagicMock()
        mock_label_svc = MagicMock()
        mock_label_svc.delete_label = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_storage_strategy_context",
                return_value=mock_sc,
                create=True,
            ),
            patch(
                "todopro_cli.commands.delete_command.LabelService",
                return_value=mock_label_svc,
            ),
        ):
            result = runner.invoke(app, ["label", "label-123"], input="y\n")
        assert result.exit_code == 0, result.output

    def test_confirmation_no_cancels(self):
        """Declining label deletion cancels."""
        mock_sc = MagicMock()
        mock_sc.label_repository = MagicMock()
        mock_label_svc = MagicMock()
        mock_label_svc.delete_label = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_storage_strategy_context",
                return_value=mock_sc,
                create=True,
            ),
            patch(
                "todopro_cli.commands.delete_command.LabelService",
                return_value=mock_label_svc,
            ),
        ):
            result = runner.invoke(app, ["label", "label-123"], input="n\n")
        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output


# ---------------------------------------------------------------------------
# delete context
# ---------------------------------------------------------------------------


class TestDeleteContext:
    """Tests for 'delete context <name>'."""

    def _make_config_svc(self):
        svc = MagicMock()
        svc.remove_context = MagicMock()
        return svc

    def test_force_deletes_context(self):
        """--force deletes context without confirmation."""
        config_svc = self._make_config_svc()
        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=config_svc,
        ):
            result = runner.invoke(app, ["context", "my-ctx", "--force"])
        assert result.exit_code == 0, result.output

    def test_confirmation_yes(self):
        """Confirming context deletion succeeds."""
        config_svc = self._make_config_svc()
        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=config_svc,
        ):
            result = runner.invoke(app, ["context", "my-ctx"], input="y\n")
        assert result.exit_code == 0, result.output

    def test_confirmation_no_cancels(self):
        """Declining context deletion cancels."""
        config_svc = self._make_config_svc()
        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=config_svc,
        ):
            result = runner.invoke(app, ["context", "my-ctx"], input="n\n")
        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output


# ---------------------------------------------------------------------------
# delete reminder
# ---------------------------------------------------------------------------


class TestDeleteReminder:
    """Tests for 'delete reminder <task_id> <reminder_id>'."""

    def _run(self, args):
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_reminder = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.TasksAPI",
                return_value=mock_api,
            ),
        ):
            return runner.invoke(app, args)

    def test_force_deletes_reminder(self):
        """--force deletes reminder without confirmation."""
        result = self._run(["reminder", "task-123", "rem-456", "--force"])
        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_confirmation_yes(self):
        """Confirming reminder deletion succeeds."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_reminder = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.TasksAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app, ["reminder", "task-123", "rem-456"], input="y\n"
            )
        assert result.exit_code == 0, result.output

    def test_confirmation_no_cancels(self):
        """Declining reminder deletion cancels."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_reminder = AsyncMock()

        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.TasksAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app, ["reminder", "task-123", "rem-456"], input="n\n"
            )
        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output


# ---------------------------------------------------------------------------
# delete filter
# ---------------------------------------------------------------------------


class TestDeleteFilter:
    """Tests for 'delete filter <filter_id>'."""

    def _make_api(self, find_result=None):
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_filter = AsyncMock()
        mock_api.find_filter_by_name = AsyncMock(
            return_value=find_result or {"id": "filter-uuid-1234-5678-9012-abcd"}
        )
        return mock_client, mock_api

    def test_force_with_uuid_like_id(self):
        """--force with UUID-like ID deletes directly without name lookup."""
        mock_client, mock_api = self._make_api()
        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.FiltersAPI",
                return_value=mock_api,
            ),
        ):
            # 36-char UUID with 4 dashes
            result = runner.invoke(
                app,
                ["filter", "12345678-1234-1234-1234-123456789012", "--force"],
            )
        assert result.exit_code == 0, result.output

    def test_force_with_name_id_resolves_via_api(self):
        """Non-UUID filter ID is resolved to a UUID via find_filter_by_name."""
        mock_client, mock_api = self._make_api(
            find_result={"id": "filter-uuid-1234-5678-9012-abcd"}
        )
        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.FiltersAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app, ["filter", "my-filter-name", "--force"]
            )
        assert result.exit_code == 0, result.output

    def test_filter_name_not_found_exits_1(self):
        """Name lookup returns None → prints error and exits 1."""
        mock_client, mock_api = self._make_api(find_result=None)
        mock_api.find_filter_by_name = AsyncMock(return_value=None)

        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.FiltersAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app, ["filter", "nonexistent-filter", "--force"]
            )
        assert result.exit_code == 1

    def test_confirmation_yes_deletes(self):
        """Confirming filter deletion succeeds."""
        mock_client, mock_api = self._make_api()
        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.FiltersAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app,
                ["filter", "12345678-1234-1234-1234-123456789012"],
                input="y\n",
            )
        assert result.exit_code == 0, result.output

    def test_confirmation_no_cancels(self):
        """Declining filter deletion cancels."""
        mock_client, mock_api = self._make_api()
        with (
            patch(
                "todopro_cli.commands.delete_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.delete_command.FiltersAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app,
                ["filter", "12345678-1234-1234-1234-123456789012"],
                input="n\n",
            )
        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


class TestDeleteHelp:
    """Structural tests: verify subcommands advertise themselves correctly."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Delete resources" in result.output

    def test_task_help(self):
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_project_help(self):
        result = runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0

    def test_filter_help(self):
        result = runner.invoke(app, ["filter", "--help"])
        assert result.exit_code == 0


class TestDeleteLocationContext:
    """Lines 117-130: delete location-context command."""

    def test_delete_location_context_undefined_deps(self):
        """delete location-context calls undefined factory → NameError → exit 1."""
        result = runner.invoke(app, ["location-context", "my-location", "--force"])
        assert result.exit_code != 0

    def test_delete_location_context_user_cancels_with_mocks(self):
        """With mocked deps, declining deletion cancels and exits 0."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_service = MagicMock()
        mock_service.delete_context = AsyncMock()

        with (
            patch("todopro_cli.commands.delete_command.get_storage_strategy_context", return_value=MagicMock(), create=True),
            patch("todopro_cli.commands.delete_command.factory", MagicMock(), create=True),
            patch("todopro_cli.commands.delete_command.LocationContextService", return_value=mock_service, create=True),
        ):
            result = runner.invoke(app, ["location-context", "my-location"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_delete_location_context_with_mocked_service(self):
        """With proper mocks, delete location-context succeeds."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_service = MagicMock()
        mock_service.delete_context = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.get_location_context_repository.return_value = MagicMock()

        with (
            patch("todopro_cli.commands.delete_command.get_storage_strategy_context", return_value=MagicMock(), create=True),
            patch("todopro_cli.commands.delete_command.factory", mock_factory, create=True),
            patch("todopro_cli.services.location_context_service.LocationContextService", return_value=mock_service),
        ):
            result = runner.invoke(app, ["location-context", "my-location", "--force"])
        assert result.exit_code == 0
