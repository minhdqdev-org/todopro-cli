---
updated_at: 2026-10-14T00:11:01+07:00
---

# TodoPro CLI

> A professional CLI-first task management system with an offline-first architecture.

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

## 🎯 Why TodoPro?

TodoPro is a **CLI-first task manager** for power users, developers, and privacy-conscious individuals who want:

- 🖥️ **Terminal Interface:** Keyboard-driven, fast, and distraction-free
- 💾 **Offline-First:** Works without internet, local SQLite storage
- 🤖 **Automation-Ready:** JSON output, scripting support, CI/CD friendly
- 🎯 **Privacy-Focused:** You own your data, no tracking, no ads

**Perfect for:** Developers, sysadmins, CLI enthusiasts, privacy advocates

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Essential Commands](#essential-commands)
- [Documentation](#documentation)
- [Development](#development)

---

## Features

### ✨ Core Features

**Task Management:**

- ✅ Create, edit, complete, reopen, reschedule, and delete tasks
- ✅ Natural language quick add (`todopro add "Review PR tomorrow at 2pm #Work p1 @urgent"`), including dates, recurrence (`every friday`), and reminders. Natural language parsing needs a cloud context; in a local context the text is stored as the task content
- ✅ Priority levels (P1 urgent to P4 normal, P4 by default), due dates, hard deadlines, descriptions
- ✅ Search and filter tasks by status, project, and priority; apply saved filters
- ✅ Comments, task dependencies (`task link`), and saved task templates
- ✅ Complete several tasks in one call (`todopro complete 3f 9a`)

**Organization:**

- ✅ Projects and sections for grouping tasks
- ✅ Labels for tagging (`@urgent`, `@work`)
- ✅ Project sharing and collaborators (`project share`)
- ✅ Scratchpads attached to projects
- ✅ Multiple contexts (local SQLite, remote cloud)
- ✅ Archive and unarchive projects

**Focus & Insights:**

- ✅ Pomodoro focus sessions (`focus`) and reusable focus templates
- ✅ Focus stats (`stats`), productivity analytics (`analytics`), goals (`goals`), and achievements (`achievements`)

**Sync & Backup:**

- ✅ Bidirectional sync between a local and a cloud context (`sync push` / `sync pull`) with a conflict strategy
- ✅ Export/import data (JSON, gzip, or a complete ZIP archive with attachments)
- ✅ **Todoist import** — migrate projects, tasks, and labels from Todoist via API key (`todopro import todoist`)

**Integrations (cloud context):**

- ✅ **GitHub** — connect a personal access token, import issues, link GitHub Projects, and sync both ways (`todopro github`)
- ✅ **Hub** — one unified list of external items from linked providers (`todopro hub list`, Pro)
- ✅ **Google Calendar** — connect, push tasks, and pull events (`todopro calendar`)

**Security & Privacy:**

- ✅ Local-only mode — data stays on your machine, no account required
- ✅ Per-context credentials stored in `~/.config/todopro_cli/credentials/` with `0600` permissions
- ✅ Token-based authentication over HTTPS to the cloud backend
- ⚠️ End-to-end encryption was **discontinued** (ADR-0024). Data synced to the cloud is protected in transit and at rest by the server, **not** encrypted client-side. The `todopro encryption` commands remain only as discontinued stubs.

**Voice:**

- ✅ **Dictate** — voice-to-tasks (speak, then tasks are created from the recording)

## Installation

TodoPro CLI requires **Python 3.14 or newer**. The package manager is [uv](https://docs.astral.sh/uv/).

### Using uv (Recommended)

```bash
# Install TodoPro CLI
uv tool install todopro-cli

# Or install the latest from GitHub
uv tool install git+https://github.com/minhdqdev-org/todopro-cli.git

# Verify installation
todopro version
```

Both `todopro` and the short alias `tp` are installed. Run `todopro update` to upgrade to the latest release.

### From Source

```bash
git clone https://github.com/minhdqdev-org/todopro-cli.git
cd todopro-cli
mise install        # Python 3.14 and uv
mise run install    # uv sync --all-groups

# Run from the checkout
uv run todopro --help
```

---

## Quick Start

### 🚀 First Run (Offline)

TodoPro starts in the **`local` context** (SQLite on your machine). No signup required!

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

Two contexts exist out of the box: `local` (SQLite, the default) and `cloud` (the TodoPro API at `https://todopro.minhdq.dev/api`). `auth` commands only work in a remote context.

```bash
# 1. Create an account in the cloud context
todopro context use cloud
todopro auth signup

# 2. Back in the local context, push your data to the cloud
todopro context use local
todopro sync push --context cloud
```

**On another device:**

```bash
# 1. Log in to the cloud context
todopro context use cloud
todopro auth login

# 2. Switch to local and pull the data down
todopro context use local
todopro sync pull --context cloud
```

You can also work directly against the cloud by staying in the `cloud` context after logging in.

---

## Essential Commands

Run `todopro --help` for the full command list, or `todopro <command> --help` for flags. `tp` is a short alias for `todopro`.

### Task Management

```bash
# Add tasks (natural language, cloud context)
todopro add "Task title"
todopro add "Review PR tomorrow at 2pm #Work p1 @urgent"
todopro add "Buy groceries today" --project Inbox      # assign to project by name
todopro add "File taxes" --deadline "April 15"         # hard deadline
todopro add "Stand-up at 9am #Work" --output json      # JSON output (-o json / --json also works)

# Create a task with explicit fields (works in any context)
todopro task create "Write report" --due tomorrow --priority 1 --labels work,urgent

# List tasks
todopro task list
todopro today                    # Overdue and today's tasks (shows a unique short suffix like [3f])
todopro task list --status completed
todopro task list --project <project-id> --priority 1 --search "meeting"

# Complete/reopen
todopro complete <suffix>        # suffix shown in brackets, e.g. [3f]
todopro reopen <suffix>          # undo a completion

# Edit a task
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
todopro project unarchive <id>

# Sections inside a project
todopro section create <project-id> "Backlog"
todopro section list <project-id>

# Labels
todopro label create "urgent" --color red
todopro label list
```

### Contexts (Offline / Cloud)

```bash
# List contexts (default: local and cloud)
todopro context list

# Create a second local vault with its own database
todopro context create my-vault --type local --source ~/.todopro-work.db

# Switch contexts; all commands then act on that context
todopro context use my-vault
todopro add "Work on the plane without WiFi"
todopro task list

# Switch back
todopro context use local
```

The remote API defaults to `https://todopro.minhdq.dev/api`. To point a remote context at another server, pass `--endpoint` to `todopro auth login`, create a context with `todopro context create <name> --type remote --source <url>`, or set the `TODOPRO_BACKEND_URL` environment variable.

### Sync & Backup

```bash
# Sync (run from a local context; --context names the remote one)
todopro sync push --context cloud     # Upload to cloud
todopro sync pull --context cloud     # Download from cloud
todopro sync status                   # Show last sync times
todopro sync pull --context cloud --dry-run --strategy remote-wins

# Backup/Restore
todopro data export --output backup.json
todopro data export --compress        # Gzip compressed
todopro data export --archive         # Complete ZIP with attachments (remote contexts only)
todopro data import backup.json
todopro data purge --dry-run          # Preview data deletion

# Import from Todoist (requires a personal API token)
todopro import todoist --api-key YOUR_TOKEN
TODOIST_API_KEY=YOUR_TOKEN todopro import todoist
todopro import todoist --dry-run --api-key YOUR_TOKEN
todopro import todoist --project-prefix "" --max-tasks 200
```

### 🎙️ Dictate (Voice-to-Tasks)

Requires the cloud context, since transcription and task extraction run on the TodoPro backend.

```bash
# Speak, then stop — the recording is transcribed in one batch and tasks are created
todopro dictate                              # 30s default
todopro dictate --duration=60                # Custom duration
todopro dictate --project=work               # Send tasks to specific project
todopro dictate --dry-run                    # Preview parsed tasks without creating
todopro dictate --text "Buy milk tomorrow"   # Text mode (no mic)
todopro dictate history                      # Past sessions
todopro dictate usage                        # Today's usage
todopro dictate config --show                # Show Dictate configuration
```

Transcription is batch: audio is buffered while recording and processed once you stop, so there is no live transcript and no interim results.

### Focus, Stats & Goals

```bash
todopro focus start <task-id>          # Pomodoro session (25 min by default)
todopro focus status
todopro focus stop
todopro stats today                    # Focus summary (also: week, month, streak, score, heatmap)
todopro analytics stats                # Productivity score and basic statistics
todopro goals set daily-sessions 8     # Local focus goal (see `goals set --help`)
todopro achievements list
```

### Templates, Sharing & Scratchpads

```bash
todopro template list
todopro template apply <name-or-id>

todopro project share share <project-id> --email teammate@example.com
todopro project share collaborators <project-id>

todopro scratchpad list <project-id>
todopro scratchpad create <project-id> --title "Ideas"
```

### Integrations (cloud context)

```bash
# GitHub
todopro github connect --pat <token>
todopro github projects                        # GitHub Projects v2 you can link
todopro github sync --all                      # Two-way sync of linked projects
todopro github status

# Hub (Pro): unified feed of external items
todopro hub list

# Google Calendar
todopro calendar connect
todopro calendar status
```

### Account

```bash
todopro auth signup               # remote context only
todopro auth login                # remote context only
todopro auth logout
todopro auth resend-verification  # re-send the email confirmation link
```

Cloud accounts must confirm their email address. Until the emailed link is clicked, the API answers with an `email_not_verified` error.

### Task ID Shortcuts

Task ID suffixes are globally unique, and the minimum suffix length is shown in brackets, for example `[3f]`. Use the bracketed suffix from `todopro today` or `todopro task list` directly:

```bash
todopro complete 3f            # complete task [3f]
todopro reopen 3f              # undo completion
todopro complete abc123def     # longer suffix still works
todopro reschedule 3f          # move to today
todopro reschedule 3f --date tomorrow
todopro reschedule 3f --date 2026-02-15
todopro reschedule             # move all overdue tasks to today
todopro task get e562bb        # task details by suffix
todopro task update 123def --content "Updated task"
todopro task delete abc123     # delete by suffix
```

### Encryption (discontinued)

The `todopro encryption` command group still exists, but end-to-end encryption was discontinued in **ADR-0024**. Every subcommand is a stub — there is no key to set up, recover, or rotate. Nothing needs to be run before or after `todopro sync`.

### Scripting and Automation

```bash
todopro task list --output json       # JSON output for parsing
todopro task list -o json             # shorthand
todopro add "task" --json             # --json also works on most commands
todopro project list --json
todopro task delete <id> --yes        # skip confirmation prompts
echo $?                               # exit code (0 = success)
```

---

## Documentation

### 📖 User Guides

- **[Getting Started](./docs/GETTING_STARTED.md)** - Complete walkthrough for new users
- **[FAQ](./docs/FAQ.md)** - Frequently asked questions
- **[Troubleshooting](./docs/TROUBLESHOOTING.md)** - Common issues and solutions

### 🔧 Reference

- **[CHANGELOG](./CHANGELOG.md)** - Version history

### 💡 Examples

**Daily Task Review Script:**

```bash
#!/bin/bash
echo "📅 Overdue and today's tasks:"
todopro today
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
echo "🍅 Working on: $(todopro task get $TASK_ID --output json | jq -r '.content')"
todopro focus start "$TASK_ID" --duration 25
```

---

## Development

```bash
# Install with development dependencies
mise run install            # uv sync --all-groups

# Run all tests
mise run test
uv run pytest tests/commands -v      # a specific module

# Tests with coverage report
mise run test-cov

# Lint
mise run lint

# Type check
mise run type-check
```

Run `mise tasks` to see every task defined for this repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
