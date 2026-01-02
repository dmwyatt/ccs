# CCS (Cursor Conversation Search) - Project Overview

## What This Is

A Python CLI tool for reading, searching, and exporting Cursor agent conversations from the local SQLite database.

## Project Status

✅ **Investigation Complete** - Fully documented how Cursor stores conversations
✅ **Working CLI** - Functional CLI with all core features implemented
✅ **Managed by uv** - Proper Python project setup with uv
🔲 **Not Yet Published** - Not yet installable via `uv tool install`

## Project Structure

```
ccs/
├── ccs/                       # Main package
│   ├── __init__.py            # Package metadata
│   ├── cli.py                 # CLI commands (click-based)
│   ├── database.py            # Database interface
│   └── datetime_utils.py      # Time filtering utilities
├── pyproject.toml             # Project configuration
├── uv.lock                    # Dependency lock file
├── README.md                  # User documentation
├── AGENT_GUIDE.md             # Guide for AI agents
├── .cursorrules               # Cursor integration rules
└── PROJECT_OVERVIEW.md        # This file
```

## Quick Start

### Run the CLI in Development Mode

```bash
# Show database info
uv run ccs info

# List conversations
uv run ccs list

# Show a conversation
uv run ccs show <title or id>

# Export to markdown
uv run ccs export <title or id> --format markdown

# Search
uv run ccs search "query"
```

## Key Files

### `ccs/database.py`

Core database interface with these classes/functions:

- `get_cursor_db_path()` - Get path to Cursor's database
- `CursorDatabase` - Main database interface
  - `list_conversations()` - Get all conversations with time filtering
  - `get_conversation(id)` - Get specific conversation metadata
  - `get_messages(id)` - Get messages for a conversation
  - `search_conversations(query)` - Search conversations (keyword AND logic, supports quoted phrases)

### `ccs/cli.py`

CLI commands using Click and Rich:

- `ccs list` - List all conversations
- `ccs show <title or id>` - Display conversation
- `ccs export <title or id>` - Export conversation
- `ccs search <query>` - Search conversations
- `ccs info` - Show database info

### `pyproject.toml`

Project configuration:
- Dependencies: `click`, `rich`
- Dev dependencies: `pytest`, `black`, `ruff`
- Entry point: `ccs` command

## Investigation Findings

Cursor stores conversations in:
- **Location:** `~/.config/Cursor/User/globalStorage/state.vscdb`
- **Format:** SQLite database with key-value pattern
- **Structure:**
  - `composerData:<id>` - Conversation metadata
  - `bubbleId:<composer_id>:<bubble_id>` - Individual messages

See `INVESTIGATION.md` for complete details.

## Next Steps to Publish

To make this installable via `uv tool install`:

1. **Choose a package name** (check PyPI availability)
2. **Add a LICENSE file** (MIT, Apache 2.0, etc.)
3. **Update author info** in `pyproject.toml`
4. **Add tests** using pytest
5. **Build the package:**
   ```bash
   uv build
   ```
6. **Publish to PyPI:**
   ```bash
   uv publish
   ```
7. **Install as tool:**
   ```bash
   uv tool install ccs
   # Or from GitHub:
   uv tool install git+https://github.com/dmwyatt/ccs.git
   ```

## Development Commands

```bash
# Sync dependencies
uv sync

# Add a dependency
uv add <package>

# Run tests (when added)
uv run pytest

# Format code
uv run black .

# Lint code
uv run ruff check .
```

## Platform Support

- **Linux:** ✅ Tested and working
- **macOS:** 🔲 Should work with path adjustment
- **Windows:** 🔲 Should work with path adjustment

Database paths:
- Linux: `~/.config/Cursor/User/globalStorage/state.vscdb`
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- Windows: `%APPDATA%\Cursor\User\globalStorage\state.vscdb`

## Features

- ✅ List all conversations with metadata
- ✅ Show individual conversations by title or ID
- ✅ Export to Markdown, JSON, or Text
- ✅ Search conversations
- ✅ Display statistics
- ✅ Rich terminal output with tables
- ✅ Partial ID matching
- ✅ Title-based access with fuzzy matching
- ✅ Date/time filtering (relative and absolute)
- 🔲 Rich text rendering
- 🔲 Code block syntax highlighting
- 🔲 HTML export
- 🔲 Conversation deletion/archiving

## Use Cases

1. **Documentation** - Export important conversations for reference
2. **Sharing** - Share AI conversations with team members
3. **Search** - Find past conversations about specific topics
4. **Analytics** - Analyze AI usage patterns
5. **Backup** - Create backups of valuable conversations
6. **Migration** - Move conversations between systems

## Technical Notes

- Uses SQLite for database access (built-in Python)
- Click for CLI framework (excellent UX)
- Rich for beautiful terminal output
- No external dependencies besides click and rich
- Database is read-only (safe to use)
- Supports partial ID matching for convenience

## Contributing Ideas

- Add tests for database operations
- Implement rich text rendering
- Add code syntax highlighting
- Support multiple platforms automatically
- Add conversation statistics/analytics
- Implement conversation tagging
- Add conversation import/export in standard formats
- Create a web UI alternative
