"""Recurrence utility functions for the TodoPro CLI."""

# Maps human-friendly names to iCalendar RRULE strings.
# These match the backend's RECURRENCE_TEMPLATES in
# tasks/services/recurrence_service.py.
RECURRENCE_PATTERNS: dict[str, str] = {
    "daily": "FREQ=DAILY",
    "weekdays": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    "weekly": "FREQ=WEEKLY",
    "bi-weekly": "FREQ=WEEKLY;INTERVAL=2",
    "monthly": "FREQ=MONTHLY",
}

VALID_PATTERNS = list(RECURRENCE_PATTERNS.keys())


def resolve_rrule(pattern: str) -> str | None:
    """Convert a human-friendly recurrence pattern name to an RRULE string.

    Args:
        pattern: Pattern name (e.g., "daily", "weekly")

    Returns:
        RRULE string, or None if pattern is not recognized
    """
    return RECURRENCE_PATTERNS.get(pattern.lower())


def describe_rrule(rrule: str) -> str:
    """Convert an RRULE string back to a human-readable description.

    Args:
        rrule: iCalendar RRULE string

    Returns:
        Human-readable description
    """
    reverse = {v: k for k, v in RECURRENCE_PATTERNS.items()}
    return reverse.get(rrule, rrule)
