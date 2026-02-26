"""Comprehensive unit tests for todopro_cli.utils.exit_codes.

Covers every constant, helper function, and edge case including
unknown / out-of-range codes.
"""

from __future__ import annotations

import pytest

from todopro_cli.utils.exit_codes import (
    AGENT_ACTIONS,
    ERROR_AUTH_FAILURE,
    ERROR_GENERAL,
    ERROR_INVALID_ARGS,
    ERROR_NETWORK,
    ERROR_NOT_FOUND,
    ERROR_PERMISSION_DENIED,
    SUCCESS,
    get_agent_action,
    get_exit_code_description,
    get_exit_code_name,
)


# ---------------------------------------------------------------------------
# Constant value tests
# ---------------------------------------------------------------------------


class TestExitCodeConstants:
    """Verify the numeric values of every exit-code constant."""

    def test_success_is_zero(self):
        assert SUCCESS == 0

    def test_error_general_is_one(self):
        assert ERROR_GENERAL == 1

    def test_error_invalid_args_is_two(self):
        assert ERROR_INVALID_ARGS == 2

    def test_error_auth_failure_is_three(self):
        assert ERROR_AUTH_FAILURE == 3

    def test_error_network_is_four(self):
        assert ERROR_NETWORK == 4

    def test_error_not_found_is_five(self):
        assert ERROR_NOT_FOUND == 5

    def test_error_permission_denied_is_six(self):
        assert ERROR_PERMISSION_DENIED == 6

    def test_all_constants_are_unique(self):
        """No two exit codes share the same numeric value."""
        codes = [
            SUCCESS,
            ERROR_GENERAL,
            ERROR_INVALID_ARGS,
            ERROR_AUTH_FAILURE,
            ERROR_NETWORK,
            ERROR_NOT_FOUND,
            ERROR_PERMISSION_DENIED,
        ]
        assert len(codes) == len(set(codes))

    def test_all_constants_are_integers(self):
        codes = [
            SUCCESS,
            ERROR_GENERAL,
            ERROR_INVALID_ARGS,
            ERROR_AUTH_FAILURE,
            ERROR_NETWORK,
            ERROR_NOT_FOUND,
            ERROR_PERMISSION_DENIED,
        ]
        for code in codes:
            assert isinstance(code, int), f"Expected int, got {type(code)} for {code}"

    def test_success_is_falsy(self):
        """SUCCESS (0) evaluates as False – useful for shell-style checks."""
        assert not SUCCESS

    def test_error_codes_are_truthy(self):
        """All error codes (nonzero) evaluate as True."""
        error_codes = [
            ERROR_GENERAL,
            ERROR_INVALID_ARGS,
            ERROR_AUTH_FAILURE,
            ERROR_NETWORK,
            ERROR_NOT_FOUND,
            ERROR_PERMISSION_DENIED,
        ]
        for code in error_codes:
            assert code, f"Expected truthy for error code {code}"


# ---------------------------------------------------------------------------
# get_exit_code_name
# ---------------------------------------------------------------------------


class TestGetExitCodeName:
    """Tests for get_exit_code_name()."""

    @pytest.mark.parametrize(
        "code, expected_name",
        [
            (SUCCESS, "SUCCESS"),
            (ERROR_GENERAL, "ERROR_GENERAL"),
            (ERROR_INVALID_ARGS, "ERROR_INVALID_ARGS"),
            (ERROR_AUTH_FAILURE, "ERROR_AUTH_FAILURE"),
            (ERROR_NETWORK, "ERROR_NETWORK"),
            (ERROR_NOT_FOUND, "ERROR_NOT_FOUND"),
            (ERROR_PERMISSION_DENIED, "ERROR_PERMISSION_DENIED"),
        ],
    )
    def test_known_code_returns_name(self, code, expected_name):
        assert get_exit_code_name(code) == expected_name

    def test_unknown_code_returns_unknown_label(self):
        result = get_exit_code_name(99)
        assert result == "UNKNOWN(99)"

    def test_unknown_negative_code(self):
        result = get_exit_code_name(-1)
        assert result == "UNKNOWN(-1)"

    def test_unknown_large_code(self):
        result = get_exit_code_name(255)
        assert result == "UNKNOWN(255)"

    def test_return_type_is_str(self):
        assert isinstance(get_exit_code_name(SUCCESS), str)
        assert isinstance(get_exit_code_name(999), str)

    def test_unknown_format_contains_code_value(self):
        """The UNKNOWN(...) label embeds the actual numeric value."""
        code = 42
        result = get_exit_code_name(code)
        assert str(code) in result

    def test_known_codes_do_not_start_with_unknown(self):
        known = [
            SUCCESS,
            ERROR_GENERAL,
            ERROR_INVALID_ARGS,
            ERROR_AUTH_FAILURE,
            ERROR_NETWORK,
            ERROR_NOT_FOUND,
            ERROR_PERMISSION_DENIED,
        ]
        for code in known:
            assert not get_exit_code_name(code).startswith("UNKNOWN")


# ---------------------------------------------------------------------------
# get_exit_code_description
# ---------------------------------------------------------------------------


class TestGetExitCodeDescription:
    """Tests for get_exit_code_description()."""

    @pytest.mark.parametrize(
        "code, expected_fragment",
        [
            (SUCCESS, "successfully"),
            (ERROR_GENERAL, "general error"),
            (ERROR_INVALID_ARGS, "Invalid arguments"),
            (ERROR_AUTH_FAILURE, "Authentication failure"),
            (ERROR_NETWORK, "Network"),
            (ERROR_NOT_FOUND, "not found"),
            (ERROR_PERMISSION_DENIED, "Permission denied"),
        ],
    )
    def test_known_code_description_contains_expected_text(
        self, code, expected_fragment
    ):
        desc = get_exit_code_description(code)
        assert expected_fragment.lower() in desc.lower(), (
            f"Expected '{expected_fragment}' in description for code {code}: '{desc}'"
        )

    def test_unknown_code_returns_unknown_error(self):
        result = get_exit_code_description(99)
        assert "Unknown" in result or "unknown" in result.lower()

    def test_return_type_is_str(self):
        assert isinstance(get_exit_code_description(SUCCESS), str)
        assert isinstance(get_exit_code_description(999), str)

    def test_descriptions_are_non_empty(self):
        """Every description (including unknown) is a non-empty string."""
        codes = [SUCCESS, ERROR_GENERAL, ERROR_INVALID_ARGS, 9999]
        for code in codes:
            desc = get_exit_code_description(code)
            assert desc and isinstance(desc, str)

    def test_unknown_negative_code_returns_fallback(self):
        result = get_exit_code_description(-5)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# AGENT_ACTIONS mapping
# ---------------------------------------------------------------------------


class TestAgentActionsMapping:
    """Tests for the AGENT_ACTIONS constant dict."""

    def test_agent_actions_is_dict(self):
        assert isinstance(AGENT_ACTIONS, dict)

    def test_all_known_codes_have_actions(self):
        known_codes = [
            SUCCESS,
            ERROR_GENERAL,
            ERROR_INVALID_ARGS,
            ERROR_AUTH_FAILURE,
            ERROR_NETWORK,
            ERROR_NOT_FOUND,
            ERROR_PERMISSION_DENIED,
        ]
        for code in known_codes:
            assert code in AGENT_ACTIONS, f"Missing action for code {code}"

    def test_all_action_values_are_non_empty_strings(self):
        for code, action in AGENT_ACTIONS.items():
            assert isinstance(action, str), f"Action for {code} is not a str"
            assert action, f"Action for {code} is empty"

    def test_success_action_suggests_proceeding(self):
        action = AGENT_ACTIONS[SUCCESS]
        assert "proceed" in action.lower() or "next" in action.lower()

    def test_auth_failure_action_mentions_login_or_credentials(self):
        action = AGENT_ACTIONS[ERROR_AUTH_FAILURE]
        assert "login" in action.lower() or "credentials" in action.lower()

    def test_network_action_mentions_retry(self):
        action = AGENT_ACTIONS[ERROR_NETWORK]
        assert "retry" in action.lower()


# ---------------------------------------------------------------------------
# get_agent_action
# ---------------------------------------------------------------------------


class TestGetAgentAction:
    """Tests for get_agent_action()."""

    @pytest.mark.parametrize(
        "code",
        [
            SUCCESS,
            ERROR_GENERAL,
            ERROR_INVALID_ARGS,
            ERROR_AUTH_FAILURE,
            ERROR_NETWORK,
            ERROR_NOT_FOUND,
            ERROR_PERMISSION_DENIED,
        ],
    )
    def test_known_code_returns_string(self, code):
        result = get_agent_action(code)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_code_returns_fallback_string(self):
        result = get_agent_action(99)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_known_code_matches_agent_actions_dict(self):
        """Return value must equal the AGENT_ACTIONS entry for known codes."""
        for code, expected in AGENT_ACTIONS.items():
            assert get_agent_action(code) == expected

    def test_success_action_differs_from_error_actions(self):
        """The success action should be meaningfully different from error actions."""
        success_action = get_agent_action(SUCCESS)
        error_action = get_agent_action(ERROR_GENERAL)
        assert success_action != error_action

    def test_unknown_large_code_returns_fallback(self):
        result = get_agent_action(1000)
        assert "Log" in result or "user" in result or "intervention" in result

    def test_auth_failure_action_mentions_login(self):
        action = get_agent_action(ERROR_AUTH_FAILURE)
        assert "login" in action.lower() or "credentials" in action.lower()

    def test_network_action_mentions_retry(self):
        action = get_agent_action(ERROR_NETWORK)
        assert "retry" in action.lower()

    def test_not_found_action_mentions_verify_or_create(self):
        action = get_agent_action(ERROR_NOT_FOUND)
        assert "verify" in action.lower() or "create" in action.lower() or "exist" in action.lower()
