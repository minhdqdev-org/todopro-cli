# Getting Started with TodoPro CLI

Welcome to TodoPro! This guide will help you get up and running in less than 5 minutes.

---

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [First Task](#first-task)
- [Basic Workflows](#basic-workflows)
- [Offline vs Online](#offline-vs-online)
- [Next Steps](#next-steps)

---

## Installation

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

# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

---

## Quick Start

TodoPro works **offline by default**. No signup or internet required!

### Create Your First Task

```bash
# Quick add (simplest way)
todopro add "Buy groceries"

# With more details
todopro add "Buy groceries" --priority 1 --due today
```

**Output:**
```
Success: ✓ Task created: Buy groceries
```

### View Your Tasks

```bash
# See today's tasks
todopro today

# List all tasks
todopro list tasks
```

**Output:**
```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Task               ┃ Priority ┃ Due Date ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ Buy groceries      │ P1       │ Today    │ Active │
└────────────────────┴──────────┴──────────┴────────┘
```

### Complete a Task

```bash
# Mark task as done
todopro complete <task-id>

# Or use task number from list
todopro complete 1
```

**Congratulations! 🎉** You've created and completed your first task in TodoPro.

---

## First Task - Interactive Tutorial

Let's walk through a complete workflow:

### Step 1: Add Your First Project

```bash
# Create a project to organize tasks
todopro create project "Personal" --description "Personal tasks and errands"
```

### Step 2: Add Tasks to Project

```bash
# Add task with project
todopro add "Read productivity book" --project Personal --priority 2

# Add another task
todopro add "Call dentist for appointment" --project Personal --due tomorrow
```

### Step 3: View Your Tasks

```bash
# See all tasks
todopro list tasks

# Filter by project
todopro list tasks --project Personal

# See only today's tasks
todopro today
```

### Step 4: Add Labels for Organization

```bash
# Create labels
todopro create label "urgent" --color red
todopro create label "health" --color green

# Add label to task
todopro update task <task-id> --label health
```

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
todopro add "Respond to emails" --due today --priority 1

# Mark tasks complete as you finish
todopro complete <task-id>

# Evening: Review what's left
todopro today
```

### Weekly Planning

```bash
# Review all active tasks
todopro list tasks --status active

# Reschedule overdue tasks
todopro reschedule --overdue

# Add tasks for upcoming week
todopro add "Team meeting prep" --due monday
todopro add "Submit report" --due friday
```

### Project Management

```bash
# Create project
todopro create project "Website Redesign" --description "Q1 redesign project"

# View project
todopro describe project "Website Redesign"

# Add tasks to project
todopro add "Design mockups" --project "Website Redesign" --priority 1
todopro add "Write content" --project "Website Redesign" --priority 2

# View project's tasks
todopro list tasks --project "Website Redesign"

# Archive when done
todopro archive project "Website Redesign"
```

---

## Offline vs Online

### Offline Mode (Default)

TodoPro works offline by default. All your data is stored locally in SQLite.

**Location:**
- Linux: `~/.local/share/todopro_cli/todopro.db`
- macOS: `~/Library/Application Support/todopro_cli/todopro.db`
- Windows: `%LOCALAPPDATA%\todopro_cli\todopro.db`

**Benefits:**
- ✅ Works without internet
- ✅ Fast and responsive
- ✅ Complete privacy (data never leaves your device)
- ✅ Free forever

### Online Mode (Optional Sync)

Sign up for a free account to sync across devices:

```bash
# Sign up for account
todopro signup

# Login on another device
todopro login

# Sync your data
todopro sync push   # Upload local data
todopro sync pull   # Download remote data
```

**When to use online mode:**
- Multiple devices (laptop, desktop, phone)
- Team collaboration (future feature)
- Cloud backup of tasks

**Privacy:** TodoPro uses **end-to-end encryption** (E2EE) when syncing. The server never sees your plaintext data.

---

## Understanding Contexts

TodoPro uses **contexts** to manage different storage locations:

### Local Context (Default)

```bash
# Your data is stored locally
# No account or internet needed
```

### Remote Context (After Login)

```bash
# Switch to remote (cloud) storage
todopro use cloud

# Your data syncs with the server
# Accessible from any device
```

### Switch Between Contexts

```bash
# Use local storage
todopro use local

# Use cloud storage (after login)
todopro use cloud

# List available contexts
todopro list contexts
```

**Tip:** Use local context when offline, remote when you need sync.

---

## End-to-End Encryption (E2EE)

TodoPro encrypts your data before syncing to the cloud:

### Set Up Encryption

```bash
# Enable E2EE (one-time setup)
todopro encryption setup

# Save your 24-word recovery phrase (shown on screen)
# ⚠️ CRITICAL: Write it down and store securely!
```

### Check Encryption Status

```bash
# Verify E2EE is enabled
todopro encryption status
```

**Output:**
```
Encryption Status: ✅ Enabled
Key Location: ~/.config/todopro_cli/encryption.key
Key Fingerprint: a1b2c3...
```

### Recover on New Device

```bash
# If you lost your encryption key
todopro encryption recover

# Enter your 24-word recovery phrase when prompted
```

**Important:**
- ✅ Server never sees your plaintext data
- ✅ All task content and descriptions are encrypted
- ⚠️ If you lose your recovery phrase, your data is unrecoverable!

---

## Essential Commands

### Task Commands

```bash
# Add
todopro add "Task title"
todopro add "Task" --due tomorrow --priority 1 --project "Work"

# List
todopro list tasks
todopro today
todopro list tasks --filter=overdue

# Update
todopro update task <id> --content "New title"
todopro update task <id> --due "next monday"

# Complete
todopro complete <id>
todopro reopen <id>

# Delete
todopro delete task <id>
```

### Project Commands

```bash
# Create
todopro create project "Project Name"

# List
todopro list projects

# Update
todopro update project <id> --name "New Name"

# Archive
todopro archive project <id>
todopro unarchive project <id>
```

### Label Commands

```bash
# Create
todopro create label "urgent" --color red

# List
todopro list labels

# Update
todopro update label <id> --color blue
```

### Sync Commands

```bash
# Push local changes to server
todopro sync push

# Pull server changes to local
todopro sync pull

# Check sync status
todopro sync status
```

### Data Management

```bash
# Export data (backup)
todopro data export --output backup.json

# Export compressed
todopro data export --output backup.json.gz --compress

# Import data (restore)
todopro data import backup.json
```

---

## Keyboard Shortcuts & Tips

### Quick Tips

1. **Use Tab Completion:**
   ```bash
   todopro --install-completion  # One-time setup
   todopro add <TAB>             # Auto-complete
   ```

2. **Natural Language Dates:**
   ```bash
   todopro add "Task" --due today
   todopro add "Task" --due tomorrow
   todopro add "Task" --due "next friday"
   todopro add "Task" --due "2026-03-01"
   ```

3. **Priority Levels:**
   - P1 = Highest (urgent & important)
   - P2 = High (important but not urgent)
   - P3 = Medium (default)
   - P4 = Low (nice to have)

4. **JSON Output (for scripting):**
   ```bash
   todopro list tasks --format json | jq '.[]'
   ```

5. **Bulk Operations:**
   ```bash
   # Complete multiple tasks
   todopro complete <id1> <id2> <id3>
   
   # Delete multiple
   todopro delete task <id1> <id2>
   ```

---

## Common Workflows

### Daily Review

```bash
#!/bin/bash
# Save as ~/bin/todopro-daily

# Show today's tasks
echo "📅 Today's Tasks:"
todopro today

# Show overdue tasks
echo "\n⚠️  Overdue:"
todopro list tasks --filter=overdue
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

### Pomodoro Timer Script

```bash
#!/bin/bash
# pomodoro.sh - Simple Pomodoro with TodoPro

TASK_ID=$1
MINUTES=${2:-25}

echo "🍅 Pomodoro: $MINUTES minutes"
echo "Working on task: $(todopro get task $TASK_ID --format json | jq -r '.content')"

# Timer
sleep ${MINUTES}m

# Mark progress (add comment or update)
echo "✅ Pomodoro completed!"
```

---

## Getting Help

### In-CLI Help

```bash
# General help
todopro --help

# Command-specific help
todopro add --help
todopro list --help
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

1. ✅ **Set up E2EE** (if using online sync):
   ```bash
   todopro encryption setup
   ```

2. ✅ **Create your project structure:**
   ```bash
   todopro create project "Work"
   todopro create project "Personal"
   todopro create project "Learning"
   ```

3. ✅ **Set up labels:**
   ```bash
   todopro create label "urgent" --color red
   todopro create label "important" --color yellow
   todopro create label "delegated" --color blue
   ```

4. ✅ **Configure auto-backup:**
   - See "Weekly Backup" workflow above

5. ✅ **Explore advanced features:**
   - Filtering: `todopro list tasks --filter=today --project=Work`
   - Searching: `todopro list tasks --search "meeting"`
   - Bulk operations: `todopro complete <id1> <id2> <id3>`

---

## Welcome to TodoPro! 🎉

You're all set! TodoPro is designed to be simple yet powerful. Start with basic task management and gradually explore advanced features as you need them.

**Remember:**
- 🖥️ Works offline by default
- 🔐 End-to-end encrypted sync (optional)
- 🚀 Fast and keyboard-friendly
- 🎯 Privacy-focused (your data, your control)

Happy tasking! 📝
