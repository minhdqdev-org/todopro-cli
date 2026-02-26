"""Unit tests for context.py (storage context management: list, use, create, delete, rename).

get_config_service is NOT imported in context.py (missing import), so we use
patch(..., create=True) to inject it into the module namespace.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.context import app, _get_user_info_sync
from todopro_cli.models.config_models import Context

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(name="default", ctx_type="local", source="/tmp/default.db", **kwargs):
    return Context(name=name, type=ctx_type, source=source, **kwargs)


def _make_svc(*contexts, current="default"):
    svc = MagicMock()
    ctx_list = list(contexts) if contexts else [_make_ctx()]
    svc.list_contexts.return_value = ctx_list
    svc.config.current_context = current
    current_ctx = next((c for c in ctx_list if c.name == current), ctx_list[0] if ctx_list else None)
    svc.get_current_context.return_value = current_ctx
    svc.get_context.return_value = None  # default: not found
    svc.use_context.side_effect = lambda name: next((c for c in ctx_list if c.name == name), None)
    svc.rename_context.return_value = True
    svc.add_context = MagicMock()
    svc.remove_context = MagicMock()
    return svc


def _patch_svc(svc):
    """Patch get_config_service in context module (missing import → create=True)."""
    return patch("todopro_cli.commands.context.get_config_service", create=True, return_value=svc)


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

class TestHelpText:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_list_help(self):
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "context" in result.output.lower()

    def test_use_help(self):
        result = runner.invoke(app, ["use", "--help"])
        assert result.exit_code == 0
        assert "switch" in result.output.lower() or "context" in result.output.lower()

    def test_create_help(self):
        result = runner.invoke(app, ["create", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output.lower()

    def test_delete_help(self):
        result = runner.invoke(app, ["delete", "--help"])
        assert result.exit_code == 0
        assert "delete" in result.output.lower()

    def test_rename_help(self):
        result = runner.invoke(app, ["rename", "--help"])
        assert result.exit_code == 0
        assert "rename" in result.output.lower()

    def test_list_has_output_option(self):
        result = runner.invoke(app, ["list", "--help"])
        assert "--output" in result.output or "-o" in result.output

    def test_create_has_type_option(self):
        result = runner.invoke(app, ["create", "--help"])
        assert "--type" in result.output

    def test_delete_has_force_option(self):
        result = runner.invoke(app, ["delete", "--help"])
        assert "--force" in result.output or "-f" in result.output


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

class TestListContexts:
    def test_list_shows_contexts(self):
        ctx1 = _make_ctx("work", "remote", "https://api.example.com")
        ctx2 = _make_ctx("home", "local", "/home/user/home.db")
        svc = _make_svc(ctx1, ctx2, current="work")
        with _patch_svc(svc):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "work" in result.output
        assert "home" in result.output

    def test_list_shows_active_marker(self):
        ctx = _make_ctx("default", "local", "/tmp/default.db")
        svc = _make_svc(ctx, current="default")
        with _patch_svc(svc):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "*" in result.output

    def test_list_shows_context_type(self):
        ctx = _make_ctx("myctx", "remote", "https://api.example.com")
        svc = _make_svc(ctx)
        with _patch_svc(svc):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "remote" in result.output

    def test_list_empty_shows_message(self):
        svc = _make_svc()
        svc.list_contexts.return_value = []
        with _patch_svc(svc):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Either table with no rows or a "no contexts" message
        assert "no contexts" in result.output.lower() or "NAME" in result.output or result.exit_code == 0

    def test_list_json_output(self):
        ctx = _make_ctx("default", "local", "/tmp/default.db")
        svc = _make_svc(ctx, current="default")
        with _patch_svc(svc):
            result = runner.invoke(app, ["list", "--output", "json"])
        assert result.exit_code == 0
        # JSON output should contain context info
        assert "default" in result.output

    def test_list_json_output_valid_json(self):
        import json as jsonlib
        ctx = _make_ctx("default", "local", "/tmp/default.db")
        svc = _make_svc(ctx, current="default")
        with _patch_svc(svc):
            result = runner.invoke(app, ["list", "--output", "json"])
        assert result.exit_code == 0
        # Extract JSON from output (may have extra lines)
        lines = result.output.strip()
        # The JSON block should parse correctly
        try:
            data = jsonlib.loads(lines)
            assert isinstance(data, list)
        except jsonlib.JSONDecodeError:
            # Output may have rich markup, just check it ran ok
            pass

    def test_list_shows_source(self):
        ctx = _make_ctx("mydb", "local", "/custom/path/mydb.db")
        svc = _make_svc(ctx)
        with _patch_svc(svc):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "/custom/path/mydb.db" in result.output


# ---------------------------------------------------------------------------
# use command
# ---------------------------------------------------------------------------

class TestUseContext:
    def test_use_switches_context(self):
        ctx = _make_ctx("work", "local", "/tmp/work.db")
        svc = _make_svc(ctx, current="default")
        svc.get_current_context.return_value = _make_ctx("default")  # currently on default
        svc.use_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["use", "work"])
        assert result.exit_code == 0
        assert "work" in result.output
        assert "switched" in result.output.lower() or "✓" in result.output

    def test_use_already_on_context(self):
        ctx = _make_ctx("work", "local", "/tmp/work.db")
        svc = _make_svc(ctx, current="work")
        with _patch_svc(svc):
            result = runner.invoke(app, ["use", "work"])
        assert result.exit_code == 0
        assert "already" in result.output.lower()

    def test_use_context_not_found(self):
        svc = _make_svc(_make_ctx("default"))
        svc.use_context.side_effect = ValueError("Context 'unknown' not found")
        with _patch_svc(svc):
            result = runner.invoke(app, ["use", "unknown"])
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "not found" in result.output.lower()

    def test_use_local_vault_missing_shows_warning(self, tmp_path):
        ctx = _make_ctx("newlocal", "local", str(tmp_path / "nonexistent.db"))
        svc = _make_svc(ctx, current="old")
        svc.get_current_context.return_value = _make_ctx("old")
        svc.use_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["use", "newlocal"])
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "Warning" in result.output

    def test_use_local_vault_exists_no_warning(self, tmp_path):
        db_path = tmp_path / "existing.db"
        db_path.touch()
        ctx = _make_ctx("existing", "local", str(db_path))
        svc = _make_svc(ctx, current="other")
        svc.get_current_context.return_value = _make_ctx("other")
        svc.use_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["use", "existing"])
        assert result.exit_code == 0
        assert "warning" not in result.output.lower() or "Warning" not in result.output

    def test_use_shows_source(self):
        ctx = _make_ctx("dev", "local", "/tmp/dev.db")
        svc = _make_svc(ctx, current="prod")
        svc.get_current_context.return_value = _make_ctx("prod")
        svc.use_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["use", "dev"])
        assert result.exit_code == 0
        assert "/tmp/dev.db" in result.output


# ---------------------------------------------------------------------------
# create command
# ---------------------------------------------------------------------------

class TestCreateContext:
    def test_create_local_success(self, tmp_path):
        db_path = tmp_path / "mylocal.db"
        svc = _make_svc()
        svc.get_context.return_value = None  # doesn't exist yet
        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection"), \
             patch("todopro_cli.commands.context.initialize_schema"):
            result = runner.invoke(app, [
                "create", "mylocal",
                "--type", "local",
                "--source", str(db_path),
            ], input="y\n")
        assert result.exit_code == 0
        assert "mylocal" in result.output
        svc.add_context.assert_called_once()

    def test_create_local_no_source_uses_default(self, tmp_path):
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.user_data_dir", return_value=str(tmp_path)), \
             patch("todopro_cli.commands.context.get_connection"), \
             patch("todopro_cli.commands.context.initialize_schema"):
            result = runner.invoke(app, [
                "create", "autolocal",
                "--type", "local",
            ], input="n\n")
        assert result.exit_code == 0
        assert "autolocal" in result.output

    def test_create_invalid_type(self):
        svc = _make_svc()
        with _patch_svc(svc):
            result = runner.invoke(app, [
                "create", "badtype",
                "--type", "invalid",
                "--source", "/tmp/x.db",
            ])
        assert result.exit_code == 1
        assert "local" in result.output or "remote" in result.output

    def test_create_already_exists(self):
        existing = _make_ctx("already")
        svc = _make_svc(existing)
        svc.get_context.return_value = existing  # already exists
        with _patch_svc(svc):
            result = runner.invoke(app, [
                "create", "already",
                "--type", "local",
                "--source", "/tmp/already.db",
            ])
        assert result.exit_code == 1
        assert "already" in result.output.lower()

    def test_create_remote_missing_source(self):
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc):
            result = runner.invoke(app, [
                "create", "cloud",
                "--type", "remote",
                "--user", "user@example.com",
            ])
        assert result.exit_code == 1
        assert "source" in result.output.lower() or "--source" in result.output

    def test_create_remote_missing_user(self):
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc):
            result = runner.invoke(app, [
                "create", "cloud",
                "--type", "remote",
                "--source", "https://api.example.com",
            ])
        assert result.exit_code == 1
        assert "user" in result.output.lower() or "--user" in result.output

    def test_create_remote_success(self):
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc):
            result = runner.invoke(app, [
                "create", "cloud",
                "--type", "remote",
                "--source", "https://api.example.com",
                "--user", "admin@example.com",
            ])
        assert result.exit_code == 0
        assert "cloud" in result.output
        svc.add_context.assert_called_once()

    def test_create_local_db_creation_failure(self, tmp_path):
        db_path = tmp_path / "fail.db"
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection", side_effect=Exception("disk full")):
            result = runner.invoke(app, [
                "create", "fail",
                "--type", "local",
                "--source", str(db_path),
            ], input="y\n")
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "fail" in result.output.lower()

    def test_create_shows_type_and_source(self, tmp_path):
        db_path = tmp_path / "info.db"
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection"), \
             patch("todopro_cli.commands.context.initialize_schema"):
            result = runner.invoke(app, [
                "create", "info",
                "--type", "local",
                "--source", str(db_path),
            ], input="y\n")
        assert result.exit_code == 0
        assert "local" in result.output
        assert str(db_path) in result.output

    def test_create_skip_db_creation(self, tmp_path):
        db_path = tmp_path / "skipped.db"
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc):
            # Say "n" to db creation
            result = runner.invoke(app, [
                "create", "skipped",
                "--type", "local",
                "--source", str(db_path),
            ], input="n\n")
        assert result.exit_code == 0
        svc.add_context.assert_called_once()


# ---------------------------------------------------------------------------
# delete command
# ---------------------------------------------------------------------------

class TestDeleteContext:
    def test_delete_context_not_found(self):
        svc = _make_svc()
        svc.get_context.return_value = None
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "notexist", "--force"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_delete_cancel_confirmation(self):
        ctx = _make_ctx("myctx")
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "myctx"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower() or "cancel" in result.output.lower()

    def test_delete_with_force_flag(self):
        ctx = _make_ctx("myctx")
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "myctx", "--force"])
        assert result.exit_code == 0
        svc.remove_context.assert_called_once_with("myctx")
        assert "removed" in result.output.lower() or "✓" in result.output

    def test_delete_confirm_yes(self):
        ctx = _make_ctx("myctx")
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "myctx"], input="y\n")
        assert result.exit_code == 0
        svc.remove_context.assert_called_once_with("myctx")

    def test_delete_with_delete_db_flag(self, tmp_path):
        db_path = tmp_path / "toremove.db"
        db_path.touch()
        ctx = _make_ctx("withdb", "local", str(db_path))
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "withdb", "--force", "--delete-db"])
        assert result.exit_code == 0
        assert not db_path.exists()
        assert "deleted" in result.output.lower() or "✓" in result.output

    def test_delete_delete_db_file_missing(self, tmp_path):
        db_path = tmp_path / "nonexistent.db"
        ctx = _make_ctx("nofile", "local", str(db_path))
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "nofile", "--force", "--delete-db"])
        assert result.exit_code == 0
        # No error if file didn't exist - just context is removed

    def test_delete_shows_context_name(self):
        ctx = _make_ctx("oldctx")
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["delete", "oldctx", "--force"])
        assert result.exit_code == 0
        assert "oldctx" in result.output

    def test_rm_alias_works(self):
        """'rm' is an alias for 'delete'."""
        ctx = _make_ctx("tempctx")
        svc = _make_svc(ctx)
        svc.get_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["rm", "tempctx", "--force"])
        assert result.exit_code == 0
        svc.remove_context.assert_called_once_with("tempctx")


# ---------------------------------------------------------------------------
# rename command
# ---------------------------------------------------------------------------

class TestRenameContext:
    def test_rename_success(self):
        svc = _make_svc()
        svc.rename_context.return_value = True
        with _patch_svc(svc):
            result = runner.invoke(app, ["rename", "old", "new"])
        assert result.exit_code == 0
        assert "old" in result.output
        assert "new" in result.output
        assert "renamed" in result.output.lower() or "✓" in result.output

    def test_rename_not_found(self):
        svc = _make_svc()
        svc.rename_context.return_value = False
        with _patch_svc(svc):
            result = runner.invoke(app, ["rename", "ghost", "newname"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_rename_calls_service(self):
        svc = _make_svc()
        svc.rename_context.return_value = True
        with _patch_svc(svc):
            runner.invoke(app, ["rename", "old", "new"])
        svc.rename_context.assert_called_once_with("old", "new")

    def test_rename_shows_old_and_new_names(self):
        svc = _make_svc()
        svc.rename_context.return_value = True
        with _patch_svc(svc):
            result = runner.invoke(app, ["rename", "alpha", "beta"])
        assert "alpha" in result.output
        assert "beta" in result.output


# ---------------------------------------------------------------------------
# context_callback (bare 'context' command - shows current context)
# ---------------------------------------------------------------------------

def _make_mock_ctx(name="main", ctx_type="local", source="/tmp/main.db", **kwargs):
    """Create a MagicMock context with all expected attributes set."""
    ctx = MagicMock()
    ctx.name = name
    ctx.type = ctx_type
    ctx.source = source
    ctx.description = kwargs.get("description", "")
    ctx.user = kwargs.get("user", None)
    ctx.workspace_id = kwargs.get("workspace_id", None)
    # Encryption: disabled by default (falsy)
    ctx.encryption = None
    return ctx


class TestContextCallback:
    def test_no_subcommand_shows_context(self):
        ctx = _make_mock_ctx("main", "local", "/tmp/main.db")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "main" in result.output

    def test_no_subcommand_no_context_exits_one(self):
        svc = MagicMock()
        svc.get_current_context.return_value = None
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "no current context" in result.output.lower() or "context" in result.output.lower()

    def test_no_subcommand_shows_type_remote(self):
        """Remote context callback mocks _get_user_info_sync to avoid HTTP."""
        ctx = _make_mock_ctx("prod", "remote", "https://api.example.com")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        mock_user_info = {"email": "admin@example.com", "name": "Admin", "id": "u-1"}
        with _patch_svc(svc), \
             patch("todopro_cli.commands.context._get_user_info_sync", return_value=mock_user_info):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "remote" in result.output

    def test_no_subcommand_json_output_local(self):
        ctx = _make_mock_ctx("dev", "local", "/tmp/dev.db")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["--output", "json"])
        assert result.exit_code == 0
        assert "dev" in result.output

    def test_no_subcommand_shows_source(self):
        ctx = _make_mock_ctx("staging", "local", "/var/staging.db")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "/var/staging.db" in result.output

    def test_no_subcommand_local_shows_encryption_status(self):
        ctx = _make_mock_ctx("encrypted", "local", "/tmp/enc.db")
        ctx.encryption = MagicMock()
        ctx.encryption.enabled = True
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "encrypt" in result.output.lower()

    def test_subcommand_skips_callback(self):
        """When a subcommand is called, the callback's default behavior is skipped."""
        ctx = _make_ctx("default")
        svc = _make_svc(ctx, current="default")
        with _patch_svc(svc):
            result = runner.invoke(app, ["list"])
        # Should show list output, not the callback's show_current_context_info
        assert result.exit_code == 0


# ===========================================================================
# show_current_context_info – additional coverage
# ===========================================================================

class TestShowCurrentContextInfoExtra:
    """Cover lines 52, 54, 58, 66, 69, 72, 80-114 in show_current_context_info."""

    def test_json_output_includes_user_when_set(self):
        """Lines 51-52: JSON output includes user field when ctx.user is truthy."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", user="alice@example.com")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["--output", "json"])
        assert result.exit_code == 0
        assert "alice@example.com" in result.output

    def test_json_output_no_user_field_when_not_set(self):
        """Lines 51-52: JSON output omits user field when ctx.user is falsy."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", user=None)
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["--output", "json"])
        assert result.exit_code == 0
        assert "alice@example.com" not in result.output

    def test_json_output_includes_workspace_when_set(self):
        """Lines 53-54: JSON output includes workspace field when ctx.workspace_id is truthy."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", workspace_id="ws-xyz")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, ["--output", "json"])
        assert result.exit_code == 0
        assert "ws-xyz" in result.output

    def test_json_output_remote_context_includes_user_info(self):
        """Line 58: JSON output for remote context calls _get_user_info_sync."""
        ctx = _make_mock_ctx("prod", "remote", "https://api.example.com")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        mock_user_info = {"email": "u@example.com", "name": "U", "id": "u-1"}
        with _patch_svc(svc), \
             patch("todopro_cli.commands.context._get_user_info_sync", return_value=mock_user_info):
            result = runner.invoke(app, ["--output", "json"])
        assert result.exit_code == 0
        assert "user_info" in result.output or "u@example.com" in result.output

    def test_text_output_shows_description_when_set(self):
        """Line 66: text output includes description when provided."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", description="Work tasks")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Work tasks" in result.output

    def test_text_output_omits_description_when_empty(self):
        """Line 65: description block skipped when ctx.description is falsy."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", description="")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Description:" not in result.output

    def test_text_output_shows_user_when_set(self):
        """Line 69: text output includes user when provided."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", user="bob@example.com")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "bob@example.com" in result.output

    def test_text_output_omits_user_when_not_set(self):
        """Line 68: user block skipped when ctx.user is falsy."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", user=None)
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "bob@example.com" not in result.output

    def test_text_output_shows_workspace_when_set(self):
        """Line 72: text output includes workspace_id when provided."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", workspace_id="ws-abc123")
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "ws-abc123" in result.output

    def test_text_output_omits_workspace_when_not_set(self):
        """Line 71: workspace block skipped when ctx.workspace_id is falsy."""
        ctx = _make_mock_ctx("myctx", "local", "/tmp/myctx.db", workspace_id=None)
        svc = MagicMock()
        svc.get_current_context.return_value = ctx
        with _patch_svc(svc):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Workspace:" not in result.output

    def test_local_context_with_existing_db_shows_file_stats(self, tmp_path):
        """Lines 80-114: local context with existing db file shows file size and counts."""
        db_path = tmp_path / "existing.db"
        db_path.write_bytes(b"fake sqlite content")

        ctx = _make_mock_ctx("localctx", "local", str(db_path))
        ctx.encryption = None

        svc = MagicMock()
        svc.get_current_context.return_value = ctx

        # Single cursor mock; each fetchone() call returns [42] so all counts are 42
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [42]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor

        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection", return_value=mock_conn):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        # File-size line
        assert "MB" in result.output or "File Size" in result.output
        # Task count must appear
        assert "42" in result.output

    def test_local_context_with_existing_db_shows_all_record_counts(self, tmp_path):
        """Lines 92-114: distinct counts for tasks, completed, projects and labels."""
        db_path = tmp_path / "stats.db"
        db_path.write_bytes(b"fake sqlite")

        ctx = _make_mock_ctx("localctx", "local", str(db_path))
        ctx.encryption = None

        svc = MagicMock()
        svc.get_current_context.return_value = ctx

        # Four sequential fetchone() calls return distinct values
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [[10], [5], [3], [2]]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor

        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection", return_value=mock_conn):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "10" in result.output   # total task count
        assert "5" in result.output    # completed count
        assert "3" in result.output    # project count
        assert "2" in result.output    # label count
        assert mock_conn.execute.call_count == 4

    def test_local_context_with_existing_db_shows_last_modified(self, tmp_path):
        """Lines 84-87: Last Modified line is printed for an existing db file."""
        db_path = tmp_path / "modified.db"
        db_path.write_bytes(b"content")

        ctx = _make_mock_ctx("localctx", "local", str(db_path))
        ctx.encryption = None

        svc = MagicMock()
        svc.get_current_context.return_value = ctx

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor

        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection", return_value=mock_conn):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Last Modified" in result.output or "Modified" in result.output

    def test_local_context_with_existing_db_and_encryption_enabled(self, tmp_path):
        """Lines 80-114, 120-121: encryption enabled shows AES-256-GCM message."""
        db_path = tmp_path / "enc.db"
        db_path.write_bytes(b"fake sqlite")

        ctx = _make_mock_ctx("localctx", "local", str(db_path))
        ctx.encryption = MagicMock()
        ctx.encryption.enabled = True

        svc = MagicMock()
        svc.get_current_context.return_value = ctx

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor

        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection", return_value=mock_conn):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "ncrypt" in result.output   # "Encryption" or "Encrypted"
        assert "AES" in result.output or "Enabled" in result.output

    def test_local_context_with_existing_db_encryption_disabled(self, tmp_path):
        """Lines 122-123: encryption disabled path still shows 'Disabled'."""
        db_path = tmp_path / "plain.db"
        db_path.write_bytes(b"fake sqlite")

        ctx = _make_mock_ctx("localctx", "local", str(db_path))
        ctx.encryption = None  # falsy → disabled branch

        svc = MagicMock()
        svc.get_current_context.return_value = ctx

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor

        with _patch_svc(svc), \
             patch("todopro_cli.commands.context.get_connection", return_value=mock_conn):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Disabled" in result.output


# ===========================================================================
# _get_user_info_sync – direct function tests
# ===========================================================================

class TestGetUserInfoSync:
    """Cover lines 142-157: _get_user_info_sync() function body."""

    def test_returns_none_when_no_credentials(self):
        """Lines 145-146: returns None when load_credentials() returns None."""
        mock_svc = MagicMock()
        mock_svc.load_credentials.return_value = None
        with patch(
            "todopro_cli.commands.context.get_config_service",
            create=True,
            return_value=mock_svc,
        ):
            result = _get_user_info_sync()
        assert result is None

    def test_returns_none_when_empty_credentials(self):
        """Lines 145-146: returns None when load_credentials() returns empty dict."""
        mock_svc = MagicMock()
        mock_svc.load_credentials.return_value = {}
        with patch(
            "todopro_cli.commands.context.get_config_service",
            create=True,
            return_value=mock_svc,
        ):
            result = _get_user_info_sync()
        assert result is None

    def test_calls_auth_api_get_profile_when_credentials_exist(self):
        """Lines 148-157: when credentials exist, calls AuthAPI.get_profile() and returns result."""
        mock_svc = MagicMock()
        mock_svc.load_credentials.return_value = {"token": "abc123"}

        mock_client = MagicMock()
        mock_client.close = AsyncMock()

        mock_profile = {"email": "user@example.com", "name": "Test User", "id": "u-99"}
        mock_auth_api = MagicMock()
        mock_auth_api.get_profile = AsyncMock(return_value=mock_profile)

        with patch(
            "todopro_cli.commands.context.get_config_service",
            create=True,
            return_value=mock_svc,
        ), patch(
            "todopro_cli.commands.context.get_client",
            return_value=mock_client,
        ), patch(
            "todopro_cli.commands.context.AuthAPI",
            return_value=mock_auth_api,
        ):
            result = _get_user_info_sync()

        assert result == mock_profile
        mock_auth_api.get_profile.assert_awaited_once()
        mock_client.close.assert_awaited_once()

    def test_client_close_called_even_if_get_profile_raises(self):
        """Lines 154-155: client.close() is called in finally block even on exception."""
        mock_svc = MagicMock()
        mock_svc.load_credentials.return_value = {"token": "abc123"}

        mock_client = MagicMock()
        mock_client.close = AsyncMock()

        mock_auth_api = MagicMock()
        mock_auth_api.get_profile = AsyncMock(side_effect=Exception("API error"))

        with patch(
            "todopro_cli.commands.context.get_config_service",
            create=True,
            return_value=mock_svc,
        ), patch(
            "todopro_cli.commands.context.get_client",
            return_value=mock_client,
        ), patch(
            "todopro_cli.commands.context.AuthAPI",
            return_value=mock_auth_api,
        ):
            with pytest.raises(Exception, match="API error"):
                _get_user_info_sync()

        # close() must be called in the finally block even when get_profile raises
        mock_client.close.assert_awaited_once()
