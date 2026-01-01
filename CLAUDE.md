# Claude/Agent Development Guide

This project uses `uv` for package management and tool installation.

## UV Commands

```bash
# Setup (first time or after dependency changes)
uv sync

# Run commands in development mode (no install needed)
uv run ccs <command>

# Install/update as global tool (required after code changes)
uv tool install --force .

# Add/remove dependencies
uv add <package>
uv add --dev <package>
uv remove <package>

# Run tests/linting
uv run pytest
uv run black ccs/
uv run ruff check ccs/
```

## Typical Workflow

1. Edit code
2. Reinstall: `uv tool install --force .`
3. Test: `ccs <command>`

Or skip step 2 and use: `uv run ccs <command>`
