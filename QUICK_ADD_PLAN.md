# TodoPro Quick Add - Natural Language Task Creation

## Implementation Plan

### Phase 1: Backend API Enhancement
**Goal:** Add endpoint to accept natural language task input and parse it

#### 1.1 Natural Language Parser
Create a parser module to extract:
- Task content (the main text)
- Due date/time (tomorrow, next monday, every friday, etc.)
- Project (#ProjectName)
- Labels (@label1, @label2)
- Priority (p1, p2, p3, p4)
- Recurrence patterns (every day, every week, etc.)

**Dependencies:**
- `dateparser` - Parse natural language dates
- `python-dateutil` - Enhanced date parsing
- Custom regex patterns for #project, @label, p1-p4

#### 1.2 New Backend Endpoint
```
POST /v1/tasks/quick-add
{
  "input": "Call Mom tomorrow at 3pm #Personal p1 @family"
}

Response:
{
  "task": {
    "id": "uuid",
    "content": "Call Mom",
    "due_date": "2026-01-16T15:00:00Z",
    "priority": 4,
    "project": {"id": "...", "name": "Personal"},
    "labels": ["family"]
  },
  "parsed": {
    "original": "Call Mom tomorrow at 3pm #Personal p1 @family",
    "content": "Call Mom",
    "due_string": "tomorrow at 3pm",
    "project_name": "Personal",
    "priority": 4,
    "labels": ["family"]
  }
}
```

### Phase 2: CLI Enhancement
**Goal:** Add quick-add command with interactive and direct modes

#### 2.1 Command Structure
```bash
# Interactive mode (default)
todopro add

# Direct input mode
todopro add "Buy groceries tomorrow #Shopping @urgent p2"

# Quick alias
todopro a "Meeting with team next monday at 2pm #Work p1"
```

#### 2.2 Interactive Flow
1. Show prompt with hints
2. User types task with natural language
3. Show preview of parsed elements (highlighted)
4. Confirm or edit
5. Submit to API

### Phase 3: Parser Rules & Patterns

#### 3.1 Date/Time Patterns
```python
PATTERNS = {
    # Relative dates
    "today": today,
    "tomorrow": today + 1 day,
    "yesterday": today - 1 day,
    "next week": next monday,
    "next monday": next monday,
    
    # Specific dates
    "Jan 15": 2026-01-15,
    "15/01": 2026-01-15,
    "2026-01-15": 2026-01-15,
    
    # Time
    "at 3pm": 15:00,
    "at 14:30": 14:30,
    "3:30pm": 15:30,
    
    # Recurring
    "every day": daily recurrence,
    "every week": weekly recurrence,
    "every monday": weekly on monday,
    "every 2 weeks": bi-weekly,
}
```

#### 3.2 Element Patterns
```python
ELEMENT_PATTERNS = {
    "project": r"#(\w+)",           # #Work, #Personal
    "label": r"@(\w+)",             # @urgent, @waiting
    "priority": r"\bp([1-4])\b",    # p1, p2, p3, p4
    "section": r"/([\w\s]+)",       # /Admin, /Personal Tasks
}
```

### Phase 4: User Experience

#### 4.1 Rich Preview
Show parsed elements with colors:
```
Input: Call Mom tomorrow at 3pm #Personal p1 @family

Preview:
  Content:  Call Mom
  Due:      📅 Tomorrow at 3:00 PM
  Project:  📁 Personal
  Priority: 🔴 URGENT (p1)
  Labels:   🏷️  family

Create this task? [Y/n]:
```

#### 4.2 Auto-complete & Suggestions
- Suggest existing project names after typing #
- Suggest existing labels after typing @
- Show date examples when typing date keywords

## Sample Implementation Results

### Example 1: Simple Task
```bash
$ todopro add "Buy milk"

Preview:
  Content:  Buy milk
  Due:      None
  Project:  📁 Inbox (default)
  Priority: 🟢 Normal (p4)

Create this task? [Y/n]: y
✅ Task created: Buy milk
```

### Example 2: Complete Task with All Elements
```bash
$ todopro add "Review pull request tomorrow at 2pm #Work p1 @code-review"

Parsing... ✓

Preview:
  Content:  Review pull request
  Due:      📅 Tomorrow (Jan 16) at 2:00 PM
  Project:  📁 Work
  Priority: 🔴 URGENT (p1)
  Labels:   🏷️  code-review

Create this task? [Y/n]: y
✅ Task created: Review pull request (ID: abc-123)
```

### Example 3: Recurring Task
```bash
$ todopro add "Team standup every monday at 9am #Work p2"

Parsing... ✓

Preview:
  Content:  Team standup
  Due:      📅 Every Monday at 9:00 AM
  Project:  📁 Work
  Priority: 🟠 HIGH (p2)
  Recurring: Yes (weekly on Monday)

Create this task? [Y/n]: y
✅ Recurring task created: Team standup
   Next occurrence: Monday, Jan 20 at 9:00 AM
```

### Example 4: Interactive Mode
```bash
$ todopro add

Quick Add Task
─────────────────────────────────────────────────────────────
Type your task with natural language. Examples:
  • "Call John tomorrow at 3pm #Work p1"
  • "Buy groceries every friday @shopping"
  • "Review code next monday p2 @review"

Shortcuts:
  #project  @label  p1-p4  tomorrow  every [day|week|month]

Task: ▊
```

User types: `Dentist appointment Jan 20 at 2pm #Personal p3`

```
Task: Dentist appointment Jan 20 at 2pm #Personal p3

Preview:
  Content:  Dentist appointment
  Due:      📅 Jan 20, 2026 at 2:00 PM
  Project:  📁 Personal
  Priority: 🟡 MEDIUM (p3)

[A]dd task  [E]dit  [C]ancel: a
✅ Task created: Dentist appointment
```

### Example 5: Complex Recurring with Multiple Labels
```bash
$ todopro add "Send weekly report every friday at 5pm #Work p2 @reporting @weekly"

Preview:
  Content:  Send weekly report
  Due:      📅 Every Friday at 5:00 PM
  Project:  📁 Work
  Priority: 🟠 HIGH (p2)
  Labels:   🏷️  reporting, weekly
  Recurring: Yes (weekly on Friday)

Create this task? [Y/n]: y
✅ Recurring task created: Send weekly report
   Next occurrence: Friday, Jan 17 at 5:00 PM
```

### Example 6: Error Handling
```bash
$ todopro add "Meeting #NonExistentProject p1"

⚠️  Warning: Project 'NonExistentProject' not found
    Options:
    1. Create new project 'NonExistentProject'
    2. Use default project (Inbox)
    3. Choose from existing projects

Select [1/2/3]: 2

Preview:
  Content:  Meeting
  Project:  📁 Inbox
  Priority: 🔴 URGENT (p1)

Create this task? [Y/n]: y
✅ Task created: Meeting
```

## Technical Architecture

### Backend Files to Create/Modify
```
todopro-core-svc/
├── src/tasks/
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── natural_language.py      # Main NL parser
│   │   ├── date_parser.py           # Date/time parsing
│   │   ├── element_parser.py        # Extract #, @, p1-p4
│   │   └── recurrence_parser.py     # Handle "every X"
│   ├── views/
│   │   └── views.py                 # Add quick_add_task endpoint
│   └── urls.py                      # Add route
└── requirements.txt                 # Add dateparser, python-dateutil
```

### CLI Files to Create/Modify
```
todopro-cli/
├── src/todopro_cli/
│   ├── api/
│   │   └── tasks.py                 # Add quick_add() method
│   ├── commands/
│   │   └── tasks.py                 # Add 'add' command
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── preview.py               # Preview formatter
│   └── ui/
│       └── interactive.py           # Interactive mode UI
└── pyproject.toml                   # Add prompt_toolkit for interactive
```

## Implementation Phases Timeline

### Phase 1 (Backend) - 2-3 hours
- [ ] Create parser module
- [ ] Add date/time parsing logic
- [ ] Add element extraction (project, labels, priority)
- [ ] Create quick-add endpoint
- [ ] Write unit tests
- [ ] Deploy to production

### Phase 2 (CLI) - 2-3 hours
- [ ] Add API client method
- [ ] Create basic 'add' command (direct mode)
- [ ] Add preview/confirmation
- [ ] Handle errors gracefully
- [ ] Test with various inputs

### Phase 3 (Enhancement) - 2-3 hours
- [ ] Add interactive mode
- [ ] Add auto-complete suggestions
- [ ] Add colored preview
- [ ] Add recurrence support
- [ ] Create comprehensive documentation

### Phase 4 (Polish) - 1-2 hours
- [ ] Add keyboard shortcuts (Ctrl+Q for quick add)
- [ ] Add validation and helpful error messages
- [ ] Create examples and help text
- [ ] Update README and documentation

## Dependencies to Add

### Backend
```toml
# In pyproject.toml
dependencies = [
    # ... existing dependencies
    "dateparser>=1.2.0",
    "python-dateutil>=2.8.2",
]
```

### CLI
```toml
# In pyproject.toml
dependencies = [
    # ... existing dependencies
    "prompt_toolkit>=3.0.43",  # For interactive input
    "dateparser>=1.2.0",       # Client-side validation
]
```

## Success Metrics

1. **Parsing Accuracy**: 95%+ correct parsing of common phrases
2. **Speed**: Task creation < 2 seconds (including API call)
3. **User Adoption**: Natural language input becomes primary method
4. **Error Rate**: < 5% need manual correction

## Future Enhancements

1. **Smart Suggestions**: Learn from user patterns
2. **Context Awareness**: Suggest project based on time/location
3. **Bulk Add**: Parse multiple tasks from multi-line input
4. **Voice Input**: Integrate with speech-to-text
5. **Template Expansion**: "meeting" → "Meeting with {name} on {date}"
6. **AI Enhancement**: Use LLM for complex parsing

