"""Database interface for reading Cursor conversations."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from .datetime_utils import filter_by_time_range


def get_cursor_db_path() -> Path:
    """Get the path to Cursor's global state database."""
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

        cursor.execute('SELECT key, value FROM cursorDiskKV WHERE key LIKE "composerData:%"')

        conversations = []
        for row in cursor.fetchall():
            data = json.loads(row[1])
            composer_id = data.get('composerId', row[0].split(':')[1])
            created_at = data.get('createdAt', 0)

            # Count messages for this conversation
            cursor.execute(
                f'SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE "bubbleId:{composer_id}:%"'
            )
            msg_count = cursor.fetchone()[0]

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

        # Filter out empty conversations by default (status="none" with 0 messages)
        if not include_empty:
            conversations = [c for c in conversations if c['message_count'] > 0]

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
            messages.append({
                'id': data.get('bubbleId'),
                'type': 'user' if data.get('type') == 1 else 'assistant',
                'created': data.get('createdAt'),
                'text': data.get('text', ''),
                'rich_text': data.get('richText', ''),
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
        self, query: str, since: Optional[str] = None, before: Optional[str] = None, include_empty: bool = False
    ) -> List[Dict[str, Any]]:
        """Search conversations by text content.

        Args:
            query: Search query string.
            since: Filter conversations created since this time
            before: Filter conversations created before this time
            include_empty: Include empty conversations. Default: False

        Returns:
            List of matching conversations.
        """
        all_conversations = self.list_conversations(since=since, before=before, include_empty=include_empty)
        query_lower = query.lower()

        results = []
        for conv in all_conversations:
            # Search in title and subtitle first
            if query_lower in conv['title'].lower() or query_lower in conv['subtitle'].lower():
                results.append(conv)
                continue

            # Search in preview text
            if query_lower in conv['preview'].lower():
                results.append(conv)
                continue

            # Search in full messages
            messages = self.get_messages(conv['id'])
            for msg in messages:
                if query_lower in msg['text'].lower():
                    results.append(conv)
                    break

        return results

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
