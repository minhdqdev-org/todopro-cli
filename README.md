# TodoPro CLI

> A professional command-line interface for TodoPro task management system, inspired by kubectl.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Development](#development)
- [Releasing](#releasing)
- [Documentation](#documentation)

## Features

- **CLI-first design**: Built for the terminal with developers in mind
- **Natural language input**: `todopro add "Buy milk tomorrow at 2pm #groceries"`
- **Context-aware**: Maintains authentication state and user preferences
- **Multi-environment**: Switch between dev, staging, and prod contexts seamlessly
- **Output flexibility**: JSON, YAML, table, and custom formats
- **Interactive & scriptable**: Menu-driven UI for exploration, flags for automation
- **AI-agent friendly**: JSON output, semantic exit codes, idempotent operations
- **End-to-end encryption**: Client-side encryption with AES-256-GCM
- **Import/Export**: Backup and restore all your data
- **Professional UX**: Rich terminal UI with colors, progress indicators, and helpful messages

## Installation

> 📖 **For detailed installation instructions and troubleshooting, see [docs/INSTALLATION.md](docs/INSTALLATION.md)**

### One-Liner (Recommended)

Install `uv` and `todopro-cli` in one command:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install git+https://github.com/minhdqdev-org/todopro-cli.git
```

This will:
- Install `uv` (if not already installed)
- Pull the CLI tool directly from GitHub
- Build an isolated environment with all dependencies
- Place the `todopro` and `tp` commands in your PATH

### Update

```bash
uv tool upgrade todopro-cli
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/minhdqdev-org/todopro-cli.git
cd todopro-cli

# Install locally
uv tool install --from . todopro-cli
```

### Install from Release

```bash
# Install a specific version from GitHub releases
uv tool install https://github.com/minhdqdev-org/todopro-cli/releases/download/v0.1.0/todopro_cli-0.1.0-py3-none-any.whl
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

# Data management
todopro data export --output backup.json      # Export all data
todopro data import backup.json               # Import data
todopro data purge --dry-run                  # Preview data deletion

# AI-agent friendly usage
todopro tasks list --output json              # JSON output for parsing
todopro complete task-abc --yes               # Skip confirmation prompts
echo $?                                        # Check exit code (0=success)
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

## Releasing

> 📖 **For detailed release instructions, see [docs/RELEASE.md](docs/RELEASE.md)**

This project uses automated GitHub Actions workflows for testing and releasing.

### Create a Release

1. **Tag your code:**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **Automatic Release:** GitHub Actions will:
   - Run all tests
   - Build the package (`.whl` and `.tar.gz`)
   - Create a GitHub Release with the artifacts

3. **Users can install:** Once released, users can install directly from the release URL or via the one-liner command.

### Workflow Details

- **On Push to `main`:** Runs tests to ensure code quality
- **On Tag Push (`v*`):** Runs tests + builds and publishes release artifacts

## Documentation

- 📦 [Installation Guide](docs/INSTALLATION.md) - Detailed installation instructions and troubleshooting
- 🚀 [Release Process](docs/RELEASE.md) - How to create and publish releases
- 💡 [Package Ideas](docs/PACKAGE_IDEA.md) - Original implementation ideas and rationale
- 🤖 [AI Agent Integration](docs/AI_AGENT_INTEGRATION.md) - Guide for automation and AI agents

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
