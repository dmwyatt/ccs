"""Utility functions for CCS CLI."""

from pathlib import Path
from typing import Dict, Any, List


def get_code_blocks_for_message(bubble_id: str, code_block_data: dict) -> List[Dict[str, Any]]:
    """Extract code blocks associated with a specific message bubble.

    Args:
        bubble_id: The message bubble ID
        code_block_data: The codeBlockData from the conversation

    Returns:
        List of code block info dictionaries with keys: file, full_path, language, status, diff_id, created_at
    """
    code_blocks = []

    # codeBlockData structure: {file_uri: {codeblock_id: {...data, bubbleId: ...}}}
    for file_uri, blocks in code_block_data.items():
        for block_id, block_data in blocks.items():
            if block_data.get('bubbleId') == bubble_id:
                # Extract file path from URI
                file_path = file_uri.replace('file://', '')
                # Get just the filename
                filename = Path(file_path).name

                code_blocks.append({
                    'file': filename,
                    'full_path': file_path,
                    'language': block_data.get('languageId', 'unknown'),
                    'status': block_data.get('status', 'unknown'),
                    'diff_id': block_data.get('diffId', ''),
                    'created_at': block_data.get('createdAt', ''),
                })

    return code_blocks


def normalize_model_name(model_name: str) -> str:
    """Normalize model names for display.

    Examples:
        "claude-3-5-sonnet" -> "Claude 3 5 Sonnet"
        "gpt-4" -> "GPT-4"
        "cursor" -> "Cursor"

    Args:
        model_name: Raw model name from the database

    Returns:
        Formatted model name for display
    """
    if 'claude' in model_name.lower():
        # Clean up Claude model names: "claude-3-5-sonnet" -> "Claude 3 5 Sonnet"
        return model_name.replace('claude-', 'Claude ').replace('-', ' ').title()
    elif 'gpt' in model_name.lower():
        # Keep GPT names uppercase
        return model_name.upper().replace('-', '-')
    else:
        # Default: title case
        return model_name.title()


def format_timestamp(created: str) -> str:
    """Format ISO timestamp to HH:MM format.

    Args:
        created: ISO format timestamp string (e.g., "2024-01-01T12:34:56.789Z")

    Returns:
        Formatted time string (e.g., "12:34") or fallback on error
    """
    if not created:
        return ''

    try:
        # Try to parse and format the timestamp
        if 'T' in created:
            # Extract time portion and get HH:MM
            timestamp = created.split('T')[1].split('.')[0][:5]  # Get HH:MM
        else:
            # Fallback: take first 5 characters
            timestamp = created[:5] if len(created) >= 5 else created
        return timestamp
    except Exception:
        # Fallback: take first 10 characters
        return created[:10] if len(created) >= 10 else created


def get_model_style(model_name: str | None) -> dict:
    """Get styling information for a model based on its family/provider.

    Args:
        model_name: Model name (can be None for unknown models)

    Returns:
        Dict with 'color' (Rich color string) and 'icon' (Unicode symbol)
    """
    if not model_name:
        return {'color': '#888888', 'icon': '○'}  # Medium gray, visible on dark backgrounds

    name_lower = model_name.lower()

    # Anthropic Claude models
    if 'claude' in name_lower:
        return {'color': '#D97706', 'icon': '◉'}  # Amber/orange

    # OpenAI GPT models
    if 'gpt' in name_lower or 'openai' in name_lower or 'o1' in name_lower or 'o3' in name_lower:
        return {'color': '#10A37F', 'icon': '◆'}  # OpenAI green

    # Google Gemini models
    if 'gemini' in name_lower:
        return {'color': '#4285F4', 'icon': '✦'}  # Google blue

    # Cursor models
    if 'cursor' in name_lower:
        return {'color': 'cyan', 'icon': '▸'}

    # Meta Llama models
    if 'llama' in name_lower:
        return {'color': '#58A6FF', 'icon': '◈'}  # Lighter blue for dark backgrounds

    # Mistral models
    if 'mistral' in name_lower:
        return {'color': '#FF7000', 'icon': '◇'}  # Mistral orange

    # DeepSeek models
    if 'deepseek' in name_lower:
        return {'color': '#6CB6FF', 'icon': '◎'}  # Lighter blue for dark backgrounds

    # Default/unknown
    return {'color': 'blue', 'icon': '●'}


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncating (default: "...")

    Returns:
        Truncated text with suffix, or original text if shorter than max_length
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
