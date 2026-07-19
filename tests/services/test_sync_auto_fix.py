"""Unit tests for the sync auto-fix engine (services/sync_auto_fix.py).

Mirror of the SPA's src/lib/sync/auto-fix.test.ts.
"""

from __future__ import annotations

import httpx

from todopro_cli.services.sync_auto_fix import (
    ApiError,
    compute_auto_fix,
    describe_fix,
    is_permanent_failure,
    is_pro_required,
    normalize_hex_color,
    parse_api_error,
)


def _http_error(status: int, body: dict | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://example.test/api")
    response = httpx.Response(
        status, json=body if body is not None else {}, request=request
    )
    return httpx.HTTPStatusError("boom", request=request, response=response)


class TestNormalizeHexColor:
    def test_adds_missing_hash_and_lowercases(self):
        assert normalize_hex_color("AABBCC") == "#aabbcc"

    def test_expands_shorthand(self):
        assert normalize_hex_color("#abc") == "#aabbcc"

    def test_falls_back_for_garbage(self):
        assert normalize_hex_color("not-a-color") == "#808080"
        assert normalize_hex_color("") == "#808080"
        assert normalize_hex_color(123) == "#808080"


class TestParseApiError:
    def test_parses_wrapped_backend_shape(self):
        err = parse_api_error(
            _http_error(
                400,
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": {
                            "content": "Content must not exceed 500 characters"
                        },
                    }
                },
            )
        )
        assert err.status == 400
        assert err.code == "VALIDATION_ERROR"
        assert err.detail["content"].endswith("500 characters")

    def test_parses_plain_drf_shape(self):
        err = parse_api_error(
            _http_error(
                400, {"content": ["Ensure this has no more than 500 characters."]}
            )
        )
        assert err.detail["content"].startswith("Ensure this")

    def test_pro_required_402(self):
        err = parse_api_error(
            _http_error(
                402,
                {
                    "error": {
                        "code": "pro_required",
                        "details": {"upgrade_url": "https://x/pricing"},
                    }
                },
            )
        )
        assert is_pro_required(err)
        assert err.upgrade_url == "https://x/pricing"

    def test_non_json_body_is_tolerated(self):
        request = httpx.Request("POST", "http://example.test/api")
        response = httpx.Response(400, text="Bad Request", request=request)
        err = parse_api_error(
            httpx.HTTPStatusError("boom", request=request, response=response)
        )
        assert err.status == 400
        assert err.detail == {}


class TestFailureClassification:
    def test_permanent(self):
        assert is_permanent_failure(ApiError(status=400))
        assert is_permanent_failure(ApiError(status=402))
        assert not is_permanent_failure(ApiError(status=429))
        assert not is_permanent_failure(ApiError(status=500))
        assert not is_permanent_failure(ApiError(status=None))

    def test_pro_required(self):
        assert is_pro_required(ApiError(status=402))
        assert is_pro_required(ApiError(status=400, code="pro_required"))
        assert not is_pro_required(ApiError(status=400, code="VALIDATION_ERROR"))


class TestComputeAutoFix:
    def test_truncates_over_length_task_title(self):
        result = compute_auto_fix(
            "task",
            {"content": "x" * 620},
            ApiError(
                status=400, detail={"content": "Content must not exceed 500 characters"}
            ),
        )
        assert result is not None
        assert len(result.overrides["content"]) == 500
        assert result.fixes[0].kind == "truncate"
        assert result.fixes[0].from_length == 620
        assert result.fixes[0].to_length == 500

    def test_truncates_description_with_spaced_number(self):
        result = compute_auto_fix(
            "task",
            {"description": "y" * 10_050},
            ApiError(
                status=400,
                detail={"description": "Description must not exceed 10 000 characters"},
            ),
        )
        assert result is not None
        assert len(result.overrides["description"]) == 10_000

    def test_normalizes_bad_label_color(self):
        result = compute_auto_fix(
            "label",
            {"name": "urgent", "color": "red"},
            ApiError(
                status=400, detail={"color": "Color must be in hex format (#RRGGBB)"}
            ),
        )
        assert result is not None
        assert result.overrides["color"] == "#808080"
        assert result.fixes[0].kind == "color"

    def test_multiple_fields(self):
        result = compute_auto_fix(
            "task",
            {"content": "a" * 600, "description": "b" * 20_000},
            ApiError(
                status=400,
                detail={
                    "content": "Content must not exceed 500 characters",
                    "description": "Description must not exceed 10 000 characters",
                },
            ),
        )
        assert result is not None
        assert len(result.fixes) == 2

    def test_returns_none_for_pro_required(self):
        result = compute_auto_fix(
            "task",
            {"deadline": "2026-07-10"},
            ApiError(
                status=402, code="pro_required", detail={"upgrade_url": "https://x"}
            ),
        )
        assert result is None

    def test_returns_none_when_any_field_unfixable(self):
        result = compute_auto_fix(
            "task",
            {"content": "a" * 600},
            ApiError(
                status=400,
                detail={
                    "content": "Content must not exceed 500 characters",
                    "project": "Invalid project.",
                },
            ),
        )
        assert result is None

    def test_returns_none_without_detail(self):
        assert compute_auto_fix("task", {}, ApiError(status=400)) is None


class TestDescribeFix:
    def test_single_truncate(self):
        result = compute_auto_fix(
            "task",
            {"content": "x" * 600},
            ApiError(
                status=400, detail={"content": "Content must not exceed 500 characters"}
            ),
        )
        assert result is not None
        assert "shortened title to fit (500 characters)" in describe_fix(
            "task", result.fixes
        )
