"""Auto-fix engine for sync-push validation failures.

Python mirror of the SPA's ``src/lib/sync/auto-fix.ts``. When ``todopro sync
push`` sends a local change the backend rejects with a permanent (4xx)
validation error, we correct the mechanically-fixable cases (text over the
length limit, a malformed hex color), re-push, and tell the user plainly —
instead of surfacing a raw, unactionable exception. Anything we can't fix is
reported with the item name + reason so the user knows what to edit.

Pure module (no I/O) so it's easy to unit-test; ``sync_service`` applies the
result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

# Server-enforced max lengths (todopro-core-svc serializers), keyed by the field
# name each payload sends. Unknown fields fall back to parsing the server
# message ("...must not exceed N characters").
LENGTH_LIMITS: dict[str, dict[str, int]] = {
    "task": {"content": 500, "description": 10000},
    "project": {"name": 120},
    "section": {"name": 100},
    "label": {"name": 50},
}

FIELD_LABELS: dict[str, str] = {
    "content": "title",
    "description": "description",
    "name": "name",
    "color": "color",
}

DEFAULT_LABEL_COLOR = "#808080"


@dataclass
class ApiError:
    """Structured view of a failed request body."""

    status: int | None = None
    code: str | None = None
    detail: dict[str, str] = field(default_factory=dict)

    @property
    def upgrade_url(self) -> str | None:
        return self.detail.get("upgrade_url")

    @property
    def first_reason(self) -> str | None:
        for key, value in self.detail.items():
            if key not in ("_", "upgrade_url"):
                return value
        return self.detail.get("_")


def parse_api_error(exc: httpx.HTTPStatusError) -> ApiError:
    """Extract status + field-level detail from a failed request.

    Handles the backend's wrapped shape
    ``{"error": {"code", "message", "details": {field: msg}}}`` and plain DRF
    ``{field: [msg]}``.
    """
    resp = exc.response
    status = resp.status_code if resp is not None else None
    try:
        data: Any = resp.json() if resp is not None else None
    except Exception:
        data = None
    if not isinstance(data, dict):
        return ApiError(status=status)

    detail: dict[str, str] = {}
    code: str | None = None

    wrapped = data.get("error")
    if isinstance(wrapped, dict):
        raw_code = wrapped.get("code")
        code = raw_code if isinstance(raw_code, str) else None
        details = wrapped.get("details")
        if isinstance(details, dict):
            for key, value in details.items():
                detail[key] = (
                    str(value[0]) if isinstance(value, list) and value else str(value)
                )
        if not detail and isinstance(wrapped.get("message"), str):
            detail["_"] = wrapped["message"]
    else:
        for key, value in data.items():
            if isinstance(value, list) and value:
                detail[key] = str(value[0])
            elif isinstance(value, str):
                detail[key] = value

    return ApiError(status=status, code=code, detail=detail)


def is_permanent_failure(err: ApiError) -> bool:
    """A 4xx (except 429) — retrying as-is won't help; the data must change."""
    return err.status is not None and 400 <= err.status < 500 and err.status != 429


def is_pro_required(err: ApiError) -> bool:
    """Pro-gated 402 — the field is valid, just gated; not mechanically fixable."""
    return err.status == 402 or err.code == "pro_required"


def normalize_hex_color(value: Any) -> str:
    """Normalize a hex color to ``#rrggbb``; expand ``#rgb``; add a missing ``#``."""
    if not isinstance(value, str):
        return DEFAULT_LABEL_COLOR
    s = value.strip()
    if s == "":
        return DEFAULT_LABEL_COLOR
    if not s.startswith("#"):
        s = f"#{s}"
    if re.fullmatch(r"#[0-9a-fA-F]{3}", s):
        s = "#" + "".join(c * 2 for c in s[1:])
    if re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        return s.lower()
    return DEFAULT_LABEL_COLOR


def _length_limit_for(
    entity_type: str, field_name: str, message: str | None
) -> int | None:
    known = LENGTH_LIMITS.get(entity_type, {}).get(field_name)
    if known is not None:
        return known
    # Fallback: parse "...no more than N characters" / "...must not exceed N
    # characters". Numbers may carry spaces/commas ("10 000 characters").
    if message:
        match = re.search(r"([\d][\d\s,]*)\s*characters", message, re.IGNORECASE)
        if match:
            try:
                return int(re.sub(r"[\s,]", "", match.group(1)))
            except ValueError:
                return None
    return None


def _looks_like_length_error(message: str | None) -> bool:
    if not message:
        return False
    return bool(
        re.search(
            r"exceed|no more than|too long|characters|at most", message, re.IGNORECASE
        )
    )


def _looks_like_color_error(field_name: str, message: str | None) -> bool:
    if field_name != "color":
        return False
    if not message:
        return True  # a color-field error we can't read — try to normalize anyway
    return bool(re.search(r"hex|color|#rrggbb|format", message, re.IGNORECASE))


@dataclass
class AppliedFieldFix:
    field: str
    label: str
    kind: str  # "truncate" | "color"
    from_length: int | None = None
    to_length: int | None = None


@dataclass
class AutoFixResult:
    overrides: dict[str, Any]
    fixes: list[AppliedFieldFix]


def compute_auto_fix(
    entity_type: str,
    values: dict[str, Any],
    err: ApiError,
) -> AutoFixResult | None:
    """Compute mechanical corrections for a rejected payload, or ``None``.

    All-or-nothing: if any rejected field can't be fixed (unknown field, missing
    from the payload, Pro-gated) return ``None`` so the caller surfaces the whole
    item — fixing only some fields would just re-fail.
    """
    if not err.detail or is_pro_required(err):
        return None

    overrides: dict[str, Any] = {}
    fixes: list[AppliedFieldFix] = []

    for field_name, message in err.detail.items():
        if field_name == "_":
            # A generic message with no field we can target.
            return None
        current = values.get(field_name)
        label = FIELD_LABELS.get(field_name, field_name)

        # Length overflow → truncate to the server limit.
        limit = _length_limit_for(entity_type, field_name, message)
        if (
            limit is not None
            and isinstance(current, str)
            and (len(current) > limit or _looks_like_length_error(message))
        ):
            if len(current) <= limit:
                # Message claims a length error but the value already fits — we
                # can't safely correct this; bail on the whole item.
                return None
            truncated = current[:limit].rstrip()
            overrides[field_name] = truncated
            fixes.append(
                AppliedFieldFix(
                    field_name, label, "truncate", len(current), len(truncated)
                )
            )
            continue

        # Malformed color → normalize to #rrggbb.
        if _looks_like_color_error(field_name, message):
            overrides[field_name] = normalize_hex_color(current)
            fixes.append(AppliedFieldFix(field_name, label, "color"))
            continue

        # A rejected field we don't know how to fix → not auto-fixable.
        return None

    if not fixes:
        return None
    return AutoFixResult(overrides=overrides, fixes=fixes)


def describe_fix(_entity_type: str, fixes: list[AppliedFieldFix]) -> str:
    """Short, plain description of an applied fix, for console output.

    ``_entity_type`` is accepted for parity with the SPA signature; the caller
    already prints the entity type around this message.
    """
    if len(fixes) == 1:
        f = fixes[0]
        if f.kind == "truncate":
            return f"shortened {f.label} to fit ({f.to_length} characters)"
        return "reset an invalid color"
    labels = " and ".join(f.label for f in fixes)
    return f"adjusted {labels}"
