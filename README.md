# CCS - Cursor Conversation Search

A Python CLI tool to read and export Cursor agent conversations from the local SQLite database.

## 🤖 For AI Agents

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

## Investigation Findings

### Storage Location

Cursor stores agent conversations in a SQLite database at:
```
~/.config/Cursor/User/globalStorage/state.vscdb
```

### Database Structure

The database uses a key-value store pattern with the `cursorDiskKV` table:

#### Key Patterns:

1. **`composerData:<composerId>`** - Conversation threads
   - Contains metadata about the conversation
   - Fields: composerId, status, createdAt, modelConfig, text, context, capabilities
   - One entry per conversation/chat session

2. **`bubbleId:<composerId>:<bubbleId>`** - Individual messages
   - Format links messages to their parent conversation
   - Fields: bubbleId, type, text, richText, createdAt, toolResults, codeBlocks, images
   - Type values: 1 = user message, 2 = assistant message

3. **Other key types** (discovered but not yet explored):
   - `checkpointId:*` - Conversation checkpoints/state saves
   - `codeBlockDiff:*` - Code change diffs
   - `messageRequestContext:*` - Context for API requests
   - `inlineDiffs-<workspaceId>` - Per-workspace inline diffs

### Additional Storage Locations

- `~/.cursor/ai-tracking/ai-code-tracking.db` - Tracks AI-generated code changes
  - Tables: `ai_code_hashes`, `scored_commits`, `tracking_state`

- `~/.cursor/projects/<project-path>/` - Per-project data
  - Rules and project-specific settings

- `~/.config/Cursor/User/workspaceStorage/<workspace-id>/state.vscdb` - Per-workspace state

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

### For Development

```bash
cd ccs
uv sync
```

### As a Tool

#### From GitHub

```bash
# Install directly from GitHub
uv tool install git+https://github.com/dmwyatt/ccs.git

# Or from a local clone
uv tool install /path/to/ccs

# Or from the current directory
cd ccs
uv tool install .
```

#### From PyPI (if published)

```bash
uv tool install ccs
```

## Usage

### Development Mode

Run commands using `uv run`:

```bash
# Show database info and statistics
uv run ccs info

# List all conversations
uv run ccs list

# List with options
uv run ccs list --limit 10
uv run ccs list --all  # Include archived

# Time filtering - relative times (abbreviated)
uv run ccs list --since "15m"
uv run ccs list --since "3d"
uv run ccs list --since "4h"

# Time filtering - absolute dates
uv run ccs list --since "2026-01-01"
uv run ccs list --before "2026-01-01"
uv run ccs list --since "2025-12-01" --before "2026-01-01"

# Show a conversation by title (fuzzy matching)
uv run ccs show "application lister"

# Show with time filter (helps with disambiguation)
uv run ccs show "folder" --since "3d"

# Or by partial ID
uv run ccs show e39aa420

# Show as JSON
uv run ccs show "python script" --format json

# Export to markdown by title
uv run ccs export "home directory" --format markdown --output chat.md

# Export with time filter
uv run ccs export "folder" --since "1w" --format markdown

# Export by ID
uv run ccs export e39aa420 --format json

# Search conversations (searches titles, content, and messages)
uv run ccs search "folder"

# Search with time filtering
uv run ccs search "folder" --since "3d"
uv run ccs search "python" --since "2026-01-01"
```

### Installed as Tool

Once installed via `uv tool install`, use directly:

```bash
ccs list
ccs show <conversation-id>
ccs export <conversation-id> --format markdown
ccs search "query"
```

## Next Steps

Potential improvements:
1. Handle and display rich text formatting properly
2. Extract and display code blocks in a readable format
3. Support exporting to HTML format
4. Add filtering options (by date, status, model)
5. Add conversation deletion/archiving capabilities
6. Support multiple Cursor profiles
7. Add conversation statistics and analytics
