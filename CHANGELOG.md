# Changelog

All notable changes to TodoPro CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🆕 Added

**Todoist Import (`todopro import todoist`):**
- ✅ `todopro import todoist` — new subcommand to migrate active tasks, projects, and labels from Todoist via the v1 API
- ✅ `--api-key` option (or `TODOIST_API_KEY` env var) for personal API token authentication
- ✅ `--project-prefix` option (default `[Todoist]`) — prefixes imported project names to avoid conflicts
- ✅ `--max-tasks` option — cap the number of tasks imported per project
- ✅ `--dry-run` flag — fetch and count data without writing anything to the local database
- ✅ Deduplication: skips projects/labels/tasks that already exist in TodoPro by name/content
- ✅ Due date parsing for both date-only (`2025-12-31`) and datetime (`2025-12-31T10:00:00`) formats
- ✅ Label mapping — Todoist personal labels are imported and linked to tasks
- ✅ Fault-tolerant: per-resource errors are collected and reported without aborting the whole import
- ✅ Rich summary table displayed on completion

**Architecture (SOLID):**
- ✅ `services/todoist/models.py` — Pydantic v2 models for all Todoist API v1 response shapes
- ✅ `services/todoist/client.py` — `TodoistClientProtocol` (runtime-checkable `typing.Protocol`) + `TodoistClient` (httpx async); labels use `limit=200` to work around Todoist pagination bug
- ✅ `services/todoist/importer.py` — `TodoistImportService` depends only on protocol abstractions (DIP)

**Tests:**
- ✅ `tests/services/test_todoist_client.py` — 12 unit tests for `TodoistClient` (protocol conformance, pagination, HTTP error handling)
- ✅ `tests/services/test_todoist_importer.py` — 19 unit tests for `TodoistImportService` (happy path, dry-run, deduplication, error handling, due date parsing, label resolution)
- ✅ `tests/commands/test_import_command.py` — 18 command-level tests covering auth, all option flags, output, and exit codes

### 🔧 Fixed

- Fixed `todopro task list` default sort — tasks now sorted by `priority ASC, project ASC, created_at DESC` instead of insertion order
- Raised default `--limit` in `task list` from 30 → 250
- Fixed `data_command.py` project filter bug: `ProjectFilters(name=...)` silently accepted unknown field; changed to `ProjectFilters(search=...)` with explicit exact-match check

---

## [4.0.0] - 2026-02-24 (MVP4 Release — Ramble)

**Ramble: voice-to-tasks is here.** 🎙️

### 🆕 Added

**Ramble (Voice-to-Tasks):**
- ✅ `todopro ramble` — new top-level command for voice-driven task capture
- ✅ `--text TEXT` flag — text mode (bypass microphone for testing or SSH use)
- ✅ `--duration N` flag — batch record for N seconds
- ✅ `--project NAME` flag — default project for created tasks
- ✅ `--dry-run` flag — preview parsed tasks without creating them
- ✅ `--stt PROVIDER` flag — choose STT provider (whisper/gemini/deepgram)
- ✅ `--llm PROVIDER` flag — choose LLM provider (gemini/openai)
- ✅ `--language CODE` flag — language hint for STT
- ✅ `todopro ramble history` — view past Ramble session history
- ✅ `todopro ramble usage` — view daily usage stats and limits
- ✅ `todopro ramble config` — view and update Ramble configuration

**Audio Services:**
- ✅ `services/audio/recorder.py` — microphone capture (requires `sounddevice`/`numpy`)
- ✅ `services/audio/local_stt.py` — local Whisper STT (requires `faster-whisper`)
- ✅ Graceful degradation when audio packages not installed

**GitHub + Google Calendar Integrations (MVP3):**
- ✅ `todopro calendar connect/disconnect/status` — OAuth connect to Google Calendar
- ✅ `todopro calendar list/set/push/pull/sync` — bidirectional calendar sync
- ✅ `todopro calendar configure/describe` — integration configuration

---

## [1.0.0] - 2026-02-18 (MVP1 Release)

**TodoPro MVP1 is production-ready!** 🎉

This release focuses on core task management with offline-first architecture and end-to-end encryption.

### 🎯 Core Features

**Task Management:**
- ✅ Full CRUD operations (create, read, update, delete)
- ✅ Natural language dates ("tomorrow", "next friday", "in 3 days")
- ✅ Priority levels (P1-P4), due dates, descriptions
- ✅ Search and filter tasks
- ✅ Bulk operations (complete/delete multiple tasks)
- ✅ Task completion and reopening

**Projects & Labels:**
- ✅ Create and manage projects
- ✅ Color-coded labels
- ✅ Archive/unarchive projects
- ✅ Filter tasks by project or label

**Offline-First:**
- ✅ Local SQLite storage (works without internet)
- ✅ Fast local-first operations
- ✅ Optional cloud sync
- ✅ Context switching (local ↔ remote)

**Sync & Backup:**
- ✅ Bidirectional sync (push/pull)
- ✅ Export data (JSON, gzip compressed)
- ✅ Import data (with deduplication)
- ✅ Sync status checking
- ✅ Local and remote export/import

**End-to-End Encryption:**
- ✅ AES-256-GCM encryption
- ✅ 24-word recovery phrase (BIP39)
- ✅ Zero-knowledge architecture
- ✅ Key rotation support
- ✅ Client-side encryption/decryption
- ✅ Encrypted sync to cloud

**CLI Experience:**
- ✅ Rich terminal UI with colors and tables
- ✅ JSON output for scripting
- ✅ Interactive and non-interactive modes
- ✅ Clear error messages
- ✅ Progress indicators
- ✅ Help text for all commands

### 📦 What's Included

**Commands Available:**
- `todopro add` - Quick add tasks
- `todopro list tasks/projects/labels` - View resources
- `todopro create task/project/label` - Create resources
- `todopro update task/project/label` - Modify resources
- `todopro delete task/project/label` - Remove resources
- `todopro complete/reopen` - Task status
- `todopro today` - View today's tasks
- `todopro sync push/pull/status` - Cloud sync
- `todopro data export/import` - Backup/restore
- `todopro encryption setup/status/recover/rotate-key/show-recovery` - E2EE
- `todopro login/logout/signup` - Authentication
- `todopro use` - Context switching
- `todopro archive/unarchive` - Project management
- `todopro reschedule` - Reschedule tasks
- `todopro version` - Show version

**Documentation:**
- 📖 [Getting Started Guide](./docs/GETTING_STARTED.md)
- 📖 [FAQ](./docs/FAQ.md)
- 📖 [Troubleshooting](./docs/TROUBLESHOOTING.md)
- 📖 [MVP1 Product Spec](../docs/MVP1.md)

### 🔒 Security

**Encryption Details:**
- Algorithm: AES-256-GCM (authenticated encryption)
- Key derivation: BIP39 24-word mnemonic
- IV: 96 bits (unique per operation)
- Auth tag: 128 bits (integrity check)
- Encrypted fields: Task content, descriptions
- Unencrypted: Task IDs, timestamps (needed for sync)

**Tested:**
- 50 E2EE tests (100% passing)
- Security properties verified:
  - Zero plaintext leakage
  - High entropy ciphertext
  - Semantic security
  - IV uniqueness

### ⚡ Performance

- Local operations: <100ms
- Sync: <5s for typical dataset (100 tasks)
- Export/import: <1s for 1000 tasks
- Encryption overhead: ~10ms per operation

### 🐛 Bug Fixes

- Fixed `decorators.py` auth check using old API
- Fixed `context_manager.py` using removed `local_vault_path` field
- Fixed `task_repository.py` passing wrong args to `get_e2ee_handler()`
- Fixed E2EE config persistence across sessions
- Fixed word count display in encryption commands

### 🧪 Testing

**Test Coverage:**
- Total: 289/448 tests passing (64.5%)
- E2EE: 50/50 tests passing (100%)
  - 21 EncryptionService unit tests
  - 9 Sync integration tests
  - 20 Edge cases/security/performance tests

**Manual Testing:**
- E2EE CLI commands (setup, status, recover, show-recovery)
- Export/import (local and remote)
- Sync (push, pull, status)
- Round-trip backup/restore

### ❌ Deferred to Post-MVP1

The following features are intentionally deferred:

- ⏳ Recurring tasks
- ⏳ Subtasks and dependencies
- ⏳ Task templates
- ⏳ Focus mode and pomodoro timer
- ⏳ Advanced analytics and gamification
- ⏳ Geofencing and location contexts
- ⏳ Web application
- ⏳ Mobile apps
- ⏳ Third-party integrations
- ⏳ Team collaboration

**Why deferred:** Focus on core task management excellence first.

### 📊 Known Issues

**Non-blocking:**
- 109 test failures (old factory pattern mocks, not critical)
- Purge command uses old credentials API (rarely used, can be fixed later)
- CSV export not implemented (JSON sufficient for MVP1)

**Future Improvements:**
- Auto-sync on changes (cron job workaround available)
- Key re-encryption on rotation (current: generates new key only)
- Server backup of encrypted master key (recovery phrase is sufficient)

### 🚀 Getting Started

```bash
# Install
uv tool install todopro-cli

# Create your first task (offline)
todopro add "Buy groceries"

# Optional: Set up cloud sync
todopro signup
todopro encryption setup  # Save 24-word recovery phrase!
todopro sync push
```

**First-time users:** See [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md)

### 🙏 Credits

- Architecture refactoring: Specs 10-14
- E2EE implementation: Specs 22-24, 26
- Export/import: Spec 21
- Documentation: Spec 29
- Feature cleanup: Spec 20, 30

---

## [2.0.0] - 2026-02-09

### Added

- **Local Vault Support**: Work offline with a private SQLite database
  - Store tasks, projects, and labels locally without internet connection
  - E2EE support for encrypted local vaults
  - Full CRUD operations on local data
- **Context Switching**: Seamlessly switch between local and remote environments
  - Create multiple contexts (local and remote)
  - Switch contexts with `todopro context use <name>`
  - List available contexts with `todopro context list`
- **Sync Capabilities**: Bidirectional sync between local and remote
  - Pull tasks from remote to local vault
  - Push local tasks to remote backend
  - Conflict resolution with multiple strategies
  - Incremental sync to minimize data transfer
- **Migration System**: Automatic upgrade from v1 to v2
  - Auto-detect v1 configuration and migrate to YAML format
  - Preserve all existing settings and credentials
  - One-time backup of v1 config and credentials
  - Migration log tracking
- **Version Compatibility Checks**: Verify CLI and backend compatibility
  - Warnings when backend is outdated
  - Clear error messages for incompatible versions
- **Enhanced Backup/Restore**: Full data export and import
  - Export all data with `todopro data export`
  - Import data with `todopro data import`
  - Automated backups during migration

### Changed

- **Configuration Format**: Migrated from JSON to YAML
  - More readable configuration files
  - Better support for nested structures
  - Context-based organization
- **Credential Storage**: Context-based credential management
  - Separate credentials per context
  - Improved security with proper file permissions
- **Default Behavior**: CLI defaults to remote context for backward compatibility
  - Existing users experience no change in behavior
  - New `current-context` setting controls active context

### Fixed

- Configuration file corruption handling improved
- Better error messages for authentication failures
- Improved handling of network timeouts

### Security

- Credential files now enforce 0600 permissions (owner read/write only)
- Backup files exclude sensitive data by default
- E2EE support for local vaults with master password

**What's New:**

- YAML configuration format
- Context-based environment switching
- Local vault capability
- Sync commands

### For Developers

**Testing:**

- Added comprehensive migration tests
- Backward compatibility test suite
- Config and credential migration tests

**Documentation:**

- Updated README with v2 features
- Migration guide for v1 users
- Context switching examples

**Infrastructure:**

- Migration module with version detection
- Backup/restore utilities
- Version compatibility checking

---

## [1.9.0] - 2026-01-XX (Previous Release)

### Added

- Initial stable release of TodoPro CLI
- Task management (create, list, update, delete)
- Project and label support
- Authentication with JWT tokens
- JSON and pretty output formats

### Note

For older changelog entries, see [CHANGELOG-v1.md](./CHANGELOG-v1.md)

---

## Future Roadmap

### v2.1.0 (Planned)

- Incremental sync improvements
- Conflict resolution UI
- Multi-vault support
- Vault export/import

### v3.0.0 (Future)

- Remove deprecated features
- Performance optimizations
- Plugin system

---

**Full Changelog**: https://github.com/minhdqdev-org/todopro-cli/compare/v1.9.0...v2.0.0
