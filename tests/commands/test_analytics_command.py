"""Unit tests for analytics commands (stats, streaks, export)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.analytics import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCORE_DATA = {
    "score": 75.0,
    "trend": 5.0,
    "breakdown": {
        "completion_count": 80.0,
        "completion_rate": 70.0,
        "on_time_rate": 65.0,
    },
}

_STATS_DATA = {
    "total_completed": 42,
    "completion_rate": 85.0,
    "on_time_rate": 70.0,
    "avg_completion_time_hours": 2.5,
}

_STREAKS_DATA = {
    "current_streak": 10,
    "longest_streak": 30,
}


def _patch_analytics(score=None, stats=None, streaks=None, export_data=b""):
    """Context manager that patches get_client and AnalyticsAPI together."""
    score = score if score is not None else _SCORE_DATA
    stats = stats if stats is not None else _STATS_DATA
    streaks = streaks if streaks is not None else _STREAKS_DATA

    mock_client = AsyncMock()
    mock_api = MagicMock()
    mock_api.get_productivity_score = AsyncMock(return_value=score)
    mock_api.get_completion_stats = AsyncMock(return_value=stats)
    mock_api.get_streaks = AsyncMock(return_value=streaks)
    mock_api.export_data = AsyncMock(return_value=export_data)

    p_client = patch("todopro_cli.commands.analytics.get_client", return_value=mock_client)
    p_api = patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api)
    return p_client, p_api, mock_client, mock_api


# ---------------------------------------------------------------------------
# Help flags
# ---------------------------------------------------------------------------


class TestHelpFlags:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "analytics" in result.output.lower() or "command" in result.output.lower()

    def test_stats_help(self):
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0

    def test_streaks_help(self):
        result = runner.invoke(app, ["streaks", "--help"])
        assert result.exit_code == 0

    def test_export_help(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# analytics stats
# ---------------------------------------------------------------------------


class TestAnalyticsStats:
    def test_stats_table_output(self):
        p_client, p_api, mock_client, mock_api = _patch_analytics()
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        mock_api.get_productivity_score.assert_awaited_once()
        mock_api.get_completion_stats.assert_awaited_once()
        mock_client.close.assert_awaited_once()

    def test_stats_json_output(self):
        p_client, p_api, mock_client, mock_api = _patch_analytics()
        with p_client, p_api:
            result = runner.invoke(app, ["stats", "--output", "json"])
        assert result.exit_code == 0
        import json
        # Output should contain valid JSON
        output = result.output
        data = json.loads(output)
        assert "productivity_score" in data
        assert "completion_stats" in data

    def test_stats_score_green_when_above_80(self):
        """Score >= 80 renders successfully (Rich markup stripped by CliRunner)."""
        high_score = {**_SCORE_DATA, "score": 90.0, "trend": 2.0}
        p_client, p_api, _, _ = _patch_analytics(score=high_score)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "90.0/100" in result.output

    def test_stats_score_blue_when_above_60(self):
        """Score in [60, 80) renders successfully."""
        mid_score = {**_SCORE_DATA, "score": 65.0, "trend": 0.0}
        p_client, p_api, _, _ = _patch_analytics(score=mid_score)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "65.0/100" in result.output

    def test_stats_score_yellow_when_above_40(self):
        """Score in [40, 60) renders successfully."""
        low_score = {**_SCORE_DATA, "score": 50.0, "trend": -1.0}
        p_client, p_api, _, _ = _patch_analytics(score=low_score)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "50.0/100" in result.output

    def test_stats_score_red_when_below_40(self):
        """Score < 40 renders successfully."""
        poor_score = {**_SCORE_DATA, "score": 20.0, "trend": -5.0}
        p_client, p_api, _, _ = _patch_analytics(score=poor_score)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "20.0/100" in result.output

    def test_stats_positive_trend_formatted(self):
        positive_trend = {**_SCORE_DATA, "trend": 3.5}
        p_client, p_api, _, _ = _patch_analytics(score=positive_trend)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "+3.5%" in result.output

    def test_stats_negative_trend_formatted(self):
        negative_trend = {**_SCORE_DATA, "trend": -2.0}
        p_client, p_api, _, _ = _patch_analytics(score=negative_trend)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "-2.0%" in result.output

    def test_stats_zero_trend_formatted(self):
        zero_trend = {**_SCORE_DATA, "trend": 0.0}
        p_client, p_api, _, _ = _patch_analytics(score=zero_trend)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0

    def test_stats_closes_client_on_api_error(self):
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.get_productivity_score = AsyncMock(side_effect=RuntimeError("API down"))
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                result = runner.invoke(app, ["stats"])
        mock_client.close.assert_awaited_once()

    def test_stats_empty_breakdown(self):
        score_no_breakdown = {"score": 50.0, "trend": 0.0, "breakdown": {}}
        p_client, p_api, _, _ = _patch_analytics(score=score_no_breakdown)
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0

    def test_stats_completion_rate_displayed(self):
        p_client, p_api, _, _ = _patch_analytics()
        with p_client, p_api:
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        # Should display completion rate and other stats
        assert "85.0%" in result.output or "85" in result.output


# ---------------------------------------------------------------------------
# analytics streaks
# ---------------------------------------------------------------------------


class TestAnalyticsStreaks:
    def test_streaks_table_output(self):
        p_client, p_api, mock_client, mock_api = _patch_analytics()
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        mock_api.get_streaks.assert_awaited_once()
        mock_client.close.assert_awaited_once()

    def test_streaks_json_output(self):
        p_client, p_api, _, _ = _patch_analytics()
        with p_client, p_api:
            result = runner.invoke(app, ["streaks", "--output", "json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "current_streak" in data

    def test_streaks_best_ever_message_shown(self):
        """current_streak == longest_streak triggers best-ever message."""
        data = {"current_streak": 15, "longest_streak": 15}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        assert "best streak" in result.output.lower()

    def test_streaks_great_consistency_message(self):
        """current >= 7 but < longest shows 'Great consistency'."""
        data = {"current_streak": 8, "longest_streak": 20}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        assert "consistency" in result.output.lower() or "great" in result.output.lower()

    def test_streaks_building_momentum_message(self):
        """current >= 3 but < 7 shows 'Building momentum'."""
        data = {"current_streak": 4, "longest_streak": 20}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        assert "momentum" in result.output.lower()

    def test_streaks_no_motivation_message_on_zero(self):
        """current == 0 shows no motivation message."""
        data = {"current_streak": 0, "longest_streak": 10}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        # No special message for zero streak
        assert "momentum" not in result.output.lower()
        assert "best streak" not in result.output.lower()

    def test_streaks_current_green_when_above_7(self):
        """Current streak >= 7 renders successfully."""
        data = {"current_streak": 10, "longest_streak": 30}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        assert "10 days" in result.output

    def test_streaks_current_yellow_when_above_3(self):
        """Current streak in [3, 7) renders successfully."""
        data = {"current_streak": 5, "longest_streak": 30}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        assert "5 days" in result.output

    def test_streaks_longest_blue_when_above_7(self):
        """Longest streak >= 7 renders successfully."""
        data = {"current_streak": 2, "longest_streak": 10}
        p_client, p_api, _, _ = _patch_analytics(streaks=data)
        with p_client, p_api:
            result = runner.invoke(app, ["streaks"])
        assert result.exit_code == 0
        assert "10 days" in result.output

    def test_streaks_closes_client_on_error(self):
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.get_streaks = AsyncMock(side_effect=RuntimeError("connection error"))
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                result = runner.invoke(app, ["streaks"])
        mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# analytics export
# ---------------------------------------------------------------------------


class TestAnalyticsExport:
    def test_export_invalid_format_exits_1(self):
        result = runner.invoke(app, ["export", "--format", "xml"])
        assert result.exit_code == 1

    def test_export_csv_with_output_path(self, tmp_path):
        out_file = str(tmp_path / "out.csv")
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.export_data = AsyncMock(return_value=b"col1,col2\nval1,val2")
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                result = runner.invoke(app, ["export", "--format", "csv", "--output", out_file])
        assert result.exit_code == 0
        mock_api.export_data.assert_awaited_once_with(format="csv")
        assert (tmp_path / "out.csv").exists()

    def test_export_json_with_output_path(self, tmp_path):
        out_file = str(tmp_path / "out.json")
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.export_data = AsyncMock(return_value=b'{"key": "value"}')
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                result = runner.invoke(app, ["export", "--format", "json", "--output", out_file])
        assert result.exit_code == 0
        assert (tmp_path / "out.json").read_bytes() == b'{"key": "value"}'

    def test_export_auto_generates_filename(self, tmp_path):
        """Without --output, a timestamped filename is used."""
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.export_data = AsyncMock(return_value=b"data")
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                # Change working dir so auto-generated file lands in tmp_path
                import os
                old_cwd = os.getcwd()
                os.chdir(tmp_path)
                try:
                    result = runner.invoke(app, ["export", "--format", "csv"])
                finally:
                    os.chdir(old_cwd)
        assert result.exit_code == 0
        csv_files = list(tmp_path.glob("todopro_analytics_*.csv"))
        assert len(csv_files) == 1

    def test_export_closes_client_on_error(self):
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.export_data = AsyncMock(side_effect=RuntimeError("server error"))
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                result = runner.invoke(app, ["export", "--format", "csv", "--output", "/tmp/x.csv"])
        mock_client.close.assert_awaited_once()

    def test_export_default_format_is_csv(self, tmp_path):
        """Default --format is csv."""
        out_file = str(tmp_path / "out.csv")
        mock_client = AsyncMock()
        mock_api = MagicMock()
        mock_api.export_data = AsyncMock(return_value=b"a,b")
        with patch("todopro_cli.commands.analytics.get_client", return_value=mock_client):
            with patch("todopro_cli.commands.analytics.AnalyticsAPI", return_value=mock_api):
                result = runner.invoke(app, ["export", "--output", out_file])
        assert result.exit_code == 0
        mock_api.export_data.assert_awaited_once_with(format="csv")
