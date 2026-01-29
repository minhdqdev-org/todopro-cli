# TodoPro CLI

> A professional command-line interface for TodoPro task management system, inspired by kubectl.

## Features

- **Kubectl-inspired**: Resource-oriented commands with consistent patterns
- **Context-aware**: Maintains authentication state and user preferences
- **Multi-environment**: Switch between dev, staging, and prod contexts seamlessly
- **Output flexibility**: JSON, YAML, table, and custom formats
- **Interactive & scriptable**: Menu-driven UI for exploration, flags for automation
- **Professional UX**: Rich terminal UI with colors, progress indicators, and helpful messages

## Installation

```bash
# Install from source
uv tool install --from . todopro-cli
```

## Quick Start

```bash
# Login to TodoPro
todopro login

# Quick add a task (natural language, just like Todoist)
todopro add "Buy milk tomorrow at 2pm #groceries @shopping"

# List tasks
todopro tasks list

# Create a task (traditional way)
todopro tasks create "Buy groceries"

# Reschedule all overdue tasks to today
todopro tasks reschedule overdue

# Skip confirmation prompt
todopro tasks reschedule overdue --yes

# Get current timezone
todopro auth timezone

# Set timezone (IANA format)
todopro auth timezone Asia/Ho_Chi_Minh
todopro auth timezone America/New_York
todopro auth timezone Europe/London

# 1. Set your timezone
todopro auth timezone Asia/Ho_Chi_Minh

# 2. Check today's tasks (includes overdue)
todopro today

# 3. Reschedule all overdue tasks to today
todopro tasks reschedule overdue

# See what's due today
todopro today

# Get the next task to work on
todopro next

# Complete a task
todopro complete <task_id>

# Reschedule a task to today (quick rescheduling)
todopro reschedule <task_id>

# Reschedule to a specific date
todopro reschedule <task_id> --date tomorrow
todopro reschedule <task_id> --date 2026-02-15

# Task ID Shortcuts
# You can use task ID suffixes instead of full IDs for convenience
# If the full ID is "task-abc123def", you can use:
todopro complete abc123def    # Uses suffix
todopro complete 123def       # Even shorter suffix
todopro reschedule e562bb     # Reschedule to today by suffix
todopro get e562bb            # Get task details by suffix
todopro update 123def --content "Updated task"
todopro delete abc123         # Delete by suffix

# View project details
todopro describe project <project_id>

# Get help
todopro --help
```

## Development

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Run all tests with coverage
uv run pytest --cov=src/todopro_cli --cov-report=term-missing

# Run tests for specific module
uv run pytest tests/test_api_client.py -v

# Generate HTML coverage report
uv run pytest --cov=src/todopro_cli --cov-report=html
# Open htmlcov/index.html in browser

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```
