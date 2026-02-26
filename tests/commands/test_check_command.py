"""Unit tests for the 'check' sub-commands.

Covers check achievements and check location, including:
- Happy-path output for both sub-commands
- Output format flags (--output json/table/yaml)
- Empty results
- Service returning None (location)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.check_command import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fake domain objects
# ---------------------------------------------------------------------------


def _make_achievement(id_: str = "ach-1", name: str = "First Step"):
    """Build a lightweight achievement-like mock with model_dump()."""
    ach = MagicMock()
    ach.model_dump.return_value = {"id": id_, "name": name, "description": "desc"}
    return ach


def _make_location(name: str = "@home"):
    """Build a lightweight location-context-like mock with model_dump()."""
    loc = MagicMock()
    loc.model_dump.return_value = {"id": "loc-1", "name": name}
    return loc


# ---------------------------------------------------------------------------
# check achievements
# ---------------------------------------------------------------------------


class TestCheckAchievements:
    """Tests for 'check achievements' sub-command."""

    def _run(self, args=None, achievements=None):
        if achievements is None:
            achievements = [_make_achievement()]
        svc = MagicMock()
        svc.check_achievements = AsyncMock(return_value=achievements)

        # The service is imported lazily inside the function body, so we must
        # patch the source module rather than the check_command namespace.
        with patch(
            "todopro_cli.services.achievement_service.get_achievement_service",
            return_value=svc,
        ):
            return runner.invoke(
                app, ["achievements"] + (args or []), catch_exceptions=False
            )

    def test_exits_zero_with_achievements(self):
        """Achievement check exits 0 when service returns results."""
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_shows_achievement_data(self):
        """Output contains achievement data from service."""
        result = self._run(achievements=[_make_achievement(name="Superstar")])
        assert "Superstar" in result.output

    def test_empty_achievements(self):
        """Empty list from service still exits 0."""
        result = self._run(achievements=[])
        assert result.exit_code == 0

    def test_json_output_flag(self):
        """--output json flag is accepted."""
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_table_output_flag(self):
        """--output table (default) flag is accepted."""
        result = self._run(args=["--output", "table"])
        assert result.exit_code == 0

    def test_multiple_achievements(self):
        """Multiple achievements are all included in output."""
        result = self._run(
            achievements=[
                _make_achievement("a1", "Alpha"),
                _make_achievement("a2", "Beta"),
            ]
        )
        assert result.exit_code == 0
        assert "Alpha" in result.output
        assert "Beta" in result.output

    def test_service_called_once(self):
        """check_achievements is awaited exactly once."""
        svc = MagicMock()
        svc.check_achievements = AsyncMock(return_value=[])
        with patch(
            "todopro_cli.services.achievement_service.get_achievement_service",
            return_value=svc,
        ):
            runner.invoke(app, ["achievements"], catch_exceptions=False)
        svc.check_achievements.assert_awaited_once()

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["achievements", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# check location
# ---------------------------------------------------------------------------


class TestCheckLocation:
    """Tests for 'check location' sub-command."""

    def _run(self, args=None, location=None, return_none=False):
        if return_none:
            loc_return = None
        else:
            loc_return = location or _make_location()

        svc = MagicMock()
        svc.check_current_location = AsyncMock(return_value=loc_return)

        # Lazy import inside function body → patch source module
        with patch(
            "todopro_cli.services.location_context_service.get_location_context_service",
            return_value=svc,
        ):
            return runner.invoke(
                app, ["location"] + (args or []), catch_exceptions=False
            )

    def test_exits_zero_with_location(self):
        """Location check exits 0 when service returns a location."""
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_shows_location_name(self):
        """Output contains the location name."""
        result = self._run(location=_make_location("@office"))
        assert "@office" in result.output

    def test_none_location_exits_zero(self):
        """When service returns None, command exits 0 gracefully."""
        result = self._run(return_none=True)
        assert result.exit_code == 0

    def test_none_location_shows_unknown(self):
        """When service returns None, output contains 'Unknown'."""
        result = self._run(return_none=True)
        assert "Unknown" in result.output

    def test_json_output_flag(self):
        """--output json flag is accepted."""
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_service_called_once(self):
        """check_current_location is awaited exactly once."""
        svc = MagicMock()
        svc.check_current_location = AsyncMock(return_value=_make_location())
        with patch(
            "todopro_cli.services.location_context_service.get_location_context_service",
            return_value=svc,
        ):
            runner.invoke(app, ["location"], catch_exceptions=False)
        svc.check_current_location.assert_awaited_once()

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["location", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Top-level help
# ---------------------------------------------------------------------------


class TestCheckTopLevel:
    """Smoke tests for the top-level check app."""

    def test_top_level_help(self):
        """Top-level --help exits 0 and lists sub-commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "achievements" in result.output
        assert "location" in result.output
