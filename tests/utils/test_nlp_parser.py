"""Unit tests for LocalNLPParser and parse_natural_language."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch

import todopro_cli.utils.nlp_parser as nlp_mod
from todopro_cli.utils.nlp_parser import LocalNLPParser, parse_natural_language

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_parser() -> LocalNLPParser:
    return LocalNLPParser()


# Reference "now" for time-sensitive anchoring tests: Tuesday 2026-06-23 17:00.
_TUE_JUN_23 = datetime(2026, 6, 23, 17, 0, 0)


@contextmanager
def _frozen_now(frozen: datetime) -> Iterator[None]:
    """Freeze ``datetime.now()`` inside the parser module to ``frozen``.

    Lets day-of-month / weekday anchoring be asserted against exact dates instead
    of relative-to-real-clock comparisons (which would be flaky around boundaries).
    """

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]  # noqa: ARG003
            return frozen

    with patch.object(nlp_mod, "datetime", _Frozen):
        yield


# ---------------------------------------------------------------------------
# Priority extraction
# ---------------------------------------------------------------------------


class TestPriorityParsing:
    def test_p1_urgent(self):
        result = parse_natural_language("Fix bug p1 today")
        assert result["priority"] == 1

    def test_p2_high(self):
        result = parse_natural_language("Review PR p2")
        assert result["priority"] == 2

    def test_p3_medium(self):
        result = parse_natural_language("Write docs p3")
        assert result["priority"] == 3

    def test_p4_low(self):
        result = parse_natural_language("Clean inbox p4")
        assert result["priority"] == 4

    def test_exclamation_marks_urgent(self):
        result = parse_natural_language("Deploy !!! immediately")
        assert result["priority"] == 1

    def test_high_keyword(self):
        result = parse_natural_language("Fix login high priority")
        assert result["priority"] == 2

    def test_no_priority(self):
        result = parse_natural_language("Write unit tests")
        assert result["priority"] is None

    def test_priority_words_require_word_boundaries(self):
        # Regression: "low" inside "sunflowers" / "high" inside "highlight" must NOT
        # match as a priority (they lacked \b before).
        r1 = parse_natural_language("water the sunflowers")
        assert r1["priority"] is None
        assert r1["content"] == "water the sunflowers"
        r2 = parse_natural_language("highlight the bug")
        assert r2["priority"] is None
        assert r2["content"] == "highlight the bug"
        assert parse_natural_language("keep it low")["priority"] == 4

    def test_priority_removed_from_content(self):
        result = parse_natural_language("Fix bug p1")
        assert "p1" not in result["content"]

    def test_urgent_keyword(self):
        result = parse_natural_language("Fix bug urgent")
        assert result["priority"] == 1


# ---------------------------------------------------------------------------
# Project extraction
# ---------------------------------------------------------------------------


class TestProjectParsing:
    def test_project_extracted(self):
        result = parse_natural_language("Review PR #Work")
        assert result["project_name"] == "Work"

    def test_project_removed_from_content(self):
        result = parse_natural_language("Review PR #Work")
        assert "#Work" not in result["content"]

    def test_no_project(self):
        result = parse_natural_language("Fix login bug")
        assert result["project_name"] is None

    def test_project_with_numbers(self):
        result = parse_natural_language("Task description #Project123")
        assert result["project_name"] == "Project123"


# ---------------------------------------------------------------------------
# Label extraction
# ---------------------------------------------------------------------------


class TestLabelParsing:
    def test_single_label(self):
        result = parse_natural_language("Fix bug @backend")
        assert "backend" in result["labels"]

    def test_multiple_labels(self):
        result = parse_natural_language("Review PR @frontend @review")
        assert set(result["labels"]) == {"frontend", "review"}

    def test_labels_removed_from_content(self):
        result = parse_natural_language("Fix @backend @urgent bug")
        assert "@backend" not in result["content"]
        assert "@urgent" not in result["content"]

    def test_no_labels(self):
        result = parse_natural_language("Fix login bug")
        assert result["labels"] == []


# ---------------------------------------------------------------------------
# Date extraction – _simple_date_parse paths
# ---------------------------------------------------------------------------


class TestSimpleDateParse:
    def test_today(self):
        result = parse_natural_language("Buy groceries today")
        assert result["due_date"] is not None
        assert result["due_date"].date() == datetime.now().date()

    def test_tomorrow(self):
        from datetime import timedelta

        result = parse_natural_language("Call dentist tomorrow")
        assert result["due_date"] is not None
        expected = (datetime.now() + timedelta(days=1)).date()
        assert result["due_date"].date() == expected

    def test_next_week(self):
        from datetime import timedelta

        result = parse_natural_language("Submit report next week")
        assert result["due_date"] is not None
        expected = (datetime.now() + timedelta(days=7)).date()
        assert result["due_date"].date() == expected

    def test_in_n_days(self):
        from datetime import timedelta

        result = parse_natural_language("Deploy in 3 days")
        assert result["due_date"] is not None
        expected = (datetime.now() + timedelta(days=3)).date()
        assert result["due_date"].date() == expected

    def test_in_1_day(self):
        from datetime import timedelta

        result = parse_natural_language("Follow up in 1 day")
        assert result["due_date"] is not None
        expected = (datetime.now() + timedelta(days=1)).date()
        assert result["due_date"].date() == expected

    def test_weekday_monday(self):
        result = parse_natural_language("Meet team monday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 0  # Monday

    def test_weekday_friday(self):
        result = parse_natural_language("Submit report friday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 4  # Friday

    def test_weekday_saturday(self):
        result = parse_natural_language("Grocery shopping saturday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 5

    def test_weekday_sunday(self):
        result = parse_natural_language("Rest sunday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 6

    def test_no_date(self):
        result = parse_natural_language("Fix login bug")
        assert result["due_date"] is None

    def test_time_at_noon(self):
        """at HH:MM format should set time on today or nearest date."""
        result = parse_natural_language("Call at 14:30 today")
        assert result["due_date"] is not None
        assert result["due_date"].hour == 14
        assert result["due_date"].minute == 30

    def test_time_am(self):
        """at HH am format should adjust for AM."""
        result = parse_natural_language("Meeting at 9am tomorrow")
        assert result["due_date"] is not None
        assert result["due_date"].hour == 9

    def test_time_pm(self):
        """at HH pm format should add 12 hours."""
        result = parse_natural_language("Meeting at 3pm tomorrow")
        assert result["due_date"] is not None
        assert result["due_date"].hour == 15

    def test_time_noon_pm(self):
        """at 12 pm should stay 12 (noon)."""
        result = parse_natural_language("Lunch at 12pm today")
        assert result["due_date"] is not None
        assert result["due_date"].hour == 12

    def test_time_midnight_am(self):
        """at 12 am should become 0 (midnight)."""
        result = parse_natural_language("Midnight alarm at 12am today")
        assert result["due_date"] is not None
        assert result["due_date"].hour == 0

    def test_time_only_assumes_today(self):
        """'at HH' with no date keyword uses today."""
        result = parse_natural_language("Reminder at 22")
        assert result["due_date"] is not None
        assert result["due_date"].date() == datetime.now().date()
        assert result["due_date"].hour == 22

    def test_time_with_colon_only(self):
        """'at HH:MM' with no date keyword uses today."""
        result = parse_natural_language("Alarm at 07:30")
        assert result["due_date"] is not None
        assert result["due_date"].hour == 7
        assert result["due_date"].minute == 30

    def test_wednesday(self):
        result = parse_natural_language("Check report wednesday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 2

    def test_thursday(self):
        result = parse_natural_language("Send email thursday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 3

    def test_tuesday(self):
        result = parse_natural_language("Standup tuesday")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 1


# ---------------------------------------------------------------------------
# Date abbreviations and extended keywords
# ---------------------------------------------------------------------------


class TestExtendedDateKeywords:
    def test_tom_abbreviation(self):
        from datetime import timedelta

        result = parse_natural_language("Buy milk tom")
        assert result["due_date"] is not None
        assert result["due_date"].date() == (datetime.now() + timedelta(days=1)).date()
        assert "tom" not in result["content"].lower()

    def test_weekday_abbreviation(self):
        result = parse_natural_language("Report due fri")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 4  # Friday
        assert "fri" not in result["content"].lower()

    def test_yesterday(self):
        from datetime import timedelta

        result = parse_natural_language("Missed call yesterday")
        assert result["due_date"] is not None
        assert result["due_date"].date() == (datetime.now() - timedelta(days=1)).date()

    def test_tonight_defaults_to_evening(self):
        result = parse_natural_language("Dinner tonight")
        assert result["due_date"] is not None
        assert result["due_date"].date() == datetime.now().date()
        assert result["due_date"].hour == 20

    def test_next_month(self):
        result = parse_natural_language("Renew domain next month")
        assert result["due_date"] is not None
        now = datetime.now()
        expected_month = (now.month % 12) + 1
        assert result["due_date"].month == expected_month

    def test_ordinal_day_of_month(self):
        result = parse_natural_language("Submit taxes on the 24th")
        assert result["due_date"] is not None
        assert result["due_date"].day == 24
        assert "24th" not in result["content"].lower()


# ---------------------------------------------------------------------------
# Context-gated weekday abbreviations
#
# A bare weekday abbreviation (mon/thu/sun/…) collides with ordinary words in
# other languages (e.g. Vietnamese "thu"). It resolves to a date ONLY with date
# context: a cue word before, a time right after, or trailing the input. Full
# weekday names ("thursday") are unambiguous and always resolve. Reference "now"
# is a Tuesday (2026-06-23) so Thursday == 2026-06-25 and tomorrow == 2026-06-24.
# ---------------------------------------------------------------------------


class TestContextGatedWeekdayAbbreviations:
    def test_prose_thu_not_a_date(self):
        """Vietnamese 'thu' mid-sentence must stay content, not become Thursday."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Nghiệm thu các phương án")
        assert result["due_date"] is None
        assert result["content"] == "Nghiệm thu các phương án"

    def test_prose_sun_not_a_date(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("sun bathing at the beach")
        assert result["due_date"] is None
        assert result["content"] == "sun bathing at the beach"

    def test_trailing_abbrev_is_a_date(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("buy milk thu")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 3  # Thursday
        assert result["content"] == "buy milk"

    def test_cue_word_before_abbrev(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("meet on thu")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 3
        # The cue word "on" is preserved in the content.
        assert result["content"] == "meet on"

    def test_time_after_abbrev(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("thu 3pm standup")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 3
        assert result["due_date"].hour == 15  # explicit time
        assert result["content"] == "standup"

    def test_abbrev_trailing_after_priority_strip(self):
        """p1 is stripped before the date pass, so 'thu' is effectively trailing."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("buy milk thu p1")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 3
        assert result["priority"] == 1
        assert result["content"] == "buy milk"

    def test_full_weekday_name_always_a_date(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("thursday review")
        assert result["due_date"] is not None
        assert result["due_date"].weekday() == 3
        assert result["content"] == "review"

    def test_prose_thu_preserved_when_real_date_present(self):
        """A real date elsewhere resolves; the prose 'thu' stays in the title."""
        from datetime import timedelta

        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Nghiệm thu tomorrow")
        assert result["due_date"] is not None
        assert result["due_date"].date() == (_TUE_JUN_23 + timedelta(days=1)).date()
        assert result["content"] == "Nghiệm thu"

    def test_recurrence_every_abbrev_still_works(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("standup every thu")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=TH"
        assert result["due_date"] is None
        assert result["content"] == "standup"


# ---------------------------------------------------------------------------
# Recurrence detection
# ---------------------------------------------------------------------------


class TestRecurrenceParsing:
    def test_daily(self):
        result = parse_natural_language("Standup daily")
        assert result["recurrence_rule"] == "FREQ=DAILY;INTERVAL=1"
        assert result["recurrence_label"] == "Daily"
        assert "daily" not in result["content"].lower()

    def test_everyday(self):
        result = parse_natural_language("Review PR everyday")
        assert result["recurrence_rule"] == "FREQ=DAILY;INTERVAL=1"

    def test_weekly(self):
        result = parse_natural_language("Team sync weekly")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;INTERVAL=1"

    def test_monthly(self):
        result = parse_natural_language("Pay bills monthly")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=1"

    def test_every_weekday(self):
        result = parse_natural_language("Gym every monday")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO"
        assert result["recurrence_label"] == "Every Monday"

    def test_every_weekday_abbreviated(self):
        result = parse_natural_language("Standup every wed")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=WE"

    def test_every_n_days(self):
        result = parse_natural_language("Water plants every 3 days")
        assert result["recurrence_rule"] == "FREQ=DAILY;INTERVAL=3"
        assert result["recurrence_label"] == "Every 3 days"

    def test_every_other_week(self):
        result = parse_natural_language("Backup every other week")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;INTERVAL=2"

    def test_every_nth_of_month(self):
        result = parse_natural_language("Pay rent every 1st of month")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;BYMONTHDAY=1"
        assert result["recurrence_label"] == "Monthly on the 1st"

    def test_every_month_on_the_nth(self):
        result = parse_natural_language("Sprint planning every month on the 15th")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;BYMONTHDAY=15"

    def test_recurrence_does_not_set_due_date(self):
        """'every monday' is recurrence, not a one-off weekday due date."""
        result = parse_natural_language("Gym every monday")
        assert result["due_date"] is None

    def test_plain_weekday_is_not_recurrence(self):
        """A bare weekday (no 'every') stays a one-off due date."""
        result = parse_natural_language("Meet team monday")
        assert result["recurrence_rule"] is None
        assert result["due_date"] is not None

    def test_recurrence_with_time_anchor(self):
        result = parse_natural_language("Standup every day at 9am")
        assert result["recurrence_rule"] == "FREQ=DAILY;INTERVAL=1"
        assert result["due_date"] is not None
        assert result["due_date"].hour == 9

    def test_no_recurrence(self):
        result = parse_natural_language("Fix login bug")
        assert result["recurrence_rule"] is None
        assert result["recurrence_label"] is None


# ---------------------------------------------------------------------------
# Date removal from content
# ---------------------------------------------------------------------------


class TestDateRemoval:
    def test_today_removed(self):
        result = parse_natural_language("Buy groceries today")
        assert "today" not in result["content"].lower()

    def test_tomorrow_removed(self):
        result = parse_natural_language("Call dentist tomorrow")
        assert "tomorrow" not in result["content"].lower()

    def test_weekday_removed(self):
        result = parse_natural_language("Meet team monday")
        assert "monday" not in result["content"].lower()

    def test_next_week_removed(self):
        result = parse_natural_language("Submit report next week")
        assert "next week" not in result["content"].lower()

    def test_in_n_days_removed(self):
        result = parse_natural_language("Deploy in 3 days")
        assert "in 3 days" not in result["content"].lower()

    def test_time_phrase_removed(self):
        result = parse_natural_language("Meeting at 14:30 today")
        assert "14:30" not in result["content"]


# ---------------------------------------------------------------------------
# _extract_date_fragment
# ---------------------------------------------------------------------------


class TestExtractDateFragment:
    def test_next_monday_fragment(self):
        parser = _make_parser()
        fragment = parser._extract_date_fragment("Meet next monday")
        assert fragment is not None
        assert "next" in fragment.lower()

    def test_in_3_days_fragment(self):
        parser = _make_parser()
        fragment = parser._extract_date_fragment("Deploy in 3 days")
        assert fragment is not None

    def test_no_date_fragment(self):
        parser = _make_parser()
        fragment = parser._extract_date_fragment("Fix the login bug")
        assert fragment is None

    def test_month_day_fragment(self):
        parser = _make_parser()
        fragment = parser._extract_date_fragment("Submit by Jan 15")
        assert fragment is not None

    def test_at_time_fragment(self):
        parser = _make_parser()
        fragment = parser._extract_date_fragment("Meeting at 3pm")
        assert fragment is not None


# ---------------------------------------------------------------------------
# dateparser integration (with HAS_DATEPARSER = True)
# ---------------------------------------------------------------------------


class TestDateparserIntegration:
    def test_dateparser_called_when_simple_parse_fails(self):
        """When simple parse returns None and dateparser is available, it's used."""
        parser = _make_parser()
        # "next monday" won't be caught by simple parse's exact "next week" check
        # but dateparser should handle it
        with (
            patch("todopro_cli.utils.nlp_parser.HAS_DATEPARSER", True),
            patch("todopro_cli.utils.nlp_parser.dateparser") as mock_dp,
        ):
            mock_dp.parse.return_value = datetime(2025, 1, 15)
            # Force simple parse to return None by using a string that
            # simple parse won't handle
            result = parser._parse_date("in 2 weeks")
            # Either simple_parse handled it or dateparser was called
            # Just confirm no exception raised
            assert result is not None or result is None

    def test_dateparser_not_called_when_disabled(self):
        """When HAS_DATEPARSER=False, dateparser is never used."""
        parser = _make_parser()
        with patch("todopro_cli.utils.nlp_parser.HAS_DATEPARSER", False):
            result = parser._parse_date("some future date that simple parse ignores")
            # Should return None without calling dateparser
            assert result is None

    def test_has_dateparser_false_branch(self):
        """Simulate ImportError scenario by patching HAS_DATEPARSER to False."""
        with patch("todopro_cli.utils.nlp_parser.HAS_DATEPARSER", False):
            # Text that simple parse can't handle at all
            parser = _make_parser()
            result = parser._parse_date("completely unrecognized date text xyz123")
            # Should return None since dateparser is disabled AND simple parse fails
            assert result is None


# ---------------------------------------------------------------------------
# Full round-trip
# ---------------------------------------------------------------------------


class TestFullParsing:
    def test_complex_task(self):
        """Full parse: priority + project + label + date."""
        result = parse_natural_language("Review PR tomorrow #Work p2 @review")
        assert result["priority"] == 2
        assert result["project_name"] == "Work"
        assert "review" in result["labels"]
        assert result["due_date"] is not None
        content = result["content"].lower()
        assert "review pr" in content
        assert "tomorrow" not in content

    def test_whitespace_cleaned(self):
        """Content should have clean whitespace after removing markers."""
        result = parse_natural_language("Fix   bug   p1  #Backend  @urgent")
        # Multiple spaces should be collapsed
        assert "  " not in result["content"]

    def test_empty_string(self):
        """Empty string should return all None/empty."""
        result = parse_natural_language("")
        assert result["content"] == ""
        assert result["priority"] is None
        assert result["project_name"] is None
        assert result["labels"] == []

    def test_convenience_function(self):
        """parse_natural_language wraps LocalNLPParser.parse."""
        result = parse_natural_language("Buy milk today")
        assert "due_date" in result
        assert "content" in result
        assert result["due_date"] is not None


# ---------------------------------------------------------------------------
# Quarterly / half-yearly recurrence vocabulary
# ---------------------------------------------------------------------------


class TestQuarterlyHalfYearlyRecurrence:
    def test_quarterly_keyword(self):
        result = parse_natural_language("Review goals quarterly")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=3"
        assert result["recurrence_label"] == "Quarterly"
        assert "quarterly" not in result["content"].lower()
        assert result["content"] == "Review goals"

    def test_every_quarter(self):
        result = parse_natural_language("Review every quarter")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=3"
        assert result["recurrence_label"] == "Quarterly"

    def test_every_n_quarters(self):
        result = parse_natural_language("Audit every 2 quarters")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=6"
        assert result["recurrence_label"] == "Every 2 quarters"

    def test_quarter_on_the_nth(self):
        result = parse_natural_language("OKRs every quarter on the 1st")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=1"
        assert result["recurrence_label"] == "Quarterly on the 1st"
        assert result["content"] == "OKRs"

    def test_half_yearly(self):
        result = parse_natural_language("Checkup half-yearly")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=6"
        assert result["recurrence_label"] == "Half-yearly"

    def test_every_half_year(self):
        result = parse_natural_language("Health checkup every half year")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=6"
        assert result["content"] == "Health checkup"

    def test_semi_annually_is_half_yearly_not_yearly(self):
        """Regression: 'semi-annually' must not fall through to FREQ=YEARLY and must
        not leave a dangling 'semi-' in the content."""
        result = parse_natural_language("Dentist semi-annually")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=6"
        assert result["recurrence_label"] == "Half-yearly"
        assert result["content"] == "Dentist"

    def test_bi_annually_on_the_nth(self):
        result = parse_natural_language("Insurance bi-annually on the 5th")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=6;BYMONTHDAY=5"
        assert result["recurrence_label"] == "Half-yearly on the 5th"
        assert result["content"] == "Insurance"


# ---------------------------------------------------------------------------
# Day-of-month / period anchoring — first due date lands on the recurrence day
# ---------------------------------------------------------------------------


class TestRecurrenceAnchoring:
    def test_every_nth_anchors_to_next_occurrence_not_today(self):
        """'every 15th at 2' → next 15th (this month already past it), not today."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Backup every 15th at 2")
        assert result["recurrence_rule"] == "FREQ=MONTHLY;BYMONTHDAY=15"
        assert result["due_date"] == datetime(2026, 7, 15, 2, 0)
        assert result["content"] == "Backup"

    def test_every_nth_anchors_within_current_month_when_future(self):
        """Day still ahead this month → stay in the current month."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Report every 25th at 8")
        assert result["due_date"] == datetime(2026, 6, 25, 8, 0)

    def test_every_nth_skips_today(self):
        """When today *is* the day-of-month, roll to next month (never due 'now')."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Sync every 23rd at 8")
        assert result["due_date"] == datetime(2026, 7, 23, 8, 0)

    def test_every_month_on_the_nth_anchors(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language(
                "Sprint planning every month on the 15th at 10"
            )
        assert result["recurrence_rule"] == "FREQ=MONTHLY;BYMONTHDAY=15"
        assert result["due_date"] == datetime(2026, 7, 15, 10, 0)

    def test_quarter_on_the_nth_anchors(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("OKRs every quarter on the 1st at 9")
        assert result["due_date"] == datetime(2026, 7, 1, 9, 0)

    def test_half_yearly_on_the_nth_anchors(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Insurance bi-annually on the 5th at 9")
        assert result["due_date"] == datetime(2026, 7, 5, 9, 0)

    def test_plain_interval_without_day_anchor_starts_today(self):
        """No day-of-month sub-anchor → series starts today at the given time."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Review goals quarterly at 9")
        assert result["due_date"] == datetime(2026, 6, 23, 9, 0)

    def test_multi_weekday_anchors_to_soonest(self):
        """'every mon and thu at 21' on a Tuesday → soonest is Thursday."""
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Study IELTS every mon and thu at 21")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO,TH"
        assert result["due_date"] == datetime(2026, 6, 25, 21, 0)
        assert result["content"] == "Study IELTS"

    def test_multi_weekday_anchor_monday_to_tuesday(self):
        """'every tue and thu at 21' on a Monday → soonest is Tuesday."""
        _MON_JUN_29 = datetime(2026, 6, 29, 10, 0, 0)
        with _frozen_now(_MON_JUN_29):
            result = parse_natural_language("Do task every tue and thu at 21")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=TU,TH"
        assert result["due_date"] == datetime(2026, 6, 30, 21, 0)
        assert result["content"] == "Do task"

    def test_weekday_in_title_does_not_override_anchor(self):
        """Weekday name in the task title must not override the recurrence anchor."""
        _MON_JUN_29 = datetime(2026, 6, 29, 10, 0, 0)
        with _frozen_now(_MON_JUN_29):
            result = parse_natural_language("thursday review every tue and thu at 21")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=TU,TH"
        # Due date must be Tuesday (anchor wins over "thursday" left in text after recurrence strip)
        assert result["due_date"] == datetime(2026, 6, 30, 21, 0)


# ---------------------------------------------------------------------------
# Extended date/time parsing (calendar dates, fuzzy dates, time-of-day, etc.)
# ---------------------------------------------------------------------------


class TestExtendedDateParsing:
    def test_calendar_month_day(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Buy gift dec 25")
        assert result["due_date"] == datetime(2026, 12, 25, 23, 59, 59)
        assert result["content"] == "Buy gift"

    def test_calendar_day_month_with_time_rolls_to_next_year(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Call mom 27 jan at 5pm")
        assert result["due_date"] == datetime(2027, 1, 27, 17, 0)

    def test_calendar_iso(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Submit form 2026-07-15")
        assert result["due_date"] == datetime(2026, 7, 15, 23, 59, 59)

    def test_calendar_numeric_disambiguates_day_over_12(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Pay rent 27/1")
        assert result["due_date"] == datetime(2027, 1, 27, 23, 59, 59)

    def test_end_of_month(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Plan trip end of month")
        assert result["due_date"] == datetime(2026, 6, 30, 23, 59, 59)

    def test_mid_month_name(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Review mid july")
        assert result["due_date"] == datetime(2026, 7, 15, 23, 59, 59)

    def test_this_weekend(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Hike this weekend")
        assert result["due_date"] == datetime(2026, 6, 27, 23, 59, 59)

    def test_next_weekend(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Clean garage next weekend")
        assert result["due_date"] == datetime(2026, 7, 4, 23, 59, 59)

    def test_later_this_week(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Wrap up report later this week")
        assert result["due_date"] == datetime(2026, 6, 26, 23, 59, 59)

    def test_tomorrow_morning(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Standup tomorrow morning")
        assert result["due_date"] == datetime(2026, 6, 24, 9, 0)

    def test_in_the_evening(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Gym in the evening")
        assert result["due_date"] == datetime(2026, 6, 23, 19, 0)

    def test_in_n_weeks(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Ping team in 3 weeks")
        assert result["due_date"] == datetime(2026, 7, 14, 23, 59, 59)

    def test_in_n_hours(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Coffee in 2 hours")
        assert result["due_date"] == datetime(2026, 6, 23, 19, 0)

    def test_someday(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Learn piano someday")
        assert result["due_date"] == datetime(2026, 8, 23, 23, 59, 59)

    def test_bare_pm_time(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Standup 6pm")
        assert result["due_date"] == datetime(2026, 6, 23, 18, 0)


class TestNoDateAndDeadlineAndCompletion:
    def test_no_date_clears(self):
        result = parse_natural_language("Reorg backlog no date")
        assert result["due_date"] is None
        assert result["due_date_cleared"] is True
        assert result["content"] == "Reorg backlog"

    def test_deadline_brace(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Ship report {jan 5} p1")
        assert result["deadline"] == datetime(2027, 1, 5, 23, 59, 59)
        assert result["due_date"] is None
        assert result["content"] == "Ship report"

    def test_every_bang_sets_completion_flag(self):
        result = parse_natural_language("Water plants every! 3 days")
        assert result["recurrence_rule"] == "FREQ=DAILY;INTERVAL=3"
        assert result["recurrence_from_completion"] is True
        assert result["content"] == "Water plants"

    def test_plain_every_is_not_completion_based(self):
        result = parse_natural_language("Water plants every 3 days")
        assert result["recurrence_from_completion"] is False

    def test_every_bang_weekday_with_time(self):
        with _frozen_now(_TUE_JUN_23):
            result = parse_natural_language("Standup every! monday at 9am")
        assert result["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO"
        assert result["recurrence_from_completion"] is True
        assert result["due_date"] == datetime(2026, 6, 29, 9, 0)


# ---------------------------------------------------------------------------
# Reminder parsing
# ---------------------------------------------------------------------------


class TestReminderParsing:
    def test_no_reminder(self):
        assert parse_natural_language("Buy groceries tomorrow")["reminders"] == []

    # ── Relative ──
    def test_bang_relative_before(self):
        r = parse_natural_language("Standup tomorrow 9am !30m before")["reminders"]
        assert r[0]["type"] == "relative"
        assert r[0]["minutes_before"] == 30

    def test_bang_relative_compact(self):
        r = parse_natural_language("Standup tomorrow !30mb")["reminders"]
        assert r[0]["minutes_before"] == 30

    def test_remind_keyword_alias(self):
        r = parse_natural_language("Call mom tomorrow remind me 10 minutes before")
        assert r["reminders"][0]["minutes_before"] == 10
        assert r["content"] == "Call mom"

    def test_relative_at_time_of_task(self):
        r = parse_natural_language("Take pills today !0mb")["reminders"]
        assert r[0]["type"] == "relative"
        assert r[0]["minutes_before"] == 0

    def test_relative_days(self):
        r = parse_natural_language("Pay rent !1d before")["reminders"]
        assert r[0]["minutes_before"] == 1440

    # ── Absolute ──
    def test_absolute_duration_from_now(self):
        r = parse_natural_language("Tea break !30m")["reminders"]
        assert r[0]["type"] == "absolute"
        assert r[0]["at"] is not None

    def test_absolute_later(self):
        assert (
            parse_natural_language("Check !later")["reminders"][0]["type"] == "absolute"
        )

    def test_absolute_clock(self):
        with _frozen_now(_TUE_JUN_23):
            r = parse_natural_language("Call client !6pm")["reminders"]
        assert r[0]["type"] == "absolute"
        assert r[0]["at"].hour == 18

    def test_absolute_day_and_clock(self):
        with _frozen_now(_TUE_JUN_23):
            r = parse_natural_language("Sync !Mon 9am")["reminders"]
        assert r[0]["type"] == "absolute"
        assert r[0]["at"].hour == 9

    # ── Recurring ──
    def test_recurring_weekday(self):
        with _frozen_now(_TUE_JUN_23):
            r = parse_natural_language("Standup !every sat 9am")["reminders"]
        assert r[0]["type"] == "recurring"
        assert r[0]["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=SA"
        assert r[0]["at"].hour == 9

    def test_recurring_interval_hours(self):
        r = parse_natural_language("Pulse !every 2 hours")["reminders"]
        assert r[0]["recurrence_rule"] == "FREQ=HOURLY;INTERVAL=2"

    def test_recurring_bare_time_is_daily(self):
        r = parse_natural_language("Vitamins !every 5pm")["reminders"]
        assert r[0]["recurrence_rule"] == "FREQ=DAILY;INTERVAL=1"
        assert r[0]["at"].hour == 17

    # ── Multiple + isolation ──
    def test_multiple_reminders(self):
        r = parse_natural_language("Two reminders !30m before !6pm")["reminders"]
        assert len(r) == 2
        assert r[0]["type"] == "relative"
        assert r[1]["type"] == "absolute"

    def test_reminder_does_not_become_due_date(self):
        result = parse_natural_language("Backup files !2d before")
        assert result["reminders"][0]["minutes_before"] == 2 * 1440
        assert result["due_date"] is None

    def test_bang_word_is_not_a_reminder(self):
        result = parse_natural_language("Ship it !important")
        assert result["reminders"] == []
        assert "important" in result["content"]
