# TodoPro CLI - Feature Specification

> A professional command-line interface for TodoPro task management system, inspired by kubectl and built with Python.

## 🎯 Overview

The TodoPro CLI (`todopro` or `tp`) is a comprehensive command-line tool that provides full access to the TodoPro API (`todopro.minhdq.dev/api/`), enabling both interactive and non-interactive workflows for task management, project organization, and productivity tracking.

**Design Principles:**
- **Kubectl-inspired**: Resource-oriented commands with consistent patterns
- **Context-aware**: Maintains authentication state and user preferences
- **Output flexibility**: JSON, YAML, table, and custom formats
- **Interactive & scriptable**: Menu-driven UI for exploration, flags for automation
- **Offline-capable**: Local caching and sync management
- **Professional UX**: Rich terminal UI with colors, progress indicators, and helpful messages

---

## 📦 Core Architecture

### Technology Stack
- **Language**: Python 3.12+
- **CLI Framework**: Typer (type-safe, auto-documentation)
- **HTTP Client**: httpx (async support)
- **UI Components**: Rich (tables, progress, colors)
- **Interactive Menus**: readchar / prompt-toolkit
- **Config Management**: platformdirs (XDG-compliant)
- **Output Formats**: JSON, YAML, table, custom

### Project Structure
```
todopro-cli/
├── src/
│   └── todopro_cli/
│       ├── __init__.py
│       ├── main.py              # Entry point, Typer app
│       ├── config.py            # Configuration management
│       ├── api/
│       │   ├── client.py        # HTTP client wrapper
│       │   ├── auth.py          # Authentication handlers
│       │   ├── tasks.py         # Task API endpoints
│       │   ├── projects.py      # Project API endpoints
│       │   ├── labels.py        # Label API endpoints
│       │   ├── filters.py       # Filter API endpoints
│       │   ├── analytics.py     # Analytics API endpoints
│       │   └── sync.py          # Sync API endpoints
│       ├── commands/
│       │   ├── auth.py          # login, logout, whoami
│       │   ├── tasks.py         # task CRUD operations
│       │   ├── projects.py      # project management
│       │   ├── labels.py        # label management
│       │   ├── filters.py       # filter operations
│       │   ├── analytics.py     # analytics commands
│       │   ├── sync.py          # sync operations
│       │   └── interactive.py   # interactive menu mode
│       ├── models/
│       │   ├── task.py          # Task data models
│       │   ├── project.py       # Project data models
│       │   └── user.py          # User data models
│       ├── ui/
│       │   ├── formatters.py    # Output formatters
│       │   ├── tables.py        # Table rendering
│       │   ├── menus.py         # Interactive menus
│       │   └── prompts.py       # User input prompts
│       ├── utils/
│       │   ├── cache.py         # Local caching
│       │   ├── validation.py    # Input validation
│       │   └── helpers.py       # Common utilities
│       └── tests/
├── pyproject.toml
├── README.md
└── FEATURES.md (this file)
```

---

## 🔐 1. Authentication & Authorization

### 1.1 Login
**Command:** `todopro login [OPTIONS]`

**Features:**
- Username/email + password authentication
- Token storage in secure keyring (or ~/.todopro/credentials)
- Support for JWT refresh tokens
- Multi-profile support (dev, staging, prod)
- API endpoint configuration

**Examples:**
```bash
# Interactive login
todopro login

# Non-interactive with credentials
todopro login --email user@example.com --password secret

# Login to different environment
todopro login --profile staging --endpoint https://staging.todopro.minhdq.dev/api

# Using environment variables
TODOPRO_EMAIL=user@example.com TODOPRO_PASSWORD=secret todopro login
```

**Flags:**
- `--email, -e`: Email address
- `--password, -p`: Password (prompt if not provided)
- `--profile`: Configuration profile name (default: "default")
- `--endpoint`: API endpoint URL
- `--save-profile`: Save as default profile

### 1.2 Logout
**Command:** `todopro logout [OPTIONS]`

**Features:**
- Clear stored credentials
- Revoke tokens on server (if supported)
- Profile-specific logout

**Examples:**
```bash
# Logout from current profile
todopro logout

# Logout from specific profile
todopro logout --profile staging

# Logout from all profiles
todopro logout --all
```

### 1.3 User Profile
**Command:** `todopro whoami`, `todopro profile [SUBCOMMAND]`

**Features:**
- Display current user information
- Update profile settings
- Manage notification preferences

**Examples:**
```bash
# Show current user
todopro whoami

# Show detailed profile
todopro profile show
todopro profile show -o json

# Update profile
todopro profile update --name "John Doe"

# Manage notification preferences
todopro profile notifications
todopro profile notifications --enable email --disable push
```

---

## 📋 2. Task Management

### 2.1 List Tasks
**Command:** `todopro tasks list`, `todopro get tasks`, `todopro tasks`

**Features:**
- List all tasks with filtering
- Search tasks by content/description
- Sort by various fields
- Pagination support
- Multiple output formats

**Examples:**
```bash
# List all tasks
todopro tasks list
todopro get tasks

# Filter by status
todopro tasks list --status open
todopro tasks list --completed

# Filter by project
todopro tasks list --project "Work"
todopro tasks list --project-id <uuid>

# Filter by priority
todopro tasks list --priority high,urgent
todopro tasks list --priority 3,4

# Filter by due date
todopro tasks list --due today
todopro tasks list --due-before "2024-12-31"
todopro tasks list --overdue

# Search
todopro tasks list --search "meeting"

# Sort and limit
todopro tasks list --sort due-date --limit 10
todopro tasks list --sort priority,desc

# Output formats
todopro tasks list -o json
todopro tasks list -o yaml
todopro tasks list -o table
todopro tasks list -o wide  # More columns
todopro tasks list -o custom="id,content,due_date"
```

**Flags:**
- `--status`: Filter by status (open, completed, all)
- `--completed, -c`: Show only completed tasks
- `--project, -p`: Filter by project name
- `--project-id`: Filter by project UUID
- `--label, -l`: Filter by label(s)
- `--priority`: Filter by priority (1-4 or normal,medium,high,urgent)
- `--due`: Filter by due date (today, tomorrow, this-week, overdue)
- `--due-before`: Due before date
- `--due-after`: Due after date
- `--assigned-to`: Filter by assignee
- `--assigned-to-me`: Only tasks assigned to current user
- `--created-by-me`: Only tasks created by current user
- `--search, -s`: Search in content/description
- `--sort`: Sort field (due-date, priority, created-at, updated-at)
- `--limit, -n`: Limit results
- `--offset`: Pagination offset
- `--output, -o`: Output format (json, yaml, table, wide, custom)

### 2.2 Get Task Details
**Command:** `todopro tasks get <TASK_ID>`, `todopro get task <TASK_ID>`

**Features:**
- Display full task details
- Include related data (labels, comments, history)
- Show recurrence information

**Examples:**
```bash
# Get task by ID
todopro tasks get abc123
todopro get task abc123

# Get with related data
todopro tasks get abc123 --with-comments
todopro tasks get abc123 --with-history
todopro tasks get abc123 --with-occurrences

# Output formats
todopro tasks get abc123 -o json
todopro tasks get abc123 -o yaml
```

### 2.3 Create Task
**Command:** `todopro tasks create`, `todopro create task`

**Features:**
- Create new task with all attributes
- Interactive mode with prompts
- Bulk create from file/stdin

**Examples:**
```bash
# Interactive creation
todopro tasks create

# Quick create
todopro tasks create "Buy groceries"
todopro tasks create "Meeting with team" --project Work --priority high

# Detailed creation
todopro tasks create \
  --content "Review PR #123" \
  --description "Check code quality and test coverage" \
  --project "Development" \
  --due "2024-12-31 15:00" \
  --priority 3 \
  --labels "code-review,urgent"

# Create recurring task
todopro tasks create "Weekly standup" \
  --recurring "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9" \
  --due "2024-01-08 09:00"

# Bulk create from file
todopro tasks create --file tasks.json
todopro tasks create --file tasks.yaml

# Create from stdin
echo '{"content": "Task 1"}\n{"content": "Task 2"}' | todopro tasks create --stdin
```

**Flags:**
- `--content, -c`: Task content (required)
- `--description, -d`: Task description
- `--project, -p`: Project name or ID
- `--due`: Due date/time (ISO format or relative)
- `--priority`: Priority (1-4 or normal,medium,high,urgent)
- `--labels, -l`: Comma-separated labels
- `--assign`: Assign to user (email or ID)
- `--recurring`: Recurrence rule (RRULE format)
- `--file, -f`: Create from JSON/YAML file
- `--stdin`: Read from stdin

### 2.4 Update Task
**Command:** `todopro tasks update <TASK_ID>`, `todopro edit task <TASK_ID>`

**Features:**
- Update task attributes
- Interactive editor
- Bulk update operations

**Examples:**
```bash
# Update specific fields
todopro tasks update abc123 --content "Updated content"
todopro tasks update abc123 --priority urgent
todopro tasks update abc123 --due "tomorrow 14:00"

# Move to different project
todopro tasks update abc123 --project "Personal"
todopro tasks move abc123 --to-project "Work"

# Update labels
todopro tasks update abc123 --labels "important,today"
todopro tasks label abc123 --add "urgent" --remove "later"

# Assign task
todopro tasks assign abc123 --to user@example.com
todopro tasks unassign abc123

# Interactive editor
todopro tasks edit abc123

# Bulk update
todopro tasks update --filter "project=Work" --priority high
todopro tasks bulk-update --ids abc,def,ghi --due tomorrow
```

### 2.5 Complete/Reopen Task
**Command:** `todopro tasks complete <TASK_ID>`, `todopro tasks reopen <TASK_ID>`

**Examples:**
```bash
# Complete task
todopro tasks complete abc123
todopro tasks done abc123
todopro tasks close abc123

# Complete multiple tasks
todopro tasks complete abc123 def456 ghi789

# Reopen task
todopro tasks reopen abc123
todopro tasks uncomplete abc123

# Bulk complete
todopro tasks complete --filter "priority=low"
```

### 2.6 Delete Task
**Command:** `todopro tasks delete <TASK_ID>`, `todopro delete task <TASK_ID>`

**Examples:**
```bash
# Delete task
todopro tasks delete abc123

# Delete with confirmation skip
todopro tasks delete abc123 --yes

# Delete multiple
todopro tasks delete abc123 def456 ghi789

# Bulk delete
todopro tasks delete --filter "completed=true,older-than=30d"
```

### 2.7 Task Comments
**Command:** `todopro tasks comments <TASK_ID> [SUBCOMMAND]`

**Examples:**
```bash
# List comments
todopro tasks comments abc123 list

# Add comment
todopro tasks comments abc123 add "This is important"
todopro tasks comments abc123 add --mention @user "What do you think?"

# Update comment
todopro tasks comments abc123 update comment-id --text "Updated text"

# Delete comment
todopro tasks comments abc123 delete comment-id
```

### 2.8 Recurring Tasks
**Command:** `todopro tasks recurring <TASK_ID> [SUBCOMMAND]`

**Examples:**
```bash
# List occurrences
todopro tasks recurring abc123 occurrences

# Skip occurrence
todopro tasks recurring abc123 skip

# Pause/Resume
todopro tasks recurring abc123 pause
todopro tasks recurring abc123 resume

# Update recurrence rule
todopro tasks recurring abc123 update --rule "FREQ=DAILY;INTERVAL=2"
```

---

## 📁 3. Project Management

### 3.1 List Projects
**Command:** `todopro projects list`, `todopro get projects`

**Examples:**
```bash
# List all projects
todopro projects list

# Show archived
todopro projects list --archived
todopro projects list --all

# Show favorites only
todopro projects list --favorites

# With statistics
todopro projects list --with-stats

# Output formats
todopro projects list -o json
todopro projects list -o table
```

### 3.2 Get Project Details
**Command:** `todopro projects get <PROJECT_ID>`

**Examples:**
```bash
# Get project details
todopro projects get abc123

# With tasks
todopro projects get abc123 --with-tasks

# With statistics
todopro projects get abc123 --with-stats

# Get activity
todopro projects get abc123 --activity
```

### 3.3 Create Project
**Command:** `todopro projects create`

**Examples:**
```bash
# Interactive creation
todopro projects create

# Quick create
todopro projects create "Work Project"

# Detailed creation
todopro projects create \
  --name "Personal Tasks" \
  --color "#FF5733" \
  --favorite
```

### 3.4 Update Project
**Command:** `todopro projects update <PROJECT_ID>`

**Examples:**
```bash
# Update name
todopro projects update abc123 --name "New Name"

# Update color
todopro projects update abc123 --color "#00FF00"

# Toggle favorite
todopro projects favorite abc123
todopro projects unfavorite abc123

# Archive/Unarchive
todopro projects archive abc123
todopro projects unarchive abc123

# Reorder projects
todopro projects reorder --ids "abc,def,ghi"
```

### 3.5 Project Collaboration
**Command:** `todopro projects share <PROJECT_ID>`, `todopro projects collaborators <PROJECT_ID>`

**Examples:**
```bash
# Share project
todopro projects share abc123 --with user@example.com --permission edit

# List collaborators
todopro projects collaborators abc123 list

# Update permissions
todopro projects collaborators abc123 update user@example.com --permission view

# Remove collaborator
todopro projects collaborators abc123 remove user@example.com

# Leave project
todopro projects leave abc123
```

### 3.6 Project Statistics
**Command:** `todopro projects stats <PROJECT_ID>`

**Examples:**
```bash
# Get project stats
todopro projects stats abc123

# Show activity
todopro projects activity abc123

# Output format
todopro projects stats abc123 -o json
```

---

## 🏷️ 4. Label Management

### 4.1 List Labels
**Command:** `todopro labels list`, `todopro get labels`

**Examples:**
```bash
# List all labels
todopro labels list

# With statistics
todopro labels list --with-stats

# Output formats
todopro labels list -o json
```

### 4.2 Create Label
**Command:** `todopro labels create`

**Examples:**
```bash
# Interactive
todopro labels create

# Quick create
todopro labels create "urgent"
todopro labels create "urgent" --color "#FF0000"
```

### 4.3 Label Operations
**Command:** `todopro labels <SUBCOMMAND>`

**Examples:**
```bash
# Update label
todopro labels update abc123 --name "very-urgent" --color "#FF0000"

# Delete label
todopro labels delete abc123

# Get label tasks
todopro labels tasks abc123

# Get label statistics
todopro labels stats abc123

# Bulk operations
todopro labels bulk-add --tasks "task1,task2" --label "urgent"
todopro labels bulk-remove --tasks "task1,task2" --label "later"
```

---

## 🔍 5. Filters & Search

### 5.1 Custom Filters
**Command:** `todopro filters [SUBCOMMAND]`

**Examples:**
```bash
# List saved filters
todopro filters list

# Create filter
todopro filters create "High Priority Work" \
  --query "project=Work AND priority>=3"

# Apply filter
todopro filters apply abc123
todopro tasks list --filter abc123

# Update filter
todopro filters update abc123 --query "project=Work AND priority=4"

# Delete filter
todopro filters delete abc123
```

### 5.2 Advanced Search
**Command:** `todopro search [OPTIONS]`

**Examples:**
```bash
# Full-text search
todopro search "meeting notes"

# Search with filters
todopro search "design" --type tasks --project Work

# Search across all resources
todopro search "urgent" --all
```

---

## 📊 6. Analytics & Reports

### 6.1 Productivity Trends
**Command:** `todopro analytics trends [OPTIONS]`

**Examples:**
```bash
# Get productivity trends
todopro analytics trends

# Specific time period
todopro analytics trends --period 30d
todopro analytics trends --from 2024-01-01 --to 2024-01-31

# Output format
todopro analytics trends -o json
todopro analytics trends -o chart  # ASCII chart
```

### 6.2 Completion Statistics
**Command:** `todopro analytics completion [OPTIONS]`

**Examples:**
```bash
# Completion stats
todopro analytics completion

# By project
todopro analytics completion --by-project

# Completion time analysis
todopro analytics completion-time
```

### 6.3 Streaks
**Command:** `todopro analytics streaks`

**Examples:**
```bash
# Get streak information
todopro analytics streaks

# Current streak only
todopro analytics streaks --current
```

### 6.4 Custom Reports
**Command:** `todopro analytics report [OPTIONS]`

**Examples:**
```bash
# Weekly summary
todopro analytics report --weekly

# Custom report
todopro analytics report \
  --metrics "completed,created,overdue" \
  --group-by project \
  --period 7d

# Export report
todopro analytics report --weekly --export report.json
todopro analytics report --period 30d -o csv > report.csv
```

### 6.5 Priority Distribution
**Command:** `todopro analytics priority`

**Examples:**
```bash
# Get priority distribution
todopro analytics priority

# By project
todopro analytics priority --project Work
```

### 6.6 Overdue Analysis
**Command:** `todopro analytics overdue`

**Examples:**
```bash
# Overdue task analysis
todopro analytics overdue

# With breakdown
todopro analytics overdue --breakdown
```

---

## 🔄 7. Sync & Offline Support

### 7.1 Sync Status
**Command:** `todopro sync status`

**Examples:**
```bash
# Check sync status
todopro sync status

# Quick status
todopro sync status --quick

# Detailed status
todopro sync status --verbose
```

### 7.2 Manual Sync
**Command:** `todopro sync [OPTIONS]`

**Examples:**
```bash
# Full sync
todopro sync

# Delta sync
todopro sync --delta

# Force sync
todopro sync --force

# Sync specific resources
todopro sync --tasks-only
todopro sync --projects-only
```

### 7.3 Device Management
**Command:** `todopro devices [SUBCOMMAND]`

**Examples:**
```bash
# List devices
todopro devices list

# Register current device
todopro devices register --name "My Laptop"

# Unregister device
todopro devices unregister device-id

# Get device details
todopro devices get device-id
```

### 7.4 Conflict Resolution
**Command:** `todopro sync resolve [OPTIONS]`

**Examples:**
```bash
# List conflicts
todopro sync conflicts

# Resolve conflict
todopro sync resolve conflict-id --use-local
todopro sync resolve conflict-id --use-remote
todopro sync resolve conflict-id --merge
```

---

## 🔔 8. Notifications & Reminders

### 8.1 Notification History
**Command:** `todopro notifications [SUBCOMMAND]`

**Examples:**
```bash
# List notifications
todopro notifications list

# Mark as read
todopro notifications read notification-id

# Mark all as read
todopro notifications read-all

# Get notification preferences
todopro notifications preferences
```

### 8.2 Reminders
**Command:** `todopro reminders [SUBCOMMAND]`

**Examples:**
```bash
# List reminders
todopro reminders list

# Create reminder for task
todopro tasks abc123 remind --at "2024-12-31 09:00"

# Snooze reminder
todopro reminders snooze reminder-id --for 1h

# Delete reminder
todopro reminders delete reminder-id
```

---

## 🎨 9. Interactive Mode

### 9.1 Main Menu
**Command:** `todopro interactive`, `todopro menu`, `todopro`

**Features:**
- Full-featured TUI (Text User Interface)
- Navigate through tasks, projects, labels
- Create, update, delete operations
- Visual task boards (kanban-like view)
- Keyboard shortcuts
- Mouse support (optional)

**Example:**
```bash
# Launch interactive mode
todopro
todopro interactive
todopro menu

# Launch with specific view
todopro interactive --view tasks
todopro interactive --view projects
todopro interactive --view kanban
```

**Interactive Features:**
- Task list view with filtering
- Project board view
- Calendar view (tasks by due date)
- Kanban board (by priority/status)
- Quick actions (complete, edit, delete)
- Search and filter
- Multi-select operations

---

## ⚙️ 10. Configuration & Context

### 10.1 Configuration Management
**Command:** `todopro config [SUBCOMMAND]`

**Examples:**
```bash
# View current config
todopro config view
todopro config get api.endpoint

# Set configuration
todopro config set api.endpoint https://todopro.minhdq.dev/api
todopro config set output.format json
todopro config set ui.color true

# List all settings
todopro config list

# Reset to defaults
todopro config reset
todopro config reset output.format
```

**Configuration Options:**
- `api.endpoint`: API base URL
- `api.timeout`: Request timeout (seconds)
- `api.retry`: Retry attempts
- `auth.auto-refresh`: Auto-refresh tokens
- `output.format`: Default output format (table, json, yaml)
- `output.color`: Enable colored output
- `output.wide`: Wide table format
- `ui.interactive`: Enable interactive mode by default
- `ui.page-size`: Items per page
- `cache.enabled`: Enable local caching
- `cache.ttl`: Cache time-to-live
- `sync.auto`: Auto-sync on startup
- `sync.interval`: Auto-sync interval

### 10.2 Profile Management
**Command:** `todopro context [SUBCOMMAND]`

**Examples:**
```bash
# List profiles/contexts
todopro context list

# Switch context
todopro context use staging
todopro context use prod

# Create new context
todopro context create dev --endpoint https://dev.todopro.minhdq.dev/api

# Delete context
todopro context delete staging

# Show current context
todopro context current
```

---

## 🛠️ 11. Utility Commands

### 11.1 Version & Info
**Command:** `todopro version`, `todopro info`

**Examples:**
```bash
# Show version
todopro version
todopro --version

# Show detailed info
todopro info
todopro info --debug
```

### 11.2 Health Check
**Command:** `todopro health`, `todopro check`

**Examples:**
```bash
# Check API connectivity
todopro health

# Detailed health check
todopro health --verbose

# Check specific components
todopro check auth
todopro check sync
```

### 11.3 Completion
**Command:** `todopro completion [SHELL]`

**Examples:**
```bash
# Generate completion for bash
todopro completion bash > ~/.todopro-completion.bash

# Generate for zsh
todopro completion zsh > ~/.todopro-completion.zsh

# Generate for fish
todopro completion fish > ~/.config/fish/completions/todopro.fish
```

### 11.4 Aliases
**Command:** `todopro alias [SUBCOMMAND]`

**Examples:**
```bash
# Create alias
todopro alias create tp "tasks list"
todopro alias create tw "tasks list --project Work"

# List aliases
todopro alias list

# Delete alias
todopro alias delete tw
```

---

## 📤 12. Import/Export

### 12.1 Export Data
**Command:** `todopro export [OPTIONS]`

**Examples:**
```bash
# Export all tasks
todopro export tasks -o tasks.json
todopro export tasks -o tasks.yaml

# Export specific project
todopro export tasks --project Work -o work-tasks.json

# Export with filters
todopro export tasks --filter "priority>=3" -o high-priority.json

# Export all data
todopro export all -o backup.json
```

### 12.2 Import Data
**Command:** `todopro import [OPTIONS]`

**Examples:**
```bash
# Import tasks
todopro import tasks tasks.json

# Import with conflict resolution
todopro import tasks tasks.json --on-conflict skip
todopro import tasks tasks.json --on-conflict overwrite
todopro import tasks tasks.json --on-conflict merge

# Dry run
todopro import tasks tasks.json --dry-run
```

---

## 🚀 13. Advanced Features

### 13.1 Batch Operations
**Command:** `todopro batch [OPTIONS]`

**Examples:**
```bash
# Batch operations from file
todopro batch -f operations.yaml

# Batch from stdin
cat operations.json | todopro batch --stdin
```

### 13.2 Watch Mode
**Command:** `todopro watch [RESOURCE]`

**Examples:**
```bash
# Watch tasks
todopro watch tasks

# Watch specific filter
todopro watch tasks --filter "project=Work"

# Watch with interval
todopro watch tasks --interval 5s
```

### 13.3 Scripting Support
**Features:**
- Exit codes for success/failure
- Machine-readable output (JSON)
- Quiet mode (--quiet, -q)
- Non-interactive mode (--yes, -y)
- Error output to stderr

**Examples:**
```bash
# Scripting-friendly commands
todopro tasks list -o json --quiet
todopro tasks create "Task" --yes --output json

# Exit code usage
if todopro health --quiet; then
  echo "API is healthy"
fi

# JSON parsing with jq
todopro tasks list -o json | jq '.[] | select(.priority > 2)'
```

### 13.4 Plugins
**Command:** `todopro plugins [SUBCOMMAND]`

**Features:**
- Plugin discovery and installation
- Custom commands
- Extension hooks

**Examples:**
```bash
# List plugins
todopro plugins list

# Install plugin
todopro plugins install todopro-export-notion

# Enable/disable plugin
todopro plugins enable export-notion
todopro plugins disable export-notion
```

---

## 📝 14. Output Formats

### Supported Formats
1. **table** (default): Human-readable tables with colors
2. **wide**: Extended table with more columns
3. **json**: Machine-readable JSON
4. **yaml**: YAML format
5. **csv**: Comma-separated values
6. **custom**: Custom format with template
7. **quiet**: Minimal output (IDs only)

### Custom Templates
**Command:** `todopro tasks list -o custom="template"`

**Examples:**
```bash
# Custom columns
todopro tasks list -o custom="id,content,priority"

# Go template syntax
todopro tasks list -o custom='{{ .ID }}: {{ .Content }}'

# Save template
todopro config set templates.my-tasks '{{ .ID }}: {{ .Content }}'
todopro tasks list --template my-tasks
```

---

## 🎯 15. Productivity Features

### 15.1 Quick Add
**Command:** `todopro add <CONTENT>`

**Examples:**
```bash
# Quick add with smart parsing
todopro add "Meeting tomorrow at 2pm #work @high"
# Parses: content="Meeting", due="tomorrow 14:00", project="work", priority="high"

# Quick add with syntax
todopro add "Review PR #123 ^tomorrow !high @work +code-review"
# ^due-date, !priority, @project, +label
```

### 15.2 Today View
**Command:** `todopro today`

**Features:**
- Show today's tasks
- Overdue tasks
- Tasks due soon
- Quick actions

**Examples:**
```bash
# Today's view
todopro today

# With completed tasks
todopro today --all

# Interactive today view
todopro today --interactive
```

### 15.3 Inbox
**Command:** `todopro inbox`

**Features:**
- Tasks without project
- Tasks without due date
- Quick triage

**Examples:**
```bash
# Show inbox
todopro inbox

# Process inbox interactively
todopro inbox --process
```

### 15.4 Weekly Review
**Command:** `todopro review [OPTIONS]`

**Examples:**
```bash
# Weekly review
todopro review --weekly

# Custom period review
todopro review --from 2024-01-01 --to 2024-01-07
```

---

## 🔒 16. Security Features

### 16.1 Credential Management
- Secure credential storage (OS keyring)
- Token encryption
- Session timeout
- Auto-logout on inactivity

### 16.2 Audit Trail
**Command:** `todopro audit [OPTIONS]`

**Examples:**
```bash
# Show audit log
todopro audit log

# Filter by action
todopro audit log --action create
todopro audit log --resource tasks
```

---

## 🌐 17. Multi-language Support

### Internationalization
- Language detection from environment
- Configurable language
- Date/time localization

**Examples:**
```bash
# Set language
todopro config set ui.language en
todopro config set ui.language vi

# Set timezone
todopro config set ui.timezone "Asia/Ho_Chi_Minh"
```

---

## 📚 18. Help & Documentation

### 18.1 Built-in Help
**Command:** `todopro help [COMMAND]`

**Examples:**
```bash
# General help
todopro help
todopro --help

# Command-specific help
todopro tasks --help
todopro tasks create --help

# Show examples
todopro tasks create --examples

# Show all commands
todopro help --all
```

### 18.2 Manual Pages
**Command:** `todopro man [COMMAND]`

**Examples:**
```bash
# Open man page
todopro man
todopro man tasks

# Generate man pages
todopro man --generate
```

---

## 🎓 19. Tutorial & Onboarding

### 19.1 Interactive Tutorial
**Command:** `todopro tutorial`

**Features:**
- Step-by-step guide
- Interactive exercises
- Best practices

### 19.2 Quick Start
**Command:** `todopro quickstart`

**Features:**
- Initial setup wizard
- Sample data creation
- Configuration assistance

---

## 🧪 20. Development & Debug

### 20.1 Debug Mode
**Examples:**
```bash
# Enable debug output
todopro --debug tasks list
todopro -vvv tasks list  # Verbose levels

# Debug specific component
todopro --debug-api tasks list
todopro --debug-cache tasks list
```

### 20.2 Dry Run
**Examples:**
```bash
# Dry run operations
todopro tasks create "Test" --dry-run
todopro tasks delete abc123 --dry-run
```

---

## 📊 Summary

### Command Categories
1. **Authentication**: login, logout, whoami, profile
2. **Tasks**: create, list, get, update, delete, complete, assign
3. **Projects**: create, list, get, update, archive, share
4. **Labels**: create, list, update, delete, bulk operations
5. **Filters**: create, list, apply, update, delete
6. **Analytics**: trends, completion, streaks, reports, priority
7. **Sync**: status, sync, devices, conflicts
8. **Notifications**: list, read, preferences
9. **Interactive**: menu, kanban, calendar
10. **Config**: view, set, reset, profiles
11. **Utilities**: version, health, completion, aliases
12. **Import/Export**: export, import
13. **Advanced**: batch, watch, plugins
14. **Productivity**: add, today, inbox, review

### Key Differentiators
- ✅ **Kubectl-inspired design**: Consistent patterns, predictable behavior
- ✅ **Dual mode**: Interactive TUI + scriptable CLI
- ✅ **Rich output**: Tables, JSON, YAML, custom formats
- ✅ **Offline support**: Local caching and sync
- ✅ **Professional UX**: Colors, progress, helpful messages
- ✅ **Extensible**: Plugins, aliases, custom templates
- ✅ **Production-ready**: Error handling, retries, logging
- ✅ **Well-documented**: Help, examples, man pages
- ✅ **Productivity-focused**: Quick add, smart parsing, keyboard shortcuts

---

## 🎯 Development Roadmap

### Phase 1: Core (MVP)
- [x] Project structure setup
- [ ] Authentication (login, logout, profile)
- [ ] Task CRUD operations
- [ ] Project management
- [ ] Basic output formats (table, JSON)
- [ ] Configuration management
- [ ] Error handling

### Phase 2: Enhanced Features
- [ ] Label management
- [ ] Filter operations
- [ ] Analytics and reports
- [ ] Interactive mode
- [ ] Offline sync
- [ ] Advanced search

### Phase 3: Advanced Features
- [ ] Batch operations
- [ ] Import/export
- [ ] Plugin system
- [ ] Custom templates
- [ ] Watch mode
- [ ] Multi-language support

### Phase 4: Productivity
- [ ] Quick add with smart parsing
- [ ] Today/Inbox views
- [ ] Kanban board
- [ ] Calendar view
- [ ] Review workflows
- [ ] Mobile companion (optional)

---

## 📄 References

**Similar CLIs for inspiration:**
- `kubectl` - Kubernetes CLI (resource-oriented, context-aware)
- `gh` - GitHub CLI (interactive menus, rich output)
- `aws` - AWS CLI (comprehensive, well-documented)
- `gcloud` - Google Cloud CLI (consistent patterns)
- `stripe` - Stripe CLI (great UX, interactive)
- `todoist-cli` - Todoist CLI (task management specific)

**Technologies:**
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [httpx](https://www.python-httpx.org/) - HTTP client
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) - Interactive prompts
- [platformdirs](https://platformdirs.readthedocs.io/) - Config directories

---

**Last Updated:** 2024-01-12
**Version:** 1.0.0
**Author:** TodoPro Team
