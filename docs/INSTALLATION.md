# Installation Guide

## Quick Install (Recommended)

The easiest way to install todopro-cli is using our one-liner installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install git+https://github.com/minhdqdev-org/todopro-cli.git
```

### What This Does

1. **Installs `uv`** - A fast Python package installer and resolver (if not already installed)
2. **Installs todopro-cli** - Pulls the CLI tool directly from GitHub
3. **Creates an isolated environment** - All dependencies are installed in isolation
4. **Adds commands to PATH** - Makes `todopro` and `tp` commands available globally

### Why This Works

- ✅ **Zero Manual Config:** `uv` automatically detects Python version from `pyproject.toml`
- ✅ **Isolated:** Dependencies won't conflict with your system Python
- ✅ **Fast:** `uv` is written in Rust and caches aggressively
- ✅ **Easy Updates:** Simply run `uv tool upgrade todopro-cli`

---

## Alternative Installation Methods

### From a Specific Release

Install a specific version from GitHub releases:

```bash
uv tool install https://github.com/minhdqdev-org/todopro-cli/releases/download/v0.1.0/todopro_cli-0.1.0-py3-none-any.whl
```

### From Local Source

If you've cloned the repository:

```bash
cd todopro-cli
uv tool install --from . todopro-cli
```

### For Development

Install in editable mode with dev dependencies:

```bash
cd todopro-cli
uv pip install -e ".[dev]"
```

---

## Updating

Keep your installation up to date:

```bash
uv tool upgrade todopro-cli
```

---

## Uninstalling

Remove todopro-cli completely:

```bash
uv tool uninstall todopro-cli
```

---

## Troubleshooting

### Command not found after installation

Make sure `uv`'s bin directory is in your PATH. Add this to your shell profile:

```bash
# For bash (~/.bashrc) or zsh (~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Private Repository Access

If the repository is private, you'll need SSH access:

```bash
# Make sure your SSH key is added to ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519  # or your key file

# Then install using SSH URL
uv tool install git+ssh://git@github.com/minhdqdev-org/todopro-cli.git
```

### Python Version Issues

todopro-cli requires Python 3.12 or later. Check your version:

```bash
python3 --version
```

If needed, install Python 3.12:

```bash
# Using uv (recommended)
uv python install 3.12

# Or use your system package manager
# Ubuntu/Debian:
sudo apt install python3.12

# macOS with Homebrew:
brew install python@3.12
```

---

## Verification

After installation, verify it works:

```bash
# Check version
todopro --version

# Get help
todopro --help

# Test with short alias
tp --help
```

---

## Next Steps

Once installed, start using todopro-cli:

1. **Login:** `todopro login`
2. **Add a task:** `todopro add "Buy milk tomorrow"`
3. **List tasks:** `todopro tasks list`

See the [README](../README.md) for full usage documentation.
