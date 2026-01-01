# Agent Guide: Using CCS (Cursor Conversation Search)

## Overview

`ccs` is a CLI tool for searching local Cursor agent conversations. Use it to reference past conversations, find previous solutions, or help users locate specific discussions.

**Installation:** If `ccs` is not available:
```bash
uv tool install git+https://github.com/dmwyatt/ccs.git
```

**For command syntax:** Run `ccs --help` or `ccs <command> --help`

## When CCS Is Useful

CCS helps when users want to reference past conversations. Examples:
- User is looking for a solution you discussed before
- User wants to review what they worked on recently
- User wants to find a specific discussion to export or share
- User seems stuck on a problem you may have already solved together

CCS won't help when:
- User is asking about the current conversation
- User wants code execution results (CCS only searches conversation text)
- User is asking about Cursor features rather than past work

## Example Workflow

Here's one way you might use CCS:

```bash
# Search for relevant conversations
ccs search "authentication" --since "3d"

# Review results, identify a specific conversation

# Show it to understand the content
ccs show a1b2c3d4

# Summarize key points for the user

# If valuable, offer to export
ccs export "oauth setup" --format markdown --output notes.md
```

## Time Filtering

Time filters help narrow results. Map user time references:
- "today" / "earlier" → `--since "1d"`
- "yesterday" → `--since "2d"`
- "recently" / ambiguous → `--since "3d"` is often useful
- "this week" → `--since "1w"`

Starting narrow and widening if needed typically works well.

Run `ccs list --help` for all time format options.

## Presenting Results to Users

**Consider these patterns:**
- **Summarize before showing full output:** "I found 3 auth conversations from last week. Most recent: 'OAuth setup' (2 days ago). Want to see it?"
- **Extract relevant information:** Pull out code snippets, decisions, solutions rather than dumping entire conversations
- **Confirm before showing large outputs:** Ask before displaying full conversations
- **Offer export for valuable discussions:** Markdown export can be useful for documentation

**Avoid:**
- Dumping full conversation output without context or warning
- Searching without time filters when you have time context
- Assuming user remembers exact conversation titles

## Handling Edge Cases

**Multiple matches:**
You can add more specific terms, narrow the time window, or ask the user which conversation they mean.

**No results:**
Try widening the time window, different keywords, or using `search` instead of `show` (searches content vs titles).

**Disambiguation:**
When the tool shows multiple matches, present the options clearly to the user and help them identify which one they want.

## Key Principles

- **Be proactive:** Offer to search when user mentions past work
- **Use time context:** If user mentions "yesterday" or "last week," use those filters
- **Summarize, don't dump:** Extract and present relevant information
- **Respect user attention:** Not every conversation needs to be shown in full
