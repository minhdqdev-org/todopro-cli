# Release Process

This document describes how to create a new release of todopro-cli.

## Overview

The release process is automated using GitHub Actions. When you push a version tag, the CI workflow will:

1. ✅ Run all tests
2. 📦 Build the package (`.whl` and `.tar.gz`)
3. 🚀 Create a GitHub Release with the artifacts

## Creating a Release

### 1. Update Version

Edit `pyproject.toml` and update the version number:

```toml
[project]
name = "todopro-cli"
version = "0.2.0"  # <-- Update this
```

### 2. Commit Changes

```bash
git add pyproject.toml
git commit -m "Bump version to 0.2.0"
git push origin main
```

### 3. Create and Push Tag

```bash
# Create a tag matching the version
git tag v0.2.0

# Push the tag to trigger the release workflow
git push origin v0.2.0
```

### 4. Monitor GitHub Actions

1. Go to https://github.com/minhdqdev-org/todopro-cli/actions
2. Watch the "CI & Release" workflow
3. Verify tests pass and build succeeds

### 5. Verify Release

1. Go to https://github.com/minhdqdev-org/todopro-cli/releases
2. The new release should be created automatically
3. Check that `.whl` and `.tar.gz` files are attached

## Versioning Scheme

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR version** (v1.0.0 → v2.0.0): Breaking changes
- **MINOR version** (v0.1.0 → v0.2.0): New features (backward compatible)
- **PATCH version** (v0.1.0 → v0.1.1): Bug fixes

### Examples

```bash
# Bug fix release
v0.1.0 → v0.1.1

# New feature release
v0.1.1 → v0.2.0

# Breaking change release
v0.2.0 → v1.0.0
```

## Pre-Release Checklist

Before creating a release:

- [ ] All tests pass locally: `uv run pytest`
- [ ] Code is formatted: `black src/ tests/`
- [ ] Code passes linting: `ruff check src/ tests/`
- [ ] README.md is up to date
- [ ] CHANGELOG.md is updated (if exists)
- [ ] Version number follows semver
- [ ] Git working directory is clean

## Post-Release

After the release is published:

### Test Installation

```bash
# Test installing from the release
uv tool install https://github.com/minhdqdev-org/todopro-cli/releases/download/v0.2.0/todopro_cli-0.2.0-py3-none-any.whl

# Verify it works
todopro --version
```

### Update Documentation

If needed, update:
- README.md with new features
- docs/INSTALLATION.md with new version numbers
- Example commands

### Announce

Consider announcing the release:
- GitHub Discussions
- Team chat
- Email to users

## Rollback

If a release has critical issues:

### Option 1: Delete the Tag and Release

```bash
# Delete remote tag
git push --delete origin v0.2.0

# Delete local tag
git tag -d v0.2.0

# Delete the GitHub Release manually in the web UI
```

### Option 2: Create a Hotfix Release

```bash
# Fix the issue
git commit -m "Fix critical bug"
git push origin main

# Create a new patch version
git tag v0.2.1
git push origin v0.2.1
```

## Troubleshooting

### Build Fails

1. Check GitHub Actions logs
2. Run `uv build` locally to reproduce
3. Fix issues and create a new tag

### Tests Fail

1. Check which tests failed in Actions
2. Run tests locally: `uv run pytest -v`
3. Fix issues, commit, and create a new tag

### Wrong Version Number

If you pushed a tag with the wrong version:

```bash
# Delete the tag
git push --delete origin v0.2.0
git tag -d v0.2.0

# Update pyproject.toml with correct version
# Commit and create new tag
git tag v0.3.0
git push origin v0.3.0
```

## GitHub Actions Workflow

The workflow file is at `.github/workflows/publish.yml`:

```yaml
- Push to main → Runs tests only
- Push tag v* → Runs tests + builds + creates release
```

### Required Secrets

No additional secrets needed! The workflow uses:
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Advanced: Manual Release

If you need to create a release manually:

```bash
# Build locally
uv build

# Upload to GitHub Release manually
# (Use GitHub web UI to create release and upload dist/*)
```

## Questions?

- Check GitHub Actions logs for detailed error messages
- Review the workflow file: `.github/workflows/publish.yml`
- See uv documentation: https://docs.astral.sh/uv/
