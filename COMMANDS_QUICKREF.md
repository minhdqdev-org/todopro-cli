# TodoPro CLI - Quick Command Reference

## New Commands (Quick Access)

### Daily Task Management

```bash
# See what's due today
todopro today

# Get the next task to work on
todopro next

# Complete a task
todopro complete <task_id>

# View project details
todopro describe project <project_id>
```

## All Available Commands

### Top-Level Commands
| Command | Description |
|---------|-------------|
| `todopro version` | Show version information |
| `todopro login` | Login to TodoPro |
| `todopro whoami` | Show current user info |
| `todopro logout` | Logout from TodoPro |
| `todopro health` | Check API health |
| **`todopro today`** | **Show today's tasks** |
| **`todopro next`** | **Show next task to do** |
| **`todopro complete <id>`** | **Complete a task** |
| **`todopro describe project <id>`** | **Describe project** |

### Task Commands (`todopro tasks ...`)
| Command | Description |
|---------|-------------|
| `list` | List tasks with filters |
| `get <id>` | Get task details |
| `create <content>` | Create a new task |
| `update <id>` | Update a task |
| `delete <id>` | Delete a task |
| `complete <id>` | Mark task as completed |
| `reopen <id>` | Reopen completed task |
| **`today`** | **Show today's tasks** |
| **`next`** | **Show next task** |

### Project Commands (`todopro projects ...`)
| Command | Description |
|---------|-------------|
| `list` | List all projects |
| `get <id>` | Get project details |
| `create <name>` | Create a new project |
| `update <id>` | Update a project |
| `delete <id>` | Delete a project |
| `archive <id>` | Archive a project |
| `unarchive <id>` | Unarchive a project |
| **`describe <id>`** | **Detailed project info** |

### Label Commands (`todopro labels ...`)
| Command | Description |
|---------|-------------|
| `list` | List all labels |
| `get <id>` | Get label details |
| `create <name>` | Create a new label |
| `update <id>` | Update a label |
| `delete <id>` | Delete a label |

## Common Options

All commands support:
- `--output, -o`: Output format (table, json, yaml, csv, pretty)
- `--profile`: Profile name (default: default)
- `--compact`: Compact table output
- `--help`: Show command help

## Examples

### Daily Workflow
```bash
# Morning routine
todopro login
todopro today

# During work
todopro next
todopro complete abc-123-def

# Check progress
todopro describe project work-project-id
```

### Task Management
```bash
# Create task
todopro tasks create "Fix bug in login" --project work-id --priority 4

# List high priority tasks
todopro tasks list --priority 4 --status pending

# Complete and move on
todopro complete <task-id>
todopro next
```

### Project Management
```bash
# List all projects
todopro projects list

# Get project details with stats
todopro describe project <project-id>

# Create new project
todopro projects create "Q1 Goals" --color "#FF5733" --favorite
```

## Tips

1. **Use aliases**: Create shell aliases for frequently used commands
   ```bash
   alias tpt="todopro today"
   alias tpn="todopro next"
   alias tpc="todopro complete"
   ```

2. **Check next task**: Make `todopro next` part of your workflow after completing each task

3. **Daily review**: Start each day with `todopro today` to see what needs attention

4. **Project monitoring**: Use `todopro describe project <id>` to track project progress

5. **Output formats**: Use `--output json` for scripting and automation
