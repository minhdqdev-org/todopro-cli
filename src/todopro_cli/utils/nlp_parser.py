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

        # Parse date
        result["due_date"] = self._parse_date(text)
        if result["due_date"]:
            # Remove parsed date phrases from text
            text = self._remove_date_phrases(text)

        # Clean up the content
        result["content"] = " ".join(text.split()).strip()

        return result

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
                parsed = dateparser.parse(
                    fragment,
                    settings={
                        "PREFER_DATES_FROM": "future",
                        "RELATIVE_BASE": datetime.now(),
                    },
                )
                return parsed

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
        text_lower = text.lower()

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

        # Tomorrow
        if "tomorrow" in text_lower:
            return _apply_time(now + timedelta(days=1))

        # Next week
        if "next week" in text_lower:
            return _apply_time(now + timedelta(days=7))

        # In N days
        match = re.search(r"in (\d+) days?", text_lower)
        if match:
            days = int(match.group(1))
            return _apply_time(now + timedelta(days=days))

        # Weekdays
        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        for day_name, day_num in weekdays.items():
            if day_name in text_lower:
                # Find next occurrence of this weekday
                current_weekday = now.weekday()
                days_ahead = (day_num - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week if today
                target = now + timedelta(days=days_ahead)
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
            r"\btoday\b",
            r"\btomorrow\b",
            r"\bnext week\b",
            r"\bin \d+ days?\b",
            r"\bmonday\b",
            r"\btuesday\b",
            r"\bwednesday\b",
            r"\bthursday\b",
            r"\bfriday\b",
            r"\bsaturday\b",
            r"\bsunday\b",
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
