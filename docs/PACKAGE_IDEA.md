Since you are using **uv** and hosting on GitHub, you can create a seamless installation experience that combines the official `uv` installer with a direct "tool install" from your repository.

Because your repository is at `minhdqdev-org/todopro-cli`, you can use the following approach.

---

## 1. The One-Liner (User-Facing)

You can provide this command to your users. It installs `uv` (if they don't have it) and then uses `uv` to pull your CLI tool directly from GitHub, build its environment, and place the executable in their path.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install git+https://github.com/minhdqdev-org/todopro-cli.git

```

### Why this is effective:

* **Zero Manual Config:** `uv` automatically detects the Python version needed from your `pyproject.toml`.
* **Isolated:** The tool and its dependencies (like `requests` or `typer`) are kept in an isolated environment, so they won't break the user's system Python.
* **Easy Updates:** Once installed, the user can update your tool simply by running:
`uv tool upgrade todopro-cli`

---

## 2. Prepare your `pyproject.toml`

For the command above to work, your repository must be configured as a "package." Ensure your `pyproject.toml` has a `[project.scripts]` section. This tells `uv` what command name to create and which Python function to run.

```toml
[project]
name = "todopro-cli"
version = "0.1.0"
dependencies = [
    "rich",  # add your actual dependencies here
]

[project.scripts]
todo = "todopro_cli.main:app"  # 'todo' is the command the user will type

```

---

## 3. Handling Private Repositories

If `todopro-cli` is a **private** repository, the `curl | sh` command will fail for users who don't have SSH keys set up for that repo. In that case, you have two options:

1. **Publicly Release Wheels:** Use GitHub Actions to build a `.whl` file on every release. Users can then install the specific release:
```bash
uv tool install https://github.com/minhdqdev-org/todopro-cli/releases/download/v0.1.0/todopro_cli-0.1.0-py3-none-any.whl

```


2. **SSH Authentication:** Ensure the user has their GitHub SSH key added to their `ssh-agent`. `uv` will automatically use it when it sees the `git+ssh://` or `git+https://` URL.

---

## 4. Automation with GitHub Actions

To make this truly professional, you can set up a GitHub Action so that every time you "Tag" a version (e.g., `v1.0.1`), it automatically builds the tool and verifies the installation.

### Recommended Workflow:

1. **Develop:** Write code in your local `uv` environment.
2. **Push:** `git push origin main`.
3. **Tag:** `git tag v0.1.0 && git push origin v0.1.0`.
4. **Install:** Users run the `curl | sh && uv tool install ...` command.

---

To automate your workflow, you can use a GitHub Action that triggers whenever you push a new version tag. This ensures your code is tested and "clean" before users try to install it via `uv`.

Create a file at `.github/workflows/publish.yml` in your repository:

```yaml
name: CI & Release

on:
  push:
    tags:
      - 'v*' # Triggers on v1.0, v0.1.1, etc.
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Set up Python
        run: uv python install
      - name: Install dependencies
        run: uv sync
      - name: Run Tests
        run: uv run pytest # Assumes you have tests

  build-dist:
    needs: test
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Build package
        run: uv build
      - name: Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

```

---

## How to use this workflow

1. **Tag your code:** When you're ready for a release, run:
```bash
git tag v0.1.0
git push origin v0.1.0

```


2. **Automatic Release:** GitHub will create a "Release" page and upload the `.whl` and `.tar.gz` files.
3. **Clean Installation:** Now, your `curl | sh` one-liner becomes even more powerful because it pulls from a verified, tagged version of your tool.

### User Experience

Your user runs the command, `uv` builds the environment in seconds, and they immediately have the `todo` command available. Because `uv` caches aggressively, if they run the installer again, it will finish almost instantly.

---
