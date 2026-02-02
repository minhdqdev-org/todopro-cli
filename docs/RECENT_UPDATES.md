# TodoPro CLI - Recent Updates

## Version 0.1.0+ Features

### ✨ Dynamic Task ID Suffixes (NEW!)

Task IDs now display the **shortest unique suffix** needed to identify each task, similar to Git's short commit hashes.

#### Before
```bash
$ todopro today
📋 Tasks (3 active)
  ☐ Review pull request #abc123
  ☐ Fix production bug #def456
  ☐ Update documentation #xyz789
```

#### After
```bash
$ todopro today
📋 Tasks (3 active)
  ☐ Review pull request #3
  ☐ Fix production bug #6
  ☐ Update documentation #9
```

#### Benefits
- **Shorter IDs**: Most tasks show 1-3 characters instead of 6
- **Less clutter**: Cleaner, more readable task lists
- **Faster typing**: `todopro complete a` instead of `todopro complete abc123`
- **Context-aware**: Adapts to what you're viewing
- **Always unique**: Guaranteed no ambiguity within a view

[Learn more →](docs/DYNAMIC_TASK_ID_SUFFIXES.md)

### 🎯 Background Task Cache

When completing tasks in background mode, they now hide immediately from your task list for better UX.

#### How It Works
```bash
$ todopro complete abc123
✓ Marking task as complete: abc123

$ todopro today
Hiding 1 task(s) being completed in background...
[Task abc123 hidden immediately! ✨]
```

#### Benefits
- **Instant feedback**: Tasks disappear immediately
- **No confusion**: Clear what's happening
- **Safe**: Auto-recovers from failures (5-min TTL)
- **Transparent**: Works automatically, no config needed

[Learn more →](docs/BACKGROUND_TASK_CACHE.md)

### 🔄 Auto-Update System

The CLI now includes a comprehensive auto-update system:

#### Automatic Update Notifications
- Checks for updates every hour (non-blocking, 0.5s timeout)
- Displays friendly notifications after command execution
- Caches results to minimize API calls

#### Manual Update Command
```bash
# Interactive mode (prompts for confirmation)
todopro update

# Non-interactive mode
todopro update -y
```

### 🌐 Dynamic Backend Configuration

The CLI now supports dynamic backend URL discovery:

#### Priority Hierarchy
1. **Environment Variable** - `TODOPRO_BACKEND_URL` (highest priority)
2. **Local Cache** - Cached from PyPI (1-hour TTL)
3. **PyPI Metadata** - Fetched from `project_urls.Backend`
4. **Hard-coded Default** - Fallback URL

#### Development & Testing
```bash
# Point to local development server
export TODOPRO_BACKEND_URL="http://localhost:8000/api"
todopro tasks list

# Point to staging environment
export TODOPRO_BACKEND_URL="https://staging.todopro.com/api"
todopro login
```

#### Benefits
- **Remote Updates**: Change backend URL without CLI updates
- **Zero Downtime**: Seamless migration to new domains
- **Development Friendly**: Easy testing against local/staging backends
- **Automatic Discovery**: Updates within 1 hour of PyPI publication

### 📦 Cache Management

All update and configuration data is cached at:
- **Linux**: `~/.cache/todopro/update_check.json`
- **macOS**: `~/Library/Caches/todopro/update_check.json`
- **Windows**: `C:\Users\<User>\AppData\Local\todopro\cache\update_check.json`

Cache structure:
```json
{
  "last_check_timestamp": 1700000000.0,
  "latest_version": "1.2.3",
  "backend_url": "https://todopro.minhdq.dev/api"
}
```

### 📚 Documentation

- [Dynamic Task ID Suffixes](docs/DYNAMIC_TASK_ID_SUFFIXES.md) - Context-aware unique suffixes
- [Background Task Cache](docs/BACKGROUND_TASK_CACHE.md) - Optimistic UI for background operations
- [Auto Update Checker](docs/AUTO_UPDATE_CHECKER.md) - Complete update system documentation
- [Dynamic Backend Configuration](docs/DYNAMIC_BACKEND_CONFIGURATION.md) - Backend URL discovery guide

### 🧪 Testing

All features are comprehensively tested:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test suites
uv run pytest tests/test_update_checker.py -v
uv run pytest tests/test_task_cache.py -v
uv run pytest tests/test_unique_suffixes.py -v
```

### 🛠️ For Developers

#### Publishing Updates

When publishing to PyPI, include backend URL in `pyproject.toml`:

```toml
[project.urls]
Backend = "https://todopro.minhdq.dev/api"
Homepage = "https://github.com/minhdqdev/todopro"
```

Users' CLIs will automatically discover the new URL within 1 hour.

#### Local Development

```bash
# Install in development mode
uv tool install -e . --force

# Run with local backend
TODOPRO_BACKEND_URL="http://localhost:8000/api" todopro tasks list

# Check current backend URL
uv run python -c "from todopro_cli.utils.update_checker import get_backend_url; print(get_backend_url())"
```

## Migration Notes

### For End Users
- No action required! Updates and backend discovery happen automatically
- To override backend URL, set `TODOPRO_BACKEND_URL` environment variable

### For Developers
- Dynamic backend discovery is integrated into `APIClient` automatically
- No code changes needed to benefit from the feature
- Use environment variable for testing against non-production backends

## Troubleshooting

### CLI using wrong backend URL
```bash
# Check current URL
uv run python -c "from todopro_cli.utils.update_checker import get_backend_url; print(get_backend_url())"

# Check environment variable
echo $TODOPRO_BACKEND_URL

# Clear cache to force refresh
rm ~/.cache/todopro/update_check.json
todopro update
```

### Update notifications not showing
```bash
# Clear cache to force check
rm ~/.cache/todopro/update_check.json

# Run any command to trigger check
todopro version
```

## Future Enhancements

Planned features:
- [ ] Configuration option to disable update checks
- [ ] Configurable check interval
- [ ] Support for update channels (stable, beta)
- [ ] Auto-update with user confirmation
- [ ] Regional backend selection
- [ ] Global task ID cache for consistent suffixes
- [ ] Configurable minimum suffix length
