# Dynamic Backend Configuration

## Overview

The TodoPro CLI supports dynamic backend URL discovery, allowing the backend API endpoint to be changed remotely without requiring users to update their CLI version. This feature combines PyPI metadata with environment variable overrides for maximum flexibility.

## Features

- **Remote Configuration**: Backend URL can be updated via PyPI metadata
- **Automatic Discovery**: CLI fetches backend URL when checking for updates (every hour)
- **Environment Override**: Developers can override backend URL for testing
- **Fallback Chain**: Multiple fallback layers ensure CLI always has a working backend URL
- **Cache-based**: Minimizes API calls using local cache

## Priority Hierarchy

The CLI determines the backend URL using the following priority order (highest to lowest):

1. **Environment Variable** (`TODOPRO_BACKEND_URL`) - Highest priority, for development/testing
2. **Local Cache** - If PyPI was fetched within the last hour
3. **PyPI Metadata** - Fetched from `project_urls.Backend` field
4. **Hard-coded Fallback** - Default URL: `https://todopro.minhdq.dev/api`

## Configuration

### PyPI Metadata Setup

The backend URL is defined in `pyproject.toml` and published to PyPI:

```toml
[project.urls]
Backend = "https://todopro.minhdq.dev/api"
Homepage = "https://github.com/minhdqdev/todopro"
```

When you publish a new version (or update metadata on PyPI), the CLI will automatically discover the new backend URL within 1 hour.

### Environment Variable Override

For development or testing, you can override the backend URL:

```bash
# Point to local development server
export TODOPRO_BACKEND_URL="http://localhost:8000/api"
todopro tasks list

# Or use it for a single command
TODOPRO_BACKEND_URL="http://localhost:8000/api" todopro tasks list

# Point to staging environment
export TODOPRO_BACKEND_URL="https://staging.todopro.com/api"
todopro tasks list
```

## Cache Structure

The backend URL is cached alongside update check data in `~/.cache/todopro/update_check.json`:

```json
{
  "last_check_timestamp": 1700000000.0,
  "latest_version": "1.2.3",
  "backend_url": "https://todopro.minhdq.dev/api"
}
```

## How It Works

### Automatic Update Discovery

When the CLI checks for updates (every hour or on `todopro update`), it:

1. Calls PyPI API: `https://pypi.org/pypi/todopro-cli/json`
2. Extracts latest version from `info.version`
3. Extracts backend URL from `info.project_urls.Backend`
4. Caches both values locally for 1 hour

### API Client Integration

The `APIClient` class automatically uses dynamic backend discovery:

```python
class APIClient:
    def __init__(self, profile: str = "default"):
        self.config_manager = get_config_manager(profile)
        self.config = self.config_manager.config
        # Use dynamic backend URL with fallback to config
        self.base_url = self._get_backend_url()
        # ...

    def _get_backend_url(self) -> str:
        """Get backend URL with priority: env > dynamic discovery > config."""
        # Priority 1: Environment variable
        # Priority 2: Dynamic discovery from PyPI/cache
        # Priority 3: Fallback to config
```

## Use Cases

### Use Case 1: Changing Backend Domain

When you acquire a new domain (e.g., `todopro.com`):

1. Update `pyproject.toml`:
   ```toml
   [project.urls]
   Backend = "https://api.todopro.com"
   ```

2. Publish to PyPI (can be a new version or just metadata update)

3. Users' CLIs will automatically discover the new URL within 1 hour

### Use Case 2: Development Testing

Developer wants to test CLI against local backend:

```bash
export TODOPRO_BACKEND_URL="http://localhost:8000/api"
todopro login
todopro tasks list
todopro tasks add "Test task"
```

### Use Case 3: Staging Environment

QA team testing against staging:

```bash
export TODOPRO_BACKEND_URL="https://staging.todopro.minhdq.dev/api"
todopro login
todopro tasks list
```

### Use Case 4: Regional Backends

Supporting different regions:

```toml
# Europe
Backend = "https://eu.todopro.com/api"

# Asia
Backend = "https://asia.todopro.com/api"
```

Users in different regions get different published versions.

## Implementation Details

### get_backend_url() Function

Located in `src/todopro_cli/utils/update_checker.py`:

```python
def get_backend_url() -> str:
    """Get backend URL with priority: env var > cache > PyPI > default."""
    # 1. Check environment variable
    env_url = os.getenv("TODOPRO_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")

    # 2. Check fresh cache (< 1 hour old)
    if cache_is_fresh():
        return cached_backend_url

    # 3. Fetch from PyPI metadata
    try:
        pypi_data = fetch_from_pypi()
        backend_url = pypi_data["project_urls"]["Backend"]
        update_cache(backend_url)
        return backend_url
    except:
        pass

    # 4. Use expired cache as fallback
    if cache_exists():
        return cached_backend_url

    # 5. Hard-coded default
    return DEFAULT_BACKEND_URL
```

### API Client Integration

The `APIClient` class in `src/todopro_cli/api/client.py` uses dynamic backend discovery:

```python
def _get_backend_url(self) -> str:
    """Get backend URL with priority: env > dynamic discovery > config."""
    from todopro_cli.utils.update_checker import get_backend_url

    try:
        dynamic_url = get_backend_url()
        if dynamic_url:
            return dynamic_url
    except Exception:
        pass

    # Fallback to config
    return self.config.api.endpoint.rstrip("/")
```

## Security Considerations

1. **HTTPS Required**: Always use HTTPS URLs in production PyPI metadata
2. **No Automatic Redirect**: CLI won't follow redirects automatically
3. **Validation**: Backend URL is stripped of trailing slashes
4. **Fail-Safe**: If all discovery methods fail, falls back to hard-coded default

## Testing

Comprehensive tests in `tests/test_update_checker.py`:

```bash
# Run all backend URL tests
uv run pytest tests/test_update_checker.py::test_get_backend_url* -v

# Test environment variable priority
TODOPRO_BACKEND_URL="http://test.com/api" pytest tests/test_update_checker.py::test_get_backend_url_from_env_var -v
```

Tests cover:
- Environment variable priority
- Cache usage (fresh and expired)
- PyPI metadata fetching
- Fallback to default
- Trailing slash removal
- Network error handling

## Monitoring

To check which backend URL is being used:

```bash
# Via Python
uv run python -c "from todopro_cli.utils.update_checker import get_backend_url; print(get_backend_url())"

# Via environment variable (override)
TODOPRO_BACKEND_URL="http://localhost:8000/api" todopro tasks list

# Check cache
cat ~/.cache/todopro/update_check.json | jq .backend_url
```

## Troubleshooting

### CLI using wrong backend URL

1. Check environment variable: `echo $TODOPRO_BACKEND_URL`
2. Clear cache: `rm ~/.cache/todopro/update_check.json`
3. Force refresh: `todopro update` (fetches latest from PyPI)

### Backend URL not updating

1. Verify PyPI metadata is published correctly
2. Check cache timestamp: `cat ~/.cache/todopro/update_check.json`
3. Wait up to 1 hour for cache to expire, or clear it manually
4. Run `todopro update` to force refresh

## Best Practices

1. **Always use HTTPS** in production PyPI metadata
2. **Test changes** with environment variable before publishing to PyPI
3. **Gradual rollout**: Publish metadata update, monitor, then publish new version
4. **Document changes**: Notify users when changing backend URL
5. **Keep fallback**: Ensure hard-coded default always works
