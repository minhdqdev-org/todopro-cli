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


class LocalNLPParser:
    """Parse natural language task descriptions locally."""

    def __init__(self):
        """Initialize the parser."""
        self.priority_patterns = {
            r"\bp1\b|!!1|!!!|urgent": 4,
            r"\bp2\b|!!2|high": 3,
            r"\bp3\b|!!3|medium": 2,
            r"\bp4\b|!!4|low": 1,
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
            "recurrence_rule": None,
            "recurrence_label": None,
            "priority": None,
            "project_name": None,
            "labels": [],
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

        # Extract recurrence before the date pass, so phrases like "every monday"
        # don't also resolve to a one-off due date.
        recurrence = self._parse_recurrence(text)
        if recurrence:
            result["recurrence_rule"] = recurrence["rule"]
            result["recurrence_label"] = recurrence["label"]
            text = re.sub(
                re.escape(recurrence["matched"]),
                " ",
                text,
                count=1,
                flags=re.IGNORECASE,
            )

        # Parse date
        result["due_date"] = self._parse_date(text)
        if result["due_date"]:
            # Remove parsed date phrases from text
            text = self._remove_date_phrases(text)

        # Clean up the content
        result["content"] = " ".join(text.split()).strip()

        return result

    def _parse_recurrence(self, text: str) -> dict[str, Any] | None:
        """Detect a recurrence pattern.

        Returns a dict with 'rule' (iCalendar RRULE), 'label' (human-readable),
        and 'matched' (the substring to strip), or None. First match wins;
        patterns are ordered specific → general.
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

    def _parse_date(self, text: str) -> datetime | None:
        """Parse date from text.

        Args:
            text: Text potentially containing date phrase

        Returns:
            Parsed datetime or None
        """
        # Always try simple pattern matching first — reliable for full sentences
        simple_result = self._simple_date_parse(text)
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

    def _simple_date_parse(self, text: str) -> datetime | None:
        """Simple date parsing fallback without dateparser.

        Args:
            text: Text to parse

        Returns:
            Parsed datetime or None
        """
        now = datetime.now()
        # Expand abbreviations (tom → tomorrow, mon → monday, …) for detection only.
        text_lower = _expand_abbreviations(text.lower())

        # Extract time component: "at HH", "at HH:MM", "at HHam/pm"
        time_hour: int | None = None
        time_minute: int = 0
        time_match = re.search(r"\bat (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
        if time_match:
            time_hour = int(time_match.group(1))
            time_minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)
            if meridiem == "pm" and time_hour < 12:
                time_hour += 12
            elif meridiem == "am" and time_hour == 12:
                time_hour = 0

        def _apply_time(dt: datetime) -> datetime:
            if time_hour is not None:
                return dt.replace(
                    hour=time_hour, minute=time_minute, second=0, microsecond=0
                )
            return dt.replace(hour=23, minute=59, second=59)

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

        # Next week / month / year
        if "next week" in text_lower:
            return _apply_time(now + timedelta(days=7))
        if "next month" in text_lower:
            return _apply_time(_add_months(now, 1))
        if "next year" in text_lower:
            return _apply_time(now.replace(year=now.year + 1))

        # In N days
        match = re.search(r"in (\d+) days?", text_lower)
        if match:
            days = int(match.group(1))
            return _apply_time(now + timedelta(days=days))

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

        # Time only (e.g. "at 22") with no date keyword — assume today
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
            r"\b(?:tmrw|tmr|tom|tdy|yest)\b",
            # next/this {week,month,year}
            r"\b(?:next|this)\s+(?:week|month|year)\b",
            r"\bin \d+ days?\b",
            # Weekdays (optionally prefixed by next/this), full + abbreviated
            rf"\b(?:next|this)\s+(?:{_WEEKDAY_ALT})\b",
            r"\bmonday\b",
            r"\btuesday\b",
            r"\bwednesday\b",
            r"\bthursday\b",
            r"\bfriday\b",
            r"\bsaturday\b",
            r"\bsunday\b",
            r"\b(?:mon|tues|tue|wed|thurs|thur|thu|fri|sat|sun)\b",
            # Day-of-month ordinals: "1st", "on the 24th", "2nd of month"
            r"\b(?:on\s+)?(?:the\s+)?\d{1,2}(?:st|nd|rd|th)(?:\s+of(?:\s+the)?\s+month)?\b",
            # Time
            r"\bat \d{1,2}:\d{2}\s*[ap]m\b",
            r"\bat \d{1,2}\s*[ap]m\b",
            r"\bat \d{1,2}:\d{2}\b",
            r"\bat \d{1,2}\b",
        ]

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
            'priority': 4,
            'project_name': 'Work',
            'labels': ['urgent']
        }
    """
    parser = LocalNLPParser()
    return parser.parse(text)
