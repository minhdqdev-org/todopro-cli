"""Tests for the server-backed `goals` / `achievements` rendering.

Replaces `test_goal_service.py`, which only exercised the misspelled
`GoldService` stub (deleted — it re-saved the config and touched no goal).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from todopro_cli.commands import remote_goals


def _returns(value):
    """Stand in for `_run`, closing the coroutine it was handed.

    Patching `_run` with a plain return_value leaves the un-awaited coroutine
    to be garbage collected, which pytest surfaces as a RuntimeWarning.
    """

    def fake_run(coro):
        coro.close()
        return value

    return fake_run


def _context(kind: str):
    config_service = MagicMock()
    config_service.config.get_current_context.return_value = MagicMock(type=kind)
    return config_service


class TestIsRemoteContext:
    def test_local_context_is_not_remote(self):
        with patch.object(
            remote_goals, "get_config_service", return_value=_context("local")
        ):
            assert remote_goals.is_remote_context() is False

    def test_remote_context_is_remote(self):
        with patch.object(
            remote_goals, "get_config_service", return_value=_context("remote")
        ):
            assert remote_goals.is_remote_context() is True

    def test_missing_context_falls_back_to_local(self):
        config_service = MagicMock()
        config_service.config.get_current_context.side_effect = ValueError
        with patch.object(
            remote_goals, "get_config_service", return_value=config_service
        ):
            assert remote_goals.is_remote_context() is False


class TestRenderProgressBar:
    def test_full_and_empty(self):
        assert remote_goals.render_progress_bar(10, 10, width=4) == "████"
        assert remote_goals.render_progress_bar(0, 10, width=4) == "░░░░"

    def test_zero_max_does_not_divide_by_zero(self):
        assert remote_goals.render_progress_bar(5, 0, width=4) == "░░░░"

    def test_overshoot_is_clamped(self):
        assert remote_goals.render_progress_bar(99, 10, width=4) == "████"


class TestShowRemoteGoals:
    def test_renders_progress(self, capsys):
        payload = {
            "goals": [
                {
                    "period": "daily",
                    "achieved_value": 3,
                    "target_value": 5,
                    "percent": 60,
                    "is_met": False,
                    "period_start": "2026-07-20",
                    "period_end": "2026-07-20",
                }
            ]
        }
        with patch.object(remote_goals, "_run", side_effect=_returns(payload)):
            remote_goals.show_remote_goals()
        out = capsys.readouterr().out
        assert "3/5" in out
        assert "60%" in out

    def test_empty_prompts_the_user_to_set_one(self, capsys):
        with patch.object(remote_goals, "_run", side_effect=_returns({"goals": []})):
            remote_goals.show_remote_goals()
        assert "No goals set" in capsys.readouterr().out


class TestSetRemoteGoal:
    def test_rejects_an_unknown_period(self, capsys):
        with patch.object(remote_goals, "_run", side_effect=_returns([])):
            try:
                remote_goals.set_remote_goal("fortnightly", 5)
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("expected SystemExit")
        assert "unknown period" in capsys.readouterr().out

    def test_creates_when_no_active_goal_exists(self, capsys):
        calls = []

        def fake_run(coro):
            coro.close()
            calls.append(1)
            return [] if len(calls) == 1 else {}

        with patch.object(remote_goals, "_run", side_effect=fake_run):
            remote_goals.set_remote_goal("daily", 5)
        assert "set to 5 tasks" in capsys.readouterr().out

    def test_updates_when_one_already_exists(self, capsys):
        existing = [{"id": "abc", "period": "daily", "is_active": True}]
        calls = []

        def fake_run(coro):
            coro.close()
            calls.append(1)
            return existing if len(calls) == 1 else {}

        with patch.object(remote_goals, "_run", side_effect=fake_run):
            remote_goals.set_remote_goal("daily", 9)
        assert "updated to 9 tasks" in capsys.readouterr().out


class TestShowRemoteAchievements:
    def test_earned_are_rendered(self, capsys):
        payload = {
            "achievements": [
                {
                    "code": "first-task",
                    "name": "First Steps",
                    "description": "Complete your first task.",
                    "points": 5,
                    "earned": True,
                    "earned_at": "2026-07-20T10:00:00+00:00",
                }
            ],
            "earned_count": 1,
            "total_count": 2,
            "points": 5,
        }
        with patch.object(remote_goals, "_run", side_effect=_returns(payload)):
            remote_goals.show_remote_achievements()
        out = capsys.readouterr().out
        assert "First Steps" in out
        assert "1/2" in out

    def test_nothing_earned_hints_at_all_flag(self, capsys):
        payload = {"achievements": [], "earned_count": 0, "total_count": 0}
        with patch.object(remote_goals, "_run", side_effect=_returns(payload)):
            remote_goals.show_remote_achievements()
        assert "--all" in capsys.readouterr().out

    def test_all_flag_lists_locked(self, capsys):
        payload = {
            "achievements": [
                {
                    "code": "centurion",
                    "name": "Centurion",
                    "description": "Complete 100 tasks.",
                    "points": 25,
                    "earned": False,
                    "earned_at": None,
                }
            ],
            "earned_count": 0,
            "total_count": 1,
            "points": 0,
        }
        with patch.object(remote_goals, "_run", side_effect=_returns(payload)):
            remote_goals.show_remote_achievements(show_all=True)
        out = capsys.readouterr().out
        assert "Centurion" in out
        assert "Locked" in out
