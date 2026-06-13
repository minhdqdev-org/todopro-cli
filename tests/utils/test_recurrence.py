"""Unit tests for recurrence utilities."""

from __future__ import annotations

from todopro_cli.utils.recurrence import (
    VALID_PATTERNS,
    describe_rrule,
    resolve_rrule,
)


class TestResolveRrule:
    def test_daily(self):
        assert resolve_rrule("daily") == "FREQ=DAILY;INTERVAL=1"

    def test_weekdays(self):
        assert resolve_rrule("weekdays") == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"

    def test_weekly(self):
        assert resolve_rrule("weekly") == "FREQ=WEEKLY;INTERVAL=1"

    def test_bi_weekly(self):
        assert resolve_rrule("bi-weekly") == "FREQ=WEEKLY;INTERVAL=2"

    def test_monthly(self):
        assert resolve_rrule("monthly") == "FREQ=MONTHLY;INTERVAL=1"

    def test_case_insensitive(self):
        assert resolve_rrule("DAILY") == "FREQ=DAILY;INTERVAL=1"
        assert resolve_rrule("Weekly") == "FREQ=WEEKLY;INTERVAL=1"

    def test_unknown_returns_none(self):
        assert resolve_rrule("hourly") is None
        assert resolve_rrule("yearly") is None
        assert resolve_rrule("") is None


class TestDescribeRrule:
    def test_known_rrule(self):
        # Canonical CLI form (explicit INTERVAL).
        assert describe_rrule("FREQ=DAILY;INTERVAL=1") == "daily"
        assert describe_rrule("FREQ=WEEKLY;INTERVAL=1") == "weekly"
        assert describe_rrule("FREQ=MONTHLY;INTERVAL=1") == "monthly"
        assert describe_rrule("FREQ=WEEKLY;INTERVAL=2") == "bi-weekly"
        assert describe_rrule("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR") == "weekdays"

    def test_backend_legacy_short_form(self):
        """Short-form RRULEs from the backend still describe correctly."""
        assert describe_rrule("FREQ=DAILY") == "daily"
        assert describe_rrule("FREQ=WEEKLY") == "weekly"
        assert describe_rrule("FREQ=MONTHLY") == "monthly"

    def test_unknown_rrule_returns_rrule_itself(self):
        """Unknown RRULE strings are returned as-is."""
        unknown = "FREQ=HOURLY;INTERVAL=2"
        assert describe_rrule(unknown) == unknown

    def test_empty_rrule_returns_empty(self):
        """Empty string is not in the map and returned as-is."""
        assert describe_rrule("") == ""

    def test_roundtrip(self):
        """resolve_rrule then describe_rrule should give back original name."""
        for name in VALID_PATTERNS:
            rrule = resolve_rrule(name)
            assert rrule is not None
            assert describe_rrule(rrule) == name


class TestValidPatterns:
    def test_all_patterns_present(self):
        expected = {"daily", "weekdays", "weekly", "bi-weekly", "monthly"}
        assert set(VALID_PATTERNS) == expected

    def test_valid_patterns_is_list(self):
        assert isinstance(VALID_PATTERNS, list)
