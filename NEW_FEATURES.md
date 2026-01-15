# TodoPro New Features

## 1. Reschedule Overdue Tasks

### Feature Description
Automatically reschedule all overdue tasks to today with a single command.

### Backend API
- **Endpoint**: `POST /v1/tasks/reschedule-overdue`
- **Authentication**: Required
- **Response**: Returns count of rescheduled tasks and the updated task list

### CLI Command
```bash
# Reschedule all overdue tasks to today
todopro tasks reschedule overdue

# Skip confirmation prompt
todopro tasks reschedule overdue --yes
```

### Behavior
- Finds all incomplete tasks with due dates before today
- Updates their due dates to today at 00:00 in user's timezone
- Asks for confirmation before rescheduling (unless --yes flag is used)
- Displays the rescheduled tasks after operation

## 2. Timezone Management

### Feature Description
Get and set user timezone for accurate date calculations.

### CLI Commands
```bash
# Get current timezone
todopro auth timezone

# Set timezone (IANA format)
todopro auth timezone Asia/Ho_Chi_Minh
todopro auth timezone America/New_York
todopro auth timezone Europe/London
```

### Supported Timezones
Any IANA timezone format is supported. Common examples:
- `Asia/Ho_Chi_Minh` - Vietnam
- `America/New_York` - US Eastern
- `America/Los_Angeles` - US Pacific
- `Europe/London` - UK
- `Asia/Tokyo` - Japan
- `UTC` - Universal Time

### Integration
- User timezone is stored in the database
- Used by backend for date calculations
- Affects:
  - Today's task view
  - Overdue task detection
  - Reschedule operations

## Examples

### Complete Workflow

```bash
# 1. Set your timezone
todopro auth timezone Asia/Ho_Chi_Minh

# 2. Check today's tasks (includes overdue)
todopro today

# 3. Reschedule all overdue tasks to today
todopro tasks reschedule overdue

# 4. Verify tasks were rescheduled
todopro today
```

### Output Example

```bash
$ todopro auth timezone
Current timezone: Asia/Ho_Chi_Minh

To set a new timezone, use:
  todopro auth timezone <IANA_TIMEZONE>
  Example: todopro auth timezone Asia/Ho_Chi_Minh

$ todopro tasks reschedule overdue
Reschedule 32 overdue task(s) to today? [y/N]: y
Success: Rescheduled 32 overdue task(s) to today

Rescheduled Tasks:
🔴 URGENT
  ⬜ Task 1
  ⬜ Task 2
🟠 HIGH PRIORITY
  ⬜ Task 3
  ⬜ Task 4
```

## Technical Details

### Backend Changes
- Added `reschedule_overdue_tasks` view in `tasks/views/views.py`
- Added route `/v1/tasks/reschedule-overdue` in `tasks/urls.py`
- Uses user's timezone for date calculations

### CLI Changes
- Added `reschedule` command in `todopro_cli/commands/tasks.py`
- Added `timezone` command in `todopro_cli/commands/auth.py`
- Added `reschedule_overdue` method in `todopro_cli/api/tasks.py`

### Files Modified

#### Backend (todopro-core-svc)
- `src/tasks/views/views.py` - New reschedule endpoint
- `src/tasks/urls.py` - New route

#### CLI (todopro-cli)
- `src/todopro_cli/api/tasks.py` - API client method
- `src/todopro_cli/commands/tasks.py` - Reschedule command
- `src/todopro_cli/commands/auth.py` - Timezone command

## Deployment Status
- ✅ Backend deployed to production
- ✅ CLI committed and pushed to repository
- ✅ Tested and verified working
