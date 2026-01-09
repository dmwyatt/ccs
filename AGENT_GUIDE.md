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

## Output Format

CCS supports two output formats via `--format`:
- `rich` (default): Terminal-styled output with colors and formatting for human viewing
- `markdown`: Clean markdown output optimized for agent consumption

**Always use `--format markdown` when processing output programmatically.** The rich format includes ANSI escape codes that waste tokens and add noise. Markdown output is clean, structured, and easy to parse.

```bash
# For your own processing
ccs search "authentication" --since "3d" --format markdown
ccs show a1b2c3d4 --format markdown

# When showing output directly to users in a terminal, rich (default) is fine
ccs list --since "1w"
```

## Example Workflow

Here's one way you might use CCS:

```bash
# Search for relevant conversations (markdown for parsing)
ccs search "authentication" --since "3d" --format markdown

# Review results, identify a specific conversation

# Show it to understand the content
ccs show a1b2c3d4 --format markdown

# Summarize key points for the user

# If valuable, offer to export
ccs export "oauth setup" --format markdown --output notes.md
```

## Search Syntax

The `search` command uses keyword-based matching with AND logic:

- **Multiple words** are treated as separate keywords—all must appear somewhere in the conversation
- **Quoted phrases** match exactly: `"user authentication"` finds that exact phrase
- **Mixing both** works: `"error handling" refactor` finds conversations with the exact phrase "error handling" AND the word "refactor"

```bash
# Find conversations mentioning both "refactor" and "tests"
ccs search "refactor tests" --format markdown

# Find exact phrase "user auth" plus keyword "login"
ccs search '"user auth" login' --format markdown

# Single keyword still works
ccs search "authentication" --format markdown
```

**Pagination:** Both `list` and `search` return 20 results per page by default. Output includes total count and page info:
```
Showing 1-20 of 87 results (page 1/5)
```

Use `--page` (or `-p`) to navigate and `--per-page` (or `-n`) to adjust page size:
```bash
ccs search "auth" --page 2 --format markdown        # Get page 2
ccs search "auth" -n 50 --format markdown           # 50 results per page
```

**Archived conversations** are excluded by default. Use `--all` to include them.

Search is case-insensitive. Keywords/phrases can appear anywhere in the conversation (title, messages, or code diffs with `--search-diffs`).

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

## Statistics

Use `ccs stats` to analyze conversation patterns:

```bash
# Overall statistics
ccs stats --format markdown

# Stats for a specific time period
ccs stats --since 4w --format markdown

# Weekly breakdown
ccs stats --by-week --format markdown

# More weeks
ccs stats --by-week --weeks 8 --format markdown
```

Stats output includes:
- Count, mean, median, P25/P75/P90, range
- Distribution buckets (1-5, 6-15, 16-30, 31-50, 51-100, 100+ messages)
- Top 5 largest conversations (overall mode only)
- Weekly breakdown with distribution (--by-week mode)

## Key Principles

- **Be proactive:** Offer to search when user mentions past work
- **Use time context:** If user mentions "yesterday" or "last week," use those filters
- **Summarize, don't dump:** Extract and present relevant information
- **Respect user attention:** Not every conversation needs to be shown in full
