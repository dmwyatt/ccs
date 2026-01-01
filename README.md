# CCS - Cursor Conversation Search

A Python CLI tool to read and export Cursor agent conversations from the local SQLite database.

## For AI Agents

**[AGENT_GUIDE.md](AGENT_GUIDE.md)** - Integration guide for AI agents (Claude, Cursor, etc.)

This guide teaches AI agents **when and how** to use CCS effectively:
- Workflow patterns (not just command syntax)
- User interaction best practices
- Time filtering strategies
- How to present search results

**Use it by:**
- Copying into your `.cursorrules` file
- Dropping into `AGENTS.md` or `CLAUDE.md`
- Referencing in agent configuration

The guide focuses on decision-making and integration patterns. For command syntax, agents can run `ccs --help`.

## Technical Details

For information about how Cursor stores conversations locally, including database structure and storage locations, see [INVESTIGATION.md](INVESTIGATION.md).

## Features

The CLI is **title-focused** for better usability:
- **List** - View all conversations with titles, subtitles, and metadata
- **Show** - Display conversations by title or ID
- **Export** - Export conversations by title or ID to markdown, JSON, or text
- **Search** - Search conversations by title, subtitle, or message content
- **Info** - Display statistics about stored conversations

### Title-Based Access

Conversations can be accessed by their **title** (e.g., "Home directory script") or **ID**:
- Titles are automatically extracted from Cursor's metadata (`name` field)
- Subtitles provide additional context (often filenames)
- Fuzzy matching: type part of a title to find conversations
- Falls back to ID matching if no title matches

### DateTime Filtering

Filter conversations by when they were created using human-friendly expressions:

**Relative times (abbreviated format):**
- `--since "15m"` - Last 15 minutes
- `--since "3d"` - Last 3 days
- `--since "4h"` - Last 4 hours
- `--since "1w"` - Last week
- `--since "2mo"` - Last 2 months

**Supported time units:**
- **Minutes**: `m`, `min`, `mins`, `minute`, `minutes`
- **Hours**: `h`, `hr`, `hrs`, `hour`, `hours`
- **Days**: `d`, `day`, `days`
- **Weeks**: `w`, `week`, `weeks`
- **Months**: `mo`, `month`, `months` (30 days)
- **Years**: `y`, `year`, `years` (365 days)

**Absolute dates:**
- `--since "2026-01-01"` - From Jan 1st onwards
- `--before "2026-01-01"` - Before Jan 1st
- `--since "2025-12-01" --before "2026-01-01"` - Date range

**Supported date formats:**
- `YYYY-MM-DD` (e.g., "2026-01-01")
- `YYYY-MM-DD HH:MM` (e.g., "2026-01-01 14:30")
- `MM/DD/YYYY`

## Installation

```bash
# Install directly from GitHub
uv tool install git+https://github.com/dmwyatt/ccs.git

# Or from PyPI (if published)
uv tool install ccs
```

## Usage

```bash
# Show database info and statistics
ccs info

# List conversations (most recent first)
ccs list
ccs list --limit 10 --since "3d"

# Show a conversation by title (fuzzy matching) or ID
ccs show "application lister"
ccs show e39aa420 --format json

# Export to file
ccs export "home directory" --format markdown --output chat.md

# Search conversations (titles and message content)
ccs search "python" --since "1w"
```

Time filters (`--since`, `--before`) work on all commands. See DateTime Filtering above for syntax.

## Next Steps

Potential improvements:
1. Handle and display rich text formatting properly
2. Extract and display code blocks in a readable format
3. Support exporting to HTML format
4. Add filtering options (by date, status, model)
5. Add conversation deletion/archiving capabilities
6. Support multiple Cursor profiles
7. Add conversation statistics and analytics

## Development

```bash
# Setup
cd ccs
uv sync

# Run during development (no install needed)
uv run ccs <command>

# Or install locally and iterate
uv tool install --reinstall .
ccs <command>
```
