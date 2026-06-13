"""Recurrence utility functions for the TodoPro CLI."""

# Maps human-friendly names to iCalendar RRULE strings.
# Uses the explicit-INTERVAL style emitted by the natural-language parser
# (utils/nlp_parser.py) and the backend's RECURRENCE_TEMPLATES, so all TodoPro
# clients produce one canonical RRULE form. describe_rrule additionally accepts
# the equivalent short form (INTERVAL omitted, e.g. "FREQ=DAILY") so tasks
# persisted before this unification still round-trip correctly.
RECURRENCE_PATTERNS: dict[str, str] = {
    "daily": "FREQ=DAILY;INTERVAL=1",
    "weekdays": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    "weekly": "FREQ=WEEKLY;INTERVAL=1",
    "bi-weekly": "FREQ=WEEKLY;INTERVAL=2",
    "monthly": "FREQ=MONTHLY;INTERVAL=1",
}

VALID_PATTERNS = list(RECURRENCE_PATTERNS.keys())

# Backend / legacy short-form RRULEs (INTERVAL omitted) mapped to pattern names,
# so describe_rrule round-trips both the CLI's canonical form and the backend's.
_LEGACY_ALIASES: dict[str, str] = {
    "FREQ=DAILY": "daily",
    "FREQ=WEEKLY": "weekly",
    "FREQ=MONTHLY": "monthly",
}


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

    Recognises both the CLI's canonical form ("FREQ=DAILY;INTERVAL=1") and the
    backend's short form ("FREQ=DAILY").

    Args:
        rrule: iCalendar RRULE string

    Returns:
        Human-readable description, or the RRULE itself if unrecognised
    """
    reverse = {v: k for k, v in RECURRENCE_PATTERNS.items()}
    if rrule in reverse:
        return reverse[rrule]
    return _LEGACY_ALIASES.get(rrule, rrule)
