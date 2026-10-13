---
updated_at: 2026-10-14T00:11:01+07:00
---

# TodoPro CLI - Frequently Asked Questions (FAQ)

---

## General Questions

### What is TodoPro?

TodoPro is a **CLI-first task management system** designed for power users, developers, and privacy-conscious individuals. It works offline by default, syncs with the TodoPro cloud when you want it to, and provides a scriptable interface for automation.

**Key Features:**

- 🖥️ **CLI-First:** Terminal interface with intuitive commands
- 💾 **Offline-Capable:** Local SQLite storage, no internet required
- 🤖 **Scriptable:** JSON output, automation-ready
- 🎯 **Privacy-Focused:** Local-only mode keeps your data on your machine, no account needed

---

### How is TodoPro different from Todoist?

| Feature          | TodoPro                           | Todoist             |
| ---------------- | --------------------------------- | ------------------- |
| **Interface**    | CLI, plus web and mobile apps     | Web/Mobile GUI      |
| **Offline Mode** | ✅ Works fully offline            | ⚠️ Limited offline  |
| **Privacy**      | ✅ Local-only mode, no account    | ❌ Account required |
| **Target User**  | Developers, power users           | General consumers   |
| **Automation**   | ✅ Fully scriptable               | ⚠️ Limited API      |
| **Open Source**  | ✅ Yes                            | ❌ No               |

**Choose TodoPro if:**

- You prefer keyboard over mouse
- You value privacy and data ownership
- You need offline access
- You want to automate task management
- You're comfortable with command-line tools

**Choose Todoist if:**

- You prefer a purely visual interface and a long-established ecosystem

Coming from Todoist? `todopro import todoist` migrates your projects, tasks, and labels.

---

### Is TodoPro free?

**Yes!** Offline usage in the `local` context is **completely free** with no limitations, and needs no account.

A cloud account (the `cloud` context) is optional and has Free and Pro plans. Pro unlocks extras such as the productivity hub (`todopro hub list`). See the TodoPro web app for current plans and limits.

**What's free forever:**

- ✅ Unlimited tasks and projects in a local context
- ✅ All core task features
- ✅ Export/import data
- ✅ CLI interface

---

## Installation & Setup

### How do I install TodoPro?

TodoPro CLI requires **Python 3.14 or newer**.

**Recommended (using uv):**

```bash
uv tool install todopro-cli
todopro version
```

Both `todopro` and the short alias `tp` are installed. To upgrade later, run `todopro update`.

See [GETTING_STARTED.md](./GETTING_STARTED.md#installation) for detailed instructions.

---

### Where is my data stored?

TodoPro stores data locally by default, in the paths chosen by [platformdirs](https://pypi.org/project/platformdirs/).

**Linux:**

```
~/.local/share/todopro_cli/todopro.db
```

**macOS:**

```
~/Library/Application Support/todopro_cli/todopro.db
```

**Windows:** under `%LOCALAPPDATA%\todopro_cli\`.

**Configuration (Linux):**

```
~/.config/todopro_cli/config.json
```

On macOS the configuration lives next to the database in `~/Library/Application Support/todopro_cli/`. Per-context login credentials are kept in a `credentials/` folder beside `config.json` with `0600` permissions.

---

### What are contexts?

A **context** is a named place where your tasks live. Two exist out of the box:

- `local` (the default): a SQLite database on your machine
- `cloud`: the TodoPro API at `https://todopro.minhdq.dev/api`, which needs a login

Switch with `todopro context use <name>`. See [How do I use multiple contexts?](#how-do-i-use-multiple-contexts).

---

### Can I use TodoPro without an account?

**Yes!** TodoPro works completely offline in the `local` context without any account. Just install and start using it.

You only need an account if you want to:

- Sync across multiple devices
- Back up data to the cloud
- Use cloud-only features such as natural language quick add, Dictate, the GitHub and Calendar integrations, and the web and mobile apps

---

## Usage Questions

### How do I add a task?

**Quick add (simplest):**

```bash
todopro add "Buy groceries"
```

In a cloud context, quick add understands natural language: `#Project`, `@label`, `p1`-`p4` for priority, dates, recurrence, and reminders.

```bash
todopro add "Review PR tomorrow at 2pm #Work p1 @urgent"
todopro add "Team standup every monday at 9am #Work"
todopro add "File taxes" --deadline "April 15"
todopro add "Buy groceries" --project "Personal"
```

In a local context, `add` stores the text as the task content without parsing it. Use `task create` when you want explicit fields.

**With explicit fields (any context):**

```bash
todopro task create "Buy groceries" \
  --due tomorrow \
  --priority 1 \
  --project <project-id> \
  --labels shopping,home
```

---

### How do I view my tasks?

**Today's tasks (overdue plus due today):**

```bash
todopro today
```

**All tasks:**

```bash
todopro task list
```

**Filter by project (project ID):**

```bash
todopro task list --project <project-id>
```

**Filter by status:**

```bash
todopro task list --status active
todopro task list --status completed
```

**Filter by priority, or include completed tasks:**

```bash
todopro task list --priority 1
todopro task list --show-completed
```

**Search:**

```bash
todopro task list --search "meeting"
```

**Saved filters:**

```bash
todopro task apply filter "My filter"
```

---

### How do I complete, edit, or reschedule a task?

Every task shows a short unique suffix in brackets, such as `[3f]`. Use it in place of the full ID.

```bash
todopro complete 3f 9a            # complete one or more tasks
todopro reopen 3f                 # undo a completion
todopro edit 3f                   # interactive
todopro edit 3f --content "New title" --due tomorrow --priority 2
todopro reschedule 3f             # move to today
todopro reschedule 3f --date tomorrow
todopro reschedule                # move all overdue tasks to today
todopro task delete 3f
```

---

### What date formats are supported?

Natural language dates work in `todopro add` (cloud context) and in the `--due` flag of `task create`, `task update`, and `edit`:

```bash
todopro task create "Task" --due today
todopro task create "Task" --due tomorrow
todopro task create "Task" --due "next monday"
todopro task create "Task" --due "in 3 days"
```

Also ISO format:

```bash
todopro task create "Task" --due 2026-03-15
```

`todopro reschedule --date` accepts `today`, `tomorrow`, or `YYYY-MM-DD`.

---

### How do priority levels work?

TodoPro uses 4 priority levels, where 1 is the most urgent:

- **P1 (Urgent)**
- **P2 (High)**
- **P3 (Medium)**
- **P4 (Normal):** the default

In quick add, write `p1`-`p4` (or `!!1`-`!!4`) in the text. With the explicit commands, use `--priority`:

```bash
todopro add "Pay rent p1"
todopro task create "Pay rent" --priority 1
todopro task list --priority 1
```

**Default:** If you don't specify, tasks are created with P4.

---

### Can I use TodoPro in scripts?

**Absolutely!** TodoPro is designed for automation:

**JSON Output:**

```bash
todopro task list --output json | jq '.'
todopro today --json
```

`--json` is an alias for `--output json` on most commands.

**Example Script (Daily Report):**

```bash
#!/bin/bash
# Generate daily task report

TODAY=$(todopro today --json)
COUNT=$(echo "$TODAY" | jq 'length')

echo "📋 You have $COUNT tasks today:"
echo "$TODAY" | jq -r '.[] | "- [\(.priority)] \(.content)"'
```

Check the JSON shape of your version first, since the top-level structure may differ per command.

**Exit Codes:**

- `0` = Success
- non-zero = Error

Use `--yes` / `-y` where a command asks for confirmation.

---

## Sync & Cloud

### How do I sync my data?

`sync push` and `sync pull` move data between a **local** context and a **remote** one. Name the remote context with `--context`.

**First-time setup:**

```bash
# 1. Sign up for an account in the cloud context
todopro context use cloud
todopro auth signup

# 2. Go back to your local data and push it
todopro context use local
todopro sync push --context cloud
```

New accounts must confirm their email address. If the email did not arrive, run `todopro auth resend-verification`.

**On another device:**

```bash
# 1. Login
todopro context use cloud
todopro auth login

# 2. Pull data into the local context
todopro context use local
todopro sync pull --context cloud
```

**Regular sync:**

```bash
todopro sync push --context cloud  # Upload changes
todopro sync pull --context cloud  # Download changes
todopro sync status                # Last sync times
```

You can preview a sync with `--dry-run`, ignore the last sync timestamp with `--full`, and choose how conflicts resolve with `--strategy local-wins|remote-wins`.

---

### Is my data encrypted?

Data you sync to the cloud is protected in transit (HTTPS) and at rest by the server. **End-to-end (client-side) encryption was discontinued** (ADR-0024), so the server can read what you sync.

If you need your data to stay entirely under your control, use the `local` context: it never leaves your machine.

The `todopro encryption` command group still exists, but every subcommand is a discontinued stub. There is no key, recovery phrase, or rotation to manage.

---

### Can I use TodoPro on multiple devices?

**Yes!** Use cloud sync:

**Device 1 (First device):**

```bash
todopro context use cloud
todopro auth signup
todopro context use local
todopro sync push --context cloud
```

**Device 2 (Additional device):**

```bash
todopro context use cloud
todopro auth login
todopro context use local
todopro sync pull --context cloud
```

**Keep devices in sync:**

```bash
todopro sync push --context cloud  # After making changes
todopro sync pull --context cloud  # Before starting work
```

**Tip:** Set up a cron job for auto-sync:

```bash
# Sync every hour (run from the local context)
0 * * * * todopro sync pull --context cloud && todopro sync push --context cloud
```

Alternatively, stay in the `cloud` context on every device and skip sync entirely; the API is then the single source of truth.

---

## Data Management

### How do I backup my data?

**Export to JSON:**

```bash
todopro data export --output ~/backups/todopro-$(date +%Y%m%d).json
```

**Export compressed:**

```bash
todopro data export --compress --output ~/backups/todopro.json.gz
```

**Complete export with attachments (cloud context only):**

```bash
todopro data export --archive --output my-todopro-data.zip
```

**Automated weekly backup:**

```bash
# Add to crontab
0 9 * * 1 todopro data export --compress --output ~/Dropbox/todopro-backup-$(date +\%Y\%m\%d).json.gz
```

---

### How do I restore from backup?

**Import from backup:**

```bash
todopro data import ~/backups/todopro-20260217.json
```

**Import handles:**

- ✅ Duplicate detection (skips existing items with the same name)
- ✅ Compressed files (.json.gz)
- ✅ Confirmation prompt (use `--yes` to skip)

**Example:**

```bash
# Delete local database
rm ~/.local/share/todopro_cli/todopro.db

# Restore from backup
todopro data import backup.json --yes
```

---

### How do I delete all my data?

```bash
todopro data export --output backup.json   # export first
todopro data purge --dry-run               # preview
todopro data purge                         # delete everything; cannot be undone
```

---

### Can I export to CSV?

**Not yet.** CSV export is planned for a future release.

**Current formats:**

- ✅ JSON (full data)
- ✅ Gzip compressed JSON
- ✅ ZIP archive with attachments (`--archive`, cloud context)

**Workaround (convert JSON to CSV):**

```bash
todopro data export --output export.json
jq -r '.data.tasks[] | [.content, .priority, .due_date] | @csv' export.json > tasks.csv
```

Inspect the file first, since the exact JSON layout may differ between versions.

---

### Can I import from Todoist?

**Yes.** You need a Todoist personal API token.

```bash
todopro import todoist --api-key YOUR_TOKEN
todopro import todoist --dry-run --api-key YOUR_TOKEN     # preview counts only
todopro import todoist --include-completed --api-key YOUR_TOKEN
```

In a cloud context the import runs on the TodoPro backend and brings sections, subtasks, recurrence, and comments. In a local context it runs client-side and imports projects, labels, tasks, and due dates.

---

## Troubleshooting

### Command not found: todopro

**Cause:** Installation directory not in PATH.

**Fix:**

```bash
# If installed with uv
export PATH="$HOME/.local/bin:$PATH"

# Add to ~/.bashrc or ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

### "Login is only available for remote contexts"

**Cause:** `auth login`, `auth signup`, and `auth logout` only work in a remote context, and you are in `local`.

**Fix:**

```bash
todopro context use cloud
todopro auth login
# Enter your email and password
```

---

### Sync conflicts

**Cause:** Data modified on multiple devices without sync.

**Fix:**

```bash
# Check sync status
todopro sync status

# Pull latest from the cloud (cloud wins by default)
todopro sync pull --context cloud

# Push your changes (local wins by default)
todopro sync push --context cloud
```

**Best Practice:** Always pull before push:

```bash
todopro sync pull --context cloud && todopro sync push --context cloud
```

---

### Database locked

**Cause:** Another TodoPro process is running.

**Fix:**

```bash
# Check for running processes
ps aux | grep todopro

# Stop it by PID if necessary
kill <pid>

# Try again
todopro task list
```

---

## Advanced

### How do I use multiple contexts?

**Contexts** are different storage locations:

```bash
# List contexts
todopro context list

# Create local context
todopro context create local-work \
  --type local \
  --source ~/.todopro-work.db

# Switch contexts
todopro context use local-work

# Your data is now in a separate database
todopro add "Work task"

# Switch back to default
todopro context use local

# Rename or remove a context
todopro context rename local-work work
todopro context delete work
```

To add another cloud server, create a remote context with `todopro context create <name> --type remote --source <api-url>`.

---

### Does TodoPro support recurring tasks?

**Yes**, in a cloud context. Quick add understands recurrence:

```bash
todopro add "Weekly review every monday at 9am #Work"
todopro add "Water plants every! 3 days"
```

`every!` re-anchors the next occurrence to when you complete the task. To skip one occurrence of a recurring task, run `todopro task skip <id>`. Task templates can also carry a recurrence (`todopro template create --recur`).

---

### Can I add subtasks or dependencies?

Task dependencies are available through `task link`:

```bash
todopro task link add <task-id> --blocked-by <other-task-id>
todopro task link list <task-id>
```

For sub-steps inside a single task, use the description field:

```bash
todopro task create "Project X" --description "1. Research
2. Design
3. Implement
4. Test"
```

---

### Can I share a project?

**Yes**, in a cloud context:

```bash
todopro project share share <project-id> --email teammate@example.com
todopro project share collaborators <project-id>
todopro project share unshare <project-id> --email teammate@example.com
todopro project share leave <project-id>
```

---

### What integrations are available?

All of them need a cloud context.

- **GitHub:** `todopro github connect --pat <token>`, then `github projects`, `github link`, `github sync`, `github import`, and `github push`
- **Hub (Pro):** `todopro hub list` shows items from your linked providers in one feed
- **Google Calendar:** `todopro calendar connect`, `calendar push`, `calendar pull`
- **Voice:** `todopro dictate` turns a spoken recording into tasks; `--text "..."` skips the microphone

---

### Can I use TodoPro in CI/CD?

**Yes!** TodoPro is great for automation:

**Example (GitHub Actions):**

```yaml
name: Daily Task Report

on:
  schedule:
    - cron: "0 9 * * *" # 9am daily

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - name: Install TodoPro
        run: uv tool install todopro-cli

      - name: Login
        run: |
          todopro context use cloud
          todopro auth login --email "${{ secrets.TODOPRO_EMAIL }}" --password "${{ secrets.TODOPRO_PASSWORD }}"

      - name: Report
        run: |
          todopro today --json | jq '.[] | .content'
```

---

### How do I contribute?

**We welcome contributions!**

1. **Report bugs:** https://github.com/minhdqdev/todopro/issues
2. **Suggest features:** https://github.com/minhdqdev/todopro/discussions
3. **Submit PRs:** Fork, branch, commit, push, PR
4. **Improve docs:** Fix typos, add examples, clarify instructions

**Development:**

```bash
git clone https://github.com/minhdqdev-org/todopro-cli.git
cd todopro-cli
mise install
mise run install
mise run test
```

---

## Contact & Support

### Where can I get help?

**Documentation:**

- [Getting Started](./GETTING_STARTED.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [FAQ](./FAQ.md) (this document)

**Community:**

- GitHub Issues: https://github.com/minhdqdev/todopro/issues
- GitHub Discussions: https://github.com/minhdqdev/todopro/discussions

**Email:**

- support@todopro.minhdq.dev

---

### How do I report a bug?

**GitHub Issues:** https://github.com/minhdqdev/todopro/issues/new

**Include:**

1. TodoPro version: `todopro version`
2. OS and Python version
3. Steps to reproduce
4. Expected vs actual behavior
5. Error messages (if any)

**Example:**

```
**Bug:** Sync fails with "connection timeout"

**Environment:**
- TodoPro: <output of `todopro version`>
- OS: Ubuntu 24.04
- Python: 3.14

**Steps:**
1. Run `todopro sync push --context cloud`
2. Wait 30 seconds
3. Get timeout error

**Expected:** Data syncs successfully
**Actual:** Connection timeout after 30s

**Error:**
Error: Connection timeout
```

---

### Is there a web interface or a mobile app?

**Yes.** TodoPro also has a web app at https://app.todopro.xyz and a mobile app, backed by the same service the `cloud` context talks to. Log in with the same account to see the tasks you synced from the CLI.

---

## Didn't find your answer?

**Ask on GitHub Discussions:**
https://github.com/minhdqdev/todopro/discussions

**Or email us:**
support@todopro.minhdq.dev

We're here to help! 🚀
