"""
Exit codes for TodoPro CLI.

Following AI-agent-friendly design principles with semantic exit codes.
Agents can use these codes to understand what happened and take appropriate action.
"""

# Success
SUCCESS = 0

# General error (unspecified)
ERROR_GENERAL = 1

# Invalid arguments or validation error
ERROR_INVALID_ARGS = 2

# Authentication failure (not logged in, invalid credentials, etc.)
ERROR_AUTH_FAILURE = 3

# Network or API error (server unreachable, timeout, etc.)
ERROR_NETWORK = 4

# Resource not found
ERROR_NOT_FOUND = 5

# Permission denied
ERROR_PERMISSION_DENIED = 6

# Request timed out
ERROR_TIMEOUT = 7

# Rate limit exceeded
ERROR_RATE_LIMITED = 8


def get_exit_code_name(code: int) -> str:
    """Get the name of an exit code for display purposes."""
    code_names = {
        SUCCESS: "SUCCESS",
        ERROR_GENERAL: "ERROR_GENERAL",
        ERROR_INVALID_ARGS: "ERROR_INVALID_ARGS",
        ERROR_AUTH_FAILURE: "ERROR_AUTH_FAILURE",
        ERROR_NETWORK: "ERROR_NETWORK",
        ERROR_NOT_FOUND: "ERROR_NOT_FOUND",
        ERROR_PERMISSION_DENIED: "ERROR_PERMISSION_DENIED",
        7: "ERROR_TIMEOUT",
        8: "ERROR_RATE_LIMITED",
    }
    return code_names.get(code, f"UNKNOWN({code})")


def get_exit_code_description(code: int) -> str:
    """Get a human-readable description of an exit code."""
    descriptions = {
        SUCCESS: "Command executed successfully",
        ERROR_GENERAL: "A general error occurred",
        ERROR_INVALID_ARGS: "Invalid arguments or validation error",
        ERROR_AUTH_FAILURE: "Authentication failure - please login",
        ERROR_NETWORK: "Network or API error - check connection",
        ERROR_NOT_FOUND: "Resource not found",
        ERROR_PERMISSION_DENIED: "Permission denied",
        7: "Request timed out",
        8: "Rate limit exceeded",
    }
    return descriptions.get(code, "Unknown error")


# Agent action suggestions based on exit codes
AGENT_ACTIONS = {
    SUCCESS: "Proceed to next task",
    ERROR_GENERAL: "Log error and notify user",
    ERROR_INVALID_ARGS: "Correct the command arguments and retry",
    ERROR_AUTH_FAILURE: "Prompt user for credentials or run 'todopro login'",
    ERROR_NETWORK: "Wait and retry with exponential backoff",
    ERROR_NOT_FOUND: "Verify resource exists or create it",
    ERROR_PERMISSION_DENIED: "Check user permissions or escalate",
    ERROR_TIMEOUT: "Wait and retry with exponential backoff",
    ERROR_RATE_LIMITED: "Wait for rate limit window to reset, then retry",
}


def get_agent_action(code: int) -> str:
    """Get suggested action for an AI agent based on exit code."""
    return AGENT_ACTIONS.get(code, "Log error and request user intervention")
