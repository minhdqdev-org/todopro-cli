# TodoPro CLI - Frequently Asked Questions (FAQ)

**Last Updated:** 2026-02-17

---

## General Questions

### What is TodoPro?

TodoPro is a **CLI-first task management system** designed for power users, developers, and privacy-conscious individuals. It works offline by default, uses end-to-end encryption for cloud sync, and provides a scriptable interface for automation.

**Key Features:**
- 🖥️ **CLI-First:** Terminal interface with intuitive commands
- 💾 **Offline-Capable:** Local SQLite storage, no internet required
- 🔐 **E2EE:** Client-side encryption (AES-256-GCM) for sync
- 🤖 **Scriptable:** JSON output, automation-ready
- 🎯 **Privacy-Focused:** Zero-knowledge architecture

---

### How is TodoPro different from Todoist?

| Feature | TodoPro | Todoist |
|---------|---------|---------|
| **Interface** | CLI (command-line) | Web/Mobile GUI |
| **Offline Mode** | ✅ Works fully offline | ⚠️ Limited offline |
| **Privacy** | ✅ E2EE, zero-knowledge | ❌ Server sees data |
| **Pricing** | Free offline, $3.99/mo sync | $4/mo or $5/mo |
| **Target User** | Developers, power users | General consumers |
| **Automation** | ✅ Fully scriptable | ⚠️ Limited API |
| **Open Source** | ✅ Yes | ❌ No |

**Choose TodoPro if:**
- You prefer keyboard over mouse
- You value privacy and data ownership
- You need offline access
- You want to automate task management
- You're comfortable with command-line tools

**Choose Todoist if:**
- You prefer visual interfaces
- You need mobile apps (TodoPro mobile coming later)
- You want team collaboration (TodoPro focused on individuals for MVP1)

---

### Is TodoPro free?

**Yes!** Offline usage is **completely free** with no limitations.

**Pricing Model:**
- **Free Tier:** Unlimited offline usage (local SQLite storage)
- **Premium Tier:** $3.99/month for cloud sync
  - Free: 5 projects, 80 tasks per project
  - Premium: 300 projects, unlimited tasks

**What's free forever:**
- ✅ Unlimited tasks (offline)
- ✅ Unlimited projects (offline)
- ✅ All core features
- ✅ Export/import data
- ✅ CLI interface
- ✅ End-to-end encryption

---

## Installation & Setup

### How do I install TodoPro?

**Recommended (using uv):**
```bash
uv tool install todopro-cli
todopro version
```

**Alternative (using pip):**
```bash
pip install todopro-cli
todopro version
```

See [GETTING_STARTED.md](./GETTING_STARTED.md#installation) for detailed instructions.

---

### Where is my data stored?

TodoPro stores data locally by default:

**Linux:**
```
~/.local/share/todopro_cli/todopro.db
```

**macOS:**
```
~/Library/Application Support/todopro_cli/todopro.db
```

**Windows:**
```
%LOCALAPPDATA%\todopro_cli\todopro.db
```

**Configuration:**
```
~/.config/todopro_cli/config.json
```

---

### Can I use TodoPro without an account?

**Yes!** TodoPro works completely offline without any account. Just install and start using it.

You only need an account if you want to:
- Sync across multiple devices
- Back up data to the cloud
- Access tasks from different computers

---

## Usage Questions

### How do I add a task?

**Quick add (simplest):**
```bash
todopro add "Buy groceries"
```

**With details:**
```bash
todopro add "Buy groceries" \
  --due tomorrow \
  --priority 1 \
  --project "Personal"
```

**Interactive mode:**
```bash
todopro create task
# Follow the prompts
```

---

### How do I view my tasks?

**Today's tasks:**
```bash
todopro today
```

**All tasks:**
```bash
todopro list tasks
```

**Filter by project:**
```bash
todopro list tasks --project "Work"
```

**Filter by status:**
```bash
todopro list tasks --status active
todopro list tasks --status completed
```

**Search:**
```bash
todopro list tasks --search "meeting"
```

---

### What date formats are supported?

TodoPro supports natural language dates:

```bash
todopro add "Task" --due today
todopro add "Task" --due tomorrow
todopro add "Task" --due "next monday"
todopro add "Task" --due "next friday"
todopro add "Task" --due "in 3 days"
```

Also ISO format:
```bash
todopro add "Task" --due 2026-03-15
```

---

### How do priority levels work?

TodoPro uses 4 priority levels:

- **P1 (Highest):** Urgent & important
  - `todopro add "Task" --priority 1`
- **P2 (High):** Important but not urgent
  - `todopro add "Task" --priority 2`
- **P3 (Medium):** Default priority
  - `todopro add "Task" --priority 3`
- **P4 (Low):** Nice to have, someday/maybe
  - `todopro add "Task" --priority 4`

**Default:** If you don't specify, tasks are created with P3 (medium).

---

### Can I use TodoPro in scripts?

**Absolutely!** TodoPro is designed for automation:

**JSON Output:**
```bash
todopro list tasks --format json | jq '.[]'
```

**Example Script (Daily Report):**
```bash
#!/bin/bash
# Generate daily task report

TODAY=$(todopro list tasks --filter=today --format json)
COUNT=$(echo "$TODAY" | jq 'length')

echo "📋 You have $COUNT tasks today:"
echo "$TODAY" | jq -r '.[] | "- [\(.priority)] \(.content)"'
```

**Exit Codes:**
- `0` = Success
- `1` = General error
- `2` = Invalid arguments
- `5` = Resource not found

---

## Sync & Cloud

### How do I sync my data?

**First-time setup:**
```bash
# 1. Sign up for account
todopro signup

# 2. Set up encryption
todopro encryption setup

# 3. Push your data
todopro sync push
```

**On another device:**
```bash
# 1. Login
todopro login

# 2. Set up encryption (use same recovery phrase)
todopro encryption recover

# 3. Pull data
todopro sync pull
```

**Regular sync:**
```bash
todopro sync push  # Upload changes
todopro sync pull  # Download changes
```

---

### Is my data encrypted?

**Yes!** TodoPro uses **end-to-end encryption (E2EE)** with AES-256-GCM.

**What's encrypted:**
- ✅ Task content
- ✅ Task descriptions
- ✅ All sensitive data

**What's NOT encrypted (needed for server-side operations):**
- Task IDs (random UUIDs)
- Timestamps
- Project names
- Label names

**How it works:**
1. Data encrypted on your device before upload
2. Server stores only ciphertext
3. Server never has decryption key
4. Data decrypted on your device after download

**Setup:**
```bash
todopro encryption setup
# Save your 24-word recovery phrase!
```

---

### What happens if I lose my encryption key?

**Recovery phrase is your backup!**

If you lose your encryption key (e.g., new device, reinstall OS):

```bash
todopro encryption recover
# Enter your 24-word recovery phrase
```

**⚠️ CRITICAL:** If you lose BOTH your key AND recovery phrase:
- Your encrypted data is **permanently unrecoverable**
- Not even TodoPro staff can decrypt it (zero-knowledge encryption)
- You'll need to start fresh

**Best practices:**
- ✅ Write down recovery phrase on paper
- ✅ Store in password manager (e.g., 1Password, Bitwarden)
- ✅ Keep multiple secure copies
- ❌ Don't screenshot or email it

---

### Can I use TodoPro on multiple devices?

**Yes!** Use cloud sync:

**Device 1 (First device):**
```bash
todopro signup
todopro encryption setup
todopro sync push
```

**Device 2 (Additional device):**
```bash
todopro login
todopro encryption recover  # Enter same recovery phrase
todopro sync pull
```

**Keep devices in sync:**
```bash
todopro sync push  # After making changes
todopro sync pull  # Before starting work
```

**Tip:** Set up a cron job for auto-sync:
```bash
# Sync every hour
0 * * * * todopro sync push && todopro sync pull
```

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
- ✅ Duplicate detection (skips existing items)
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

### Can I export to CSV?

**Not yet.** CSV export is planned for a future release.

**Current formats:**
- ✅ JSON (full data)
- ✅ Gzip compressed JSON

**Workaround (convert JSON to CSV):**
```bash
todopro data export --output export.json
jq -r '.data.tasks[] | [.content, .priority, .due_date] | @csv' export.json > tasks.csv
```

---

## Encryption

### What encryption does TodoPro use?

**Algorithm:** AES-256-GCM (Galois/Counter Mode)

**Key Details:**
- **Key Size:** 256 bits (32 bytes)
- **IV Size:** 96 bits (12 bytes, unique per operation)
- **Auth Tag:** 128 bits (16 bytes, for integrity)
- **Recovery Phrase:** 24 words (BIP39 standard)

**Industry Standard:** AES-256-GCM is used by:
- Signal (messaging)
- 1Password (password manager)
- TLS 1.3 (web encryption)
- Google Cloud, AWS (cloud storage)

---

### How do I check my encryption status?

```bash
todopro encryption status
```

**Output:**
```
Encryption Status: ✅ Enabled
Key Location: ~/.config/todopro_cli/encryption.key
Key Fingerprint: a1b2c3d4...
Recovery Phrase: Hidden (use 'show-recovery' to display)
```

---

### Can I view my recovery phrase again?

**Yes:**
```bash
todopro encryption show-recovery
```

**⚠️ Security Warning:** Only run this on your trusted device. The 24-word phrase will be displayed on screen.

---

### Can I change my encryption key?

**Yes (key rotation):**
```bash
todopro encryption rotate-key
```

**What happens:**
1. Generates new encryption key
2. Generates new 24-word recovery phrase
3. Re-encrypts all local data with new key
4. Pushes re-encrypted data to server (if syncing)

**Note:** Old recovery phrase won't work anymore. Save the new one!

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

### "Not logged in" error

**Cause:** Trying to sync without authentication.

**Fix:**
```bash
todopro login
# Enter your email and password
```

---

### Sync conflicts

**Cause:** Data modified on multiple devices without sync.

**Fix:**
```bash
# Check sync status
todopro sync status

# Pull latest from server (server wins)
todopro sync pull

# Push your changes (local wins)
todopro sync push
```

**Best Practice:** Always pull before push:
```bash
todopro sync pull && todopro sync push
```

---

### Database locked

**Cause:** Another TodoPro process is running.

**Fix:**
```bash
# Check for running processes
ps aux | grep todopro

# Kill if necessary
pkill todopro

# Try again
todopro list tasks
```

---

### Forgot encryption recovery phrase

**Unfortunately:** If you lost your recovery phrase AND encryption key:
- Your encrypted data is **unrecoverable**
- This is by design (zero-knowledge encryption)
- No one can decrypt it, including TodoPro staff

**Options:**
1. **If you have local unencrypted data:**
   ```bash
   # Export local data
   todopro data export --output backup.json
   
   # Disable E2EE, start fresh
   todopro encryption setup  # New key
   todopro data import backup.json
   ```

2. **If everything is encrypted:**
   - You'll need to start fresh
   - This is why we emphasize saving recovery phrase!

---

## Advanced

### How do I use multiple contexts?

**Contexts** are different storage locations:

```bash
# List contexts
todopro list contexts

# Create local context
todopro create context local-work \
  --type local \
  --source ~/.todopro-work.db

# Switch contexts
todopro use local-work

# Your data is now in a separate database
todopro add "Work task"

# Switch back to default
todopro use local
```

---

### Can I use TodoPro in CI/CD?

**Yes!** TodoPro is great for automation:

**Example (GitHub Actions):**
```yaml
name: Daily Task Report

on:
  schedule:
    - cron: '0 9 * * *'  # 9am daily

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - name: Install TodoPro
        run: pip install todopro-cli
      
      - name: Login
        run: |
          echo "${{ secrets.TODOPRO_EMAIL }}" | todopro login --password "${{ secrets.TODOPRO_PASSWORD }}"
      
      - name: Sync and Report
        run: |
          todopro sync pull
          todopro today --format json | jq '.[] | .content'
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
git clone https://github.com/minhdqdev/todopro.git
cd todopro/todopro-cli
uv pip install -e ".[dev]"
pytest tests/
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

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
- TodoPro: v1.0.0
- OS: Ubuntu 22.04
- Python: 3.12

**Steps:**
1. Run `todopro sync push`
2. Wait 30 seconds
3. Get timeout error

**Expected:** Data syncs successfully
**Actual:** Connection timeout after 30s

**Error:**
```
Error: Connection timeout
```

---

### Is there a web interface?

**Not yet for MVP1.** TodoPro MVP1 focuses on CLI excellence.

**Coming Soon:**
- Web interface (in development)
- Mobile apps (planned)

**Current Workaround:**
- Use SSH to access CLI from anywhere
- Terminal apps on mobile (Termux, iSH)

---

## Feature Requests

### Does TodoPro support recurring tasks?

**Not yet.** Recurring tasks are planned for a future release.

**Workaround:**
```bash
# Create template
todopro add "Weekly review" --due "next monday"

# Clone task when complete
todopro complete <id>
todopro add "Weekly review" --due "next monday"
```

---

### Can I add subtasks?

**Not in MVP1.** Subtasks/dependencies are planned for future releases.

**Workaround:**
- Use projects to group related tasks
- Use description field for sub-steps:
  ```bash
  todopro add "Project X" --description "
  1. Research
  2. Design
  3. Implement
  4. Test
  "
  ```

---

### Does TodoPro have a mobile app?

**Not yet.** Mobile apps are planned after MVP1 stabilizes.

**Workaround:**
- Access via SSH + terminal app (Termux, iSH)
- Web interface (coming soon)

---

## Didn't find your answer?

**Ask on GitHub Discussions:**
https://github.com/minhdqdev/todopro/discussions

**Or email us:**
support@todopro.minhdq.dev

We're here to help! 🚀
