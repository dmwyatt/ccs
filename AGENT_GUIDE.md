# Agent Guide: Using CCS (Cursor Conversation Search)

## Overview

`ccs` is a CLI tool for searching Cursor agent conversations stored locally in SQLite. Use it to reference past conversations, find previous solutions, or help users locate specific discussions.

**Installation:** If `ccs` is not available:
```bash
uv tool install git+https://github.com/dmwyatt/ccs.git
```

**For command syntax:** Run `ccs --help` or `ccs <command> --help`

## When to Proactively Use CCS

**Trigger on these user phrases:**
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

## Core Workflow

```
Search → Identify → Show → Summarize → Offer Export
```

**Example:**
```bash
# 1. Search with time filter
ccs search "authentication" --since "3d"

# 2. Review results, get ID or title

# 3. Show specific conversation
ccs show a1b2c3d4

# 4. Summarize key points for user (don't dump raw output)

# 5. Offer export if valuable
ccs export "oauth setup" --format markdown --output notes.md
```

**Key principle:** Always filter. Always summarize.

## Time Filtering

Match user time references:
- "today" / "earlier" → `--since "1d"`
- "yesterday" → `--since "2d"`
- "recently" / ambiguous → `--since "3d"` (default)
- "this week" → `--since "1w"`

**Strategy:** Start narrow, widen if no results.

Run `ccs list --help` for all time format options.

## Presenting Results

**✅ DO:**
- **Summarize first:** "I found 3 auth conversations from last week. Most recent: 'OAuth setup' (2 days ago). Want to see it?"
- **Extract key info:** Pull out code snippets, decisions, solutions
- **Confirm before dumping:** Ask before showing full conversation
- **Offer export:** For long/valuable discussions

**❌ DON'T:**
- Dump full conversation output without warning
- Show all matches when many exist (summarize instead)
- Search without time filters
- Assume user remembers exact titles

## Handling Edge Cases

**Multiple matches:**
- Add more specific terms: `ccs show "database migration script"` not `"database"`
- Narrow time: `ccs show "config" --since "2d"`
- Ask user which one they mean

**No results:**
- Widen time window: `--since "1w"` → `--since "1mo"`
- Try different keywords
- Try `search` instead of `show` (searches content vs titles)

**Disambiguation:**
- Present options clearly to user
- Offer to show most recent
- Use time filter or more specific query

## Best Practices

**Be proactive:** Offer to search when user mentions past work

**Context-aware filtering:**
- User says "yesterday" → use exact filter
- User says "recently" → default to `--since "3d"`
- Unsure → start with `--since "1w"`

**Respect attention:**
- Summarize, don't dump
- Extract relevant parts only
- Offer export for long conversations

**Chain efficiently:**
```bash
# Good: search → show specific
ccs search "api" --since "3d"
ccs show a1b2c3d4

# Avoid: guessing titles
ccs show "api"  # might match many
```

## Remember

1. **Always use time filters** - Narrow results
2. **Summarize for users** - Don't dump raw output
3. **Be proactive** - Offer CCS when you hear trigger phrases
4. **Follow the workflow** - Search → Identify → Show → Summarize
