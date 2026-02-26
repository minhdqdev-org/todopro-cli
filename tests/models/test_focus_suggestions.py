"""Comprehensive unit tests for todopro_cli.models.focus.suggestions.TaskSuggestionEngine.

Strategy
--------
* ``FocusAnalytics`` is patched so that no real SQLite database is opened on
  engine construction.
* ``_was_recently_worked_on`` is patched to ``return False`` in most tests so
  that scoring logic is exercised without filesystem access.
* For dedicated ``_was_recently_worked_on`` tests, both ``HistoryLogger`` and
  ``sqlite3.connect`` are mocked to control DB query results.
* ``_get_time_estimate_score`` depends on the current hour; ``datetime.now``
  is patched to exercise morning / afternoon / evening branches.
"""

from __future__ import annotations

from datetime import datetime as _real_datetime
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.models.config_models import AppConfig
from todopro_cli.models.focus.suggestions import TaskSuggestionEngine


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_SUGGESTIONS_MODULE = "todopro_cli.models.focus.suggestions"


def _task(
    task_id: str = "t1",
    priority: int = 2,
    due_date: str | None = None,
    estimated_minutes: int = 25,
    labels: list[str] | None = None,
) -> dict:
    """Build a minimal task dict for tests."""
    t: dict = {
        "id": task_id,
        "priority": priority,
        "estimated_minutes": estimated_minutes,
    }
    if due_date is not None:
        t["due_date"] = due_date
    if labels is not None:
        t["labels"] = labels
    return t


def _make_engine(config: AppConfig | None = None) -> TaskSuggestionEngine:
    return TaskSuggestionEngine(config=config or AppConfig())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_analytics(mocker):
    """Prevent FocusAnalytics (and therefore HistoryLogger) from opening a DB."""
    mock_cls = mocker.patch(f"{_SUGGESTIONS_MODULE}.FocusAnalytics")
    return mock_cls.return_value


@pytest.fixture()
def engine(mock_analytics) -> TaskSuggestionEngine:
    """TaskSuggestionEngine with DB access fully mocked out."""
    return _make_engine()


@pytest.fixture()
def no_recent_work(mocker):
    """Patch _was_recently_worked_on to always return False."""
    return mocker.patch.object(
        TaskSuggestionEngine, "_was_recently_worked_on", return_value=False
    )


# ---------------------------------------------------------------------------
# Tests: _get_priority_score
# ---------------------------------------------------------------------------


class TestGetPriorityScore:
    """Verify the priority → score conversion (4 - priority)."""

    @pytest.mark.parametrize(
        "priority, expected_score",
        [
            (1, 3),  # highest priority → highest score
            (2, 2),  # medium priority → medium score
            (3, 1),  # lowest priority → lowest score
        ],
    )
    def test_priority_to_score(self, engine, priority, expected_score):
        task = _task(priority=priority)
        assert engine._get_priority_score(task) == expected_score

    def test_missing_priority_defaults_to_three(self, engine):
        """Tasks without a priority key default to priority=3 → score=1."""
        task = {"id": "x"}
        assert engine._get_priority_score(task) == 1


# ---------------------------------------------------------------------------
# Tests: _get_due_date_score
# ---------------------------------------------------------------------------


class TestGetDueDateScore:
    """Verify due-date urgency scoring for all branches."""

    def test_no_due_date_returns_zero(self, engine):
        assert engine._get_due_date_score({"id": "x"}) == 0.0

    def test_overdue_returns_ten(self, engine):
        yesterday = (_real_datetime.now() - timedelta(days=1)).date().isoformat()
        assert engine._get_due_date_score(_task(due_date=yesterday)) == 10.0

    def test_due_today_returns_eight(self, engine):
        # Use a datetime 12 hours from now so (due_date - now).days == 0
        due_dt = (_real_datetime.now() + timedelta(hours=12)).isoformat()
        assert engine._get_due_date_score(_task(due_date=due_dt)) == 8.0

    def test_due_tomorrow_returns_six(self, engine):
        # Use a datetime 36 hours from now so (due_date - now).days == 1
        due_dt = (_real_datetime.now() + timedelta(hours=36)).isoformat()
        assert engine._get_due_date_score(_task(due_date=due_dt)) == 6.0

    def test_due_in_three_days_returns_four(self, engine):
        in_3 = (_real_datetime.now() + timedelta(days=3)).date().isoformat()
        assert engine._get_due_date_score(_task(due_date=in_3)) == 4.0

    def test_due_in_seven_days_returns_two(self, engine):
        in_7 = (_real_datetime.now() + timedelta(days=7)).date().isoformat()
        assert engine._get_due_date_score(_task(due_date=in_7)) == 2.0

    def test_due_in_ten_days_returns_one(self, engine):
        in_10 = (_real_datetime.now() + timedelta(days=10)).date().isoformat()
        assert engine._get_due_date_score(_task(due_date=in_10)) == 1.0

    def test_invalid_due_date_string_returns_zero(self, engine):
        assert engine._get_due_date_score(_task(due_date="not-a-date")) == 0.0

    def test_none_due_date_value_returns_zero(self, engine):
        task = {"id": "x", "due_date": None}
        assert engine._get_due_date_score(task) == 0.0

    def test_timezone_aware_due_date_handled(self, engine):
        """ISO timestamp with timezone suffix should not raise an exception."""
        future = (_real_datetime.now() + timedelta(days=2)).isoformat() + "+00:00"
        score = engine._get_due_date_score(_task(due_date=future))
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# Tests: _get_eisenhower_score
# ---------------------------------------------------------------------------


class TestGetEisenhowerScore:
    """Verify the Eisenhower matrix quadrant scoring."""

    def test_important_and_urgent_returns_four(self, engine):
        """Priority ≤ 2 AND due date score ≥ 4 → 'Do first'."""
        today = _real_datetime.now().date().isoformat()
        task = _task(priority=1, due_date=today)
        assert engine._get_eisenhower_score(task) == 4.0

    def test_important_not_urgent_returns_three(self, engine):
        """Priority ≤ 2 AND far due date → 'Schedule'."""
        far = (_real_datetime.now() + timedelta(days=30)).date().isoformat()
        task = _task(priority=1, due_date=far)
        assert engine._get_eisenhower_score(task) == 3.0

    def test_not_important_urgent_returns_two(self, engine):
        """Priority 3 AND due date score ≥ 4 → 'Delegate'."""
        today = _real_datetime.now().date().isoformat()
        task = _task(priority=3, due_date=today)
        assert engine._get_eisenhower_score(task) == 2.0

    def test_not_important_not_urgent_returns_one(self, engine):
        """Priority 3 AND no due date → 'Eliminate'."""
        task = _task(priority=3)
        assert engine._get_eisenhower_score(task) == 1.0

    def test_priority_two_is_important(self, engine):
        """Priority 2 counts as important (≤ 2)."""
        task = _task(priority=2)
        score = engine._get_eisenhower_score(task)
        # No due date so not urgent → schedule (3.0)
        assert score == 3.0

    def test_priority_three_is_not_important(self, engine):
        """Priority 3 is NOT important."""
        task = _task(priority=3)
        score = engine._get_eisenhower_score(task)
        # Not important, no due date → 1.0
        assert score == 1.0


# ---------------------------------------------------------------------------
# Tests: _get_time_estimate_score
# ---------------------------------------------------------------------------


class TestGetTimeEstimateScore:
    """Verify time-of-day preferences for task duration."""

    def _with_hour(self, mocker, hour: int):
        """Patch datetime.now() to return a specific hour."""
        mock_dt = mocker.MagicMock(wraps=_real_datetime)
        mock_dt.now.return_value = _real_datetime(2024, 1, 15, hour, 0, 0)
        mocker.patch(f"{_SUGGESTIONS_MODULE}.datetime", mock_dt)

    # ── Morning (6–11) ────────────────────────────────────────────────────

    def test_morning_preferred_range_45_to_90_returns_two(self, engine, mocker):
        self._with_hour(mocker, 9)
        assert engine._get_time_estimate_score(_task(estimated_minutes=60)) == 2.0

    def test_morning_longer_than_90_returns_1_5(self, engine, mocker):
        self._with_hour(mocker, 8)
        assert engine._get_time_estimate_score(_task(estimated_minutes=120)) == 1.5

    def test_morning_short_task_returns_1_0(self, engine, mocker):
        self._with_hour(mocker, 7)
        assert engine._get_time_estimate_score(_task(estimated_minutes=20)) == 1.0

    def test_morning_exactly_45_minutes_returns_two(self, engine, mocker):
        self._with_hour(mocker, 10)
        assert engine._get_time_estimate_score(_task(estimated_minutes=45)) == 2.0

    def test_morning_exactly_90_minutes_returns_two(self, engine, mocker):
        self._with_hour(mocker, 6)
        assert engine._get_time_estimate_score(_task(estimated_minutes=90)) == 2.0

    # ── Afternoon (12–17) ─────────────────────────────────────────────────

    def test_afternoon_preferred_range_25_to_45_returns_two(self, engine, mocker):
        self._with_hour(mocker, 14)
        assert engine._get_time_estimate_score(_task(estimated_minutes=35)) == 2.0

    def test_afternoon_outside_preferred_returns_1_0(self, engine, mocker):
        self._with_hour(mocker, 13)
        assert engine._get_time_estimate_score(_task(estimated_minutes=90)) == 1.0

    def test_afternoon_exactly_25_minutes_returns_two(self, engine, mocker):
        self._with_hour(mocker, 15)
        assert engine._get_time_estimate_score(_task(estimated_minutes=25)) == 2.0

    def test_afternoon_exactly_45_minutes_returns_two(self, engine, mocker):
        self._with_hour(mocker, 16)
        assert engine._get_time_estimate_score(_task(estimated_minutes=45)) == 2.0

    # ── Evening (18–23 and 0–5) ───────────────────────────────────────────

    def test_evening_preferred_range_15_to_25_returns_two(self, engine, mocker):
        self._with_hour(mocker, 20)
        assert engine._get_time_estimate_score(_task(estimated_minutes=20)) == 2.0

    def test_evening_outside_preferred_returns_1_0(self, engine, mocker):
        self._with_hour(mocker, 22)
        assert engine._get_time_estimate_score(_task(estimated_minutes=60)) == 1.0

    def test_evening_exactly_15_minutes_returns_two(self, engine, mocker):
        self._with_hour(mocker, 19)
        assert engine._get_time_estimate_score(_task(estimated_minutes=15)) == 2.0

    def test_evening_exactly_25_minutes_returns_two(self, engine, mocker):
        self._with_hour(mocker, 21)
        assert engine._get_time_estimate_score(_task(estimated_minutes=25)) == 2.0

    def test_missing_estimate_defaults_to_25(self, engine, mocker):
        """Default estimate (25 min) in afternoon → preferred range → score 2."""
        self._with_hour(mocker, 14)
        task = {"id": "x"}  # no estimated_minutes key
        assert engine._get_time_estimate_score(task) == 2.0


# ---------------------------------------------------------------------------
# Tests: _was_recently_worked_on
# ---------------------------------------------------------------------------


class TestWasRecentlyWorkedOn:
    """Tests for the _was_recently_worked_on helper."""

    def _make_mock_conn(self, mocker, count: int):
        """Build a mock sqlite3 connection that returns *count* from fetchone."""
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchone.return_value = (count,)
        mocker.patch(f"{_SUGGESTIONS_MODULE}.sqlite3.connect", return_value=mock_conn)
        return mock_conn

    def test_returns_true_when_session_found(self, engine, mocker):
        mock_logger = mocker.patch(f"{_SUGGESTIONS_MODULE}.HistoryLogger")
        mock_logger.return_value.db_path = ":memory:"
        self._make_mock_conn(mocker, count=1)
        assert engine._was_recently_worked_on("task-123") is True

    def test_returns_false_when_no_session_found(self, engine, mocker):
        mock_logger = mocker.patch(f"{_SUGGESTIONS_MODULE}.HistoryLogger")
        mock_logger.return_value.db_path = ":memory:"
        self._make_mock_conn(mocker, count=0)
        assert engine._was_recently_worked_on("task-xyz") is False

    def test_returns_false_when_fetchone_returns_none(self, engine, mocker):
        mock_logger = mocker.patch(f"{_SUGGESTIONS_MODULE}.HistoryLogger")
        mock_logger.return_value.db_path = ":memory:"
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchone.return_value = None
        mocker.patch(f"{_SUGGESTIONS_MODULE}.sqlite3.connect", return_value=mock_conn)
        assert engine._was_recently_worked_on("task-abc") is False

    def test_passes_task_id_to_query(self, engine, mocker):
        mock_logger = mocker.patch(f"{_SUGGESTIONS_MODULE}.HistoryLogger")
        mock_logger.return_value.db_path = ":memory:"
        mock_conn = self._make_mock_conn(mocker, count=0)
        engine._was_recently_worked_on("my-special-task")
        call_args = mock_conn.execute.call_args
        assert "my-special-task" in call_args[0][1]


# ---------------------------------------------------------------------------
# Tests: suggest_tasks
# ---------------------------------------------------------------------------


class TestSuggestTasks:
    """End-to-end tests for the suggest_tasks() method."""

    def test_empty_task_list_returns_empty(self, engine, no_recent_work):
        assert engine.suggest_tasks([]) == []

    def test_non_list_input_returns_empty(self, engine, no_recent_work):
        assert engine.suggest_tasks(None) == []  # type: ignore[arg-type]

    def test_returns_list(self, engine, no_recent_work):
        tasks = [_task("t1"), _task("t2")]
        result = engine.suggest_tasks(tasks)
        assert isinstance(result, list)

    def test_result_contains_task_score_and_components(self, engine, no_recent_work):
        tasks = [_task("t1")]
        result = engine.suggest_tasks(tasks)
        assert len(result) == 1
        entry = result[0]
        assert "task" in entry
        assert "score" in entry
        assert "components" in entry

    def test_components_have_all_scoring_keys(self, engine, no_recent_work):
        result = engine.suggest_tasks([_task("t1")])
        components = result[0]["components"]
        assert {"due_date", "priority", "eisenhower", "time_estimate"} == set(
            components.keys()
        )

    def test_respects_limit(self, engine, no_recent_work):
        tasks = [_task(f"t{i}") for i in range(10)]
        result = engine.suggest_tasks(tasks, limit=3)
        assert len(result) <= 3

    def test_default_limit_is_five(self, engine, no_recent_work):
        tasks = [_task(f"t{i}") for i in range(10)]
        result = engine.suggest_tasks(tasks)
        assert len(result) <= 5

    def test_sorted_by_score_descending(self, engine, no_recent_work):
        """Higher-priority / more-urgent tasks should appear first."""
        today = _real_datetime.now().date().isoformat()
        high_urgency = _task("urgent", priority=1, due_date=today)
        low_urgency = _task("easy", priority=3)
        result = engine.suggest_tasks([low_urgency, high_urgency], limit=2)
        assert result[0]["task"]["id"] == "urgent"

    def test_skips_recently_worked_on_tasks(self, engine, mocker):
        """Tasks that were worked on recently are excluded from suggestions."""
        mocker.patch.object(
            engine, "_was_recently_worked_on", return_value=True
        )
        tasks = [_task("t1"), _task("t2")]
        result = engine.suggest_tasks(tasks)
        assert result == []

    def test_skips_only_recent_tasks(self, engine, mocker):
        """Only tasks worked on recently are filtered; others are included."""
        def _recently_worked(task_id: str) -> bool:
            return task_id == "recent"

        mocker.patch.object(
            engine, "_was_recently_worked_on", side_effect=_recently_worked
        )
        tasks = [_task("recent"), _task("new")]
        result = engine.suggest_tasks(tasks, limit=5)
        assert len(result) == 1
        assert result[0]["task"]["id"] == "new"

    # ── Label filtering ───────────────────────────────────────────────────

    def test_label_filter_includes_matching_tasks(self, engine, no_recent_work):
        task_with_label = _task("t1", labels=["work", "focus"])
        task_no_label = _task("t2", labels=[])
        result = engine.suggest_tasks(
            [task_with_label, task_no_label], label="work"
        )
        ids = [r["task"]["id"] for r in result]
        assert "t1" in ids
        assert "t2" not in ids

    def test_label_filter_excludes_non_matching_tasks(self, engine, no_recent_work):
        task = _task("t1", labels=["personal"])
        result = engine.suggest_tasks([task], label="work")
        assert result == []

    def test_label_filter_none_returns_all_tasks(self, engine, no_recent_work):
        tasks = [_task("t1", labels=["a"]), _task("t2", labels=["b"])]
        result = engine.suggest_tasks(tasks, label=None)
        assert len(result) == 2

    def test_label_filter_on_task_with_no_labels_key(self, engine, no_recent_work):
        """Tasks missing 'labels' key should be excluded when a label filter is set."""
        task = {"id": "t1", "priority": 1}  # no 'labels' key
        result = engine.suggest_tasks([task], label="work")
        assert result == []

    # ── Custom weights ─────────────────────────────────────────────────────

    def test_custom_weights_from_config(self, no_recent_work):
        """Overriding weights in focus_suggestions config is respected."""
        config = AppConfig()
        config.focus_suggestions = {
            "weight_due_date": 0.5,
            "weight_priority": 0.3,
            "weight_eisenhower": 0.1,
            "weight_time_estimate": 0.1,
        }
        engine = _make_engine(config=config)
        today = _real_datetime.now().date().isoformat()
        task = _task("t1", priority=1, due_date=today)
        result = engine.suggest_tasks([task])
        assert len(result) == 1
        score = result[0]["score"]
        # due_score=8.0*0.5 + priority=3*0.3 + eisenhower=4.0*0.1 + time*0.1
        assert score > 0

    def test_default_weights_when_config_is_none(self, engine, no_recent_work):
        """When focus_suggestions is None, default weights are used without error."""
        engine.config.focus_suggestions = None
        task = _task("t1")
        result = engine.suggest_tasks([task])
        assert len(result) == 1

    # ── Score boundary checks ─────────────────────────────────────────────

    def test_score_is_positive_for_overdue_high_priority_task(
        self, engine, no_recent_work
    ):
        yesterday = (_real_datetime.now() - timedelta(days=1)).date().isoformat()
        task = _task("urgent", priority=1, due_date=yesterday)
        result = engine.suggest_tasks([task])
        assert result[0]["score"] > 0

    def test_score_is_float(self, engine, no_recent_work):
        result = engine.suggest_tasks([_task("t1")])
        assert isinstance(result[0]["score"], float)

    def test_task_reference_in_result_matches_input(self, engine, no_recent_work):
        original = _task("original-id")
        result = engine.suggest_tasks([original])
        assert result[0]["task"] is original

    def test_single_task_always_returned_if_not_recent(self, engine, no_recent_work):
        result = engine.suggest_tasks([_task("solo")])
        assert len(result) == 1

    def test_all_tasks_same_score_returns_limit(self, engine, no_recent_work):
        """When tasks have the same score the limit is still respected."""
        tasks = [_task(f"t{i}") for i in range(10)]
        result = engine.suggest_tasks(tasks, limit=4)
        assert len(result) == 4
