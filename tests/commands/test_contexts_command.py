"""Unit tests for contexts.py (Manage task contexts @home, @office, @errands).

Uses direct APIClient (sync, not async get_client).
Patches: todopro_cli.commands.contexts.APIClient
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.contexts import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CONTEXTS = [
    {"id": "ctx-1", "name": "@home", "icon": "🏠", "task_count": 3, "latitude": None, "longitude": None, "radius": None},
    {"id": "ctx-2", "name": "@office", "icon": "🏢", "task_count": 7, "latitude": 51.5, "longitude": -0.1, "radius": 200, "is_available": True},
    {"id": "ctx-3", "name": "@errands", "icon": "🛒", "task_count": 1, "latitude": None, "longitude": None, "radius": None, "is_available": False},
]


def _make_client(**kwargs):
    client = MagicMock()
    for method, rv in kwargs.items():
        getattr(client, method).return_value = rv
    return client


def _patch_client(client):
    return patch("todopro_cli.commands.contexts.APIClient", return_value=client)


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

    def test_create_help(self):
        result = runner.invoke(app, ["create", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output.lower()

    def test_delete_help(self):
        result = runner.invoke(app, ["delete", "--help"])
        assert result.exit_code == 0
        assert "delete" in result.output.lower()

    def test_tasks_help(self):
        result = runner.invoke(app, ["tasks", "--help"])
        assert result.exit_code == 0
        assert "tasks" in result.output.lower() or "context" in result.output.lower()

    def test_check_help(self):
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output.lower() or "available" in result.output.lower()


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

class TestListContexts:
    def test_list_empty(self):
        client = _make_client(get=[])
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "no contexts" in result.output.lower() or "create" in result.output.lower()

    def test_list_shows_contexts(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "@home" in result.output
        assert "@office" in result.output

    def test_list_shows_task_counts(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "3" in result.output  # home task count
        assert "7" in result.output  # office task count

    def test_list_shows_geo_fence_radius(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "200m" in result.output

    def test_list_shows_available_marker(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "HERE" in result.output or "✓" in result.output

    def test_list_shows_unavailable_marker(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "✗" in result.output

    def test_list_shows_dash_for_no_geo(self):
        client = _make_client(get=[{"id": "ctx-1", "name": "@home", "icon": "🏠", "task_count": 0}])
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "—" in result.output

    def test_list_api_error_exits_nonzero(self):
        client = _make_client()
        client.get.side_effect = Exception("Connection refused")
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code != 0

    def test_list_non_list_response_shows_empty(self):
        client = _make_client(get={"error": "unexpected"})
        with _patch_client(client):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "no contexts" in result.output.lower() or "create" in result.output.lower()

    def test_list_location_flag_geocoder_import_error(self):
        """--location flag with missing geocoder shows a helpful message."""
        client = _make_client(get=[])
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": None}):
                result = runner.invoke(app, ["list", "--location"])
        assert result.exit_code == 0
        # Either geocoder not installed message or empty list
        assert "geocoder" in result.output.lower() or "no contexts" in result.output.lower()

    def test_list_location_flag_with_geocoder(self):
        """--location flag with working geocoder adds lat/lon params."""
        client = _make_client(get=SAMPLE_CONTEXTS)
        mock_geo = MagicMock()
        mock_geo.ok = True
        mock_geo.latlng = [51.5, -0.1]
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
                result = runner.invoke(app, ["list", "--location"])
        assert result.exit_code == 0
        assert "51." in result.output or "@home" in result.output


# ---------------------------------------------------------------------------
# create command
# ---------------------------------------------------------------------------

class TestCreateContext:
    def test_create_success(self):
        client = _make_client(post={"name": "@work", "icon": "💼"})
        with _patch_client(client):
            result = runner.invoke(app, ["create", "@work"])
        assert result.exit_code == 0
        assert "@work" in result.output
        assert "created" in result.output.lower() or "✓" in result.output

    def test_create_with_custom_icon(self):
        client = _make_client(post={"name": "@gym", "icon": "💪"})
        with _patch_client(client):
            result = runner.invoke(app, ["create", "@gym", "--icon", "💪"])
        assert result.exit_code == 0
        client.post.assert_called_once()
        call_data = client.post.call_args[0][1]
        assert call_data["icon"] == "💪"

    def test_create_with_custom_color(self):
        client = _make_client(post={"name": "@gym", "icon": "💪"})
        with _patch_client(client):
            result = runner.invoke(app, ["create", "@gym", "--color", "#FF0000"])
        assert result.exit_code == 0
        call_data = client.post.call_args[0][1]
        assert call_data["color"] == "#FF0000"

    def test_create_default_color(self):
        client = _make_client(post={"name": "@ctx", "icon": "📍"})
        with _patch_client(client):
            runner.invoke(app, ["create", "@ctx"])
        call_data = client.post.call_args[0][1]
        assert call_data["color"] == "#3498DB"

    def test_create_geo_geocoder_import_error(self):
        """--geo without geocoder package shows an error message."""
        with patch.dict("sys.modules", {"geocoder": None}):
            result = runner.invoke(app, ["create", "@loc", "--geo"])
        assert result.exit_code == 0
        assert "geocoder" in result.output.lower() or "install" in result.output.lower()

    def test_create_geo_location_failed(self):
        """--geo when geocoder can't detect location shows error."""
        mock_geo = MagicMock()
        mock_geo.ok = False
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
            result = runner.invoke(app, ["create", "@loc", "--geo"])
        assert result.exit_code == 0
        assert "could not" in result.output.lower() or "location" in result.output.lower()

    def test_create_geo_success(self):
        client = _make_client(post={"name": "@here", "icon": "📍"})
        mock_geo = MagicMock()
        mock_geo.ok = True
        mock_geo.latlng = [51.5, -0.1]
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
                result = runner.invoke(app, ["create", "@here", "--geo", "--radius", "100"])
        assert result.exit_code == 0
        call_data = client.post.call_args[0][1]
        assert call_data["radius"] == 100
        assert "latitude" in call_data

    def test_create_api_error(self):
        client = MagicMock()
        client.post.side_effect = Exception("403 Forbidden")
        with _patch_client(client):
            result = runner.invoke(app, ["create", "@bad"])
        assert result.exit_code != 0

    def test_create_posts_to_correct_endpoint(self):
        client = _make_client(post={"name": "@x", "icon": "📍"})
        with _patch_client(client):
            runner.invoke(app, ["create", "@x"])
        client.post.assert_called_once()
        endpoint = client.post.call_args[0][0]
        assert "/v1/contexts" in endpoint


# ---------------------------------------------------------------------------
# delete command
# ---------------------------------------------------------------------------

class TestDeleteContext:
    def test_delete_cancel_confirmation(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["delete", "@home"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower() or "cancel" in result.output.lower()

    def test_delete_not_found(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["delete", "@nonexistent", "--yes"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_delete_success_with_yes_flag(self):
        client = _make_client(get=SAMPLE_CONTEXTS, delete=None)
        with _patch_client(client):
            result = runner.invoke(app, ["delete", "@home", "--yes"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower() or "✓" in result.output

    def test_delete_calls_delete_endpoint(self):
        client = _make_client(get=SAMPLE_CONTEXTS, delete=None)
        with _patch_client(client):
            runner.invoke(app, ["delete", "@home", "--yes"])
        client.delete.assert_called_once()
        call_endpoint = client.delete.call_args[0][0]
        assert "ctx-1" in call_endpoint

    def test_delete_with_at_prefix_lookup(self):
        """Contexts can be found by name without '@' prefix."""
        client = _make_client(get=SAMPLE_CONTEXTS, delete=None)
        with _patch_client(client):
            result = runner.invoke(app, ["delete", "home", "--yes"])
        # @home has name "@home" so lookup with f"@{name}" = "@home" should work
        assert result.exit_code == 0

    def test_delete_api_error(self):
        client = MagicMock()
        client.get.side_effect = Exception("Connection error")
        with _patch_client(client):
            result = runner.invoke(app, ["delete", "@home", "--yes"])
        assert result.exit_code != 0

    def test_delete_confirm_prompt_shown(self):
        client = _make_client(get=SAMPLE_CONTEXTS, delete=None)
        with _patch_client(client):
            result = runner.invoke(app, ["delete", "@home"], input="y\n")
        # Should proceed and delete
        assert result.exit_code == 0
        assert "deleted" in result.output.lower() or "✓" in result.output


# ---------------------------------------------------------------------------
# tasks command
# ---------------------------------------------------------------------------

class TestContextTasks:
    SAMPLE_TASKS = [
        {"content": "Buy milk", "is_completed": False, "priority": 2},
        {"content": "Take out trash", "is_completed": True, "priority": 1},
    ]

    def test_tasks_context_not_found(self):
        client = _make_client(get=SAMPLE_CONTEXTS)
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@nonexistent"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_tasks_empty_list(self):
        client = MagicMock()
        client.get.side_effect = [SAMPLE_CONTEXTS, {"tasks": []}]
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@home"])
        assert result.exit_code == 0
        assert "no tasks" in result.output.lower()

    def test_tasks_shows_task_list(self):
        client = MagicMock()
        client.get.side_effect = [SAMPLE_CONTEXTS, {"tasks": self.SAMPLE_TASKS}]
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@home"])
        assert result.exit_code == 0
        assert "Buy milk" in result.output
        assert "Take out trash" in result.output

    def test_tasks_shows_completion_status(self):
        client = MagicMock()
        client.get.side_effect = [SAMPLE_CONTEXTS, {"tasks": self.SAMPLE_TASKS}]
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@home"])
        assert result.exit_code == 0
        assert "✓" in result.output  # completed marker
        assert "○" in result.output  # incomplete marker

    def test_tasks_shows_priority(self):
        client = MagicMock()
        client.get.side_effect = [SAMPLE_CONTEXTS, {"tasks": self.SAMPLE_TASKS}]
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@home"])
        assert result.exit_code == 0
        assert "P2" in result.output or "P1" in result.output

    def test_tasks_at_prefix_lookup(self):
        """Can look up context by name without '@'."""
        client = MagicMock()
        client.get.side_effect = [SAMPLE_CONTEXTS, {"tasks": self.SAMPLE_TASKS}]
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "home"])
        assert result.exit_code == 0

    def test_tasks_api_error(self):
        client = MagicMock()
        client.get.side_effect = Exception("API error")
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@home"])
        assert result.exit_code != 0

    def test_tasks_shows_context_name(self):
        client = MagicMock()
        client.get.side_effect = [SAMPLE_CONTEXTS, {"tasks": self.SAMPLE_TASKS}]
        with _patch_client(client):
            result = runner.invoke(app, ["tasks", "@home"])
        assert result.exit_code == 0
        assert "@home" in result.output


# ---------------------------------------------------------------------------
# check command
# ---------------------------------------------------------------------------

class TestCheckAvailable:
    def test_check_geocoder_import_error(self):
        with patch.dict("sys.modules", {"geocoder": None}):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "geocoder" in result.output.lower() or "install" in result.output.lower()

    def test_check_location_failed(self):
        mock_geo = MagicMock()
        mock_geo.ok = False
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "could not" in result.output.lower() or "location" in result.output.lower()

    def test_check_with_available_contexts(self):
        client = _make_client(post={
            "available": [{"icon": "🏠", "name": "@home"}],
            "unavailable": [{"icon": "🏢", "name": "@office"}],
        })
        mock_geo = MagicMock()
        mock_geo.ok = True
        mock_geo.latlng = [51.5, -0.1]
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
                result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "@home" in result.output
        assert "@office" in result.output

    def test_check_no_geofenced_contexts(self):
        client = _make_client(post={"available": [], "unavailable": []})
        mock_geo = MagicMock()
        mock_geo.ok = True
        mock_geo.latlng = [51.5, -0.1]
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
                result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "no" in result.output.lower() or "geo" in result.output.lower()

    def test_check_api_error(self):
        client = MagicMock()
        client.post.side_effect = Exception("server error")
        mock_geo = MagicMock()
        mock_geo.ok = True
        mock_geo.latlng = [51.5, -0.1]
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
                result = runner.invoke(app, ["check"])
        assert result.exit_code != 0

    def test_check_shows_location(self):
        client = _make_client(post={"available": [], "unavailable": []})
        mock_geo = MagicMock()
        mock_geo.ok = True
        mock_geo.latlng = [48.8566, 2.3522]
        mock_geocoder = MagicMock()
        mock_geocoder.ip.return_value = mock_geo
        with _patch_client(client):
            with patch.dict("sys.modules", {"geocoder": mock_geocoder}):
                result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "48." in result.output or "2." in result.output
