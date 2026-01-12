# TodoPro CLI Examples

This document provides examples of using the TodoPro CLI.

## Getting Started

### Installation

```bash
# Install from source
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Initial Setup

```bash
# Login to TodoPro
todopro login

# Or login with credentials
todopro login --email user@example.com --password yourpassword

# Check current user
todopro whoami

# View configuration
todopro config view
```

## Task Management

### List Tasks

```bash
# List all tasks
todopro tasks list

# List tasks in table format
todopro tasks list -o table

# List tasks in JSON format
todopro tasks list -o json

# List tasks in YAML format
todopro tasks list -o yaml

# Filter by status
todopro tasks list --status open

# Filter by project
todopro tasks list --project project-id

# Search tasks
todopro tasks list --search "meeting"

# Limit results
todopro tasks list --limit 10

# Sort tasks
todopro tasks list --sort due-date
```

### Create Tasks

```bash
# Create a simple task
todopro tasks create "Buy groceries"

# Create task with description
todopro tasks create "Review PR" --description "Check code quality"

# Create task with project and priority
todopro tasks create "Team meeting" --project work-proj --priority 3

# Create task with due date
todopro tasks create "Submit report" --due "2024-12-31"

# Create task with labels
todopro tasks create "Bug fix" --labels "bug,urgent"
```

### Get Task Details

```bash
# Get task by ID
todopro tasks get task-id

# Get task in JSON format
todopro tasks get task-id -o json
```

### Update Tasks

```bash
# Update task content
todopro tasks update task-id --content "New content"

# Update task priority
todopro tasks update task-id --priority 4

# Update task due date
todopro tasks update task-id --due "2024-12-31"

# Move task to different project
todopro tasks update task-id --project new-project-id
```

### Complete/Delete Tasks

```bash
# Complete a task
todopro tasks complete task-id

# Reopen a task
todopro tasks reopen task-id

# Delete a task
todopro tasks delete task-id

# Delete without confirmation
todopro tasks delete task-id --yes
```

## Project Management

### List Projects

```bash
# List all projects
todopro projects list

# List archived projects
todopro projects list --archived

# List favorite projects only
todopro projects list --favorites

# Output in JSON
todopro projects list -o json
```

### Create Projects

```bash
# Create a simple project
todopro projects create "Work"

# Create project with color
todopro projects create "Personal" --color "#FF5733"

# Create favorite project
todopro projects create "Important" --favorite
```

### Update Projects

```bash
# Update project name
todopro projects update project-id --name "New Name"

# Update project color
todopro projects update project-id --color "#00FF00"
```

### Archive Projects

```bash
# Archive a project
todopro projects archive project-id

# Unarchive a project
todopro projects unarchive project-id

# Delete a project
todopro projects delete project-id --yes
```

## Label Management

### List Labels

```bash
# List all labels
todopro labels list

# Output in JSON
todopro labels list -o json
```

### Create Labels

```bash
# Create a simple label
todopro labels create "urgent"

# Create label with color
todopro labels create "important" --color "#FF0000"
```

### Update/Delete Labels

```bash
# Update label
todopro labels update label-id --name "very-urgent"

# Update label color
todopro labels update label-id --color "#FF0000"

# Delete label
todopro labels delete label-id --yes
```

## Configuration Management

### View Configuration

```bash
# View entire configuration
todopro config view

# View configuration in JSON
todopro config view -o json

# Get specific value
todopro config get api.endpoint
```

### Set Configuration

```bash
# Set API endpoint
todopro config set api.endpoint https://api.example.com

# Set output format
todopro config set output.format json

# Enable colors
todopro config set output.color true

# Set timeout
todopro config set api.timeout 60
```

### Reset Configuration

```bash
# Reset specific key
todopro config reset output.format

# Reset entire configuration
todopro config reset --yes
```

### Profile Management

```bash
# List all profiles
todopro config list

# Login with a specific profile
todopro login --profile staging

# Use commands with a specific profile
todopro tasks list --profile staging
```

## Authentication

### Login

```bash
# Interactive login
todopro login

# Login with credentials
todopro login --email user@example.com --password secret

# Login to different environment
todopro login --profile staging --endpoint https://staging.example.com/api
```

### Logout

```bash
# Logout from current profile
todopro logout

# Logout from specific profile
todopro logout --profile staging

# Logout from all profiles
todopro logout --all
```

### Check User

```bash
# Show current user
todopro whoami

# Show user in JSON
todopro whoami -o json
```

## Utility Commands

### Version

```bash
# Show version
todopro version
```

### Health Check

```bash
# Check API health
todopro health

# Verbose health check
todopro health --verbose
```

## Advanced Usage

### Using Shell Aliases

The CLI is also available as `tp` for shorter commands:

```bash
# Short version
tp tasks list
tp projects create "New Project"
tp config view
```

### JSON Processing with jq

```bash
# Get task IDs
todopro tasks list -o json | jq '.[].id'

# Get high priority tasks
todopro tasks list -o json | jq '.[] | select(.priority > 2)'

# Count tasks
todopro tasks list -o json | jq 'length'
```

### Scripting

```bash
#!/bin/bash

# Create multiple tasks
for task in "Task 1" "Task 2" "Task 3"; do
  todopro tasks create "$task"
done

# Export tasks to file
todopro tasks list -o json > tasks_backup.json

# Check if logged in
if todopro whoami &> /dev/null; then
  echo "Logged in"
else
  echo "Not logged in"
fi
```

## Tips and Tricks

1. **Use shorter aliases**: The CLI supports both `todopro` and `tp`
2. **JSON output for scripting**: Use `-o json` for machine-readable output
3. **Profiles for multiple environments**: Use `--profile` to manage dev/staging/prod
4. **Skip confirmations**: Use `--yes` or `-y` to skip deletion confirmations
5. **Shell completion**: Install shell completion with `todopro --install-completion`

## Troubleshooting

### Check API Connectivity

```bash
# Test API connection
todopro health

# View current configuration
todopro config view

# Check authentication
todopro whoami
```

### Reset Configuration

```bash
# Reset to defaults
todopro config reset --yes

# Logout and login again
todopro logout
todopro login
```

### View Logs

For debugging, you can check your configuration directory:

```bash
# On Linux/macOS
ls -la ~/.config/todopro-cli/

# On Windows
dir %APPDATA%\todopro-cli\
```
