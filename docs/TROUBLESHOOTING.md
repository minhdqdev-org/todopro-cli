# TodoPro CLI - Troubleshooting Guide

**Last Updated:** 2026-02-17

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
todopro list tasks
```

**Expected Output:**
```
TodoPro CLI v1.0.0
Python: 3.12.x
Platform: Linux/macOS/Windows
```

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

# Using pip
pip install todopro-cli
```

**Option 2: Fix PATH**
```bash
# Find where TodoPro is installed
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
python -m todopro_cli --help
```

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
python --version  # Should be 3.10+

# Install TodoPro
pip install todopro-cli

# Or with specific Python version
python3.12 -m pip install todopro-cli
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

### Problem: "Database is locked"

**Symptoms:**
```bash
$ todopro add "Task"
Error: database is locked
```

**Cause:** Another TodoPro process is accessing the database

**Solution:**

**Step 1: Check for running processes**
```bash
ps aux | grep todopro
```

**Step 2: Kill stale processes**
```bash
pkill todopro
```

**Step 3: Try again**
```bash
todopro add "Task"
```

**If problem persists:**
```bash
# Check for .db-lock files
ls -la ~/.local/share/todopro_cli/

# Remove lock file
rm ~/.local/share/todopro_cli/*.db-lock
```

---

### Problem: "Database file is corrupt"

**Symptoms:**
```bash
$ todopro list tasks
Error: database disk image is malformed
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
todopro list tasks
```

**Option 3: Start fresh (last resort)**
```bash
# Backup database
mv ~/.local/share/todopro_cli/todopro.db ~/todopro-old.db

# TodoPro will create new database
todopro list tasks
```

**Prevention:**
- Set up regular backups: `todopro data export --compress`
- Use cloud sync: `todopro sync push`

---

### Problem: "No such file or directory: todopro.db"

**Symptoms:**
```bash
$ todopro list tasks
FileNotFoundError: [Errno 2] No such file or directory: '/home/user/.local/share/todopro_cli/todopro.db'
```

**Cause:** Database file doesn't exist (first run or deleted)

**Solution:**

**This is normal on first run!** TodoPro will create the database automatically:

```bash
# Just add a task, database will be created
todopro add "First task"

# Or list tasks (creates empty database)
todopro list tasks
```

**If database was accidentally deleted:**
```bash
# Restore from backup
todopro data import backup.json

# Or pull from cloud (if you were syncing)
todopro sync pull
```

---

## Authentication Issues

### Problem: "Not logged in"

**Symptoms:**
```bash
$ todopro sync push
Error: Not logged in. Use 'todopro login' to authenticate.
```

**Cause:** Trying to use sync without logging in

**Solution:**
```bash
# Login with your account
todopro login
# Enter email and password when prompted

# Verify login
todopro list tasks
```

**If you don't have an account:**
```bash
# Sign up first
todopro signup

# Then login
todopro login
```

---

### Problem: "Invalid credentials"

**Symptoms:**
```bash
$ todopro login
Error: Invalid email or password
```

**Causes:**
1. Wrong email/password
2. Account doesn't exist
3. Network issues

**Solutions:**

**Check credentials:**
```bash
# Verify email is correct
# Check for typos in password

# If you forgot password (TODO: reset feature)
# Contact support: support@todopro.minhdq.dev
```

**Check network:**
```bash
# Test API endpoint
curl -I https://todopro.minhdq.dev/api/health

# Should return: HTTP/2 200
```

**Create new account:**
```bash
todopro signup
```

---

### Problem: "Token expired"

**Symptoms:**
```bash
$ todopro sync push
Error: Authentication token expired
```

**Cause:** JWT token expired (default: 7 days)

**Solution:**
```bash
# Just login again (auto-refreshes token)
todopro login

# Try sync again
todopro sync push
```

---

## Sync Issues

### Problem: "Connection timeout"

**Symptoms:**
```bash
$ todopro sync push
Error: Connection timeout after 30 seconds
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

# Test TodoPro API
curl -I https://todopro.minhdq.dev/api/health
```

**Check firewall:**
```bash
# If on corporate network, HTTPS might be blocked
# Try from different network (home, mobile hotspot)
```

**Increase timeout (temporary workaround):**
```bash
# Edit config (increase timeout to 60s)
vim ~/.config/todopro_cli/config.json

# Change "timeout": 30 to "timeout": 60
```

---

### Problem: "Sync conflicts"

**Symptoms:**
```bash
$ todopro sync push
Warning: Conflicts detected:
- Task "Buy milk" modified on both local and remote
```

**Cause:** Same task modified on multiple devices

**Solutions:**

**Option 1: Server wins (discard local changes)**
```bash
todopro sync pull --force
```

**Option 2: Local wins (overwrite server)**
```bash
todopro sync push --force
```

**Best Practice: Always sync before starting work**
```bash
# At start of day
todopro sync pull

# At end of day
todopro sync push
```

---

### Problem: "Sync push/pull does nothing"

**Symptoms:**
```bash
$ todopro sync push
Success: ✓ Pushed 0 changes

# But I have local changes!
```

**Cause:** Not in remote context

**Solution:**
```bash
# Check current context
todopro list contexts

# Switch to remote context
todopro use cloud

# Try sync again
todopro sync push
```

---

## Encryption Issues

### Problem: "Encryption key not found"

**Symptoms:**
```bash
$ todopro sync pull
Error: Encryption key not found
```

**Cause:** E2EE enabled but key file missing

**Solutions:**

**Option 1: Recover with recovery phrase**
```bash
todopro encryption recover
# Enter your 24-word recovery phrase
```

**Option 2: Set up encryption (if first time)**
```bash
todopro encryption setup
# Save the 24-word recovery phrase!
```

---

### Problem: "Invalid recovery phrase"

**Symptoms:**
```bash
$ todopro encryption recover
Error: Invalid recovery phrase
```

**Causes:**
1. Wrong words
2. Wrong order
3. Extra/missing words

**Solutions:**

**Check word count:**
```bash
# Should be exactly 24 words
echo "your recovery phrase" | wc -w
# Output: 24
```

**Check spelling:**
- BIP39 wordlist: https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt
- Common mistakes: "to" vs "too", "by" vs "buy"

**Try different formats:**
```bash
# With spaces
todopro encryption recover
word1 word2 word3 ... word24

# Without extra spaces
# (some terminals add extra whitespace)
```

---

### Problem: "Cannot decrypt data"

**Symptoms:**
```bash
$ todopro sync pull
Error: Failed to decrypt task data
```

**Causes:**
1. Wrong encryption key
2. Corrupted encrypted data
3. Key rotation without re-encryption

**Solutions:**

**Check encryption status:**
```bash
todopro encryption status
```

**Verify key fingerprint:**
```bash
# Should match across devices
todopro encryption status | grep Fingerprint
```

**If keys don't match:**
```bash
# Use same recovery phrase on all devices
todopro encryption recover
# Enter SAME 24-word phrase as original device
```

---

### Problem: "Lost recovery phrase"

**Unfortunately:** If you lost your recovery phrase AND encryption key:

**Your encrypted data is UNRECOVERABLE.**

This is by design (zero-knowledge encryption). No one can decrypt it, not even TodoPro staff.

**Options:**

**If you have LOCAL unencrypted data:**
```bash
# 1. Export what you have
todopro data export --output backup.json

# 2. Start fresh encryption
rm ~/.config/todopro_cli/encryption.key
todopro encryption setup  # New key, new recovery phrase

# 3. Import data
todopro data import backup.json

# 4. Push re-encrypted data
todopro sync push
```

**If EVERYTHING is encrypted:**
- You must start fresh
- Previous encrypted data is lost forever
- **This is why we emphasize saving recovery phrase!**

**Prevention:**
- ✅ Write recovery phrase on paper
- ✅ Store in password manager
- ✅ Keep multiple secure copies

---

## Performance Issues

### Problem: "Commands are slow"

**Symptoms:**
```bash
$ todopro list tasks
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

**Archive old tasks:**
```bash
# Complete old tasks
todopro list tasks --filter=completed | grep "2025" | xargs -n1 todopro delete task

# Or export and start fresh
todopro data export --output archive-2025.json
# Delete old database, start new year
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
$ todopro sync push
# Hangs for minutes
```

**Causes:**
1. Large amount of data
2. Slow internet
3. E2EE encryption overhead

**Solutions:**

**Check sync size:**
```bash
todopro sync status
# Shows pending changes
```

**Export/import instead (for large initial sync):**
```bash
# On device 1
todopro data export --compress --output ~/backup.json.gz

# Transfer file to device 2
# On device 2
todopro data import ~/backup.json.gz
```

**Increase sync timeout:**
```bash
# Edit config
vim ~/.config/todopro_cli/config.json
# Increase "timeout": 30 to "timeout": 300 (5 min)
```

---

## Command Issues

### Problem: "No such command"

**Symptoms:**
```bash
$ todopro focus
Error: No such command 'focus'.
```

**Cause:** Command doesn't exist or is deferred (post-MVP1)

**Solution:**
```bash
# Check available commands
todopro --help

# For MVP1, these features are deferred:
# - focus (focus mode)
# - timer (pomodoro)
# - stats (analytics)
# - achievements
```

---

### Problem: "Invalid arguments"

**Symptoms:**
```bash
$ todopro add
Error: Missing argument 'CONTENT'
```

**Cause:** Required arguments not provided

**Solution:**
```bash
# Check command help
todopro add --help

# Provide required arguments
todopro add "Task content"
```

---

## Data Issues

### Problem: "Tasks disappear after sync"

**Symptoms:**
- Added tasks locally
- Ran `todopro sync pull`
- Tasks are gone

**Cause:** Server data overwrote local changes

**Solution:**

**Restore from backup:**
```bash
# If you exported recently
todopro data import backup.json
```

**Best Practice: Always push before pull**
```bash
# Correct order
todopro sync push  # Upload local changes first
todopro sync pull  # Then download remote changes
```

---

### Problem: "Duplicate tasks"

**Symptoms:**
- Same task appears twice
- Happens after sync

**Cause:** Sync conflict resolution created duplicates

**Solution:**
```bash
# Delete duplicates manually
todopro list tasks | grep "Duplicate"
todopro delete task <duplicate-id>

# Or export, deduplicate, re-import
todopro data export --output export.json
# Manually edit export.json to remove duplicates
todopro data import export.json
```

---

## Config Issues

### Problem: "Invalid config.json"

**Symptoms:**
```bash
$ todopro list tasks
Error: Invalid configuration file
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
todopro list tasks
```

**Option 2: Fix manually**
```bash
# Validate JSON
cat ~/.config/todopro_cli/config.json | jq .

# If errors, fix or replace with default
```

**Default config structure:**
```json
{
  "current_context_name": "local",
  "contexts": [
    {
      "name": "local",
      "type": "local",
      "source": "/path/to/todopro.db",
      "description": "Local storage"
    }
  ],
  "api": {
    "endpoint": "https://todopro.minhdq.dev/api",
    "timeout": 30
  },
  "e2ee": {
    "enabled": false
  }
}
```

---

## Getting More Help

### Enable Debug Mode

```bash
# Set environment variable
export TODOPRO_DEBUG=1

# Run command with verbose output
todopro list tasks

# Debug logs show:
# - SQL queries
# - API requests
# - Error stack traces
```

### Collect Diagnostic Information

```bash
# System info
uname -a
python --version
todopro version

# Database info
ls -lh ~/.local/share/todopro_cli/

# Config info
cat ~/.config/todopro_cli/config.json | jq .

# Test basic commands
todopro list tasks --format json
```

### Report a Bug

**GitHub Issues:** https://github.com/minhdqdev/todopro/issues/new

**Include:**
1. TodoPro version: `todopro version`
2. OS and Python version
3. Steps to reproduce
4. Expected vs actual behavior
5. Full error message
6. Debug logs (if relevant)

**Example:**
```markdown
**Bug:** Sync fails with connection timeout

**Environment:**
- TodoPro: v1.0.0
- OS: Ubuntu 22.04
- Python: 3.12.3

**Steps to Reproduce:**
1. Run `todopro login`
2. Run `todopro sync push`
3. Wait 30 seconds

**Expected:** Data syncs successfully
**Actual:** Connection timeout

**Error:**
```
Error: Connection timeout after 30 seconds
Traceback (most recent call last):
  ...
```

**Debug Logs:**
```
[DEBUG] API request: POST https://todopro.minhdq.dev/api/sync
[DEBUG] Timeout: 30s
[ERROR] requests.exceptions.Timeout
```
```

### Contact Support

**Email:** support@todopro.minhdq.dev  
**GitHub Discussions:** https://github.com/minhdqdev/todopro/discussions

---

## Common Error Messages

### Quick Reference

| Error Message | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| "Command not found" | Not installed or not in PATH | `uv tool install todopro-cli` |
| "Database is locked" | Multiple processes | `pkill todopro` |
| "Not logged in" | Need authentication | `todopro login` |
| "Token expired" | Session expired | `todopro login` |
| "Connection timeout" | Network issues | Check internet, try later |
| "Encryption key not found" | Missing key file | `todopro encryption recover` |
| "Invalid recovery phrase" | Wrong words/order | Check BIP39 wordlist |
| "No such command" | Command doesn't exist | Check `todopro --help` |
| "Invalid arguments" | Missing required args | Check `todopro <command> --help` |
| "Database corrupt" | File corruption | Restore from backup |

---

**Still stuck?** We're here to help! 🚀

- **GitHub Issues:** https://github.com/minhdqdev/todopro/issues
- **Email:** support@todopro.minhdq.dev
