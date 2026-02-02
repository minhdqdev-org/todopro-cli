# Auto Update Checker

## Overview

The TodoPro CLI includes an automatic update checker that notifies users when a new version is available on PyPI. This feature is designed to be non-intrusive and efficient.

## Features

### Automatic Update Notification

- **Automatic checking**: Checks for updates every hour (3600 seconds)
- **Non-blocking**: Uses a 0.5 second timeout to avoid CLI lag
- **Fail-silent**: Network errors don't interrupt the user experience
- **Cache-based**: Minimizes API calls to PyPI using local cache
- **Standards-compliant**: Uses XDG Base Directory specification for cache storage

### Manual Update Command

Users can manually check and update using the `todopro update` command:

```bash
# Interactive mode (prompts for confirmation)
todopro update

# Non-interactive mode (auto-confirms)
todopro update -y
todopro update --yes
```

## How It Works

### Automatic Checking

1. **Cache Check**: First checks if a cached version check exists and is less than 1 hour old
2. **PyPI API Call**: If cache is expired or missing, makes a quick API call to PyPI
3. **Version Comparison**: Compares the latest version from PyPI with the current version
4. **Notification**: If a newer version exists, displays a friendly notification after command execution

### Manual Update Command

1. **Check for Updates**: Fetches the latest version from PyPI (uses 5-minute cache)
2. **Display Status**: Shows current vs. latest version
3. **Prompt User**: Asks for confirmation (unless `-y` flag is used)
4. **Execute Update**: Runs `uv tool upgrade todopro-cli`
5. **Verify**: Confirms successful update

## Cache Location

The update check cache is stored in the OS-specific cache directory:

- **Linux**: `~/.cache/todopro/update_check.json`
- **macOS**: `~/Library/Caches/todopro/update_check.json`
- **Windows**: `C:\Users\<User>\AppData\Local\todopro\cache\update_check.json`

## Cache Format

```json
{
  "last_check_timestamp": 1700000000.0,
  "latest_version": "1.2.3"
}
```

## Implementation Details

### Dependencies

- `requests`: For HTTP calls to PyPI API
- `packaging`: For semantic version comparison
- `platformdirs`: For OS-specific cache directory paths

### Integration

The update checker is integrated into the main CLI entry point and runs after every command execution in a `finally` block to ensure it always runs even if the command fails.

```python
def main() -> None:
    """Main entry point."""
    from todopro_cli.utils.update_checker import check_for_updates

    try:
        app()
    finally:
        # Check for updates after command execution (non-blocking)
        check_for_updates()
```

## User Experience

### Automatic Notification

When a new version is available, users see a friendly notification at the end of any command:

```
✨ New version available: 1.2.3 (Current: 1.0.0)
👉 Run: 'uv tool upgrade todopro-cli' to update.
```

The notification appears after the command output, ensuring it doesn't interfere with the command's primary function.

### Manual Update Command

**When already on latest version:**
```bash
$ todopro update
Checking for updates...
✓ You're already on the latest version (1.2.3)
```

**When update is available (interactive mode):**
```bash
$ todopro update
Checking for updates...

✨ New version available: 1.2.3
Current version: 1.0.0

Do you want to update now? [Y/n]: y

Updating TodoPro CLI...

✓ Successfully updated to version 1.2.3!
Run 'todopro version' to verify the update.
```

**Non-interactive mode:**
```bash
$ todopro update -y
Checking for updates...

✨ New version available: 1.2.3
Current version: 1.0.0

Updating TodoPro CLI...

✓ Successfully updated to version 1.2.3!
Run 'todopro version' to verify the update.
```

## Testing

Comprehensive tests are available in `tests/test_update_checker.py` covering:

### Automatic Notification Tests
- Version comparison logic (newer, same, older)
- Network error handling (fail silently)
- Cache usage and expiration
- Cache file creation
- Timeout configuration
- Silent failures

### Manual Update Command Tests
- `get_latest_version()` functionality
- Cache usage (5-minute window)
- `is_update_available()` logic
- Network error handling

Run tests with:

```bash
uv run pytest tests/test_update_checker.py -v
```

## Configuration

Currently, the update checker:
- Checks every **1 hour** (3600 seconds)
- Uses a **0.5 second** timeout for PyPI API calls
- Cannot be disabled (future enhancement)

These values are defined as constants in `src/todopro_cli/utils/update_checker.py`:

```python
CHECK_INTERVAL = 3600  # 1 hour in seconds
PYPI_URL = "https://pypi.org/pypi/todopro-cli/json"
```

## Future Enhancements

Potential improvements:
- Configuration option to disable update checks
- Configurable check interval
- Support for different update channels (stable, beta)
- Option to auto-update on user confirmation
