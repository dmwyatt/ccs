# Agent Guide: Using CCS (Cursor Conversation Search)

## Overview

`ccs` is a CLI tool for searching Cursor agent conversations stored locally in SQLite. Use it to reference past conversations, find previous solutions, or help users locate specific discussions.

**Installation:** If `ccs` is not available, install with:
```bash
uv tool install git+https://github.com/dmwyatt/ccs.git
```

**For command syntax:** Run `ccs --help` or `ccs <command> --help`

## When to Proactively Use CCS

Trigger on these user phrases:
- "What did we discuss about X?"
- "I think we solved this before"
- "What was I working on [yesterday/this week]?"
- "Didn't we already do this?"
- "Can you find that conversation about X?"
- User seems stuck on a problem you may have solved before

**Don't use when:**
- User is asking about the current conversation
- Question is about code execution results (CCS only has conversation text)
- User is asking about Cursor features (not past work)

## Core Workflow Pattern

```
1. Search → 2. Identify → 3. Show → 4. Summarize → 5. Offer Export
```

### Example Flow
```bash
# Step 1: Broad search with time filter
ccs search "authentication" --since "3d"

# Step 2: Review results, identify conversation ID or title

# Step 3: Show specific conversation
ccs show a1b2c3d4  # or: ccs show "oauth setup"

# Step 4: Summarize key points for user (don't dump raw output)

# Step 5: Offer export if discussion was valuable
ccs export "oauth setup" --format markdown --output auth-notes.md
```

**Key principle:** Always filter, always summarize.

## Time Filtering Strategy

Match user's time references to filters:
- "today" / "earlier" → `--since "1d"`
- "yesterday" → `--since "2d"`
- "recently" / ambiguous → `--since "3d"` (good default)
- "this week" → `--since "1w"`
- "last week" → `--since "2w"`

**Strategy:** Start narrow, widen if no results. Better to get few matches than thousands.

Run `ccs list --help` for all time format options (hours, days, weeks, months).

## Commands Quick Reference

```bash
# List recent conversations (metadata only - fast)
ccs list --since "3d" --limit 10

# Search conversation content (slower but thorough)
ccs search "keyword" --since "1w"

# Show specific conversation
ccs show "partial title match"
ccs show a1b2c3d4  # by ID

# Export conversation
ccs export "title" --format markdown --output file.md
```

Run `ccs <command> --help` for full options and syntax.

## Presenting Results to Users

### ✅ DO

**Summarize first:**
```
I found 3 conversations about authentication from last week:
1. "OAuth setup" - 2 days ago
2. "JWT implementation" - 4 days ago
3. "Auth middleware" - 6 days ago

The most recent covers OAuth integration with Google. Want me to show it?
```

**Extract key information:**
- Pull out code snippets that solved the problem
- Highlight decisions made
- Reference specific solutions

**Confirm before dumping:**
- Ask if user wants full conversation
- Offer to export instead of displaying in terminal

### ❌ DON'T

- Dump full conversation output without warning
- Show all matches when there are many (summarize instead)
- Assume user remembers conversation titles
- Search without time filters (too many results)

## Handling Common Scenarios

### Multiple Matches
```bash
# Add more specific terms
ccs show "database migration script"  # not just "database"

# Or narrow time window
ccs show "config" --since "2d"

# Or ask user which one they mean
```

### No Results Found
1. Try broader time window: `--since "1w"` → `--since "1mo"`
2. Try different keywords: "auth" → "authentication" / "login"
3. Try search instead of show (content vs title matching)
4. Confirm with user if timeline is correct

### Disambiguation
When you see "Multiple conversations match...":
- Present options to user clearly
- Offer to show the most recent one
- Use time filter or more specific query

## Integration Best Practices

**Be proactive:**
- Offer to search when user mentions past work
- Suggest export for valuable discussions
- Check recent work when user seems to be repeating tasks

**Context-aware filtering:**
- User says "yesterday" → use exact time filters
- User says "recently" → default to 3d
- User unsure → start with 1w

**Respect user attention:**
- Summarize instead of dumping
- Extract relevant parts only
- Offer export for long conversations

**Chain commands efficiently:**
```bash
# Good: search → review → show specific
ccs search "api" --since "3d"
ccs show a1b2c3d4

# Less efficient: show by guess
ccs show "api"  # might get "Multiple matches..."
```

## Workflow Examples

### "What did we do with X?"
```bash
ccs search "keyword" --since "3d"
# Review results
ccs show <id>
# Summarize key points for user
```

### "What was I working on recently?"
```bash
ccs list --since "1w" --limit 10
# Present conversation titles and times
# Offer to show details of any specific one
```

### "Save our discussion about X"
```bash
ccs show "topic" --since "1d"
# Confirm it's the right one
ccs export "topic" --since "1d" --format markdown --output notes.md
```

## Quick Troubleshooting

- **"No conversations found"** → Widen time filter or try different keywords
- **"Multiple conversations match"** → Add time filter or more specific terms
- **"Conversation not found"** → Try search instead of show, verify query
- **Database errors** → User may need to close Cursor (DB locked)

## Output Formats

- **Default (text)** - Human-readable, good for agent review
- **JSON** (`--format json`) - For programmatic parsing
- **Markdown** (`--format markdown`) - For export/documentation only

## Remember

1. **Let --help be your syntax reference** - Run it when you need details
2. **Focus on workflows** - Search → Identify → Show → Summarize
3. **Always use time filters** - Narrow results for better matches
4. **Summarize for users** - Don't dump raw output
5. **Be proactive** - Offer CCS when you hear trigger phrases

## Command Help

```bash
ccs --help              # Main help
ccs list --help         # List command options
ccs search --help       # Search command options
ccs show --help         # Show command options
ccs export --help       # Export command options
```
