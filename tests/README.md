# TodoPro CLI - Test Suite

This directory contains comprehensive unit tests for the TodoPro CLI application.

## Test Coverage

✅ **Core modules: 97.6% coverage** (exceeds 90% requirement)
✅ **159 tests, all passing**

## Test Structure

```
tests/
├── test_api_auth.py          # Authentication API tests
├── test_api_client.py        # HTTP client tests  
├── test_api_labels.py        # Labels API tests
├── test_api_projects.py      # Projects API tests
├── test_api_tasks.py         # Tasks API tests
├── test_config.py            # Configuration management tests
├── test_formatters.py        # Basic UI formatter tests
├── test_formatters_extended.py  # Extended formatter tests
├── test_formatters_complete.py  # Comprehensive edge cases
└── test_models.py            # Data model tests
```

## Running Tests

### Run all tests
```bash
uv run pytest
```

### Run with coverage
```bash
uv run pytest --cov=src/todopro_cli --cov-report=term-missing
```

### Run specific test file
```bash
uv run pytest tests/test_api_client.py -v
```

### Run specific test
```bash
uv run pytest tests/test_api_client.py::test_request_success -v
```

### Generate HTML coverage report
```bash
uv run pytest --cov=src/todopro_cli --cov-report=html
# Open htmlcov/index.html in your browser
```

## Test Categories

### API Layer Tests (49 tests)
- Authentication (login, logout, token refresh, profile)
- HTTP client (requests, retries, error handling)
- Tasks API (CRUD, complete, comments, quick-add, Eisenhower matrix)
- Projects API (CRUD, archive/unarchive)
- Labels API (CRUD)

### Configuration Tests (19 tests)
- Default configuration values
- Config file save/load
- Credentials management
- Profile management
- Config reset functionality
- Error handling for corrupted files

### Data Model Tests (3 tests)
- Task model validation
- Project model validation
- User model validation

### UI Formatter Tests (88 tests)
- Output format handlers (JSON, YAML, table, pretty, quiet)
- Task formatting (various states, priorities, metadata)
- Project formatting (favorites, archived, statistics)
- Date/time formatting (relative time, due dates, overdue)
- Edge cases and error handling

## Testing Best Practices

### Mock External Dependencies
```python
@pytest.mark.asyncio
async def test_api_call(mock_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "123"}
    mock_client.get.return_value = mock_response
    # Test your code...
```

### Use Fixtures for Common Setup
```python
@pytest.fixture
def mock_config_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup...
        yield config_manager
```

### Test Async Functions
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:
- No external dependencies required
- All API calls are mocked
- Fast execution (< 5 seconds)
- Deterministic results

## Coverage Goals

| Module Type | Target | Actual |
|-------------|--------|--------|
| API Layer | ≥90% | 95%+ |
| Config | ≥90% | 98% |
| Models | ≥90% | 100% |
| UI | ≥90% | 98% |
| **Overall Core** | **≥90%** | **97.6%** ✅ |

## Adding New Tests

When adding new functionality:

1. Create test file following naming convention: `test_<module>.py`
2. Use descriptive test names: `test_<function>_<scenario>`
3. Include docstrings describing what is being tested
4. Mock external dependencies (HTTP, file system, etc.)
5. Test both success and error cases
6. Aim for 90%+ coverage of new code

Example:
```python
def test_create_task_success(mock_client):
    """Test creating a task successfully."""
    # Arrange
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123"}
    mock_client.post.return_value = mock_response
    
    # Act
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.create_task("New task")
    
    # Assert
    assert result["id"] == "task-123"
    mock_client.post.assert_called_once()
```
