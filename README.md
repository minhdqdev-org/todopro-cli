# TodoPro CLI

> A professional CLI-first task management system with offline-first architecture and end-to-end encryption.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

## 🎯 Why TodoPro?

TodoPro is a **CLI-first task manager** for power users, developers, and privacy-conscious individuals who want:

- 🖥️ **Terminal Interface:** Keyboard-driven, fast, and distraction-free
- 💾 **Offline-First:** Works without internet, local SQLite storage
- 🔐 **Zero-Knowledge E2EE:** Your data encrypted before leaving your device
- 🤖 **Automation-Ready:** JSON output, scripting support, CI/CD friendly
- 🎯 **Privacy-Focused:** You own your data, no tracking, no ads

**Perfect for:** Developers, sysadmins, CLI enthusiasts, privacy advocates

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Development](#development)

---

## Features

### ✨ Core Features

**Task Management:**

- ✅ Create, update, complete, delete tasks
- ✅ Natural language dates ("tomorrow", "next friday")
- ✅ Priority levels (P1-P4), due dates, descriptions
- ✅ Search, filter, sort tasks
- ✅ Bulk operations

**Organization:**

- ✅ Projects for grouping tasks
- ✅ Labels for tagging (#urgent, #work)
- ✅ Multiple contexts (local, remote)
- ✅ Archive completed projects

**Sync & Backup:**

- ✅ Bidirectional sync (push/pull)
- ✅ Export/import data (JSON, gzip)
- ✅ Local SQLite + Cloud backend
- ✅ Conflict resolution
- ✅ **Todoist import** — migrate active tasks, projects, and labels from Todoist via API key (`todopro import todoist`)

**Security:**

- ✅ End-to-end encryption (AES-256-GCM)
- ✅ 24-word recovery phrase (BIP39)
- ✅ Zero-knowledge architecture
- ✅ Client-side encryption

**Voice & AI:**

- ✅ **Ramble** — voice-to-tasks (speak naturally, tasks appear automatically)
- ✅ **Quick Add** — natural language task creation with NLP date parsing

### 🚀 Coming Soon (Post-MVP1)

- ⏳ Recurring tasks
- ⏳ Subtasks & dependencies
- ⏳ Calendar integrations

## Installation

### Using uv (Recommended)

```bash
# Install TodoPro CLI
uv tool install todopro-cli

# Or install from GitHub releases (latest)
uv tool install git+https://github.com/minhdqdev-org/todopro-cli.git

# Verify installation
todopro version
```

### From Source

```bash
git clone https://github.com/minhdqdev-org/todopro-cli.git
cd todopro-cli
mise install
mise run install
uv pip install -e .
```

---

## Quick Start

### 🚀 First Run (Offline)

TodoPro works **offline by default**. No signup required!

```bash
# Create your first task
todopro add "Buy groceries"

# View tasks
todopro today

# Mark complete
todopro complete <task-id>
```

**Done!** You're up and running in 30 seconds.

### 📚 Learn More

**→ [Getting Started Guide](./docs/GETTING_STARTED.md)** - Complete tutorial  
**→ [FAQ](./docs/FAQ.md)** - Common questions  
**→ [Troubleshooting](./docs/TROUBLESHOOTING.md)** - Fix issues

### ☁️ Optional: Cloud Sync

Want to sync across devices?

```bash
# 1. Sign up
todopro auth signup

# 2. Set up encryption
todopro encryption setup
# ⚠️ Save your 24-word recovery phrase!

# 3. Push your data
todopro sync push
```

**On another device:**

```bash
# 1. Login
todopro auth login

# 2. Recover encryption key
todopro encryption recover

# 3. Pull data
todopro sync pull
```

---

## Essential Commands

### Task Management

```bash
# Add tasks (natural language)
todopro add "Task title"
todopro add "Task" --due tomorrow --priority 1
todopro add "Buy groceries today" --project Inbox  # assign to project by name
todopro add "Stand-up at 9am #Work" --output json  # JSON output (-o json / --json also works)

# List tasks
todopro task list
todopro today                    # Today's tasks (shows unique short suffix like #3f)
todopro task list --filter=overdue

# Complete/reopen
todopro complete <suffix>        # suffix shown in brackets, e.g. [3f]
todopro reopen <suffix>          # undo a completion

# Edit a task interactively
todopro edit <id>                # interactive mode
todopro edit <id> --content "New title" --project Work  # flag mode (project by name)

# Delete
todopro task delete <id>
```

### Projects & Labels

```bash
# Projects
# The default project is "Inbox". It is created automatically for every user
# with a unique random UUID (not shared across users or environments).
# Inbox is "protected": it cannot be archived, deleted, or renamed.
# All tasks without an explicit project belong to Inbox.
todopro project create "Work"
todopro project list             # pretty list (default)
todopro project list --json      # JSON output
todopro project archive <id>

# Labels
todopro label create "urgent" --color red
todopro label list
```

### Sync & Backup

```bash
# Sync
todopro sync push     # Upload to cloud
todopro sync pull     # Download from cloud
todopro sync status   # Check sync state

# Backup/Restore
todopro data export --output backup.json
todopro data export --compress  # Gzip compressed
todopro data import backup.json
```

### 🎙️ Ramble (Voice-to-Tasks)

```bash
# Speak naturally — tasks are created automatically
todopro ramble                              # Batch mode (30s default)
todopro ramble --duration=60               # Custom duration
todopro ramble --stream                    # Streaming mode (premium)
todopro ramble --project=work              # Send tasks to specific project
todopro ramble --dry-run                   # Preview parsed tasks without creating
todopro ramble --text "Buy milk tomorrow"  # Text mode (no mic)
todopro ramble history                     # Last 10 sessions
todopro ramble config                      # Show/set Ramble configuration
```

### Encryption

```bash
# Set up E2EE
todopro encryption setup

# Check status
todopro encryption status

# Show recovery phrase
todopro encryption show-recovery

# Recover on new device
todopro encryption recover

# Rotate key
todopro encryption rotate-key
```

---

## Documentation

### 📖 User Guides

- **[Getting Started](./docs/GETTING_STARTED.md)** - Complete walkthrough for new users
- **[FAQ](./docs/FAQ.md)** - Frequently asked questions
- **[Troubleshooting](./docs/TROUBLESHOOTING.md)** - Common issues and solutions

### 🔧 Reference

- **[CHANGELOG](./CHANGELOG.md)** - Version history
- **[MVP1 Product Spec](../docs/MVP1.md)** - Feature roadmap

### 💡 Examples

**Daily Task Review Script:**

```bash
#!/bin/bash
echo "📅 Today's Tasks:"
todopro today
echo "\n⚠️  Overdue:"
todopro list tasks --filter=overdue
```

**Weekly Backup:**

```bash
#!/bin/bash
todopro data export --compress \
  --output ~/Dropbox/todopro-backup-$(date +%Y%m%d).json.gz
```

**Pomodoro Timer:**

```bash
#!/bin/bash
TASK_ID=$1
echo "🍅 Working on: $(todopro get task $TASK_ID --format json | jq -r '.content')"
sleep 25m
echo "✅ Pomodoro complete!"
```

---

### Contexts (Offline / Cloud)

```bash
# Switch to local vault
todopro use context my-vault

# Now all commands work offline!
todopro add "Work on the plane without WiFi"
todopro list tasks

# Pull tasks from cloud to local vault
todopro pull

# Make changes locally...
todopro add "Another offline task"

# Push changes back to cloud
todopro push

# Switch back to cloud
todopro use context default-remote

# List all contexts
todopro list contexts

# Check sync status
todopro sync-status
```

### Additional Commands

```bash
# Reschedule overdue tasks
todopro reschedule

# List projects
todopro list projects

# Create a project
todopro create project "Work"

# Archive a project
todopro archive project <project_id>

# Show today's stats
todopro show stats-today

# Start a focus session
todopro start focus

# Get current timezone
todopro set timezone
todopro auth timezone Asia/Ho_Chi_Minh

# Reschedule a task to today (quick rescheduling)
todopro reschedule <task_id>

# Reschedule to a specific date
todopro reschedule <task_id> --date tomorrow
todopro reschedule <task_id> --date 2026-02-15

# Task ID Shortcuts
# Task ID suffixes are globally unique — the minimum suffix length is shown in brackets [3f].
# Use the bracketed suffix from `tp today` or `tp list tasks` directly:
todopro complete 3f            # complete task [3f]
todopro reopen 3f              # undo completion
todopro complete abc123def     # longer suffix still works
todopro reschedule e562bb     # Reschedule to today by suffix
todopro get e562bb            # Get task details by suffix
todopro update 123def --content "Updated task"
todopro delete abc123         # Delete by suffix

# View project details
todopro describe project <project_id>

# Get help
todopro --help

# Data management
todopro export data --output backup.json      # Export all data
todopro import data backup.json               # Import data
todopro purge data --dry-run                  # Preview data deletion

# Import from Todoist (requires personal API token)
todopro import todoist --api-key YOUR_TOKEN   # Import active tasks, projects, labels
TODOIST_API_KEY=YOUR_TOKEN todopro import todoist        # API key from env var
todopro import todoist --dry-run --api-key YOUR_TOKEN    # Preview without writing
todopro import todoist --project-prefix "" --max-tasks 200  # No prefix, cap per-project

# AI-agent and scripting friendly usage
todopro list tasks --output json              # JSON output for parsing
todopro list tasks -o json                    # shorthand
todopro add "task" --json                     # also --json flag
todopro list contexts --json --limit 5        # contexts with limit
todopro complete task-abc --yes               # Skip confirmation prompts
echo $?                                        # Check exit code (0=success)

# login/logout/signup only apply in remote context
todopro login      # remote context only
todopro logout     # remote context only
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

## Documentation

- 📝 [CHANGELOG](CHANGELOG.md) - What's new in v2.0
- 🚀 [Release Process](docs/RELEASE.md) - How to create and publish releases

See [implementation summaries](../docs/specs/) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
