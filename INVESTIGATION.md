# Cursor Conversation Storage Investigation

## Summary

This document summarizes the investigation into how Cursor stores agent conversations locally.

## Key Findings

### Primary Storage Location

**Database Path:** `~/.config/Cursor/User/globalStorage/state.vscdb`

This is the main SQLite database where all conversation data is stored.

### Database Schema

The database uses a simple key-value store pattern with the `cursorDiskKV` table:

```
Table: cursorDiskKV
  - key (TEXT)
  - value (BLOB) - JSON string data
```

### Data Organization

#### 1. Conversation Threads (Composers)

**Key Pattern:** `composerData:<composerId>`

Each conversation (called a "composer") is stored with comprehensive metadata:

```json
{
  "composerId": "uuid",
  "status": "completed|none|...",
  "createdAt": 1234567890000,
  "modelConfig": {
    "modelName": "default",
    "maxMode": false
  },
  "text": "Initial prompt or current state",
  "context": { /* workspace and environment context */ },
  "capabilities": [ /* available features */ ],
  "totalLinesAdded": 0,
  "totalLinesRemoved": 0,
  "isArchived": false,
  // ... many more fields
}
```

**Key Fields:**
- `composerId` - Unique identifier for the conversation
- `status` - Conversation state (completed, none, etc.)
- `createdAt` - Timestamp in milliseconds
- `modelConfig` - AI model configuration
- `totalLinesAdded/Removed` - Code change statistics
- `isArchived` - Archival status

#### 2. Individual Messages (Bubbles)

**Key Pattern:** `bubbleId:<composerId>:<bubbleId>`

Each message in a conversation is stored separately:

```json
{
  "bubbleId": "message-uuid",
  "type": 1,  // 1 = user, 2 = assistant
  "text": "Message text content",
  "richText": "{ /* Lexical editor state */ }",
  "createdAt": "2026-01-01T15:45:07.662Z",
  "toolResults": [],
  "suggestedCodeBlocks": [],
  "images": [],
  "capabilities": [],
  "context": {},
  // ... additional metadata
}
```

**Key Fields:**
- `bubbleId` - Unique message identifier
- `type` - Message type (1 = user, 2 = assistant)
- `text` - Plain text content
- `richText` - Formatted text (Lexical editor format)
- `createdAt` - ISO timestamp
- `toolResults` - Results from tool executions
- `suggestedCodeBlocks` - Code suggestions in the message

#### 3. Other Data Types

Additional key patterns found but not fully explored:

- **`checkpointId:*`** - Conversation checkpoints/snapshots
- **`codeBlockDiff:*`** - Code change diffs
- **`messageRequestContext:*`** - Context for API requests
- **`inlineDiffs-<workspaceId>`** - Per-workspace inline diffs

### Relationship Model

```
composerData:abc123
  └─ bubbleId:abc123:msg001 (user message)
  └─ bubbleId:abc123:msg002 (assistant message)
  └─ bubbleId:abc123:msg003 (assistant message)
  └─ bubbleId:abc123:msg004 (user message)
  └─ ...
```

Each composer has multiple bubbles linked by the composer ID.

## Additional Storage Locations

### AI Code Tracking Database

**Path:** `~/.cursor/ai-tracking/ai-code-tracking.db`

Tracks AI-generated code changes with these tables:
- `ai_code_hashes` - Hashes of AI-generated code
- `scored_commits` - Commits scored by AI
- `tracking_state` - State tracking

### Per-Project Data

**Path:** `~/.cursor/projects/<encoded-project-path>/`

Contains:
- `rules/` - Project-specific rules and configurations

### Workspace Storage

**Path:** `~/.config/Cursor/User/workspaceStorage/<workspace-id>/state.vscdb`

Per-workspace state databases with similar structure to global storage.

## Data Access Patterns

### Reading Conversations

1. Query `composerData:*` keys to list all conversations
2. Parse JSON value to get metadata
3. Use `composerId` to query `bubbleId:<composerId>:*` for messages
4. Sort messages by `createdAt` timestamp

### Searching

- Extract and search through `text` field in both composers and bubbles
- Can also search through metadata fields like status, model, etc.

### Statistics

Aggregate data from composer metadata:
- Count of conversations
- Total messages across all conversations
- Code change statistics (lines added/removed)
- Conversation creation trends

## Implementation

A working CLI has been implemented in this repository demonstrating:
- Database connection and querying
- Conversation listing with rich formatting
- Individual conversation viewing
- Export to multiple formats (Markdown, JSON, Text)
- Search functionality
- Statistics and info display

See the main README for usage instructions.

## Platform Compatibility

**Current Implementation:** Linux (tested on Ubuntu)

**Other Platforms:**

- **macOS:** Database likely at `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- **Windows:** Database likely at `%APPDATA%\Cursor\User\globalStorage\state.vscdb`

The CLI would need minor modifications to support multiple platforms (updating the default path detection).

## Observations

1. **Rich Storage:** Cursor stores extensive metadata beyond just messages
2. **Structured Format:** Well-organized key-value pattern makes querying straightforward
3. **SQLite:** Standard SQLite format makes it easy to query with any SQLite client
4. **JSON Values:** All data stored as JSON makes parsing flexible and extensible
5. **No Encryption:** Database appears to be unencrypted plain SQLite
6. **Comprehensive Context:** Stores full context including tool results, code blocks, images, etc.

## Potential Use Cases

- **Conversation Export:** Export chats for documentation or sharing
- **Search History:** Find past conversations about specific topics
- **Code Review:** Review AI-suggested code changes
- **Analytics:** Analyze AI usage patterns and productivity
- **Backup:** Create backups of important conversations
- **Migration:** Move conversations between machines or profiles
