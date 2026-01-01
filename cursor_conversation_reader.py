#!/usr/bin/env python3
"""
Simple script to read Cursor agent conversations from the SQLite database.
This demonstrates the structure for building a full CLI tool.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def get_cursor_db_path() -> Path:
    """Get the path to Cursor's global state database."""
    return Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"


def list_conversations(db_path: Path) -> List[Dict[str, Any]]:
    """List all conversations (composers) in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT key, value FROM cursorDiskKV WHERE key LIKE "composerData:%"')

    conversations = []
    for row in cursor.fetchall():
        data = json.loads(row[1])
        composer_id = data.get('composerId', row[0].split(':')[1])
        created_at = data.get('createdAt', 0)

        # Count messages for this conversation
        cursor.execute(f'SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE "bubbleId:{composer_id}:%"')
        msg_count = cursor.fetchone()[0]

        conversations.append({
            'id': composer_id,
            'created': datetime.fromtimestamp(created_at / 1000) if created_at else None,
            'message_count': msg_count,
            'status': data.get('status', 'unknown'),
            'preview': data.get('text', '')[:100],
            'model': data.get('modelConfig', {}).get('modelName', 'unknown')
        })

    conn.close()
    return sorted(conversations, key=lambda x: x['created'] if x['created'] else datetime.min, reverse=True)


def get_conversation_messages(db_path: Path, composer_id: str) -> List[Dict[str, Any]]:
    """Get all messages (bubbles) for a specific conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f'SELECT key, value FROM cursorDiskKV WHERE key LIKE "bubbleId:{composer_id}:%"')

    messages = []
    for row in cursor.fetchall():
        data = json.loads(row[1])
        messages.append({
            'id': data.get('bubbleId'),
            'type': 'user' if data.get('type') == 1 else 'assistant',
            'created': data.get('createdAt'),
            'text': data.get('text', ''),
            'rich_text': data.get('richText', ''),
            # Additional context that might be useful
            'tool_results': data.get('toolResults', []),
            'code_blocks': data.get('suggestedCodeBlocks', []),
            'images': data.get('images', []),
            'capabilities': data.get('capabilities', []),
        })

    conn.close()

    # Sort by creation time
    return sorted(messages, key=lambda x: x['created'] if x['created'] else '')


def main():
    db_path = get_cursor_db_path()

    if not db_path.exists():
        print(f"Error: Cursor database not found at {db_path}")
        return

    print("=" * 70)
    print("CURSOR AGENT CONVERSATIONS")
    print("=" * 70)

    # List all conversations
    conversations = list_conversations(db_path)
    print(f"\nFound {len(conversations)} conversations\n")

    for i, conv in enumerate(conversations, 1):
        print(f"{i}. {conv['id'][:30]}...")
        print(f"   Created: {conv['created']}")
        print(f"   Messages: {conv['message_count']}")
        print(f"   Status: {conv['status']}")
        print(f"   Model: {conv['model']}")
        if conv['preview']:
            print(f"   Preview: {conv['preview']}")
        print()

    # Show details of the most recent conversation
    if conversations:
        print("=" * 70)
        print("MOST RECENT CONVERSATION DETAILS")
        print("=" * 70)

        recent = conversations[0]
        messages = get_conversation_messages(db_path, recent['id'])

        print(f"\nConversation ID: {recent['id']}")
        print(f"Total messages: {len(messages)}\n")

        for i, msg in enumerate(messages[:10], 1):  # Show first 10 messages
            print(f"{i}. [{msg['type'].upper()}] - {msg['created']}")
            if msg['text']:
                # Truncate long messages
                text = msg['text'][:200]
                if len(msg['text']) > 200:
                    text += "..."
                print(f"   {text}")
            print()


if __name__ == "__main__":
    main()
