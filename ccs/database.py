"""Database interface for reading Cursor conversations."""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from .datetime_utils import filter_by_time_range


def parse_search_query(query: str) -> List[str]:
    """Parse a search query into individual terms.

    Supports:
    - Quoted phrases: "exact phrase" stays together
    - Individual keywords: unquoted words are split on whitespace

    Args:
        query: The search query string.

    Returns:
        List of search terms (phrases and/or keywords).

    Examples:
        >>> parse_search_query('refactor tests user')
        ['refactor', 'tests', 'user']
        >>> parse_search_query('"exact phrase" keyword')
        ['exact phrase', 'keyword']
        >>> parse_search_query('"hello world" foo "bar baz"')
        ['hello world', 'foo', 'bar baz']
    """
    terms = []
    # Match quoted strings or non-whitespace sequences
    pattern = r'"([^"]+)"|(\S+)'
    for match in re.finditer(pattern, query):
        # Group 1 is quoted content (without quotes), group 2 is unquoted word
        term = match.group(1) if match.group(1) is not None else match.group(2)
        if term:  # Skip empty strings
            terms.append(term)
    return terms


def get_cursor_db_path() -> Path:
    """Get the path to Cursor's global state database.

    Returns the platform-specific path:
        - Linux: ~/.config/Cursor/User/globalStorage/state.vscdb
        - macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
        - Windows: %APPDATA%/Cursor/User/globalStorage/state.vscdb
    """
    if sys.platform == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    elif sys.platform == "win32":  # Windows
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
        # Fallback if APPDATA not set
        return Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    else:  # Linux and other Unix-like
        return Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"


class CursorDatabase:
    """Interface to Cursor's conversation database."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection.

        Args:
            db_path: Path to the database file. If None, uses default location.
        """
        self.db_path = db_path or get_cursor_db_path()
        if not self.db_path.exists():
            raise FileNotFoundError(f"Cursor database not found at {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        """Create a read-only database connection."""
        return sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)

    def list_conversations(
        self, since: Optional[str] = None, before: Optional[str] = None, include_empty: bool = False
    ) -> List[Dict[str, Any]]:
        """List all conversations (composers) in the database.

        Args:
            since: Filter conversations created since this time (e.g., "3 days", "2024-01-01")
            before: Filter conversations created before this time
            include_empty: Include empty conversations (status="none" with 0 messages). Default: False

        Returns:
            List of conversation dictionaries with metadata.
        """
        conn = self._connect()
        cursor = conn.cursor()

        # Count non-empty messages per conversation:
        # - Messages with non-empty text, OR
        # - Messages that have associated code blocks
        # Uses json_tree to efficiently find bubbleId values in nested codeBlockData
        join_type = "LEFT JOIN" if include_empty else "JOIN"
        cursor.execute(f'''
            WITH
            messages AS (
                SELECT
                    SUBSTR(key, 10, INSTR(SUBSTR(key, 10), ':') - 1) as composer_id,
                    json_extract(value, '$.bubbleId') as bubble_id,
                    CASE WHEN TRIM(COALESCE(json_extract(value, '$.text'), '')) != ''
                         THEN 1 ELSE 0 END as has_text
                FROM cursorDiskKV
                WHERE key LIKE 'bubbleId:%'
            ),
            code_block_bubbles AS (
                SELECT DISTINCT
                    SUBSTR(c.key, 14) as composer_id,
                    jt.value as bubble_id
                FROM cursorDiskKV c,
                    json_tree(c.value, '$.codeBlockData') as jt
                WHERE c.key LIKE 'composerData:%'
                  AND jt.key = 'bubbleId'
            ),
            non_empty_counts AS (
                SELECT
                    m.composer_id,
                    COUNT(*) as msg_count
                FROM messages m
                LEFT JOIN code_block_bubbles cb
                    ON m.composer_id = cb.composer_id AND m.bubble_id = cb.bubble_id
                WHERE m.has_text = 1 OR cb.bubble_id IS NOT NULL
                GROUP BY m.composer_id
            )
            SELECT c.key, c.value, COALESCE(n.msg_count, 0) as msg_count
            FROM cursorDiskKV c
            {join_type} non_empty_counts n ON SUBSTR(c.key, 14) = n.composer_id
            WHERE c.key LIKE 'composerData:%' AND c.value IS NOT NULL
        ''')

        conversations = []
        for row in cursor.fetchall():
            data = json.loads(row[1])
            composer_id = data.get('composerId', row[0].split(':')[1])
            created_at = data.get('createdAt', 0)
            msg_count = row[2]

            conversations.append({
                'id': composer_id,
                'title': data.get('name', '(no title)'),
                'subtitle': data.get('subtitle', ''),
                'created': datetime.fromtimestamp(created_at / 1000) if created_at else None,
                'message_count': msg_count,
                'status': data.get('status', 'unknown'),
                'preview': data.get('text', '')[:100],
                'model': data.get('modelConfig', {}).get('modelName', 'unknown'),
                'is_archived': data.get('isArchived', False),
                'total_lines_added': data.get('totalLinesAdded', 0),
                'total_lines_removed': data.get('totalLinesRemoved', 0),
            })

        conn.close()

        # Apply time filtering if requested
        if since or before:
            conversations = filter_by_time_range(conversations, since=since, before=before)

        return sorted(
            conversations, key=lambda x: x['created'] if x['created'] else datetime.min, reverse=True
        )

    def get_conversation(self, composer_id: str) -> Dict[str, Any]:
        """Get metadata for a specific conversation.

        Args:
            composer_id: The conversation ID.

        Returns:
            Dictionary with conversation metadata.
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(f'SELECT value FROM cursorDiskKV WHERE key = "composerData:{composer_id}"')
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ValueError(f"Conversation {composer_id} not found")

        data = json.loads(row[0])
        conn.close()
        return data

    def get_messages(self, composer_id: str) -> List[Dict[str, Any]]:
        """Get all messages (bubbles) for a specific conversation.

        Args:
            composer_id: The conversation ID.

        Returns:
            List of message dictionaries sorted by creation time.
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            f'SELECT key, value FROM cursorDiskKV WHERE key LIKE "bubbleId:{composer_id}:%"'
        )

        messages = []
        for row in cursor.fetchall():
            data = json.loads(row[1])
            # Extract per-message model info if available
            model_info = data.get('modelInfo', {})
            model_name = model_info.get('modelName') if model_info else None

            # Extract thinking data (extended thinking / reasoning traces)
            thinking_data = data.get('thinking')
            thinking_text = None
            if thinking_data and isinstance(thinking_data, dict):
                thinking_text = thinking_data.get('text')

            # Extract tool call data (toolFormerData contains actual tool invocations)
            tool_former_data = data.get('toolFormerData')

            messages.append({
                'id': data.get('bubbleId'),
                'type': 'user' if data.get('type') == 1 else 'assistant',
                'created': data.get('createdAt'),
                'text': data.get('text', ''),
                'rich_text': data.get('richText', ''),
                'model': model_name,  # Per-message model (None, "default", or specific model name)
                # Thinking / reasoning traces
                'thinking': thinking_text,
                'thinking_duration_ms': data.get('thinkingDurationMs'),
                # Tool calls (actual tool invocations, not just results)
                'tool_call': tool_former_data,
                # Additional context
                'tool_results': data.get('toolResults', []),
                'suggested_code_blocks': data.get('suggestedCodeBlocks', []),
                'images': data.get('images', []),
                'capabilities': data.get('capabilities', []),
                'context': data.get('context', {}),
            })

        conn.close()

        # Sort by creation time
        return sorted(messages, key=lambda x: x['created'] if x['created'] else '')

    def search_conversations(
        self, query: str, since: Optional[str] = None, before: Optional[str] = None,
        include_empty: bool = False, search_diffs: bool = False
    ) -> List[Dict[str, Any]]:
        """Search conversations by text content.

        Search supports multiple keywords and quoted phrases:
        - Multiple words are treated as separate keywords (AND logic)
        - All keywords must appear somewhere in the conversation
        - Use quotes for exact phrase matching: "exact phrase"

        Examples:
            "refactor tests" - finds conversations containing both "refactor" AND "tests"
            '"user auth" login' - finds conversations with exact phrase "user auth" AND "login"

        Args:
            query: Search query string (keywords and/or quoted phrases).
            since: Filter conversations created since this time
            before: Filter conversations created before this time
            include_empty: Include empty conversations. Default: False
            search_diffs: Also search in code diffs (file paths and diff content). Default: False

        Returns:
            List of matching conversations.
        """
        terms = parse_search_query(query)
        if not terms:
            return []

        conn = self._connect()
        cursor = conn.cursor()

        # Find IDs matching each term, then intersect
        matching_ids: Optional[set] = None
        for term in terms:
            term_ids = self._find_ids_for_term(cursor, term, search_diffs)
            if matching_ids is None:
                matching_ids = term_ids
            else:
                matching_ids &= term_ids
            # Early exit if no matches
            if not matching_ids:
                conn.close()
                return []

        conn.close()

        # Get full conversation data for matching IDs and apply filters
        all_conversations = self.list_conversations(since=since, before=before, include_empty=include_empty)
        results = [conv for conv in all_conversations if conv['id'] in matching_ids]

        return results

    def _find_ids_for_term(
        self, cursor: sqlite3.Cursor, term: str, search_diffs: bool
    ) -> set:
        """Find conversation IDs matching a single search term.

        Args:
            cursor: Database cursor.
            term: Single search term (keyword or phrase).
            search_diffs: Also search in code diffs.

        Returns:
            Set of composer IDs matching the term.
        """
        # Escape % and _ for LIKE pattern, then wrap with %
        term_escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        like_pattern = f'%{term_escaped}%'

        # Find matching composer IDs using SQL with JSON operators
        # Search in metadata: title (name), subtitle, and preview (text)
        cursor.execute('''
            SELECT DISTINCT SUBSTR(key, 14) as composer_id
            FROM cursorDiskKV
            WHERE key LIKE 'composerData:%'
              AND (
                LOWER(value ->> '$.name') LIKE LOWER(?) ESCAPE '\\'
                OR LOWER(value ->> '$.subtitle') LIKE LOWER(?) ESCAPE '\\'
                OR LOWER(value ->> '$.text') LIKE LOWER(?) ESCAPE '\\'
              )
        ''', (like_pattern, like_pattern, like_pattern))
        matching_ids = {row[0] for row in cursor.fetchall()}

        # Search in message text
        cursor.execute('''
            SELECT DISTINCT SUBSTR(key, 10, INSTR(SUBSTR(key, 10), ':') - 1) as composer_id
            FROM cursorDiskKV
            WHERE key LIKE 'bubbleId:%'
              AND LOWER(value ->> '$.text') LIKE LOWER(?) ESCAPE '\\'
        ''', (like_pattern,))
        matching_ids.update(row[0] for row in cursor.fetchall())

        # Search in code diffs if enabled
        if search_diffs:
            matching_ids.update(self._search_code_diffs_sql(cursor, like_pattern))

        return matching_ids

    def _search_code_diffs_sql(self, cursor: sqlite3.Cursor, like_pattern: str) -> set:
        """Search code diffs using SQL.

        Args:
            cursor: Database cursor.
            like_pattern: LIKE pattern with wildcards (e.g., '%query%').

        Returns:
            Set of composer IDs that have matching diffs.
        """
        matching_ids = set()

        # Search in codeBlockData file paths (keys of the codeBlockData object)
        # Using json_each to iterate over the keys
        cursor.execute('''
            SELECT DISTINCT SUBSTR(kv.key, 14) as composer_id
            FROM cursorDiskKV kv, json_each(kv.value ->> '$.codeBlockData') as cbd
            WHERE kv.key LIKE 'composerData:%'
              AND kv.value ->> '$.codeBlockData' IS NOT NULL
              AND LOWER(cbd.key) LIKE LOWER(?) ESCAPE '\\'
        ''', (like_pattern,))
        matching_ids.update(row[0] for row in cursor.fetchall())

        # Search in codeBlockDiff entries (originalText, modifiedText, and diff content)
        # Extract composer_id from key pattern: codeBlockDiff:{composer_id}:{diff_id}
        cursor.execute('''
            SELECT DISTINCT SUBSTR(key, 15, INSTR(SUBSTR(key, 15), ':') - 1) as composer_id
            FROM cursorDiskKV
            WHERE key LIKE 'codeBlockDiff:%'
              AND (
                LOWER(value ->> '$.originalText') LIKE LOWER(?) ESCAPE '\\'
                OR LOWER(value ->> '$.modifiedText') LIKE LOWER(?) ESCAPE '\\'
                OR LOWER(value) LIKE LOWER(?) ESCAPE '\\'
              )
        ''', (like_pattern, like_pattern, like_pattern))
        matching_ids.update(row[0] for row in cursor.fetchall())

        return matching_ids

    def find_by_title(self, title_query: str, include_empty: bool = False) -> List[Dict[str, Any]]:
        """Find conversations by title or subtitle.

        Args:
            title_query: Search string for title matching.
            include_empty: Include empty conversations. Default: False

        Returns:
            List of conversations with matching titles.
        """
        all_conversations = self.list_conversations(include_empty=include_empty)
        query_lower = title_query.lower()

        return [
            conv
            for conv in all_conversations
            if query_lower in conv['title'].lower() or query_lower in conv['subtitle'].lower()
        ]

    def get_code_block_diff(self, composer_id: str, diff_id: str) -> Optional[Dict[str, Any]]:
        """Get the code block diff data for a specific diff ID.

        Args:
            composer_id: The conversation/composer ID.
            diff_id: The diff ID to fetch.

        Returns:
            Dictionary with diff data, or None if not found.
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(f'SELECT value FROM cursorDiskKV WHERE key = "codeBlockDiff:{composer_id}:{diff_id}"')
        row = cursor.fetchone()

        conn.close()

        if not row:
            return None

        return json.loads(row[0])
