# TodoPro CLI

> A professional command-line interface for TodoPro task management system, inspired by kubectl.

## 🚀 Features

- **Kubectl-inspired**: Resource-oriented commands with consistent patterns
- **Context-aware**: Maintains authentication state and user preferences
- **Output flexibility**: JSON, YAML, table, and custom formats
- **Interactive & scriptable**: Menu-driven UI for exploration, flags for automation
- **Professional UX**: Rich terminal UI with colors, progress indicators, and helpful messages

## 📦 Installation

```bash
# Install from source
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## 🎯 Quick Start

```bash
# Login to TodoPro
todopro login

# List tasks
todopro tasks list

# Create a task
todopro tasks create "Buy groceries"

# Get help
todopro --help
```

## 📚 Documentation

See [FEATURES.md](FEATURES.md) for comprehensive feature documentation and usage examples.

## 🔧 Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

## 📄 License

MIT License - see LICENSE file for details.
