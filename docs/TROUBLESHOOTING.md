---
updated_at: 2026-10-14T00:17:43+07:00
---

# TodoPro CLI - Troubleshooting Guide

**Last Updated:** 2026-10-14

This guide helps you resolve common issues with TodoPro CLI.

---

## 📋 Quick Diagnosis

### Check Your Installation

```bash
# Verify TodoPro is installed
which todopro

# Check version
todopro version

# Test basic command
todopro task list
```

**Expected Output:**

`todopro version` prints the version number on a single line.

```
1.0.0
```

On a fresh install `todopro task list` prints nothing (or an empty list) and creates the local database for you.

---

## Installation Issues

### Problem: "Command not found: todopro"

**Symptoms:**

```bash
$ todopro --help
bash: todopro: command not found
```

**Causes:**

1. TodoPro not installed
2. Installation directory not in PATH

**Solutions:**

**Option 1: Install TodoPro**

```bash
# Using uv (recommended)
uv tool install todopro-cli
```

**Option 2: Fix PATH**

```bash
# Let uv add its tool directory to your shell profile
uv tool update-shell

# Or find where TodoPro is installed
pip show todopro-cli | grep Location

# Add to PATH (Linux/macOS)
export PATH="$HOME/.local/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Option 3: Use full path**

```bash
# Find full path
which todopro

# Or use Python module
python -m todopro_cli.main --help
```

The short alias `tp` is installed alongside `todopro`, so if one is missing the other will be too.

---

### Problem: "ModuleNotFoundError: No module named 'todopro_cli'"

**Symptoms:**

```bash
$ todopro --help
ModuleNotFoundError: No module named 'todopro_cli'
```

**Cause:** TodoPro not installed or wrong Python environment

**Solution:**

```bash
# Check Python version
python --version  # Should be 3.14+

# Install TodoPro
pip install todopro-cli

# Or with specific Python version
python3.14 -m pip install todopro-cli
```

---

### Problem: pip refuses to install ("requires a different Python")

**Symptoms:**

```bash
$ pip install todopro-cli
ERROR: Package 'todopro-cli' requires a different Python: 3.12.3 not in '>=3.14'
```

**Cause:** TodoPro CLI needs Python 3.14 or newer.

**Solution:**

```bash
# uv downloads a suitable Python for you
uv tool install --python 3.14 todopro-cli
```

---

### Problem: "Permission denied" during installation

**Symptoms:**

```bash
$ pip install todopro-cli
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Cause:** Trying to install system-wide without sudo

**Solution:**

**Option 1: Install for user only (recommended)**

```bash
pip install --user todopro-cli
```

**Option 2: Use virtual environment**

```bash
python -m venv ~/.venv/todopro
source ~/.venv/todopro/bin/activate
pip install todopro-cli
```

**Option 3: Use uv (best practice)**

```bash
uv tool install todopro-cli
```

---

## Database Issues

The local context stores everything in a single SQLite file.
On Linux it lives at `~/.local/share/todopro_cli/todopro.db`, and on macOS at `~/Library/Application Support/todopro_cli/todopro.db`.
`todopro context list` shows the exact path in the `SOURCE` column.

### Problem: "Database is locked"

**Symptoms:**

```bash
$ todopro add "Task"
Error: An unexpected error occurred: database is locked
```

**Cause:** Another TodoPro process is writing to the database.
The CLI already retries a locked write a few times with a short back-off, so you only see this error when the other process holds the lock for longer.

**Solution:**

**Step 1: Check for running processes**

```bash
ps aux | grep todopro
```

**Step 2: Stop stale processes**

```bash
kill <pid>
```

**Step 3: Try again**

```bash
todopro add "Task"
```

**Note:** The database runs in WAL mode, so `todopro.db-wal` and `todopro.db-shm` files next to `todopro.db` are normal while TodoPro is running.
Do not delete them by hand, because recent writes may still be in them.

---

### Problem: "Database file is corrupt"

**Symptoms:**

```bash
$ todopro task list
Error: An unexpected error occurred: database disk image is malformed
```

**Cause:** Database corruption (power loss, disk error, etc.)

**Solution:**

**Option 1: Restore from backup**

```bash
# If you have a recent export
todopro data import backup.json
```

**Option 2: Recover what you can**

```bash
# Backup corrupt database
cp ~/.local/share/todopro_cli/todopro.db ~/todopro-corrupt.db

# Try SQLite recovery
sqlite3 ~/todopro-corrupt.db ".dump" | sqlite3 ~/todopro-recovered.db

# Replace database
mv ~/todopro-recovered.db ~/.local/share/todopro_cli/todopro.db

# Test
todopro task list
```

**Option 3: Start fresh (last resort)**

```bash
# Backup database
mv ~/.local/share/todopro_cli/todopro.db ~/todopro-old.db

# TodoPro will create new database
todopro task list
```

**Prevention:**

- Set up regular backups: `todopro data export --compress --output backup.json.gz`
- Keep a copy in the cloud context (see [Sync Issues](#sync-issues))

---

## Authentication Issues

Signing in only works in a remote context.
If you see `Login is only available for remote contexts`, switch first:

```bash
todopro context use cloud
```

### Problem: "Not logged in"

**Symptoms:**

```bash
$ todopro task list
Error: Not logged in. Use 'todopro login' to authenticate.
```

**Cause:** You are in a remote context (such as `cloud`) but have not signed in to it yet.
Credentials are stored per context.

**Solution:**

The command named in the message is spelled `todopro auth login`:

```bash
# Login with your account
todopro auth login
# Enter email and password when prompted

# Verify login
todopro task list
```

**If you don't have an account:**

```bash
# Sign up first
todopro auth signup

# Then login
todopro auth login
```

**If you only want local, offline tasks:**

```bash
todopro context use local
```

---

### Problem: "Your email address isn't confirmed yet"

**Symptoms:**

```
⚠ Your email address isn't confirmed yet.
Click the link we emailed you, or request a new one: todopro auth resend-verification
```

**Cause:** TodoPro only works for confirmed email addresses.
Sign-in still succeeds, but until you click the link in the confirmation email the server answers every other request with `403 email_not_verified`.

**Solution:**

```bash
# Ask for a fresh confirmation link
todopro auth resend-verification

# Or send it to a specific address
todopro auth resend-verification --email you@example.com
```

Open the link in the email, then run your command again.
Check your spam folder if nothing arrives.
The server gives the same reply whether or not the address is known, so a success message does not prove that an account exists.

---

### Problem: Login or signup fails

**Symptoms:**

```bash
$ todopro auth login
Error: Login failed: ...
```

**Causes:**

1. Wrong email/password
2. Account doesn't exist
3. Network issues
4. For signup, a password that breaks the rules (at least 8 characters, with an uppercase letter, a lowercase letter and a special character)

**Solutions:**

**Check credentials:**

```bash
# Verify email is correct
# Check for typos in password

# There is no password-reset command in the CLI.
# Contact support: support@todopro.minhdq.dev
```

**Check network:**

```bash
# Show which server the active context talks to
todopro context list

# Test that it answers (any HTTP status means it is reachable)
curl -sS -o /dev/null -w '%{http_code}\n' <SOURCE from context list>
```

**Create new account:**

```bash
todopro auth signup
```

---

### Problem: "Your session has expired or is no longer valid"

**Symptoms:**

```bash
$ todopro task list
⚠ Your session has expired or is no longer valid.
```

The hint printed under that line still names the old `login` command.
The current spelling is `auth login`, as shown below.

**Cause:** The stored token was rejected by the server (HTTP 401).
It may have expired, been revoked, or been issued for a different server.

**Solution:**

```bash
# Login again
todopro auth login

# Try again
todopro task list
```

---

## Sync Issues

`todopro sync` copies data between a **local** context and a **remote** one.
Run it from the local context and name the remote one with `--context`:

```bash
todopro context use local
todopro sync push --context cloud
todopro sync pull --context cloud
```

### Problem: "Connection timeout"

**Symptoms:**

```bash
$ todopro task list
# Hangs, then fails with a timeout or connection error
```

**Causes:**

1. No internet connection
2. Server is down
3. Firewall blocking connection

**Solutions:**

**Check internet:**

```bash
# Ping Google
ping -c 3 google.com

# Test the server of the active context
todopro context list
curl -sS -o /dev/null -w '%{http_code}\n' <SOURCE from context list>
```

**Check firewall:**

```bash
# If on corporate network, HTTPS might be blocked
# Try from different network (home, mobile hotspot)
```

**Increase timeout (temporary workaround):**

```bash
# Default is 30 seconds
todopro config get api.timeout
todopro config set api.timeout 60
```

Failed requests are retried automatically (`api.retry`, default 3) with a growing delay, so a command can take longer than one timeout before it gives up.

---

### Problem: "Sync conflicts"

**Symptoms:**

```bash
$ todopro sync push --context cloud
  ⚠ 1 task conflicts detected
  See ~/.todopro/sync-conflicts.json for details
  Consider running 'todopro sync pull' first
```

**Cause:** The same task was modified on both sides.

**Solutions:**

Choose who wins with `--strategy`:

**Option 1: Remote wins (discard local changes)**

```bash
todopro sync pull --context cloud --strategy remote-wins
```

**Option 2: Local wins (overwrite remote)**

```bash
todopro sync push --context cloud --strategy local-wins
```

`pull` defaults to `remote-wins` and `push` defaults to `local-wins`.

**Best Practice: preview first, and sync before starting work**

```bash
# See what would change without applying it
todopro sync pull --context cloud --dry-run

# At start of day
todopro sync pull --context cloud

# At end of day
todopro sync push --context cloud
```

---

### Problem: "Sync refuses to run"

**Symptoms and fixes:**

| Error message | What it means | Fix |
| --- | --- | --- |
| `--context is required to specify push target` | You did not say which remote context to push to | `todopro sync push --context cloud` |
| `--context is required when current context is local` | Same, for pull | `todopro sync pull --context cloud` |
| `Can only push from local contexts. Switch to a local context first.` | The active context is remote | `todopro context use local` |
| `Cannot pull from remote to remote. Switch to a local context first.` | The active context is remote | `todopro context use local` |
| `Context '<name>' not found` | Typo in `--context` | `todopro context list` |

**Check when you last synced:**

```bash
todopro sync status
```

---

## Encryption (discontinued)

End-to-end encryption was **discontinued** (ADR-0024).
There is no client-side encryption key, no 24-word recovery phrase, and nothing to set up or recover before syncing.

The `todopro encryption` command group is still present for backwards compatibility, but every subcommand is a stub that prints a notice and exits.
If a script of yours still calls `todopro encryption setup` or `todopro encryption recover`, you can remove that step.

Your tasks sync to the server as plaintext, protected in transit by HTTPS.

---

## Performance Issues

### Problem: "Commands are slow"

**Symptoms:**

```bash
$ todopro task list
# Takes 5+ seconds
```

**Causes:**

1. Large database (1000s of tasks)
2. Slow disk I/O
3. Heavy sync operations

**Solutions:**

**Check database size:**

```bash
du -h ~/.local/share/todopro_cli/todopro.db
# If >100MB, might be too large
```

**Page through results instead of listing everything:**

```bash
# task list returns up to 250 tasks by default
todopro task list --limit 50
todopro task list --limit 50 --offset 50
```

**Archive old tasks:**

```bash
# Export a backup first
todopro data export --compress --output archive-2025.json.gz

# Then delete tasks you no longer need
todopro task delete <task-id>
```

**Optimize database:**

```bash
sqlite3 ~/.local/share/todopro_cli/todopro.db "VACUUM;"
```

**Check disk I/O:**

```bash
# Test disk speed
dd if=/dev/zero of=~/testfile bs=1M count=100
# Should complete in <1 second on SSD
```

---

### Problem: "Sync takes forever"

**Symptoms:**

```bash
$ todopro sync push --context cloud
# Hangs for minutes
```

**Causes:**

1. Large amount of data
2. Slow internet

**Solutions:**

**Check when you last synced:**

```bash
todopro sync status
```

**Export/import instead (for large initial transfer):**

```bash
# On device 1
todopro data export --compress --output ~/backup.json.gz

# Transfer file to device 2
# On device 2
todopro data import ~/backup.json.gz
```

**Increase timeout:**

```bash
# 5 minutes
todopro config set api.timeout 300
```

---

## Command Issues

### Problem: "No such command"

**Symptoms:**

Running an old verb-first command, such as `list tasks`, fails like this:

```
Error: No such command 'list'.
```

**Cause:** Commands are grouped by what they act on, as `todopro <resource> <action>`.
Older guides and scripts used the action first, which no longer works.

**Solution:**

```bash
# Check available commands
todopro --help
todopro task --help
```

| Old (does not work) | Use instead |
| --- | --- |
| `list tasks` | `todopro task list` (or `todopro today`) |
| `list projects` | `todopro project list` |
| `list labels` | `todopro label list` |
| `list contexts` | `todopro context list` |
| `create project "X"` | `todopro project create "X"` |
| `create label "X"` | `todopro label create "X"` |
| `update task <id>` | `todopro task update <id>` (or `todopro edit <id>`) |
| `delete task <id>` | `todopro task delete <id>` |
| `archive project <id>` | `todopro project archive <id>` |
| `describe project <id>` | `todopro project describe <id>` |
| `use cloud` | `todopro context use cloud` |
| `login` / `signup` | `todopro auth login` / `todopro auth signup` |

`todopro add`, `todopro today`, `todopro complete`, `todopro reopen`, `todopro reschedule` and `todopro edit` are still top-level shortcuts.

---

### Problem: "Invalid arguments"

**Symptoms:**

```bash
$ todopro task create
Error: Missing argument 'CONTENT'.
```

**Cause:** Required arguments not provided

**Solution:**

```bash
# Check command help
todopro task create --help

# Provide required arguments
todopro task create "Task content"
```

---

### Problem: "Invalid isoformat string: 'tomorrow'"

**Symptoms:**

```bash
$ todopro task create "Call dentist" --due tomorrow
Error: An unexpected error occurred: Invalid isoformat string: 'tomorrow'
```

**Cause:** In the local context, `--due` on `task create`, `task update` and `edit` only accepts ISO dates.
Words like `tomorrow` or `next friday` are understood by `todopro add` in the **cloud** context.

**Solution:**

```bash
# Local context: use an ISO date
todopro task create "Call dentist" --due 2026-03-01

# Cloud context: natural language works in add
todopro context use cloud
todopro add "Call dentist tomorrow at 2pm"
```

---

## Data Issues

### Problem: "Tasks disappear after sync"

**Symptoms:**

- Added tasks locally
- Ran `todopro sync pull`
- Tasks are gone

**Cause:** `sync pull` defaults to `--strategy remote-wins`, so the remote copy overwrote your local changes.

**Solution:**

**Restore from backup:**

```bash
# If you exported recently
todopro data import backup.json
```

**Best Practice: push before pull, and preview with `--dry-run`**

```bash
# Correct order
todopro sync push --context cloud --dry-run
todopro sync push --context cloud   # Upload local changes first
todopro sync pull --context cloud   # Then download remote changes
```

---

### Problem: "Duplicate tasks"

**Symptoms:**

- Same task appears twice
- Happens after sync

**Cause:** Sync conflict resolution created duplicates

**Solution:**

```bash
# Find the duplicates
todopro task list --search "Duplicate"

# Delete the extra copy
todopro task delete <duplicate-id>
```

---

## Config Issues

The configuration file lives at `~/.config/todopro_cli/config.json` on Linux and macOS, and sign-in credentials are stored per context in `~/.config/todopro_cli/credentials/<context>.json` (readable only by you).

### Problem: "Invalid config.json"

**Symptoms:**

```bash
$ todopro task list
Error: An unexpected error occurred: Failed to load config: 1 validation error for AppConfig
  Invalid JSON: ...
```

**Cause:** Corrupted config.json

**Solution:**

**Option 1: Reset config**

```bash
# Backup current config
cp ~/.config/todopro_cli/config.json ~/config-backup.json

# Delete config (will be recreated)
rm ~/.config/todopro_cli/config.json

# Run command (creates default config)
todopro task list
```

Your tasks are not affected, because they live in the database, not the config file.
You will need to run `todopro auth login` again only if you also deleted the `credentials` folder, and any extra contexts you created must be re-added with `todopro context create`.

**Option 2: Fix manually**

```bash
# Validate JSON
cat ~/.config/todopro_cli/config.json | jq .

# If errors, fix or replace with default
```

**Default config structure** (shortened):

```json
{
  "current_context_name": "local",
  "contexts": [
    {
      "name": "local",
      "type": "local",
      "source": "/home/you/.local/share/todopro_cli/todopro.db",
      "description": "Local SQLite storage"
    },
    {
      "name": "cloud",
      "type": "remote",
      "source": "https://todopro.minhdq.dev/api",
      "description": "TodoPro Cloud (requires login)"
    }
  ],
  "api": {
    "endpoint": "https://todopro.minhdq.dev/api",
    "timeout": 30,
    "retry": 3
  }
}
```

You can read and change single values without editing the file:

```bash
todopro config view
todopro config get api.timeout
todopro config set api.timeout 60
todopro config reset api.timeout
```

`todopro config reset` with no key resets the whole configuration **and deletes your saved sign-in credentials**.

### Problem: CLI talks to the wrong server

**Cause:** The API address comes from the active remote context.
The `TODOPRO_BACKEND_URL` environment variable overrides it when set.

**Solution:**

```bash
# Is an override set?
echo "$TODOPRO_BACKEND_URL"
unset TODOPRO_BACKEND_URL

# Which context and server am I using?
todopro context list
```

---

## Getting More Help

### Collect Diagnostic Information

```bash
# System info
uname -a
python --version
todopro version

# Database info
ls -lh ~/.local/share/todopro_cli/

# Config info
todopro config view

# Test basic commands
todopro task list --json
```

### Report a Bug

**GitHub Issues:** https://github.com/minhdqdev/todopro/issues/new

**Include:**

1. TodoPro version: `todopro version`
2. OS and Python version
3. Steps to reproduce
4. Expected vs actual behavior
5. Full error message

**Example:**

```markdown
**Bug:** `todopro auth login` fails with a connection error

**Environment:**

- TodoPro: 1.0.0
- OS: Ubuntu 22.04
- Python: 3.14.0

**Steps to Reproduce:**

1. Run `todopro context use cloud`
2. Run `todopro auth login`
3. Enter email and password

**Expected:** Logged in
**Actual:** Error: Login failed: ...
```

### Contact Support

**Email:** support@todopro.minhdq.dev  
**GitHub Discussions:** https://github.com/minhdqdev/todopro/discussions

---

## Common Error Messages

### Quick Reference

| Error Message                                   | Likely Cause                       | Quick Fix                                        |
| ----------------------------------------------- | ---------------------------------- | ------------------------------------------------ |
| "Command not found"                             | Not installed or not in PATH       | `uv tool install todopro-cli`                    |
| "requires a different Python"                   | Python older than 3.14             | `uv tool install --python 3.14 todopro-cli`      |
| "database is locked"                            | Multiple processes                 | Stop the other `todopro` process                 |
| "Not logged in"                                 | Need authentication                | `todopro auth login`                             |
| "Login is only available for remote contexts"   | Active context is `local`          | `todopro context use cloud`                      |
| "Your email address isn't confirmed yet"        | Confirmation link not clicked      | `todopro auth resend-verification`               |
| "Your session has expired"                      | Token rejected by the server       | `todopro auth login`                             |
| "No such command 'list'"                        | Old verb-first command             | `todopro task list`, see the table above         |
| "Invalid isoformat string"                      | Natural-language date in local ctx | Use `YYYY-MM-DD`, or `add` in the cloud context  |
| "--context is required ..."                     | `sync` without a remote context    | `todopro sync push --context cloud`              |
| "Missing argument"                              | Missing required args              | Check `todopro <command> --help`                 |
| "database disk image is malformed"              | File corruption                    | Restore from backup                              |

---

**Still stuck?** We're here to help! 🚀

- **GitHub Issues:** https://github.com/minhdqdev/todopro/issues
- **Email:** support@todopro.minhdq.dev
