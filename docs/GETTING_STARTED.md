---
updated_at: 2026-10-14T00:25:17+07:00
---

# Getting Started with TodoPro CLI

Welcome to TodoPro! This guide will help you get up and running in less than 5 minutes.

The CLI is installed as `todopro` and as the short alias `tp`.
Both names run the same program, so every example below works with either.

---

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [First Task](#first-task---interactive-tutorial)
- [Basic Workflows](#basic-workflows)
- [Offline vs Online](#offline-vs-online)
- [Understanding Contexts](#understanding-contexts)
- [Essential Commands](#essential-commands)
- [Next Steps](#next-steps)

---

## Installation

TodoPro CLI requires **Python 3.14 or newer**.

### Using uv (Recommended)

```bash
# Install TodoPro CLI
uv tool install todopro-cli

# Verify installation
todopro version
```

### Using pip

```bash
# Install from PyPI
pip install todopro-cli

# Verify installation
todopro version
```

### From Source

```bash
# Clone repository
git clone https://github.com/minhdqdev/todopro.git
cd todopro/todopro-cli

# Install the dependencies into a virtual environment
uv sync

# Run the CLI from the checkout
uv run todopro version
```

### Updating

```bash
todopro update
```

---

## Quick Start

TodoPro works **offline by default**.
On first run it creates a `local` context backed by a SQLite file on your machine, so no signup or internet is required.

### Create Your First Task

```bash
# Quick add (simplest way)
todopro add "Buy groceries"

# Add it to a project
todopro add "Buy groceries" --project Personal
```

**Output:**
```
Success: Task created successfully!

Task: Buy groceries

Task ID: 01a1363c-757f-72b4-90c4-755ae3b65182
```

In the local context `todopro add` stores your text as the task title.
The `#project`, `@label`, `p1`-`p4` and natural-language date shortcuts (for example `todopro add "Review PR tomorrow at 2pm #Work p1 @urgent"`) are parsed only in the cloud context.
To set a priority or due date locally, use `todopro task create` as shown below.

### View Your Tasks

```bash
# See today's tasks (overdue + due today)
todopro today

# List all active tasks
todopro task list
```

**Output:**
```
○ Buy groceries
   └─ #2
```

The short `#2` is the task's ID suffix.
You can pass it, or the full ID, to any command that takes a task ID.

### Complete a Task

```bash
# Mark task as done (full ID or the short suffix shown in the list)
todopro complete <task-id>
```

**Output:**
```
Success: ✓ Completed: Buy groceries
To undo: tp reopen 2
```

**Congratulations! 🎉** You've created and completed your first task in TodoPro.

---

## First Task - Interactive Tutorial

Let's walk through a complete workflow:

### Step 1: Add Your First Project

```bash
# Create a project to organize tasks
todopro project create "Personal"
```

The command prints the new project's ID.
You can look it up again at any time with `todopro project list`.

### Step 2: Add Tasks to Project

```bash
# Add task with project (project name or ID)
todopro add "Read productivity book" --project Personal

# Add another task with a priority and a due date
todopro task create "Call dentist for appointment" --project <project-id> --priority 2 --due 2026-03-01
```

`task create` takes `--project` as an ID, `--priority` from 1 (highest) to 4 (lowest, the default), and `--due` as an ISO date such as `2026-03-01`.

### Step 3: View Your Tasks

```bash
# See all active tasks
todopro task list

# Filter by project
todopro task list --project <project-id>

# Include completed tasks
todopro task list --show-completed

# See only today's tasks
todopro today
```

### Step 4: Add Labels for Organization

```bash
# Create labels
todopro label create "urgent" --color red
todopro label create "health" --color green

# See your labels
todopro label list
```

In the cloud context you attach a label while adding a task, for example `todopro add "Book check-up @health"`.

### Step 5: Complete Tasks

```bash
# Complete a task
todopro complete <task-id>

# Reopen if you made a mistake
todopro reopen <task-id>
```

---

## Basic Workflows

### Daily Task Management

```bash
# Morning: Check today's tasks
todopro today

# Add new tasks throughout the day
todopro task create "Respond to emails" --due 2026-03-01 --priority 1

# Mark tasks complete as you finish
todopro complete <task-id>

# Evening: Review what's left
todopro today
```

### Weekly Planning

```bash
# Review all active tasks
todopro task list --status active

# Move every overdue task to today
todopro reschedule

# Move one task to a specific date
todopro reschedule <task-id> --date 2026-03-06

# Search your tasks
todopro task list --search "meeting"
```

### Project Management

```bash
# Create project
todopro project create "Website Redesign"

# View project
todopro project describe <project-id>

# Add tasks to project
todopro add "Design mockups" --project "Website Redesign"
todopro add "Write content" --project "Website Redesign"

# View project's tasks
todopro task list --project <project-id>

# Archive when done
todopro project archive <project-id>
```

---

## Offline vs Online

### Offline Mode (Default)

TodoPro works offline by default. All your data is stored locally in SQLite.

**Location** (resolved with `platformdirs`):
- Linux: `~/.local/share/todopro_cli/todopro.db`
- macOS: `~/Library/Application Support/todopro_cli/todopro.db`
- Windows: `%LOCALAPPDATA%\todopro_cli\todopro.db`

**Benefits:**
- ✅ Works without internet
- ✅ Fast and responsive
- ✅ Your data stays on your device

### Online Mode (Optional)

Create a TodoPro account to use the cloud and to sync across devices.
Signing in only works in a remote context, so switch to the built-in `cloud` context first:

```bash
# Switch to the cloud context
todopro context use cloud

# Create an account (or use the website)
todopro auth signup

# Sign in
todopro auth login
```

**Sign-up can be web-only:** the hosted service protects registration with a CAPTCHA that the CLI cannot solve.
If `todopro auth signup` says sign-up is web-only, create the account at https://app.todopro.xyz and then run `todopro auth login`.

**Password rules:** at least 8 characters, with an uppercase letter, a lowercase letter and a special character.

**Confirm your email:** TodoPro only works for confirmed addresses.
Until you click the link in the confirmation email, the API answers every request with `403 email_not_verified` and the CLI tells you your email isn't confirmed yet.
To get a fresh link, run:

```bash
todopro auth resend-verification
```

**When to use online mode:**
- Multiple devices (laptop, desktop, phone)
- Cloud backup of tasks
- Natural-language quick add (`#project`, `@label`, dates, reminders)

**Privacy:** Sync is **not** end-to-end encrypted.
End-to-end encryption was discontinued, and the `todopro encryption` commands are stubs that only print a notice.
Tasks sync to the server as plaintext over HTTPS.

### Moving Data Between Local and Cloud

`todopro sync` copies data between a local context and a remote one:

```bash
# Run from the local context. Push local data to the cloud context
todopro context use local
todopro sync push --context cloud

# Pull cloud data into the local context
todopro sync pull --context cloud

# See when you last synced
todopro sync status
```

Useful flags are `--dry-run` (preview), `--full` (ignore the last sync time) and `--strategy local-wins|remote-wins` (conflict resolution).
You must be signed in to the cloud context before you sync.

---

## Understanding Contexts

TodoPro uses **contexts** to manage different storage locations.
A fresh install has two:

| Context | Type | What it is |
|---------|------|------------|
| `local` | local | SQLite file on your machine, no account needed (default) |
| `cloud` | remote | TodoPro Cloud at `https://api.todopro.xyz/api`, requires `auth login` |

```bash
# List contexts (the active one is marked with *)
todopro context list

# Use cloud storage
todopro context use cloud

# Go back to local storage
todopro context use local
```

You can add more contexts, for example a self-hosted server:

```bash
todopro context create work --type remote --source https://todo.example.com/api
```

Sign-in credentials are stored per context, so you sign in once per remote context.

**Tip:** Use the local context when offline, the cloud context when you need sync.

---

## Essential Commands

### Task Commands

```bash
# Add
todopro add "Task title"
todopro task create "Task" --due 2026-03-01 --priority 1 --project <project-id>

# List
todopro task list
todopro today
todopro task list --status completed
todopro task list --priority 1

# Update
todopro task update <id> --content "New title"
todopro task update <id> --due 2026-03-08
todopro edit <id>   # interactive

# Complete
todopro complete <id>
todopro reopen <id>

# Delete
todopro task delete <id>
```

### Project Commands

```bash
# Create
todopro project create "Project Name"

# List
todopro project list

# Update
todopro project update <id> --name "New Name"

# Archive
todopro project archive <id>
todopro project unarchive <id>
```

### Label Commands

```bash
# Create
todopro label create "urgent" --color red

# List
todopro label list
```

### Sync Commands

```bash
# Push local changes to a remote context
todopro sync push --context cloud

# Pull remote changes into the local context
todopro sync pull --context cloud

# Check sync status
todopro sync status
```

### Data Management

```bash
# Export data (backup)
todopro data export --output backup.json

# Export compressed
todopro data export --compress --output backup.json.gz

# Complete export with attachments, as a ZIP (cloud context only)
todopro data export --archive --output my-todopro-data.zip

# Import data (restore). Existing items with the same name are skipped
todopro data import backup.json
```

---

## Keyboard Shortcuts & Tips

### Quick Tips

1. **Use Tab Completion:**
   ```bash
   todopro --install-completion  # One-time setup
   ```

2. **Natural Language Dates (cloud context):**
   ```bash
   todopro add "Task tomorrow"
   todopro add "Task next friday at 3pm"
   todopro add "Water plants every monday"
   todopro add "File taxes" --deadline "April 15"
   ```
   In the local context, pass dates to `task create --due` as ISO dates (`2026-03-01`).

3. **Priority Levels:**
   - P1 = Highest (urgent)
   - P2 = High
   - P3 = Medium
   - P4 = Low (default for new tasks)

4. **JSON Output (for scripting):**
   ```bash
   todopro task list --json | jq '.tasks[]'
   ```

5. **Bulk Completion:**
   ```bash
   # Complete multiple tasks
   todopro complete <id1> <id2> <id3>
   ```

---

## Common Workflows

### Daily Review

```bash
#!/bin/bash
# Save as ~/bin/todopro-daily

# Show overdue and today's tasks
echo "📅 Today's Tasks:"
todopro today
```

Make it executable:
```bash
chmod +x ~/bin/todopro-daily
todopro-daily  # Run daily review
```

### Weekly Backup

```bash
#!/bin/bash
# Save as ~/bin/todopro-backup

# Backup to Dropbox
todopro data export --compress --output ~/Dropbox/todopro-backup-$(date +%Y%m%d).json.gz

# Keep only last 4 backups
cd ~/Dropbox && ls todopro-backup-*.json.gz | head -n -4 | xargs rm -f
```

Set up a weekly cron:
```bash
crontab -e
# Add: 0 9 * * 1 ~/bin/todopro-backup  # Every Monday 9am
```

### Pomodoro Timer

TodoPro has a built-in focus timer, so you do not need a script:

```bash
# Start a 25-minute focus session on a task
todopro focus start <task-id>

# Pick a duration or a template (deep_work, standard, quick_task)
todopro focus start <task-id> --duration 50
todopro focus start <task-id> --template deep_work

# Check on it and stop it
todopro focus status
todopro focus stop

# See your totals
todopro stats today
```

---

## Getting Help

### In-CLI Help

```bash
# General help
todopro --help

# Command-specific help
todopro add --help
todopro task --help
todopro sync --help
```

### Documentation

- **FAQ:** See [FAQ.md](./FAQ.md) for common questions
- **Troubleshooting:** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for issues
- **Changelog:** See [CHANGELOG.md](../CHANGELOG.md) for version history

### Community & Support

- **GitHub Issues:** https://github.com/minhdqdev/todopro/issues
- **Discussions:** https://github.com/minhdqdev/todopro/discussions
- **Email:** support@todopro.minhdq.dev

---

## Next Steps

Now that you're familiar with the basics:

1. ✅ **Create your project structure:**
   ```bash
   todopro project create "Work"
   todopro project create "Personal"
   todopro project create "Learning"
   ```

2. ✅ **Set up labels:**
   ```bash
   todopro label create "urgent" --color red
   todopro label create "important" --color yellow
   todopro label create "delegated" --color blue
   ```

3. ✅ **Configure auto-backup:**
   - See "Weekly Backup" workflow above

4. ✅ **Explore advanced features:**
   - Searching: `todopro task list --search "meeting"`
   - Bulk completion: `todopro complete <id1> <id2> <id3>`
   - Focus timer and stats: `todopro focus start <task-id>`, `todopro stats today`
   - Templates: `todopro template list`

---

## Welcome to TodoPro! 🎉

You're all set! TodoPro is designed to be simple yet powerful. Start with basic task management and gradually explore advanced features as you need them.

**Remember:**
- 🖥️ Works offline by default
- ☁️ Optional cloud account for sync across devices
- 🚀 Fast and keyboard-friendly
- 🎯 Your local data stays on your device

Happy tasking! 📝
