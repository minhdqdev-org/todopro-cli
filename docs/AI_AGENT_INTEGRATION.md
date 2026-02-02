# AI Agent Integration Guide

TodoPro CLI is designed to work seamlessly with AI agents and automation tools. This guide explains how to integrate TodoPro CLI into your automated workflows.

## Key Principles

TodoPro CLI follows the AI-agent-friendly CLI design principles:

1. **Deterministic Output** - Same input always produces same output
2. **Structured Data** - JSON output with schemas
3. **Semantic Exit Codes** - Actionable status codes
4. **Idempotent Operations** - Safe to retry
5. **Non-Interactive Mode** - No prompts in automation

## Exit Codes

TodoPro CLI uses semantic exit codes that agents can use to make decisions:

| Code | Name | Meaning | Agent Action |
|------|------|---------|--------------|
| 0 | SUCCESS | Command succeeded | Proceed to next task |
| 1 | ERROR_GENERAL | General error | Log and notify user |
| 2 | ERROR_INVALID_ARGS | Invalid arguments/validation | Fix arguments and retry |
| 3 | ERROR_AUTH_FAILURE | Not authenticated | Run `todopro login` |
| 4 | ERROR_NETWORK | Network/API error | Wait and retry with backoff |
| 5 | ERROR_NOT_FOUND | Resource not found | Verify or create resource |
| 6 | ERROR_PERMISSION_DENIED | Insufficient permissions | Check permissions |

### Example: Handling Exit Codes

```bash
#!/bin/bash
todopro tasks list --output json
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "Success"
    ;;
  3)
    echo "Not authenticated, logging in..."
    todopro login --email user@example.com --password "$PASSWORD"
    ;;
  4)
    echo "Network error, retrying in 5 seconds..."
    sleep 5
    todopro tasks list --output json
    ;;
  *)
    echo "Unexpected error: $EXIT_CODE"
    exit 1
    ;;
esac
```

## JSON Output

Most commands support `--output json` for machine-readable output:

```bash
# List tasks in JSON format
todopro tasks list --output json

# Output format:
{
  "schema_version": "1.0",
  "data": [
    {
      "id": "task-abc123",
      "content": "Buy milk",
      "due_date": "2026-02-03T14:00:00Z",
      "priority": 1,
      "is_completed": false,
      "labels": ["groceries"],
      "project_id": "project-xyz789"
    }
  ],
  "metadata": {
    "total": 12,
    "page": 1,
    "limit": 30
  }
}
```

## Non-Interactive Mode

Use `--yes` / `-y` flag to skip confirmation prompts:

```bash
# Skip confirmation when importing data
todopro data import backup.json --yes

# Skip confirmation when rescheduling tasks
todopro tasks reschedule overdue --yes

# Skip confirmation when deleting
todopro tasks delete task-abc123 --yes
```

## Environment Variables

Configure TodoPro CLI via environment variables for automation:

```bash
export TODOPRO_API_URL="https://api.todopro.com"
export TODOPRO_NO_COLOR=1  # Disable colored output
export TODOPRO_PROFILE="production"

# Run commands - they'll use env vars
todopro tasks list
```

### Environment Variable Precedence

1. **Command-line flags** (highest priority)
2. **Environment variables**
3. **Config file** (`~/.config/todopro/config.yaml`)
4. **Defaults** (lowest priority)

## Idempotent Operations

Some operations are idempotent and safe to retry:

```bash
# Creating a task is idempotent - won't create duplicates
todopro tasks create "Buy milk" --due tomorrow
# Exit code 0 even if similar task exists

# Completing a task is idempotent
todopro complete task-abc123
# Exit code 0 even if already completed
```

## Dry Run Mode

Preview destructive operations without executing:

```bash
# Preview what would be deleted
todopro data purge --dry-run

# Output:
{
  "dry_run": true,
  "items_to_delete": {
    "tasks": 150,
    "projects": 5,
    "labels": 20,
    "contexts": 3
  },
  "total_items": 178,
  "message": "Dry run - no data was deleted"
}
```

## Batch Operations

Process multiple items efficiently:

```bash
# Complete multiple tasks
todopro complete task-abc123 task-def456 task-ghi789

# Export data for backup (supports gzip compression)
todopro data export --output backup.json --compress
```

## Error Handling

TodoPro CLI provides detailed error messages in JSON format:

```bash
todopro tasks create --output json
# Exit code: 2 (INVALID_ARGS)
# Output:
{
  "error": "Missing required argument: content",
  "code": "INVALID_ARGS",
  "details": {
    "missing_fields": ["content"]
  }
}
```

## Integration Examples

### Python Script

```python
import subprocess
import json
import sys

def get_tasks():
    result = subprocess.run(
        ["todopro", "tasks", "list", "--output", "json"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 3:
        # Not authenticated
        print("Please run 'todopro login' first")
        sys.exit(1)
    elif result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)
    
    return json.loads(result.stdout)

tasks = get_tasks()
print(f"You have {len(tasks['data'])} tasks")
```

### Shell Script with Retry Logic

```bash
#!/bin/bash

MAX_RETRIES=3
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
  todopro tasks list --output json > tasks.json
  EXIT_CODE=$?
  
  if [ $EXIT_CODE -eq 0 ]; then
    echo "Success!"
    break
  elif [ $EXIT_CODE -eq 4 ]; then
    echo "Network error, retrying in ${RETRY_DELAY}s... (attempt $i/$MAX_RETRIES)"
    sleep $RETRY_DELAY
    RETRY_DELAY=$((RETRY_DELAY * 2))  # Exponential backoff
  else
    echo "Failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
  fi
done
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Export TodoPro Data

on:
  schedule:
    - cron: '0 0 * * *'  # Daily backup at midnight

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Install TodoPro CLI
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv tool install git+https://github.com/minhdqdev-org/todopro-cli.git

      - name: Login to TodoPro
        run: |
          todopro login \
            --email "${{ secrets.TODOPRO_EMAIL }}" \
            --password "${{ secrets.TODOPRO_PASSWORD }}"

      - name: Export data
        run: |
          todopro data export \
            --output "backup-$(date +%Y%m%d).json" \
            --compress

      - name: Upload backup
        uses: actions/upload-artifact@v3
        with:
          name: todopro-backup
          path: backup-*.json.gz
```

## Best Practices for Agents

1. **Always check exit codes** - Don't assume success
2. **Use `--output json`** - Easier to parse than table format
3. **Handle authentication** - Detect exit code 3 and login
4. **Implement retry logic** - Use exponential backoff for network errors
5. **Use `--yes` flag** - Skip interactive prompts
6. **Respect rate limits** - Add delays between bulk operations
7. **Validate responses** - Check JSON schema before processing
8. **Log operations** - Keep audit trail of automated actions

## Schema Validation

Future versions will include:
- JSON schemas for all output formats
- `todopro schema get <command>` to retrieve schemas
- Schema versioning for backward compatibility

## Getting Help

For more information:
- CLI help: `todopro --help`
- Command-specific help: `todopro tasks --help`
- Documentation: https://github.com/minhdqdev-org/todopro-cli

## Feedback

If you're building an AI agent with TodoPro CLI, we'd love to hear about it!
- Open an issue: https://github.com/minhdqdev-org/todopro-cli/issues
- Discussions: https://github.com/minhdqdev-org/todopro-cli/discussions
