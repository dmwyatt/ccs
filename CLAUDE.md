# Claude/Agent Development Guide

This project uses `uv` for package management and tool installation.

## UV Commands

```bash
# Setup (first time or after dependency changes)
uv sync

# Run commands in development mode (no install needed)
uv run ccs <command>

# Install/update as global tool (required after code changes)
uv tool install --reinstall .

# Add/remove dependencies (if needed)
uv add <package>
uv remove <package>
```

## Typical Workflow

1. Edit code
2. Reinstall: `uv tool install --reinstall .`
3. Test: `ccs <command>`

Or skip step 2 and use: `uv run ccs <command>`

**Note**: Use `--reinstall` instead of `--force` to ensure the tool cache is properly cleared and updated.

## Coding Standards

### Import Conventions

**IMPORTANT**: All imports must be at the top of the file. Never use local imports (imports inside functions) unless absolutely necessary to resolve circular dependencies.

**Bad**:
```python
def my_function():
    from pathlib import Path  # ❌ Local import
    return Path("file.txt")
```

**Good**:
```python
from pathlib import Path  # ✅ Top-level import

def my_function():
    return Path("file.txt")
```

**Exception**: Local imports are only acceptable when resolving circular import issues that cannot be fixed through code restructuring.

### Database Schema Changes

**IMPORTANT**: When modifying code that changes expectations about the Cursor database schema (either relational structure or JSON field requirements), you **must** also update the `check-db` command in `cli.py`.

This includes changes to:
- Expected table names or columns
- Required/expected key patterns (e.g., `composerData:%`, `bubbleId:%`)
- Required or expected JSON fields in `_validate_json_schema()` field specs

Run `ccs check-db` after making changes to verify the schema expectations are correct.
