# Quick Add - Natural Language Task Creation

TodoPro CLI and backend support natural language parsing for quick task creation. Simply type what you want to do in plain English, and TodoPro will parse the details automatically.

## Overview

The quick-add feature allows you to create tasks using natural language instead of remembering flags and syntax. TodoPro understands:

- **Due dates**: tomorrow, next week, Monday, Jan 15, in 3 days
- **Times**: at 2pm, at 14:00, 9:30am
- **Projects**: #work, #personal, #groceries
- **Labels**: @urgent, @review, @shopping
- **Priority**: p1 (urgent), p2 (high), p3 (medium), p4 (normal)
- **Recurrence**: every day, every Monday, every 2 weeks

## Commands

### Top-Level Shortcut

The fastest way to add a task:

```bash
todopro add "Task description"
```

### Full Command

For more control and options:

```bash
todopro tasks quick-add "Task description"
```

## Syntax

### Projects: `#project-name`

Assign tasks to specific projects:

```bash
todopro add "Review pull request #work"
todopro add "Buy groceries #shopping"
todopro add "Plan vacation #personal"
```

### Labels: `@label-name`

Tag tasks with labels (multiple labels supported):

```bash
todopro add "Code review @urgent @code-review"
todopro add "Buy milk @shopping @groceries"
```

### Priority: `p1`, `p2`, `p3`, `p4`

Set task priority:

- **p1** = Urgent (highest priority)
- **p2** = High priority
- **p3** = Medium priority
- **p4** = Normal priority (default)

```bash
todopro add "Fix production bug p1"
todopro add "Update documentation p3"
```

### Due Dates

TodoPro understands many natural date formats:

**Relative Dates**:
```bash
todopro add "Submit report tomorrow"
todopro add "Call dentist in 3 days"
todopro add "Review contract next week"
```

**Specific Days**:
```bash
todopro add "Team meeting Monday"
todopro add "Presentation on Friday"
```

**Dates**:
```bash
todopro add "Project deadline Jan 15"
todopro add "Submit proposal 2026-02-01"
```

### Times

Add specific times to tasks:

```bash
todopro add "Dentist appointment tomorrow at 2pm"
todopro add "Stand-up meeting Monday at 9:30am"
todopro add "Call client at 14:00"
```

### Recurring Tasks

Create repeating tasks:

**Daily**:
```bash
todopro add "Morning standup every day at 9am #work"
```

**Weekly**:
```bash
todopro add "Team meeting every Monday at 10am #meetings"
todopro add "Review metrics every Friday #analytics"
```

**Custom Intervals**:
```bash
todopro add "Sprint planning every 2 weeks #agile"
todopro add "Backup database every 3 days #ops"
```

## Examples

### Simple Tasks

```bash
# Basic task
todopro add "Buy milk"

# Task with due date
todopro add "Submit timesheet tomorrow"

# Task with priority
todopro add "Fix critical bug p1"
```

### Complex Tasks

```bash
# All features combined
todopro add "Code review for user auth feature tomorrow at 2pm #work p2 @code-review @backend"

# Project task with labels
todopro add "Design landing page #website p1 @design @urgent"

# Recurring task with time
todopro add "Team standup every Monday at 9am #meetings p2"

# Shopping list
todopro add "Buy groceries Saturday at 10am #errands @shopping"
```

### Real-World Examples

**Development**:
```bash
todopro add "Implement OAuth login #backend p2 @feature"
todopro add "Write API documentation tomorrow #docs @writing"
todopro add "Deploy to staging Friday at 5pm #devops p1"
todopro add "Code review every morning at 10am #team"
```

**Personal**:
```bash
todopro add "Call mom Sunday at 3pm #personal"
todopro add "Gym workout every Monday, Wednesday, Friday #health"
todopro add "Pay rent tomorrow p1 @bills"
```

**Work**:
```bash
todopro add "Quarterly review presentation next week #work p2"
todopro add "Team lunch Friday at noon #team @social"
todopro add "1-on-1 with manager every 2 weeks #career"
```

## Show Parsing Details

Use the `--show-parsed` flag to see how TodoPro interpreted your input:

```bash
todopro add "Review PR tomorrow at 2pm #work p2 @code-review" --show-parsed
```

Output:
```
Success: Task created: 123

📝 Parsed Details:
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field       ┃ Value                       ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Content     │ Review PR                   │
│ Project     │ work                        │
│ Due Date    │ 2026-01-27T14:00:00         │
│ Priority    │ High                        │
│ Labels      │ code-review                 │
└─────────────┴─────────────────────────────┘

... (task details)
```

## Output Formats

Control output format with `-o` or `--output`:

```bash
# Table format (default)
todopro add "Buy milk" -o table

# JSON format
todopro add "Buy milk" -o json

# YAML format
todopro add "Buy milk" -o yaml

# Compact table
todopro add "Buy milk" -o pretty
```

## Context Awareness

Quick-add respects your current context (dev/staging/prod):

```bash
# Switch to dev
todopro config use-context dev

# Tasks created will use dev API
todopro add "Test feature #development"

# Switch to prod
todopro config use-context prod

# Tasks created will use prod API
todopro add "Deploy feature #production p1"
```

## Error Handling

### Project Not Found

If you reference a non-existent project:

```bash
todopro add "Task #nonexistent"
```

Error response will suggest available projects:
```
Error: Project 'nonexistent' not found
Suggestions:
  - Available projects: work, personal, shopping, inbox
  - Create new project: todopro projects create nonexistent
```

### Invalid Syntax

TodoPro is forgiving - if it can't parse something, it includes it in the task content:

```bash
# This works fine even with unclear date
todopro add "Do something sometime maybe"
# Creates task: "Do something sometime maybe"
```

## Tips & Best Practices

1. **Start Simple**: Begin with basic tasks and gradually add more details
   ```bash
   todopro add "Buy milk"
   todopro add "Buy milk tomorrow"
   todopro add "Buy milk tomorrow #shopping @groceries"
   ```

2. **Be Specific with Dates**: Use clear date formats
   ```bash
   # Good
   todopro add "Submit report Monday"
   
   # Better
   todopro add "Submit report next Monday at 5pm"
   ```

3. **Use Consistent Project Names**: Keep project names simple and lowercase
   ```bash
   todopro add "Task #work"      # Good
   todopro add "Task #Work-Proj" # Harder to remember
   ```

4. **Combine with Scripts**: Use quick-add in shell scripts
   ```bash
   #!/bin/bash
   todopro add "Daily backup completed $(date) #ops @automated"
   ```

5. **Template Tasks**: Create task templates
   ```bash
   alias standup='todopro add "Daily standup #work @meeting"'
   alias review='todopro add "Code review #work @code-review p2"'
   ```

## Comparison: Quick Add vs Regular Create

| Feature | Quick Add | Regular Create |
|---------|-----------|----------------|
| Syntax | Natural language | Flag-based |
| Speed | Very fast | Slower (more typing) |
| Learning curve | Easy | Requires remembering flags |
| Flexibility | Moderate | High (all options available) |
| Best for | Daily use, quick tasks | Complex tasks, scripting |

**Quick Add**:
```bash
todopro add "Code review tomorrow at 2pm #work p2 @review"
```

**Regular Create**:
```bash
todopro tasks create "Code review" \
  --due "2026-01-27T14:00:00" \
  --project work \
  --priority 2 \
  --labels review
```

Both create the same task, but quick-add is much faster for interactive use.

## Backend Implementation

The natural language parser runs on the backend, ensuring consistent parsing across all clients (CLI, Web, mobile). The parser:

1. Extracts projects (#), labels (@), and priority (p1-p4)
2. Removes these elements from the content
3. Parses remaining text for dates and times using `dateparser`
4. Detects recurrence patterns
5. Returns structured data to create the task

This means the same natural language syntax works everywhere in TodoPro.

## See Also

- [TodoPro CLI README](README.md)
- [Context Switching](CONTEXT_SWITCHING.md)
- [Task Management Commands](README.md#tasks)
