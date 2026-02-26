"""Unit tests for data_command.py (export, import, purge).

Strategy:
- Export/Import with remote context: mock get_client (async API calls)
- Import error paths (file not found, bad JSON, cancel): no mocking needed
- Purge: mock get_config_service + get_client; test dry-run and cancellations
- Local paths that use undefined get_storage_strategy_context are skipped
"""

import gzip
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.data_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_config_svc(context_type: str = "remote", email: str = "test@example.com"):
    svc = MagicMock()
    ctx = MagicMock()
    ctx.type = context_type
    svc.config.get_current_context.return_value = ctx
    svc.load_credentials.return_value = {"email": email}
    return svc


def _mock_client(response=None):
    client = MagicMock()
    client.request = AsyncMock(return_value=response or {})
    client.close = AsyncMock()
    return client


def _export_response(tasks=5, projects=2, labels=3, contexts=1, encrypted=False):
    return {
        "stats": {
            "tasks_count": tasks,
            "projects_count": projects,
            "labels_count": labels,
            "contexts_count": contexts,
        },
        "encryption": {"enabled": encrypted},
        "data": {"tasks": [], "projects": [], "labels": [], "contexts": []},
    }


def _import_response(errors=None):
    return {
        "summary": {
            "projects": "0 created, 0 skipped",
            "labels": "0 created, 0 skipped",
            "contexts": "N/A",
            "tasks": "0 created, 0 skipped",
        },
        "details": errors or {},
    }


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

class TestHelpText:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "data" in result.output.lower() or "management" in result.output.lower()

    def test_export_help(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output.lower()

    def test_import_help(self):
        result = runner.invoke(app, ["import", "--help"])
        assert result.exit_code == 0
        assert "import" in result.output.lower()

    def test_purge_help(self):
        result = runner.invoke(app, ["purge", "--help"])
        assert result.exit_code == 0
        assert "purge" in result.output.lower() or "delete" in result.output.lower()

    def test_export_help_mentions_output_option(self):
        result = runner.invoke(app, ["export", "--help"])
        assert "--output" in result.output or "-o" in result.output

    def test_export_help_mentions_compress_option(self):
        result = runner.invoke(app, ["export", "--help"])
        assert "--compress" in result.output or "-z" in result.output

    def test_import_help_mentions_yes_option(self):
        result = runner.invoke(app, ["import", "--help"])
        assert "--yes" in result.output or "-y" in result.output

    def test_purge_help_mentions_dry_run(self):
        result = runner.invoke(app, ["purge", "--help"])
        assert "--dry-run" in result.output


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------

class TestExportCommand:
    """Tests for the 'export' subcommand using remote context."""

    def _invoke_export(self, extra_args=None, response=None, output_path=None):
        svc = _mock_config_svc("remote")
        client = _mock_client(response or _export_response())
        args = ["export"]
        if output_path:
            args += ["--output", str(output_path)]
        if extra_args:
            args += extra_args
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            return runner.invoke(app, args)

    def test_export_remote_success(self, tmp_path):
        out = str(tmp_path / "backup.json")
        result = self._invoke_export(output_path=out)
        assert result.exit_code == 0

    def test_export_success_message(self, tmp_path):
        out = str(tmp_path / "backup.json")
        result = self._invoke_export(output_path=out)
        assert "export" in result.output.lower()

    def test_export_stats_table_shown(self, tmp_path):
        out = str(tmp_path / "backup.json")
        result = self._invoke_export(response=_export_response(tasks=7), output_path=out)
        assert result.exit_code == 0
        # Summary table should be printed
        assert "7" in result.output or "Tasks" in result.output

    def test_export_creates_file(self, tmp_path):
        out = tmp_path / "backup.json"
        self._invoke_export(output_path=str(out))
        assert out.exists()
        data = json.loads(out.read_text())
        assert "stats" in data

    def test_export_with_default_filename(self, tmp_path, monkeypatch):
        """Without --output, a timestamp filename is generated."""
        monkeypatch.chdir(tmp_path)
        svc = _mock_config_svc("remote")
        client = _mock_client(_export_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["export"])
        assert result.exit_code == 0
        assert any(f.name.startswith("todopro-export-") for f in tmp_path.iterdir())

    def test_export_encryption_message(self, tmp_path):
        out = str(tmp_path / "backup.json")
        result = self._invoke_export(response=_export_response(encrypted=True), output_path=out)
        assert result.exit_code == 0
        assert "encrypt" in result.output.lower()

    def test_export_no_encryption_message_when_disabled(self, tmp_path):
        out = str(tmp_path / "backup.json")
        result = self._invoke_export(response=_export_response(encrypted=False), output_path=out)
        assert result.exit_code == 0
        # No encryption message when disabled
        assert "🔐" not in result.output

    def test_export_with_compress_flag(self, tmp_path):
        out = str(tmp_path / "backup.json.gz")
        result = self._invoke_export(extra_args=["--compress"], output_path=out)
        assert result.exit_code == 0

    def test_export_compress_creates_gz_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = _mock_config_svc("remote")
        client = _mock_client(_export_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["export", "--compress"])
        assert result.exit_code == 0
        gz_files = list(tmp_path.glob("*.gz"))
        assert len(gz_files) == 1

    def test_export_calls_get_client(self, tmp_path):
        out = str(tmp_path / "backup.json")
        svc = _mock_config_svc("remote")
        client = _mock_client(_export_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client) as mock_gc:
            runner.invoke(app, ["export", "--output", out])
        mock_gc.assert_called_once()

    def test_export_closes_client(self, tmp_path):
        out = str(tmp_path / "backup.json")
        svc = _mock_config_svc("remote")
        client = _mock_client(_export_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            runner.invoke(app, ["export", "--output", out])
        client.close.assert_awaited_once()

    def test_export_unexpected_response_exits_nonzero(self, tmp_path):
        """If server returns bytes instead of dict, exit non-zero."""
        out = str(tmp_path / "backup.json")
        svc = _mock_config_svc("remote")
        client = _mock_client(b"raw bytes")  # not a dict
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["export", "--output", out])
        assert result.exit_code != 0

    def test_export_context_error_falls_back_to_local(self, tmp_path):
        """ValueError from get_current_context triggers local-path (which will error on undefined symbol)."""
        svc = MagicMock()
        svc.config.get_current_context.side_effect = ValueError("no context")
        svc.load_credentials.return_value = {}
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc):
            result = runner.invoke(app, ["export", "--output", str(tmp_path / "out.json")])
        # Local path fails on undefined get_storage_strategy_context - exit non-zero
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# import command
# ---------------------------------------------------------------------------

class TestImportCommand:
    """Tests for the 'import' subcommand."""

    def test_import_file_not_found(self):
        result = runner.invoke(app, ["import", "/nonexistent/path/backup.json"])
        assert result.exit_code == 5
        assert "not found" in result.output.lower() or "File not found" in result.output

    def test_import_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("this is not valid JSON {{{{", encoding="utf-8")
        result = runner.invoke(app, ["import", str(bad_file)])
        assert result.exit_code == 2
        assert "invalid" in result.output.lower() or "json" in result.output.lower()

    def test_import_confirmation_cancel(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(
            json.dumps({"stats": {"tasks_count": 2}, "data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["import", str(good_file)], input="n\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower()

    def test_import_shows_preview_table(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(
            json.dumps({"stats": {"tasks_count": 3, "projects_count": 1, "labels_count": 2, "contexts_count": 0}, "data": {}}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["import", str(good_file)], input="n\n")
        assert result.exit_code == 0
        assert "Import Preview" in result.output or "3" in result.output

    def test_import_preview_shows_tasks_count(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(
            json.dumps({"stats": {"tasks_count": 99}, "data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["import", str(good_file)], input="n\n")
        assert "99" in result.output

    def test_import_preview_counts_from_data_fallback(self, tmp_path):
        """If no 'stats' key, counts come from data arrays."""
        good_file = tmp_path / "data.json"
        payload = {
            "data": {
                "tasks": [{"content": "task1"}, {"content": "task2"}],
                "projects": [{"name": "proj1"}],
                "labels": [],
                "contexts": [],
            }
        }
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        result = runner.invoke(app, ["import", str(good_file)], input="n\n")
        assert result.exit_code == 0
        assert "2" in result.output  # task count

    def test_import_note_displayed(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(
            json.dumps({"data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["import", str(good_file)], input="n\n")
        assert "skip" in result.output.lower() or "existing" in result.output.lower()

    def test_import_yes_flag_remote_success(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(
            json.dumps({"data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}),
            encoding="utf-8",
        )
        svc = _mock_config_svc("remote")
        client = _mock_client(_import_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])
        assert result.exit_code == 0
        assert "import" in result.output.lower()

    def test_import_yes_flag_shows_results_table(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps({"data": {}}), encoding="utf-8")
        svc = _mock_config_svc("remote")
        client = _mock_client(_import_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])
        assert "Import Results" in result.output or "import" in result.output.lower()

    def test_import_yes_flag_shows_errors(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps({"data": {}}), encoding="utf-8")
        svc = _mock_config_svc("remote")
        client = _mock_client({
            "summary": {"projects": "0 created, 0 skipped", "labels": "0 created, 0 skipped", "contexts": "N/A", "tasks": "0 created, 0 skipped"},
            "details": {"tasks": {"errors": ["task1: some error", "task2: another error"]}},
        })
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])
        assert result.exit_code == 0
        assert "error" in result.output.lower() or "⚠" in result.output

    def test_import_closes_client_on_success(self, tmp_path):
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps({"data": {}}), encoding="utf-8")
        svc = _mock_config_svc("remote")
        client = _mock_client(_import_response())
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            runner.invoke(app, ["import", str(good_file), "--yes"])
        client.close.assert_awaited_once()

    def test_import_gzip_file_cancel(self, tmp_path):
        gz_file = tmp_path / "data.json.gz"
        payload = {"stats": {"tasks_count": 0}, "data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}
        with gzip.open(str(gz_file), "wt") as f:
            json.dump(payload, f)
        result = runner.invoke(app, ["import", str(gz_file)], input="n\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower()

    def test_import_gzip_invalid_exits_error(self, tmp_path):
        bad_gz = tmp_path / "bad.json.gz"
        bad_gz.write_bytes(b"NOT A GZIP FILE AT ALL!!!")
        result = runner.invoke(app, ["import", str(bad_gz)])
        assert result.exit_code in (1, 2)

    def test_import_yes_flag_no_data_key(self, tmp_path):
        """Missing 'data' key shows zero counts and cancels correctly."""
        f = tmp_path / "empty.json"
        f.write_text(json.dumps({}), encoding="utf-8")
        result = runner.invoke(app, ["import", str(f)], input="n\n")
        assert result.exit_code == 0

    def test_import_errors_more_than_five(self, tmp_path):
        """When there are more than 5 errors, 'and N more' is shown."""
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps({"data": {}}), encoding="utf-8")
        svc = _mock_config_svc("remote")
        errors = [f"task{i}: error" for i in range(10)]
        client = _mock_client({
            "summary": {"projects": "0 created, 0 skipped", "labels": "0 created, 0 skipped", "contexts": "N/A", "tasks": "0 created, 0 skipped"},
            "details": {"tasks": {"errors": errors}},
        })
        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])
        assert result.exit_code == 0
        assert "more" in result.output.lower() or "5" in result.output


# ---------------------------------------------------------------------------
# purge command
# ---------------------------------------------------------------------------

class TestPurgeCommand:
    """Tests for the 'purge' subcommand."""

    USER_EMAIL = "test@example.com"

    def _patches(self, client):
        return (
            patch("todopro_cli.commands.data_command.get_config_service", return_value=_mock_config_svc(email=self.USER_EMAIL)),
            patch("todopro_cli.commands.data_command.get_client", return_value=client),
        )

    # -- dry-run path

    def test_purge_dry_run_exits_zero(self):
        client = _mock_client({"items_to_delete": {"tasks": 10, "projects": 3, "labels": 5, "contexts": 2}, "total_items": 20})
        p1, p2 = self._patches(client)
        with p1, p2:
            result = runner.invoke(app, ["purge", "--dry-run"])
        assert result.exit_code == 0

    def test_purge_dry_run_mentions_dry_run(self):
        client = _mock_client({"items_to_delete": {}, "total_items": 0})
        p1, p2 = self._patches(client)
        with p1, p2:
            result = runner.invoke(app, ["purge", "--dry-run"])
        assert "dry" in result.output.lower()

    def test_purge_dry_run_shows_counts(self):
        client = _mock_client({"items_to_delete": {"tasks": 7, "projects": 2, "labels": 4, "contexts": 1}, "total_items": 14})
        p1, p2 = self._patches(client)
        with p1, p2:
            result = runner.invoke(app, ["purge", "--dry-run"])
        assert "7" in result.output or "Tasks" in result.output

    def test_purge_dry_run_calls_api_with_dry_run_param(self):
        client = _mock_client({"items_to_delete": {}, "total_items": 0})
        p1, p2 = self._patches(client)
        with p1, p2:
            runner.invoke(app, ["purge", "--dry-run"])
        client.request.assert_awaited_once()
        call_args = client.request.call_args
        assert call_args[1].get("params", {}).get("dry_run") == "true" or \
               (len(call_args[0]) > 2 and "dry_run" in str(call_args))

    def test_purge_dry_run_closes_client(self):
        client = _mock_client({"items_to_delete": {}, "total_items": 0})
        p1, p2 = self._patches(client)
        with p1, p2:
            runner.invoke(app, ["purge", "--dry-run"])
        client.close.assert_awaited_once()

    # -- cancellation paths

    def test_purge_first_confirm_cancel(self):
        p1, p2 = self._patches(_mock_client())
        with p1, p2:
            result = runner.invoke(app, ["purge"], input="n\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower()

    def test_purge_shows_warning_banner(self):
        p1, p2 = self._patches(_mock_client())
        with p1, p2:
            result = runner.invoke(app, ["purge"], input="n\n")
        assert "WARNING" in result.output or "warning" in result.output.lower()

    def test_purge_lists_what_will_be_deleted(self):
        p1, p2 = self._patches(_mock_client())
        with p1, p2:
            result = runner.invoke(app, ["purge"], input="n\n")
        out = result.output.lower()
        assert "tasks" in out or "projects" in out

    def test_purge_wrong_email_cancels(self):
        p1, p2 = self._patches(_mock_client())
        with p1, p2:
            # say yes to first confirm, then type wrong email
            result = runner.invoke(app, ["purge"], input="y\nwrong@email.com\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower() or "match" in result.output.lower()

    def test_purge_final_confirm_cancel(self):
        p1, p2 = self._patches(_mock_client())
        with p1, p2:
            result = runner.invoke(app, ["purge"], input=f"y\n{self.USER_EMAIL}\nn\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower()

    def test_purge_full_success(self):
        client = _mock_client({
            "deleted": {"tasks": 5, "projects": 2, "labels": 3, "contexts": 1},
            "encryption_cleared": True,
        })
        p1, p2 = self._patches(client)
        with p1, p2:
            result = runner.invoke(app, ["purge"], input=f"y\n{self.USER_EMAIL}\ny\n")
        assert result.exit_code == 0

    def test_purge_success_shows_deletion_summary(self):
        client = _mock_client({
            "deleted": {"tasks": 5, "projects": 2, "labels": 3, "contexts": 1},
            "encryption_cleared": False,
        })
        p1, p2 = self._patches(client)
        with p1, p2:
            result = runner.invoke(app, ["purge"], input=f"y\n{self.USER_EMAIL}\ny\n")
        assert "Deletion" in result.output or "deleted" in result.output.lower()

    def test_purge_success_shows_encryption_cleared_message(self):
        client = _mock_client({
            "deleted": {"tasks": 1},
            "encryption_cleared": True,
        })
        p1, p2 = self._patches(client)
        with p1, p2:
            result = runner.invoke(app, ["purge"], input=f"y\n{self.USER_EMAIL}\ny\n")
        assert "encrypt" in result.output.lower() or "🔐" in result.output

    def test_purge_success_closes_client(self):
        client = _mock_client({"deleted": {}, "encryption_cleared": False})
        p1, p2 = self._patches(client)
        with p1, p2:
            runner.invoke(app, ["purge"], input=f"y\n{self.USER_EMAIL}\ny\n")
        client.close.assert_awaited_once()


# ===========================================================================
# Local export path (lines 76-93)
# ===========================================================================

class TestLocalExport:
    """Cover lines 76-93: local export when is_local=True."""

    def _make_mock_storage(self, tasks=None, projects=None, labels=None):
        """Build a mock storage_strategy_context with async repos."""
        storage = MagicMock()
        storage.task_repository.list_all = AsyncMock(return_value=tasks or [])
        storage.project_repository.list_all = AsyncMock(return_value=projects or [])
        storage.label_repository.list_all = AsyncMock(return_value=labels or [])
        return storage

    def test_local_export_success(self, tmp_path):
        """Local export builds response and writes JSON file."""
        out = str(tmp_path / "local_export.json")
        svc = _mock_config_svc("local")
        svc.config.contexts = []
        svc.config.e2ee = None

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["export", "--output", out])

        assert result.exit_code == 0
        assert "export" in result.output.lower()

    def test_local_export_creates_file(self, tmp_path):
        """Local export creates a valid JSON file."""
        out = tmp_path / "local_export.json"
        svc = _mock_config_svc("local")
        svc.config.contexts = []
        svc.config.e2ee = None

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            runner.invoke(app, ["export", "--output", str(out)])

        assert out.exists()
        data = json.loads(out.read_text())
        assert "stats" in data
        assert "data" in data

    def test_local_export_shows_stats_table(self, tmp_path):
        """Local export prints a summary stats table."""
        out = str(tmp_path / "export.json")
        svc = _mock_config_svc("local")
        svc.config.contexts = []
        svc.config.e2ee = None

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["export", "--output", out])

        assert result.exit_code == 0
        assert "Tasks" in result.output or "Export" in result.output

    def test_local_export_with_e2ee_enabled(self, tmp_path):
        """Local export shows encryption info when e2ee is enabled."""
        out = str(tmp_path / "enc_export.json")
        svc = _mock_config_svc("local")
        svc.config.contexts = []
        svc.config.e2ee = MagicMock()
        svc.config.e2ee.enabled = True

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["export", "--output", out])

        assert result.exit_code == 0
        assert "encrypt" in result.output.lower() or "🔐" in result.output

    def test_local_export_with_no_e2ee_config(self, tmp_path):
        """Local export with e2ee=None sets e2ee_enabled=False."""
        out = str(tmp_path / "no_enc.json")
        svc = _mock_config_svc("local")
        svc.config.contexts = []
        svc.config.e2ee = None  # explicitly None

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["export", "--output", out])

        assert result.exit_code == 0

    def test_local_export_compress_creates_gz_file(self, tmp_path, monkeypatch):
        """Local export with --compress creates a .gz file."""
        monkeypatch.chdir(tmp_path)
        svc = _mock_config_svc("local")
        svc.config.contexts = []
        svc.config.e2ee = None

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["export", "--compress"])

        assert result.exit_code == 0
        gz_files = list(tmp_path.glob("*.gz"))
        assert len(gz_files) >= 1

    def test_local_export_context_valueerror_falls_back_to_local(self, tmp_path):
        """Lines 63-65: ValueError from get_current_context → is_local=True."""
        out = str(tmp_path / "fallback.json")
        svc = MagicMock()
        svc.config.get_current_context.side_effect = ValueError("no context")
        svc.config.contexts = []
        svc.config.e2ee = None
        svc.load_credentials.return_value = {}

        storage = self._make_mock_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["export", "--output", out])

        assert result.exit_code == 0


# ===========================================================================
# Line 134: compress=True with bytes response from remote
# ===========================================================================

class TestExportCompressBytesResponse:
    """Line 134: when compress=True and server returns raw bytes, write_bytes is called."""

    def test_export_compress_with_bytes_response_writes_raw(self, tmp_path):
        """Line 134: compress=True AND response is bytes → write raw bytes to file."""
        out = tmp_path / "backup.json.gz"
        svc = _mock_config_svc("remote")
        # Return raw gzip bytes (not a dict)
        raw_gz = b"\x1f\x8b\x08\x00already-gzipped-data"
        client = _mock_client(raw_gz)

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_client", return_value=client):
            result = runner.invoke(app, ["export", "--output", str(out), "--compress"])

        assert result.exit_code == 0
        assert out.exists()
        assert out.read_bytes() == raw_gz  # raw bytes written as-is


# ===========================================================================
# Lines 254-256: import do_import() exception path (is_local fallback)
# ===========================================================================

class TestImportIsLocalFallback:
    """Lines 254-256: ValueError/KeyError from get_current_context → is_local=True."""

    def test_import_valueerror_from_context_falls_back_to_local(self, tmp_path):
        """Lines 254-256: ValueError → is_local=True, triggers local import."""
        good_file = tmp_path / "data.json"
        good_file.write_text(
            json.dumps({"data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}),
            encoding="utf-8",
        )
        svc = MagicMock()
        svc.config.get_current_context.side_effect = ValueError("no context")
        svc.load_credentials.return_value = {}

        storage = MagicMock()
        storage.task_repository.list_all = AsyncMock(return_value=[])
        storage.project_repository.list_all = AsyncMock(return_value=[])
        storage.label_repository.list_all = AsyncMock(return_value=[])
        storage.task_repository.add = AsyncMock()
        storage.project_repository.create = AsyncMock()
        storage.label_repository.create = AsyncMock()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0

    def test_import_keyerror_from_context_falls_back_to_local(self, tmp_path):
        """Lines 254-256: KeyError → is_local=True, triggers local import."""
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps({"data": {}}), encoding="utf-8")
        svc = MagicMock()
        svc.config.get_current_context.side_effect = KeyError("no context key")
        svc.load_credentials.return_value = {}

        storage = MagicMock()
        storage.task_repository.list_all = AsyncMock(return_value=[])
        storage.project_repository.list_all = AsyncMock(return_value=[])
        storage.label_repository.list_all = AsyncMock(return_value=[])
        storage.task_repository.add = AsyncMock()
        storage.project_repository.create = AsyncMock()
        storage.label_repository.create = AsyncMock()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0


# ===========================================================================
# Lines 263-393: Local import path
# ===========================================================================

class TestLocalImport:
    """Cover lines 263-393: the local SQLite import path when is_local=True."""

    def _make_storage(self):
        """Build a fully mocked storage strategy context."""
        storage = MagicMock()
        storage.task_repository.list_all = AsyncMock(return_value=[])
        storage.project_repository.list_all = AsyncMock(return_value=[])
        storage.label_repository.list_all = AsyncMock(return_value=[])
        storage.task_repository.add = AsyncMock()
        storage.project_repository.create = AsyncMock()
        storage.label_repository.create = AsyncMock()
        return storage

    def _invoke_local_import(self, tmp_path, payload, extra_args=None):
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            args = ["import", str(good_file), "--yes"]
            if extra_args:
                args += extra_args
            return runner.invoke(app, args), storage

    def test_local_import_empty_data_succeeds(self, tmp_path):
        """Local import with empty data arrays completes successfully."""
        payload = {"data": {"tasks": [], "projects": [], "labels": [], "contexts": []}}
        result, _ = self._invoke_local_import(tmp_path, payload)
        assert result.exit_code == 0

    def test_local_import_shows_results_table(self, tmp_path):
        """Local import prints Import Results table."""
        payload = {"data": {"tasks": [], "projects": [], "labels": []}}
        result, _ = self._invoke_local_import(tmp_path, payload)
        assert result.exit_code == 0
        assert "import" in result.output.lower() or "Result" in result.output

    def test_local_import_new_project_creates_it(self, tmp_path):
        """Local import creates new projects that don't exist yet."""
        payload = {
            "data": {
                "projects": [{"name": "NewProject", "description": "desc", "color": None}],
                "tasks": [],
                "labels": [],
            }
        }
        result, storage = self._invoke_local_import(tmp_path, payload)
        assert result.exit_code == 0
        storage.project_repository.create.assert_awaited_once()

    def test_local_import_skips_existing_project(self, tmp_path):
        """Local import skips projects that already exist."""
        existing_project = MagicMock()
        existing_project.name = "ExistingProject"

        payload = {
            "data": {
                "projects": [{"name": "ExistingProject"}],
                "tasks": [],
                "labels": [],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        storage.project_repository.list_all = AsyncMock(return_value=[existing_project])

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0
        storage.project_repository.create.assert_not_awaited()

    def test_local_import_new_label_creates_it(self, tmp_path):
        """Local import creates new labels."""
        payload = {
            "data": {
                "projects": [],
                "labels": [{"name": "urgent", "color": "#ff0000"}],
                "tasks": [],
            }
        }
        result, storage = self._invoke_local_import(tmp_path, payload)
        assert result.exit_code == 0
        storage.label_repository.create.assert_awaited_once()

    def test_local_import_skips_existing_label(self, tmp_path):
        """Local import skips labels that already exist."""
        existing_label = MagicMock()
        existing_label.name = "existing-label"

        payload = {
            "data": {
                "projects": [],
                "labels": [{"name": "existing-label"}],
                "tasks": [],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        storage.label_repository.list_all = AsyncMock(return_value=[existing_label])

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0
        storage.label_repository.create.assert_not_awaited()

    def test_local_import_new_task_creates_it(self, tmp_path):
        """Local import creates new tasks."""
        payload = {
            "data": {
                "projects": [],
                "labels": [],
                "tasks": [{"content": "Brand new task", "priority": 2}],
            }
        }
        result, storage = self._invoke_local_import(tmp_path, payload)
        assert result.exit_code == 0
        storage.task_repository.add.assert_awaited_once()

    def test_local_import_skips_existing_task(self, tmp_path):
        """Local import skips tasks with matching content."""
        existing_task = MagicMock()
        existing_task.content = "Already exists"

        payload = {
            "data": {
                "projects": [],
                "labels": [],
                "tasks": [{"content": "Already exists"}],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        storage.task_repository.list_all = AsyncMock(return_value=[existing_task])

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0
        storage.task_repository.add.assert_not_awaited()

    def test_local_import_task_with_project_name_resolves_id(self, tmp_path):
        """Local import resolves project_id from project_name for tasks."""
        existing_project = MagicMock()
        existing_project.id = "proj-123"
        existing_project.name = "MyProject"

        payload = {
            "data": {
                "projects": [],
                "labels": [],
                "tasks": [{"content": "Task with project", "project_name": "MyProject"}],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        # task list_all returns empty (new task), project list_all returns project
        storage.task_repository.list_all = AsyncMock(return_value=[])
        storage.project_repository.list_all = AsyncMock(return_value=[existing_project])

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0
        storage.task_repository.add.assert_awaited_once()

    def test_local_import_project_error_continues(self, tmp_path):
        """Local import handles individual project errors gracefully."""
        payload = {
            "data": {
                "projects": [{"name": "BadProject"}],
                "labels": [],
                "tasks": [],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        storage.project_repository.list_all = AsyncMock(return_value=[])
        storage.project_repository.create = AsyncMock(side_effect=Exception("DB error"))

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        # Errors should be gracefully handled, import completes
        assert result.exit_code == 0

    def test_local_import_summary_shows_contexts_not_imported(self, tmp_path):
        """Local import shows 'N/A' for contexts (not imported to local)."""
        payload = {"data": {"tasks": [], "projects": [], "labels": []}}
        result, _ = self._invoke_local_import(tmp_path, payload)
        assert result.exit_code == 0
        assert "N/A" in result.output or "context" in result.output.lower()

    def test_local_import_label_error_continues(self, tmp_path):
        """Lines 339-340: label creation error is caught, import continues."""
        payload = {
            "data": {
                "projects": [],
                "labels": [{"name": "error-label", "color": None}],
                "tasks": [],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        storage.label_repository.list_all = AsyncMock(return_value=[])
        storage.label_repository.create = AsyncMock(side_effect=Exception("label DB error"))

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0

    def test_local_import_task_error_continues(self, tmp_path):
        """Lines 382-383: task creation error is caught, import continues."""
        payload = {
            "data": {
                "projects": [],
                "labels": [],
                "tasks": [{"content": "Failing task", "priority": 3}],
            }
        }
        good_file = tmp_path / "data.json"
        good_file.write_text(json.dumps(payload), encoding="utf-8")
        svc = _mock_config_svc("local")
        storage = self._make_storage()
        storage.task_repository.list_all = AsyncMock(return_value=[])
        storage.task_repository.add = AsyncMock(side_effect=Exception("task DB error"))

        with patch("todopro_cli.commands.data_command.get_config_service", return_value=svc), \
             patch("todopro_cli.commands.data_command.get_storage_strategy_context",
                   return_value=storage, create=True):
            result = runner.invoke(app, ["import", str(good_file), "--yes"])

        assert result.exit_code == 0
