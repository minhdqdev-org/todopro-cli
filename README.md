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

**Security:**
- ✅ End-to-end encryption (AES-256-GCM)
- ✅ 24-word recovery phrase (BIP39)
- ✅ Zero-knowledge architecture
- ✅ Client-side encryption

### 🚀 Coming Soon (Post-MVP1)

- ⏳ Recurring tasks
- ⏳ Subtasks & dependencies
- ⏳ Mobile apps (iOS/Android)
- ⏳ Web interface
- ⏳ Team collaboration
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

### Using pip

```bash
# Install from PyPI (coming soon)
pip install todopro-cli

# Or install from GitHub
pip install git+https://github.com/minhdqdev-org/todopro-cli.git

# Verify
todopro version
```

### From Source

```bash
git clone https://github.com/minhdqdev-org/todopro-cli.git
cd todopro-cli
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
todopro signup

# 2. Set up encryption
todopro encryption setup
# ⚠️ Save your 24-word recovery phrase!

# 3. Push your data
todopro sync push
```

**On another device:**
```bash
# 1. Login
todopro login

# 2. Recover encryption key
todopro encryption recover

# 3. Pull data
todopro sync pull
```

---

## Essential Commands

### Task Management

```bash
# Add tasks
todopro add "Task title"
todopro add "Task" --due tomorrow --priority 1

# List tasks
todopro list tasks
todopro today                    # Today's tasks
todopro list tasks --filter=overdue

# Complete/reopen
todopro complete <id>
todopro reopen <id>

# Update
todopro update task <id> --content "New title"
todopro update task <id> --due "next monday"

# Delete
todopro delete task <id>
```

### Projects & Labels

```bash
# Projects
todopro create project "Work"
todopro list projects
todopro archive project <id>

# Labels
todopro create label "urgent" --color red
todopro list labels
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
todopro export data --output backup.json      # Export all data
todopro import data backup.json               # Import data
todopro purge data --dry-run                  # Preview data deletion

# AI-agent friendly usage
todopro list tasks --output json              # JSON output for parsing
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

- 🔄 [Migration Guide](docs/migration-guide.md) - **Upgrading from v1.x to v2.0**
- 📝 [CHANGELOG](CHANGELOG.md) - What's new in v2.0
- 🚀 [Release Process](docs/RELEASE.md) - How to create and publish releases
- 💡 [Package Ideas](docs/PACKAGE_IDEA.md) - Original implementation ideas and rationale
- 🤖 [AI Agent Integration](docs/AI_AGENT_INTEGRATION.md) - Guide for automation and AI agents
- 📋 [Specifications](../docs/specs/) - Detailed technical specifications
  - [README](../docs/specs/README.md) - Specification index and roadmap
  - [01: Repository Abstraction](../docs/specs/01-repository-abstraction.md) - Hexagonal architecture
  - [03: Context Switching](../docs/specs/03-context-switching.md) - Multi-environment support
  - [10-14: Architecture Stabilization](../docs/specs/README.md#-architecture-stabilization-specs-10-15--new) - **Recent refactoring (2025-02-18)**

### Recent Architecture Improvements (Feb 2025)

The CLI recently underwent a major architecture stabilization effort (Specs 10-14):
- ✅ Fixed 38+ broken import paths
- ✅ Migrated all commands to Strategy Pattern (from Factory Pattern)
- ✅ Cleaned up configuration layer (ConfigService as single source of truth)
- ✅ Implemented REST API location context adapter
- ✅ Enhanced package exports for better IDE support

See [implementation summaries](../docs/specs/) for details.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
