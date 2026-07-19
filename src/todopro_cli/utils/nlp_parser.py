"""Local natural language parsing for tasks.

Provides date parsing, priority extraction, project/label detection
without requiring backend API.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

try:
    import dateparser

    HAS_DATEPARSER = True
except ImportError:
    HAS_DATEPARSER = False


# ── Reminder parsing (Todoist-style "!" / "remind" tokens) ────────────────────
# Shared, language-portable grammar — mirror of the SPA (nlp-parser.ts) and backend
# (natural_language.py) reminder parsers. Each parsed reminder is one of:
#   relative  — fires `minutes_before` the due date  (e.g. "!30m before", "!0mb")
#   absolute  — fires at a fixed instant             (e.g. "!30m", "!6pm", "!tmr 3pm")
#   recurring — repeats per RRULE                    (e.g. "!every sat 9am")

# Offset units → minutes; a unit's first letter is unique (m/h/d/w).
REMINDER_UNIT_MINUTES = {"m": 1, "h": 60, "d": 1440, "w": 10080}

# Weekday word (abbrev or full) → iCalendar BYDAY code.
REMINDER_WEEKDAY_BYDAY = {
    "monday": "MO",
    "mon": "MO",
    "tuesday": "TU",
    "tues": "TU",
    "tue": "TU",
    "wednesday": "WE",
    "wed": "WE",
    "thursday": "TH",
    "thurs": "TH",
    "thur": "TH",
    "thu": "TH",
    "friday": "FR",
    "fri": "FR",
    "saturday": "SA",
    "sat": "SA",
    "sunday": "SU",
    "sun": "SU",
}
# Day abbreviation → full word, so the host date parser resolves "tmr 3pm" etc.
REMINDER_DAY_EXPAND = {
    "tmrw": "tomorrow",
    "tmr": "tomorrow",
    "tom": "tomorrow",
    "tdy": "today",
    "mon": "monday",
    "tues": "tuesday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thurs": "thursday",
    "thur": "thursday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}
# Time-of-day word → (hour, minute) for reminder clock specs.
REMINDER_TIME_WORDS = {
    "noon": (12, 0),
    "midnight": (0, 0),
    "morning": (9, 0),
    "afternoon": (15, 0),
    "evening": (19, 0),
    "night": (21, 0),
}

_RDAY = (
    r"today|tonight|tomorrow|tmrw|tmr|tom|monday|mon|tuesday|tues|tue|"
    r"wednesday|wed|thursday|thurs|thur|thu|friday|fri|saturday|sat|sunday|sun"
)
_RCLOCK = r"\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|noon|midnight|morning|afternoon|evening|night"

# Token prefix: a single "!" (not the "!!" priority marker) or the word "remind".
REMINDER_PREFIX_RE = re.compile(
    r"(?:(?<![!\w])!(?!!)\s*|\bremind(?:\s+me)?\s+)", re.IGNORECASE
)
# Anchored spec patterns, tried in priority order against the text after a prefix.
_REM_AT_DUE_RE = re.compile(
    r"at\s+(?:the\s+)?(?:due(?:\s+date|\s+time)?|task(?:\s+time)?|time\s+of\s+task)",
    re.IGNORECASE,
)
_REM_RELATIVE_RE = re.compile(
    r"(\d+)\s*(minutes|minute|mins|min|hours|hour|hrs|hr|days|day|weeks|week|m|h|d|w)"
    r"\s*(?:before\b|b\b)",
    re.IGNORECASE,
)
_REM_EVERY_INTERVAL_RE = re.compile(
    r"every\s+(\d+)\s*(hours|hour|hrs|hr|h|minutes|minute|mins|min|m)\b", re.IGNORECASE
)
_REM_EVERY_WEEKDAYS_RE = re.compile(
    rf"every\s+((?:{'|'.join(REMINDER_WEEKDAY_BYDAY)})"
    rf"(?:\s*(?:,|and|&)\s*(?:{'|'.join(REMINDER_WEEKDAY_BYDAY)}))*)"
    rf"\s*(?:at\s+)?({_RCLOCK})?",
    re.IGNORECASE,
)
_REM_EVERY_SIMPLE_RE = re.compile(
    rf"every\s+(day|week|month|year|hour)\b\s*(?:at\s+)?({_RCLOCK})?", re.IGNORECASE
)
_REM_EVERY_TIME_RE = re.compile(rf"every\s+(?:at\s+)?({_RCLOCK})", re.IGNORECASE)
_REM_LATER_RE = re.compile(r"later\b", re.IGNORECASE)
_REM_DURATION_RE = re.compile(
    r"(\d+)\s*(?:hours|hour|hrs|hr|h)(?:\s*(\d+)\s*(?:minutes|minute|mins|min|m))?"
    r"|(\d+)\s*(?:minutes|minute|mins|min|m)\b",
    re.IGNORECASE,
)
_REM_CLOCK_DAY_RE = re.compile(
    rf"(?:({_RDAY})\s+)?(?:at\s+)?({_RCLOCK})|({_RDAY})", re.IGNORECASE
)


def _reminder_clock_hm(text):
    """Parse a clock spec ("6pm", "14:30", "9:00am", "noon") → (hour, minute)."""
    key = text.strip().lower()
    if key in REMINDER_TIME_WORDS:
        return REMINDER_TIME_WORDS[key]
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", key)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = m.group(3)
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def _reminder_next_at(now, hour, minute, bydays=None):
    """Soonest future datetime at ``hour:minute`` (optionally on a ``bydays`` set)."""
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if bydays:
        order = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        for add in range(8):
            day = candidate + timedelta(days=add)
            if order[day.weekday()] in bydays and day > now:
                return day
        return candidate + timedelta(days=1)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _build_recurring_reminder(spec, now):
    """Resolve an "every ..." reminder spec → (reminder_dict, consumed_len) or None."""
    m = _REM_EVERY_INTERVAL_RE.match(spec)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()[0]
        if unit == "h":
            rule, delta, lbl = f"FREQ=HOURLY;INTERVAL={n}", timedelta(hours=n), "hour"
        else:
            rule, delta, lbl = (
                f"FREQ=MINUTELY;INTERVAL={n}",
                timedelta(minutes=n),
                "minute",
            )
        at = now + delta
        return {
            "type": "recurring",
            "minutes_before": None,
            "at": at,
            "recurrence_rule": rule,
            "label": f"Every {n} {lbl}{'s' if n != 1 else ''}",
        }, m.end()

    m = _REM_EVERY_WEEKDAYS_RE.match(spec)
    if m:
        words = re.split(r"\s*(?:,|and|&)\s*", m.group(1).strip(), flags=re.IGNORECASE)
        bydays = [REMINDER_WEEKDAY_BYDAY[w.lower()] for w in words if w]
        hm = _reminder_clock_hm(m.group(2)) if m.group(2) else (9, 0)
        at = _reminder_next_at(now, hm[0], hm[1], bydays=bydays)
        return {
            "type": "recurring",
            "minutes_before": None,
            "at": at,
            "recurrence_rule": f"FREQ=WEEKLY;BYDAY={','.join(bydays)}",
            "label": f"Every {','.join(bydays)} {hm[0]:02d}:{hm[1]:02d}",
        }, m.end()

    m = _REM_EVERY_SIMPLE_RE.match(spec)
    if m:
        period = m.group(1).lower()
        if period == "hour":
            at = now + timedelta(hours=1)
            return {
                "type": "recurring",
                "minutes_before": None,
                "at": at,
                "recurrence_rule": "FREQ=HOURLY;INTERVAL=1",
                "label": "Every hour",
            }, m.end()
        freq = {"day": "DAILY", "week": "WEEKLY", "month": "MONTHLY", "year": "YEARLY"}[
            period
        ]
        hm = _reminder_clock_hm(m.group(2)) if m.group(2) else (9, 0)
        at = _reminder_next_at(now, hm[0], hm[1])
        return {
            "type": "recurring",
            "minutes_before": None,
            "at": at,
            "recurrence_rule": f"FREQ={freq};INTERVAL=1",
            "label": f"Every {period} {hm[0]:02d}:{hm[1]:02d}",
        }, m.end()

    m = _REM_EVERY_TIME_RE.match(spec)
    if m:
        hm = _reminder_clock_hm(m.group(1))
        if hm:
            at = _reminder_next_at(now, hm[0], hm[1])
            return {
                "type": "recurring",
                "minutes_before": None,
                "at": at,
                "recurrence_rule": "FREQ=DAILY;INTERVAL=1",
                "label": f"Every day {hm[0]:02d}:{hm[1]:02d}",
            }, m.end()
    return None


def parse_reminder_tokens(text, *, now, parse_datetime):
    """Extract Todoist-style reminders from ``text``.

    Args:
        text: the input string.
        now: the reference "now" (datetime).
        parse_datetime: callback ``(phrase) -> datetime | None`` resolving a date
            phrase via the host parser (used for "!6pm", "!tmr 3pm", "!Mon 9am").

    Returns ``(reminders, remaining_text)``. Each reminder is a dict with keys
    ``type`` ("relative"|"absolute"|"recurring"), ``minutes_before`` (int|None),
    ``at`` (datetime|None), ``recurrence_rule`` (str|None) and ``label`` (str).
    """
    reminders = []
    out = text
    search_from = 0
    while True:
        prefix = REMINDER_PREFIX_RE.search(out, search_from)
        if not prefix:
            break
        rest = out[prefix.end() :]
        parsed = _match_reminder_spec(rest, now=now, parse_datetime=parse_datetime)
        if parsed is None:
            search_from = prefix.end()
            continue
        reminder, consumed = parsed
        reminders.append(reminder)
        out = out[: prefix.start()] + " " + out[prefix.end() + consumed :]
        search_from = max(prefix.start() - 1, 0)
    return reminders, out


def _match_reminder_spec(rest, *, now, parse_datetime):
    """Match one reminder spec at the start of ``rest`` → (dict, consumed) or None."""
    # 1. "at time of task" / "at the due date" → relative, 0 minutes before.
    m = _REM_AT_DUE_RE.match(rest)
    if m:
        return {
            "type": "relative",
            "minutes_before": 0,
            "at": None,
            "recurrence_rule": None,
            "label": "At time of task",
        }, m.end()

    # 2. Relative offset before the due date ("30m before", "30mb", "0mb").
    m = _REM_RELATIVE_RE.match(rest)
    if m:
        minutes = int(m.group(1)) * REMINDER_UNIT_MINUTES[m.group(2).lower()[0]]
        return {
            "type": "relative",
            "minutes_before": minutes,
            "at": None,
            "recurrence_rule": None,
            "label": "At time of task"
            if minutes == 0
            else f"{_humanize_minutes(minutes)} before",
        }, m.end()

    # 3. Recurring ("every sat 9am", "every 2 hours", "every 5pm").
    if rest[:5].lower().startswith("every"):
        recurring = _build_recurring_reminder(rest, now)
        if recurring:
            return recurring

    # 4. "later" → ~4 hours from now (absolute).
    m = _REM_LATER_RE.match(rest)
    if m:
        return {
            "type": "absolute",
            "minutes_before": None,
            "at": now + timedelta(hours=4),
            "recurrence_rule": None,
            "label": "Later",
        }, m.end()

    # 5. Duration from now ("30m", "2h30m") → absolute. (Before-cases handled above.)
    m = _REM_DURATION_RE.match(rest)
    if m and m.group(0).strip():
        if m.group(1):  # Nh[Nm]
            minutes = int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)
        else:  # Nm
            minutes = int(m.group(3))
        at = now + timedelta(minutes=minutes)
        return {
            "type": "absolute",
            "minutes_before": None,
            "at": at,
            "recurrence_rule": None,
            "label": f"In {_humanize_minutes(minutes)}",
        }, m.end()

    # 6. Clock/day spec ("6pm", "tmr 3pm", "Mon 9am") → absolute via host parser.
    m = _REM_CLOCK_DAY_RE.match(rest)
    if m and m.group(0).strip():
        day = m.group(1) or m.group(3)
        clock = m.group(2)
        phrase_parts = []
        if day:
            phrase_parts.append(REMINDER_DAY_EXPAND.get(day.lower(), day.lower()))
        if clock:
            phrase_parts.append(f"at {clock}")
        at = parse_datetime(" ".join(phrase_parts))
        if at is not None:
            # A bare clock with no day resolves to today; roll to the next instance
            # if that moment already passed.
            if not day and at <= now:
                at = at + timedelta(days=1)
            return {
                "type": "absolute",
                "minutes_before": None,
                "at": at,
                "recurrence_rule": None,
                "label": _format_at_label(at),
            }, m.end()
    return None


def _humanize_minutes(minutes):
    """ "90" → "1h 30m"; "30" → "30m"; "1440" → "1d"."""
    if minutes <= 0:
        return "0m"
    days, rem = divmod(minutes, 1440)
    hours, mins = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    return " ".join(parts)


def _format_at_label(dt):
    """Short label for an absolute reminder datetime."""
    return dt.strftime("%b %d %H:%M")


# Weekday name → Python weekday() index (Mon=0 … Sun=6).
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Weekday name → iCalendar BYDAY code.
WEEKDAY_RRULE = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}

# Abbreviation → canonical word, applied (for detection only) before date parsing
# so that "tom", "mon", "thurs", … resolve like their full forms.
ABBREVIATIONS = [
    (r"\b(?:tmrw|tmr|tom)\b", "tomorrow"),
    (r"\btdy\b", "today"),
    (r"\byest\b", "yesterday"),
    (r"\bmon\b", "monday"),
    (r"\b(?:tues|tue)\b", "tuesday"),
    (r"\bwed\b", "wednesday"),
    (r"\b(?:thurs|thur|thu)\b", "thursday"),
    (r"\bfri\b", "friday"),
    (r"\bsat\b", "saturday"),
    (r"\bsun\b", "sunday"),
]

# iCalendar frequency for each unit noun.
_UNIT_FREQ = {"day": "DAILY", "week": "WEEKLY", "month": "MONTHLY", "year": "YEARLY"}
_FREQ_NOUN = {"DAILY": "day", "WEEKLY": "week", "MONTHLY": "month", "YEARLY": "year"}

# Month 3-letter abbreviation → month number. Full names resolve via name[:3].
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
# Month alternation for regexes (abbrev + full forms).
_MONTH_ALT = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?"
    r"|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)

# Time-of-day words → (hour, minute). "tonight" is handled separately (today + 20:00).
TIME_OF_DAY = {
    "morning": (9, 0),
    "afternoon": (12, 0),
    "evening": (19, 0),
    "night": (22, 0),
    "noon": (12, 0),
    "midnight": (0, 0),
}

# Weekday alternatives (full + abbreviated) for recurrence matching.
_WEEKDAY_ALT = (
    "monday|mon|tuesday|tues|tue|wednesday|wed|"
    "thursday|thurs|thur|thu|friday|fri|saturday|sat|sunday|sun"
)


def _expand_abbreviations(text: str) -> str:
    """Expand date abbreviations (tom → tomorrow, mon → monday, …)."""
    for pattern, full in ABBREVIATIONS:
        text = re.sub(pattern, full, text, flags=re.IGNORECASE)
    return text


# Relative-day abbreviations always expand (they don't collide with prose).
_RELATIVE_ABBREVIATIONS = [
    (r"\b(?:tmrw|tmr|tom)\b", "tomorrow"),
    (r"\btdy\b", "today"),
    (r"\byest\b", "yesterday"),
]

# A bare weekday abbreviation collides with ordinary words in other languages
# (e.g. Vietnamese "thu"). Treat it as a date ONLY with date context: a cue word
# before, a time right after, or trailing the input. Full names are unaffected.
_WD_ABBR_ALT = r"mon|tues|tue|wed|thurs|thur|thu|fri|sat|sun"
_WD_TIME_AFTER = (
    r"(?:at\s+)?(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
    r"|noon|midnight|morning|afternoon|evening|night)"
)
_WD_CUE_BEFORE = r"on|by|due|next|this|before|after|from"
_WEEKDAY_ABBR_TO_FULL = {
    "mon": "monday", "tue": "tuesday", "tues": "tuesday", "wed": "wednesday",
    "thu": "thursday", "thur": "thursday", "thurs": "thursday", "fri": "friday",
    "sat": "saturday", "sun": "sunday",
}
# No variable-width lookbehind in stdlib re: capture the optional cue/after context
# and decide in a callback. Participating groups are preserved so only the weekday
# token itself is rewritten (the time in `after` is removed later by the time patterns).
_CONTEXT_WEEKDAY_RE = re.compile(
    rf"(?P<cue>\b(?:{_WD_CUE_BEFORE})\s+)?"
    rf"\b(?P<wd>{_WD_ABBR_ALT})\b"
    rf"(?P<after>\s+{_WD_TIME_AFTER}\b|\s*$)?",
    re.IGNORECASE,
)


def _weekday_has_context(m: "re.Match[str]") -> bool:
    # `\s*$` can match the empty string, so distinguish "matched empty" (not None)
    # from "did not participate" (None).
    return m.group("cue") is not None or m.group("after") is not None


def _expand_free_text_abbreviations(text: str) -> str:
    """Top-level expansion: relative words always expand; weekday abbreviations only
    when context-legitimized (so a prose 'thu' isn't read as Thursday)."""
    for pattern, full in _RELATIVE_ABBREVIATIONS:
        text = re.sub(pattern, full, text, flags=re.IGNORECASE)

    def _repl(m: "re.Match[str]") -> str:
        if not _weekday_has_context(m):
            return m.group(0)
        full = _WEEKDAY_ABBR_TO_FULL[m.group("wd").lower()]
        return (m.group("cue") or "") + full + (m.group("after") or "")

    return _CONTEXT_WEEKDAY_RE.sub(_repl, text)


def _ordinal_suffix(n: int) -> str:
    """Return the ordinal suffix for an integer (1 → 'st', 2 → 'nd', …)."""
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _safe_replace_day(dt: datetime, day: int) -> datetime | None:
    """Return dt with its day set to ``day``, or None if that month has no such day."""
    import calendar

    if day > calendar.monthrange(dt.year, dt.month)[1]:
        return None
    return dt.replace(day=day)


def _add_months(dt: datetime, months: int) -> datetime:
    """Add a number of months to a datetime, clamping the day to month length."""
    import calendar

    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _next_monthday(dt: datetime, day: int) -> datetime:
    """Return the soonest strictly-future date with the given day-of-month.

    Today is skipped (mirrors the weekday anchor convention) so a recurring task
    is never anchored to "right now". Rolls to a following month when the current
    month has already passed that day or lacks it (e.g. day 31 in a 30-day month).
    """
    base = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    this_month = _safe_replace_day(base, day)
    if this_month is not None and this_month > base:
        return this_month
    nxt = _add_months(base.replace(day=1), 1)
    return _safe_replace_day(nxt, day) or nxt


def _resolve_md(
    month: int, day: int, year: int | None, now: datetime
) -> datetime | None:
    """Resolve a (month, day[, year]) to a midnight datetime.

    With no year, uses the current year but rolls to next year if the resulting
    date is already in the past (Todoist-style "prefer future"). Two-digit years
    are interpreted as 2000+YY. Returns None for impossible dates (e.g. Feb 30).
    """
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if year is None:
        candidate = _safe_replace_month_day(midnight, now.year, month, day)
        if candidate is None:
            return None
        if candidate.date() < midnight.date():
            candidate = _safe_replace_month_day(midnight, now.year + 1, month, day)
        return candidate
    if year < 100:
        year += 2000
    return _safe_replace_month_day(midnight, year, month, day)


def _safe_replace_month_day(
    dt: datetime, year: int, month: int, day: int
) -> datetime | None:
    """Return dt with year/month/day replaced, or None if that date is invalid."""
    import calendar

    if month < 1 or month > 12 or day < 1:
        return None
    if day > calendar.monthrange(year, month)[1]:
        return None
    return dt.replace(year=year, month=month, day=day)


def _resolve_numeric(
    a: int, b: int, year: int | None, now: datetime
) -> datetime | None:
    """Resolve a numeric "A/B" date, disambiguating day vs month.

    If one component exceeds 12 it must be the day (e.g. 27/1 and 1/27 both →
    Jan 27). When ambiguous (both ≤ 12) the order is month/day (MDY), matching
    the backend dateparser default.
    """
    if a > 12 and b <= 12:
        day, month = a, b
    elif b > 12 and a <= 12:
        month, day = a, b
    else:
        month, day = a, b
    return _resolve_md(month, day, year, now)


def _parse_calendar_date(text_lower: str, now: datetime) -> datetime | None:
    """Parse an explicit calendar date (ISO, month-name, or numeric). Date-only."""
    # ISO: YYYY-MM-DD
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text_lower)
    if m:
        return _safe_replace_month_day(
            now.replace(hour=0, minute=0, second=0, microsecond=0),
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        )
    # <month> <day>[ordinal][, year]
    m = re.search(
        rf"\b({_MONTH_ALT})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b",
        text_lower,
    )
    if m:
        month = MONTHS[m.group(1)[:3]]
        year = int(m.group(3)) if m.group(3) else None
        return _resolve_md(month, int(m.group(2)), year, now)
    # <day>[ordinal] <month>[, year]
    m = re.search(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_ALT})(?:,?\s+(\d{{4}}))?\b",
        text_lower,
    )
    if m:
        month = MONTHS[m.group(2)[:3]]
        year = int(m.group(3)) if m.group(3) else None
        return _resolve_md(month, int(m.group(1)), year, now)
    # numeric D/M[/Y] or M/D[/Y]
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", text_lower)
    if m:
        year = int(m.group(3)) if m.group(3) else None
        return _resolve_numeric(int(m.group(1)), int(m.group(2)), year, now)
    return None


def _coming_weekday(now: datetime, target: int) -> datetime:
    """Soonest date (today allowed) whose weekday is ``target`` (Mon=0…Sun=6)."""
    days_ahead = (target - now.weekday()) % 7
    return now + timedelta(days=days_ahead)


def _monthday_this_or_next(now: datetime, day: int) -> datetime:
    """The given day-of-month this month if not yet passed, else next month."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    this_month = _safe_replace_day(midnight, day)
    if this_month is not None and this_month >= midnight:
        return this_month
    nxt = _add_months(midnight.replace(day=1), 1)
    return _safe_replace_day(nxt, day) or nxt


class LocalNLPParser:
    """Parse natural language task descriptions locally."""

    def __init__(self):
        """Initialize the parser."""
        self.priority_patterns = {
            r"\bp1\b|!!1|!!!|\burgent\b": 1,
            r"\bp2\b|!!2|\bhigh\b": 2,
            r"\bp3\b|!!3|\bmedium\b": 3,
            r"\bp4\b|!!4|\blow\b": 4,
        }

    def parse(self, text: str) -> dict[str, Any]:
        """Parse task text for metadata.

        Args:
            text: Natural language task description

        Returns:
            dict with parsed metadata:
                - content: Cleaned task content
                - due_date: Parsed datetime or None
                - priority: 1-4 or None
                - project_name: Extracted project or None
                - labels: List of extracted labels
        """
        result = {
            "content": text,
            "due_date": None,
            "deadline": None,
            "due_date_cleared": False,
            "recurrence_rule": None,
            "recurrence_label": None,
            "recurrence_from_completion": False,
            "priority": None,
            "project_name": None,
            "labels": [],
            "reminders": [],
        }

        # Extract priority
        for pattern, priority in self.priority_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                result["priority"] = priority
                # Remove priority marker from text
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)
                break

        # Extract project (#ProjectName)
        project_match = re.search(r"#(\w+)", text)
        if project_match:
            result["project_name"] = project_match.group(1)
            text = text.replace(project_match.group(0), "")

        # Extract labels (@label)
        label_matches = re.findall(r"@(\w+)", text)
        if label_matches:
            result["labels"] = label_matches
            # Remove labels from text
            text = re.sub(r"@\w+", "", text)

        # Deadline — explicit "{...}" token (e.g. "ship report {jan 5}"). Parsed and
        # stripped before the due-date pass so its date isn't read as the due date.
        deadline_match = re.search(r"\{([^}]*)\}", text)
        if deadline_match:
            inner = deadline_match.group(1).strip()
            if inner:
                result["deadline"] = self._parse_date(inner)
            text = text[: deadline_match.start()] + " " + text[deadline_match.end() :]

        # Reminders — Todoist-style "!"/"remind" tokens (relative, absolute,
        # recurring). Stripped before the date pass so a reminder's own date isn't
        # read as the task due date.
        result["reminders"], text = parse_reminder_tokens(
            text, now=datetime.now(), parse_datetime=self._parse_date
        )

        # Completion-based recurrence marker ("every!" → re-anchor to completion).
        completion_marker = bool(re.search(r"\bevery\s*!", text, re.IGNORECASE))
        if completion_marker:
            text = re.sub(r"\b(every)\s*!", r"\1", text, flags=re.IGNORECASE)

        # Explicit "no date" / "no due date" → clear any due date.
        if re.search(r"\bno (?:due )?date\b", text, re.IGNORECASE):
            result["due_date_cleared"] = True
            text = re.sub(r"\bno (?:due )?date\b", " ", text, flags=re.IGNORECASE)

        # Extract recurrence before the date pass, so phrases like "every monday"
        # don't also resolve to a one-off due date.
        recurrence = self._parse_recurrence(text)
        anchor: dict[str, Any] | None = None
        if recurrence:
            result["recurrence_rule"] = recurrence["rule"]
            result["recurrence_label"] = recurrence["label"]
            result["recurrence_from_completion"] = completion_marker
            weekdays = recurrence.get("weekday_nums")
            monthday = recurrence.get("monthday")
            if weekdays or monthday:
                anchor = {"weekdays": weekdays, "monthday": monthday}
            text = re.sub(
                re.escape(recurrence["matched"]),
                " ",
                text,
                count=1,
                flags=re.IGNORECASE,
            )

        # Parse date — pass the recurrence anchor so "every sat at 17" / "every mon
        # and thu at 21" / "every 15th at 2" set due on the soonest recurrence
        # weekday or day-of-month, not today.
        result["due_date"] = self._parse_date(text, anchor=anchor)
        if result["due_date"]:
            # Remove parsed date phrases from text
            text = self._remove_date_phrases(text)

        # Clean up the content
        result["content"] = " ".join(text.split()).strip()

        return result

    @staticmethod
    def _monthly_interval_result(
        interval: int, base_label: str, day: str | None, matched: str
    ) -> dict[str, Any]:
        """Build a monthly-interval recurrence result (quarterly = 3, half-year = 6).

        When an "on the Nth" day was captured, add a BYMONTHDAY clause and expose a
        ``monthday`` anchor so the first due date lands on that day-of-month.
        """
        result: dict[str, Any] = {
            "rule": f"FREQ=MONTHLY;INTERVAL={interval}",
            "label": base_label,
            "matched": matched,
        }
        if day:
            d = int(day)
            if 1 <= d <= 31:
                result["rule"] = f"FREQ=MONTHLY;INTERVAL={interval};BYMONTHDAY={d}"
                result["label"] = f"{base_label} on the {d}{_ordinal_suffix(d)}"
                result["monthday"] = d
        return result

    def _parse_recurrence(self, text: str) -> dict[str, Any] | None:
        """Detect a recurrence pattern.

        Returns a dict with 'rule' (iCalendar RRULE), 'label' (human-readable),
        and 'matched' (the substring to strip), plus optional anchor hints
        ('weekday_nums' / 'monthday'), or None. First match wins; patterns are
        ordered specific → general.
        """
        lower = text.lower()

        # every N days/weeks/months/years
        m = re.search(r"\bevery\s+(\d+)\s+(day|week|month|year)s?\b", lower)
        if m:
            interval = int(m.group(1))
            freq = _UNIT_FREQ[m.group(2)]
            noun = _FREQ_NOUN[freq]
            label = f"Every {noun}" if interval == 1 else f"Every {interval} {noun}s"
            return {
                "rule": f"FREQ={freq};INTERVAL={interval}",
                "label": label,
                "matched": m.group(0),
            }

        # every other day/week/month/year → interval 2
        m = re.search(r"\bevery\s+other\s+(day|week|month|year)\b", lower)
        if m:
            freq = _UNIT_FREQ[m.group(1)]
            return {
                "rule": f"FREQ={freq};INTERVAL=2",
                "label": f"Every other {m.group(1)}",
                "matched": m.group(0),
            }

        # every month on the Nth / every Nth [of [the] month] → monthly by month-day
        m = re.search(
            r"\bevery\s+month\s+on\s+the\s+(\d{1,2})(?:st|nd|rd|th)\b", lower
        ) or re.search(
            r"\bevery\s+(\d{1,2})(?:st|nd|rd|th)(?:\s+of(?:\s+the)?\s+month)?\b", lower
        )
        if m:
            day = int(m.group(1))
            if 1 <= day <= 31:
                return {
                    "rule": f"FREQ=MONTHLY;BYMONTHDAY={day}",
                    "label": f"Monthly on the {day}{_ordinal_suffix(day)}",
                    "matched": m.group(0),
                    "monthday": day,
                }

        # quarterly — every N quarters / every quarter / quarterly [on the Nth]
        m = re.search(r"\bevery\s+(\d+)\s+quarters?\b", lower)
        if m:
            n = int(m.group(1))
            return {
                "rule": f"FREQ=MONTHLY;INTERVAL={3 * n}",
                "label": "Quarterly" if n == 1 else f"Every {n} quarters",
                "matched": m.group(0),
            }
        m = re.search(
            r"\b(?:every\s+quarter|quarterly)"
            r"(?:\s+on\s+the\s+(\d{1,2})(?:st|nd|rd|th))?\b",
            lower,
        )
        if m:
            return self._monthly_interval_result(3, "Quarterly", m.group(1), m.group(0))

        # half-yearly — half-yearly / semi-annually / bi-annually / every half year
        # [on the Nth] → monthly every 6 months. Must precede the yearly branch so
        # the trailing "…yearly"/"…annually" doesn't get swallowed as FREQ=YEARLY.
        m = re.search(
            r"\b(?:half[\s-]?yearly|half[\s-]?year|semi[\s-]?annual(?:ly)?"
            r"|bi[\s-]?annual(?:ly)?|every\s+half[\s-]?year)"
            r"(?:\s+on\s+the\s+(\d{1,2})(?:st|nd|rd|th))?\b",
            lower,
        )
        if m:
            return self._monthly_interval_result(
                6, "Half-yearly", m.group(1), m.group(0)
            )

        # every <weekday> and/, <weekday> [and/, <weekday> …] → weekly on multiple days
        m = re.search(
            rf"\bevery\s+((?:{_WEEKDAY_ALT})"
            rf"(?:\s*(?:,\s*(?:and\s*)?|and\s+)(?:{_WEEKDAY_ALT}))+)\b",
            lower,
        )
        if m:
            captured = m.group(1)
            bydays: list[str] = []
            display_names: list[str] = []
            weekday_nums: list[int] = []
            for dm in re.finditer(rf"\b({_WEEKDAY_ALT})\b", captured):
                canonical = _expand_abbreviations(dm.group(1))
                byday = WEEKDAY_RRULE[canonical]
                if byday not in bydays:
                    bydays.append(byday)
                    display_names.append(canonical.capitalize())
                    weekday_nums.append(WEEKDAYS[canonical])
            if len(bydays) >= 2:
                return {
                    "rule": f"FREQ=WEEKLY;BYDAY={','.join(bydays)}",
                    "label": f"Every {', '.join(display_names)}",
                    "matched": m.group(0),
                    "weekday_nums": weekday_nums,
                }

        # every <weekday> (full or abbreviated) → weekly on that day
        m = re.search(rf"\bevery\s+({_WEEKDAY_ALT})\b", lower)
        if m:
            day_word = _expand_abbreviations(m.group(1))
            byday = WEEKDAY_RRULE[day_word]
            return {
                "rule": f"FREQ=WEEKLY;BYDAY={byday}",
                "label": f"Every {day_word.capitalize()}",
                "matched": m.group(0),
                "weekday_nums": [WEEKDAYS[day_word]],
            }

        # daily / everyday / every day
        if re.search(r"\b(?:everyday|every\s+day|daily)\b", lower):
            m = re.search(r"\b(?:everyday|every\s+day|daily)\b", lower)
            return {
                "rule": "FREQ=DAILY;INTERVAL=1",
                "label": "Daily",
                "matched": m.group(0),
            }

        # weekly / every week
        if re.search(r"\b(?:every\s+week|weekly)\b", lower):
            m = re.search(r"\b(?:every\s+week|weekly)\b", lower)
            return {
                "rule": "FREQ=WEEKLY;INTERVAL=1",
                "label": "Weekly",
                "matched": m.group(0),
            }

        # monthly / every month
        if re.search(r"\b(?:every\s+month|monthly)\b", lower):
            m = re.search(r"\b(?:every\s+month|monthly)\b", lower)
            return {
                "rule": "FREQ=MONTHLY;INTERVAL=1",
                "label": "Monthly",
                "matched": m.group(0),
            }

        # yearly / annually / every year
        if re.search(r"\b(?:every\s+year|yearly|annually)\b", lower):
            m = re.search(r"\b(?:every\s+year|yearly|annually)\b", lower)
            return {
                "rule": "FREQ=YEARLY;INTERVAL=1",
                "label": "Yearly",
                "matched": m.group(0),
            }

        return None

    def _parse_date(
        self, text: str, anchor: dict[str, Any] | None = None
    ) -> datetime | None:
        """Parse date from text.

        Args:
            text: Text potentially containing date phrase
            anchor: Recurrence anchor from the recurrence pattern — a dict with
                optional 'weekdays' (Python weekday() indices, Mon=0…Sun=6) and/or
                'monthday' (1–31). When only a time is found, the due date is placed
                on the soonest matching weekday or day-of-month rather than today.

        Returns:
            Parsed datetime or None
        """
        # Always try simple pattern matching first — reliable for full sentences
        simple_result = self._simple_date_parse(text, anchor=anchor)
        if simple_result:
            return simple_result

        if HAS_DATEPARSER:
            # Extract date-related tokens and pass only those to dateparser
            fragment = self._extract_date_fragment(text)
            if fragment:
                return dateparser.parse(
                    fragment,
                    settings={
                        "PREFER_DATES_FROM": "future",
                        "RELATIVE_BASE": datetime.now(),
                    },
                )

        return None

    def _extract_date_fragment(self, text: str) -> str | None:
        """Extract date-related tokens from text for dateparser."""
        patterns = [
            r"\bnext \w+\b",
            r"\bin \d+ \w+\b",
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?\b",
            r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
            r"\bat \d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
        ]
        fragments = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            fragments.extend(matches)
        return " ".join(fragments) if fragments else None

    def _simple_date_parse(
        self, text: str, anchor: dict[str, Any] | None = None
    ) -> datetime | None:
        """Simple date parsing fallback without dateparser.

        Args:
            text: Text to parse
            anchor: Recurrence anchor ('weekdays' and/or 'monthday'). When set and
                only a time is found (no date keyword), the due date is placed on the
                soonest upcoming matching weekday or day-of-month rather than today.

        Returns:
            Parsed datetime or None
        """
        now = datetime.now()
        # Expand abbreviations (tom → tomorrow, mon → monday, …) for detection only.
        # Weekday abbreviations expand only with date context (see
        # _expand_free_text_abbreviations) so prose like Vietnamese "thu" isn't read
        # as Thursday.
        text_lower = _expand_free_text_abbreviations(text.lower())

        # Extract time component: explicit "at HH[:MM][am/pm]" or a time-of-day word
        # ("morning"/"evening"/"noon"/…).
        time_hour: int | None = None
        time_minute: int = 0
        time_match = re.search(
            r"\bat (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower
        ) or re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text_lower)
        if time_match:
            time_hour = int(time_match.group(1))
            time_minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)
            if meridiem == "pm" and time_hour < 12:
                time_hour += 12
            elif meridiem == "am" and time_hour == 12:
                time_hour = 0
        else:
            tod = re.search(
                r"\b(?:in the\s+|this\s+|at\s+)?"
                r"(morning|afternoon|evening|night|noon|midnight)\b",
                text_lower,
            )
            if tod:
                time_hour, time_minute = TIME_OF_DAY[tod.group(1)]

        def _apply_time(dt: datetime) -> datetime:
            if time_hour is not None:
                return dt.replace(
                    hour=time_hour, minute=time_minute, second=0, microsecond=0
                )
            return dt.replace(hour=23, minute=59, second=59, microsecond=0)

        # Today
        if "today" in text_lower:
            return _apply_time(now)

        # Tonight → today, defaulting to 20:00 unless an explicit time was given
        if "tonight" in text_lower:
            if time_hour is not None:
                return now.replace(
                    hour=time_hour, minute=time_minute, second=0, microsecond=0
                )
            return now.replace(hour=20, minute=0, second=0, microsecond=0)

        # Tomorrow
        if "tomorrow" in text_lower:
            return _apply_time(now + timedelta(days=1))

        # Yesterday
        if "yesterday" in text_lower:
            return _apply_time(now - timedelta(days=1))

        # Someday → roughly two months out (Todoist convention)
        if "someday" in text_lower:
            return _apply_time(_add_months(now, 2))

        # End of month → last day of the current month
        if "end of month" in text_lower or "end of the month" in text_lower:
            import calendar

            last = calendar.monthrange(now.year, now.month)[1]
            return _apply_time(now.replace(day=last))

        # Mid <month> / mid-month → the 15th
        m = re.search(rf"\bmid[\s-]?({_MONTH_ALT})\b", text_lower)
        if m:
            resolved = _resolve_md(MONTHS[m.group(1)[:3]], 15, None, now)
            if resolved is not None:
                return _apply_time(resolved)
        if re.search(r"\bmid[\s-]?month\b", text_lower):
            return _apply_time(_monthday_this_or_next(now, 15))

        # This / next weekend → Saturday (this week / +1 week); later this week → Friday
        if "this weekend" in text_lower:
            return _apply_time(_coming_weekday(now, 5))
        if "next weekend" in text_lower:
            return _apply_time(_coming_weekday(now, 5) + timedelta(days=7))
        if "later this week" in text_lower:
            return _apply_time(_coming_weekday(now, 4))

        # Next week / month / year
        if "next week" in text_lower:
            return _apply_time(now + timedelta(days=7))
        if "next month" in text_lower:
            return _apply_time(_add_months(now, 1))
        if "next year" in text_lower:
            return _apply_time(now.replace(year=now.year + 1))

        # In/within/+ N days/weeks/months/years/hours/minutes
        match = re.search(
            r"\b(?:in|within|\+)\s*(\d+)\s*"
            r"(day|week|month|year|hour|hr|minute|min)s?\b",
            text_lower,
        )
        if match:
            n = int(match.group(1))
            unit = match.group(2)
            if unit in ("hour", "hr"):
                return (now + timedelta(hours=n)).replace(second=0, microsecond=0)
            if unit in ("minute", "min"):
                return (now + timedelta(minutes=n)).replace(second=0, microsecond=0)
            if unit == "day":
                return _apply_time(now + timedelta(days=n))
            if unit == "week":
                return _apply_time(now + timedelta(weeks=n))
            if unit == "month":
                return _apply_time(_add_months(now, n))
            if unit == "year":
                return _apply_time(now.replace(year=now.year + n))

        # Explicit calendar date (ISO / month-name / numeric) — before the weekday
        # and ordinal branches so "jan 27" wins over a bare "27th".
        cal = _parse_calendar_date(text_lower, now)
        if cal is not None:
            return _apply_time(cal)

        # Recurrence anchor + time: when the caller supplied an anchor (from "every tue
        # and thu at 21"), use the soonest matching weekday/monthday rather than any
        # weekday name that may remain in the task title after recurrence stripping.
        if time_hour is not None and anchor:
            weekdays = anchor.get("weekdays")
            monthday = anchor.get("monthday")
            if weekdays:
                days_ahead = min((d - now.weekday()) % 7 or 7 for d in weekdays)
                return _apply_time(now + timedelta(days=days_ahead))
            if monthday:
                return _apply_time(_next_monthday(now, monthday))

        # Weekdays
        for day_name, day_num in WEEKDAYS.items():
            if day_name in text_lower:
                # Find next occurrence of this weekday
                current_weekday = now.weekday()
                days_ahead = (day_num - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week if today
                target = now + timedelta(days=days_ahead)
                return _apply_time(target)

        # Day-of-month ordinals: "1st", "on the 24th", "2nd of month" → next such day
        ordinal_match = re.search(
            r"\b(?:on\s+)?(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)"
            r"(?:\s+of(?:\s+the)?\s+month)?\b",
            text_lower,
        )
        if ordinal_match:
            day = int(ordinal_match.group(1))
            if 1 <= day <= 31:
                today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                target = today_midnight.replace(day=1)
                # Try the current month; if that day already passed, roll to next month.
                this_month = _safe_replace_day(today_midnight, day)
                if this_month is not None and this_month >= today_midnight:
                    target = this_month
                else:
                    nxt = _add_months(today_midnight.replace(day=1), 1)
                    target = _safe_replace_day(nxt, day) or nxt
                return _apply_time(target)

        # Time only (e.g. "at 22") with no date keyword and no recurrence anchor.
        if time_hour is not None:
            return _apply_time(now)

        return None

    def _remove_date_phrases(self, text: str) -> str:
        """Remove common date phrases from text.

        Args:
            text: Text with date phrases

        Returns:
            Text with date phrases removed
        """
        date_phrases = [
            # Relative day keywords + abbreviations
            r"\btoday\b",
            r"\btomorrow\b",
            r"\byesterday\b",
            r"\btonight\b",
            r"\bsomeday\b",
            r"\b(?:tmrw|tmr|tom|tdy|yest)\b",
            # Fuzzy dates
            r"\bend of (?:the )?month\b",
            rf"\bmid[\s-]?(?:{_MONTH_ALT}|month)\b",
            r"\b(?:this|next) weekend\b",
            r"\blater this week\b",
            # next/this {week,month,year}
            r"\b(?:next|this)\s+(?:week|month|year)\b",
            # in/within/+ N units
            r"\b(?:in|within|\+)\s*\d+\s*(?:day|week|month|year|hour|hr|minute|min)s?\b",
            # Calendar dates: ISO, month-name (both orders), numeric
            r"\b\d{4}-\d{1,2}-\d{1,2}\b",
            rf"\b(?:{_MONTH_ALT})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b",
            rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTH_ALT})(?:,?\s+\d{{4}})?\b",
            r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
            # Weekdays (optionally prefixed by next/this), full + abbreviated
            rf"\b(?:next|this)\s+(?:{_WEEKDAY_ALT})\b",
            r"\bmonday\b",
            r"\btuesday\b",
            r"\bwednesday\b",
            r"\bthursday\b",
            r"\bfriday\b",
            r"\bsaturday\b",
            r"\bsunday\b",
            # Day-of-month ordinals: "1st", "on the 24th", "2nd of month"
            r"\b(?:on\s+)?(?:the\s+)?\d{1,2}(?:st|nd|rd|th)(?:\s+of(?:\s+the)?\s+month)?\b",
            # Time-of-day words
            r"\b(?:in the\s+|this\s+|at\s+)?(?:morning|afternoon|evening|night|noon|midnight)\b",
            # Time
            r"\bat \d{1,2}:\d{2}\s*[ap]m\b",
            r"\bat \d{1,2}\s*[ap]m\b",
            r"\bat \d{1,2}:\d{2}\b",
            r"\bat \d{1,2}\b",
            r"\b\d{1,2}(?::\d{2})?\s*[ap]m\b",  # bare "8am" / "6pm" / "7:30pm"
        ]

        # Strip context-legitimized weekday abbreviations first, against the untouched
        # text so later removals don't shift the "trailing" context (e.g. "review thu
        # tomorrow" must keep "thu"). Only the weekday token is removed; cue/time are
        # preserved and handled by the patterns below.
        def _strip_wd(m: "re.Match[str]") -> str:
            if not _weekday_has_context(m):
                return m.group(0)
            return (m.group("cue") or "") + " " + (m.group("after") or "")

        text = _CONTEXT_WEEKDAY_RE.sub(_strip_wd, text)

        for pattern in date_phrases:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text


def parse_natural_language(text: str) -> dict[str, Any]:
    """Convenience function to parse natural language task description.

    Args:
        text: Natural language task description

    Returns:
        Parsed metadata dict

    Example:
        >>> parse_natural_language("Review PR tomorrow #Work p1 @urgent")
        {
            'content': 'Review PR',
            'due_date': datetime(...),
            'priority': 1,
            'project_name': 'Work',
            'labels': ['urgent']
        }
    """
    parser = LocalNLPParser()
    return parser.parse(text)
