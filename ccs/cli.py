"""Command-line interface for ccs (Cursor Conversation Search)."""

import click
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.padding import Padding
from datetime import datetime
from pathlib import Path
import json

from .database import CursorDatabase, get_cursor_db_path


console = Console()


@click.group()
@click.version_option()
def main():
    """Cursor Conversation CLI - Read and export Cursor agent conversations."""
    pass


@main.command()
@click.option('--all', 'show_all', is_flag=True, help='Show all conversations including archived')
@click.option('--include-empty', is_flag=True, help='Include empty conversations (0 messages)')
@click.option('--limit', '-n', type=int, default=20, help='Limit number of results')
@click.option('--since', help='Show conversations since this time. Relative: "3d", "15m", "4h", "1w". Absolute: "2024-01-01"')
@click.option('--before', help='Show conversations before this time (same format as --since)')
def list(show_all: bool, include_empty: bool, limit: int, since: str, before: str):
    """List all conversations."""
    try:
        db = CursorDatabase()
        conversations = db.list_conversations(since=since, before=before, include_empty=include_empty)

        if not show_all:
            conversations = [c for c in conversations if not c['is_archived']]

        if limit:
            conversations = conversations[:limit]

        if not conversations:
            console.print("[yellow]No conversations found.[/yellow]")
            return

        table = Table(title=f"Cursor Conversations ({len(conversations)} found)")
        table.add_column("Title", style="cyan bold", no_wrap=False)
        table.add_column("Subtitle", style="dim", no_wrap=False)
        table.add_column("Created", style="green")
        table.add_column("Msgs", justify="right", style="blue")
        table.add_column("ID", style="dim", no_wrap=True)

        for conv in conversations:
            created = conv['created'].strftime("%Y-%m-%d %H:%M") if conv['created'] else "Unknown"
            title = conv['title'][:50] + "..." if len(conv['title']) > 50 else conv['title']
            subtitle = conv['subtitle'][:30] + "..." if len(conv['subtitle']) > 30 else conv['subtitle']

            table.add_row(
                title,
                subtitle,
                created,
                str(conv['message_count']),
                conv['id'][:12] + "...",
            )

        console.print(table)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(f"[yellow]Database location: {get_cursor_db_path()}[/yellow]")
        raise click.Abort()


def find_conversation(db: CursorDatabase, query: str, since: str = None, before: str = None, include_empty: bool = False) -> tuple:
    """Find a conversation by ID or title, optionally filtered by time.

    Args:
        db: Database instance
        query: Query string (ID or title)
        since: Filter conversations since this time
        before: Filter conversations before this time
        include_empty: Include empty conversations

    Returns:
        tuple: (matching_conv, conversation_id) or (None, None) if not found
    """
    all_convs = db.list_conversations(since=since, before=before, include_empty=include_empty)
    query_lower = query.lower()

    # First try exact ID match
    for conv in all_convs:
        if conv['id'] == query:
            return conv, conv['id']

    # Try partial ID match
    for conv in all_convs:
        if conv['id'].startswith(query) or query in conv['id']:
            return conv, conv['id']

    # Try title/subtitle match
    matches = []
    for conv in all_convs:
        if query_lower in conv['title'].lower() or query_lower in conv['subtitle'].lower():
            matches.append(conv)

    if len(matches) == 1:
        return matches[0], matches[0]['id']
    elif len(matches) > 1:
        console.print(f"[yellow]Multiple conversations match '{query}':[/yellow]")
        for i, conv in enumerate(matches[:5], 1):
            console.print(f"  {i}. {conv['title']} - {conv['id'][:20]}...")
        console.print(f"\n[yellow]Please be more specific[/yellow]")
        return None, None

    return None, None


def get_code_blocks_for_message(bubble_id: str, code_block_data: dict) -> list:
    """Extract code blocks associated with a specific message bubble.

    Args:
        bubble_id: The message bubble ID
        code_block_data: The codeBlockData from the conversation

    Returns:
        List of code block info dictionaries
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


@main.command()
@click.argument('query')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json']), default='text')
@click.option('--include-empty', is_flag=True, help='Include empty conversations (0 messages)')
@click.option('--since', help='Filter to conversations since this time. Relative: "3d", "15m", "4h", "1w". Absolute: "2024-01-01"')
@click.option('--before', help='Filter to conversations before this time (same format as --since)')
@click.option('--show-code-details', is_flag=True, help='Show detailed code block information')
@click.option('--show-code-diff', is_flag=True, help='Show code diffs for code blocks')
@click.option('--show-empty', is_flag=True, help='Show empty assistant messages (streaming artifacts)')
def show(query: str, output_format: str, include_empty: bool, since: str, before: str, show_code_details: bool, show_code_diff: bool, show_empty: bool):
    """Show a specific conversation by ID or title, optionally filtered by time."""
    try:
        db = CursorDatabase()

        matching_conv, conversation_id = find_conversation(db, query, since=since, before=before, include_empty=include_empty)

        if not matching_conv:
            console.print(f"[red]Conversation matching '{query}' not found[/red]")
            raise click.Abort()

        conversation = db.get_conversation(conversation_id)
        messages = db.get_messages(conversation_id)

        if output_format == 'json':
            output = {
                'conversation': conversation,
                'messages': messages,
            }
            console.print_json(data=output)
            return

        # Text format with rich formatting
        title_display = f"[bold cyan]{matching_conv['title']}[/bold cyan]"
        if matching_conv['subtitle']:
            title_display += f"\n[dim]{matching_conv['subtitle']}[/dim]"

        console.print(Panel.fit(
            f"{title_display}\n\n"
            f"[bold]ID:[/bold] {conversation_id}\n"
            f"[bold]Created:[/bold] {matching_conv['created']}\n"
            f"[bold]Status:[/bold] {conversation.get('status', 'unknown')}\n"
            f"[bold]Messages:[/bold] {len(messages)}\n"
            f"[bold]Model:[/bold] {conversation.get('modelConfig', {}).get('modelName', 'unknown')}",
            title="[bold cyan]Conversation[/bold cyan]"
        ))

        console.print()

        # Extract code block data from conversation
        code_block_data = conversation.get('codeBlockData', {})

        # Get model name for assistant label
        model_name = conversation.get('modelConfig', {}).get('modelName', 'Cursor')
        # Clean up model name if needed (e.g., "gpt-4" -> "GPT-4", "claude-3-5-sonnet" -> "Claude 3.5 Sonnet")
        if 'claude' in model_name.lower():
            model_name = model_name.replace('claude-', 'Claude ').replace('-', ' ').title()
        elif 'gpt' in model_name.lower():
            model_name = model_name.upper().replace('-', '-')
        else:
            model_name = model_name.title()

        msg_num = 0
        for i, msg in enumerate(messages, 1):
            created = msg.get('created', '')
            # Format timestamp - just show time if available
            timestamp = ''
            if created:
                try:
                    # Try to parse and format the timestamp
                    if 'T' in created:
                        timestamp = created.split('T')[1].split('.')[0][:5]  # Get HH:MM
                    else:
                        timestamp = created[:5] if len(created) >= 5 else created
                except:
                    timestamp = created[:10]  # Fallback

            # Check for code blocks associated with this message
            code_blocks = get_code_blocks_for_message(msg['id'], code_block_data)

            # Skip empty messages unless --show-empty is set
            is_empty = not msg['text'] and not code_blocks
            if is_empty and not show_empty:
                continue

            msg_num += 1

            # Determine speaker label and styling
            if msg['type'] == 'user':
                speaker = "You"
                color = "green"
                indent = ""
            else:
                speaker = model_name
                color = "blue"
                indent = "  "  # Slight indent for assistant messages

            # Build message content
            message_content = []

            if msg['text']:
                message_content.append(msg['text'])

            # Show code blocks (can appear with or without text)
            if code_blocks:
                if msg['text']:
                    message_content.append("")  # Add spacing

                for cb in code_blocks:
                    summary = f"[cyan]📝 Code edit: {cb['file']} ({cb['language']}) - {cb['status']}[/cyan]"
                    message_content.append(summary)

                    if show_code_details:
                        message_content.append(f"  [dim]Full path: {cb['full_path']}[/dim]")
                        message_content.append(f"  [dim]Diff ID: {cb['diff_id']}[/dim]")
                        if cb['created_at']:
                            message_content.append(f"  [dim]Created: {cb['created_at']}[/dim]")

                    if show_code_diff and cb['diff_id']:
                        diff_data = db.get_code_block_diff(conversation_id, cb['diff_id'])
                        if diff_data:
                            message_content.append(f"\n[yellow]Diff for {cb['file']}:[/yellow]")
                            # Display the diff content from newModelDiffWrtV0
                            new_diffs = diff_data.get('newModelDiffWrtV0', [])
                            if new_diffs:
                                for change in new_diffs:
                                    start_line = change['original']['startLineNumber']
                                    end_line = change['original']['endLineNumberExclusive']
                                    modified_lines = change['modified']

                                    # Show the line range
                                    if end_line > start_line:
                                        message_content.append(f"[dim]Lines {start_line}-{end_line-1}:[/dim]")
                                    else:
                                        message_content.append(f"[dim]Line {start_line}:[/dim]")

                                    # Show the added/modified lines
                                    for line in modified_lines:
                                        message_content.append(f"[green]+ {line}[/green]")
                            else:
                                message_content.append("[dim]No diff changes available[/dim]")

            # Show metadata if present
            if msg.get('suggested_code_blocks'):
                message_content.append(f"\n[yellow]Suggested code blocks: {len(msg['suggested_code_blocks'])}[/yellow]")

            if msg.get('tool_results'):
                message_content.append(f"[yellow]Tool results: {len(msg['tool_results'])}[/yellow]")

            # Create the chat bubble
            content_text = "\n".join(message_content) if message_content else "[dim](empty message)[/dim]"
            title_text = f"{speaker}"
            if timestamp:
                title_text += f" • {timestamp}"

            # Create the panel
            panel = Panel(
                content_text,
                title=title_text,
                title_align="left",
                border_style=color,
                padding=(0, 1),
            )

            # For assistant messages, add left padding to create indent effect
            if msg['type'] == 'user':
                console.print(panel)
            else:
                # Assistant message - wrap in padding for indent
                padded_panel = Padding(panel, (0, 0, 0, 2))  # (top, right, bottom, left)
                console.print(padded_panel)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.argument('query')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format', type=click.Choice(['markdown', 'json', 'text']), default='markdown')
@click.option('--include-empty', is_flag=True, help='Include empty conversations (0 messages)')
@click.option('--since', help='Filter to conversations since this time. Relative: "3d", "15m", "4h", "1w". Absolute: "2024-01-01"')
@click.option('--before', help='Filter to conversations before this time (same format as --since)')
def export(query: str, output: str, output_format: str, include_empty: bool, since: str, before: str):
    """Export a conversation to a file by ID or title, optionally filtered by time."""
    try:
        db = CursorDatabase()

        matching_conv, conversation_id = find_conversation(db, query, since=since, before=before, include_empty=include_empty)

        if not matching_conv:
            console.print(f"[red]Conversation matching '{query}' not found[/red]")
            raise click.Abort()

        conversation = db.get_conversation(conversation_id)
        messages = db.get_messages(conversation_id)

        # Generate output filename if not provided
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"cursor_conversation_{timestamp}.{output_format}"

        output_path = Path(output)

        if output_format == 'json':
            data = {
                'conversation': conversation,
                'messages': messages,
            }
            output_path.write_text(json.dumps(data, indent=2))

        elif output_format == 'markdown':
            md_content = f"# {matching_conv['title']}\n\n"
            if matching_conv['subtitle']:
                md_content += f"_{matching_conv['subtitle']}_\n\n"
            md_content += f"**ID:** {conversation_id}\n\n"
            md_content += f"**Created:** {matching_conv['created']}\n\n"
            md_content += f"**Status:** {conversation.get('status', 'unknown')}\n\n"
            md_content += f"**Messages:** {len(messages)}\n\n"
            md_content += "---\n\n"

            for i, msg in enumerate(messages, 1):
                msg_type = msg['type'].upper()
                created = msg.get('created', '')
                md_content += f"## {i}. {msg_type} - {created}\n\n"
                md_content += f"{msg['text']}\n\n"

                if msg.get('suggested_code_blocks'):
                    md_content += f"*Code blocks: {len(msg['suggested_code_blocks'])}*\n\n"

            output_path.write_text(md_content)

        else:  # text format
            text_content = f"{matching_conv['title']}\n{'='*70}\n"
            if matching_conv['subtitle']:
                text_content += f"{matching_conv['subtitle']}\n\n"
            else:
                text_content += "\n"
            text_content += f"ID: {conversation_id}\n"
            text_content += f"Created: {matching_conv['created']}\n"
            text_content += f"Status: {conversation.get('status', 'unknown')}\n"
            text_content += f"Messages: {len(messages)}\n\n"
            text_content += "="*70 + "\n\n"

            for i, msg in enumerate(messages, 1):
                msg_type = msg['type'].upper()
                created = msg.get('created', '')
                text_content += f"{i}. {msg_type} - {created}\n"
                text_content += "-"*70 + "\n"
                text_content += f"{msg['text']}\n\n"

            output_path.write_text(text_content)

        console.print(f"[green]Exported to {output_path}[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.argument('query')
@click.option('--include-empty', is_flag=True, help='Include empty conversations (0 messages)')
@click.option('--since', help='Search conversations since this time. Relative: "3d", "15m", "4h", "1w". Absolute: "2024-01-01"')
@click.option('--before', help='Search conversations before this time (same format as --since)')
def search(query: str, include_empty: bool, since: str, before: str):
    """Search conversations by text content."""
    try:
        db = CursorDatabase()
        results = db.search_conversations(query, since=since, before=before, include_empty=include_empty)

        if not results:
            console.print(f"[yellow]No conversations found matching '{query}'[/yellow]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(results)} found)")
        table.add_column("Title", style="cyan bold", no_wrap=False)
        table.add_column("Subtitle", style="dim", no_wrap=False)
        table.add_column("Created", style="green")
        table.add_column("Msgs", justify="right", style="blue")
        table.add_column("ID", style="dim", no_wrap=True)

        for conv in results:
            created = conv['created'].strftime("%Y-%m-%d %H:%M") if conv['created'] else "Unknown"
            title = conv['title'][:50] + "..." if len(conv['title']) > 50 else conv['title']
            subtitle = conv['subtitle'][:30] + "..." if len(conv['subtitle']) > 30 else conv['subtitle']

            table.add_row(
                title,
                subtitle,
                created,
                str(conv['message_count']),
                conv['id'][:12] + "...",
            )

        console.print(table)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@main.command()
def info():
    """Show information about Cursor's conversation storage."""
    db_path = get_cursor_db_path()

    console.print(Panel.fit(
        f"[bold]Database Location:[/bold]\n{db_path}\n\n"
        f"[bold]Exists:[/bold] {db_path.exists()}\n"
        f"[bold]Size:[/bold] {db_path.stat().st_size / 1024:.2f} KB" if db_path.exists() else "N/A",
        title="[bold cyan]Cursor Storage Info[/bold cyan]"
    ))

    if db_path.exists():
        try:
            db = CursorDatabase()
            conversations = db.list_conversations()

            total_messages = sum(c['message_count'] for c in conversations)
            total_lines_added = sum(c.get('total_lines_added', 0) for c in conversations)
            total_lines_removed = sum(c.get('total_lines_removed', 0) for c in conversations)

            console.print()
            console.print(Panel.fit(
                f"[bold]Total Conversations:[/bold] {len(conversations)}\n"
                f"[bold]Total Messages:[/bold] {total_messages}\n"
                f"[bold]Total Lines Added:[/bold] {total_lines_added}\n"
                f"[bold]Total Lines Removed:[/bold] {total_lines_removed}",
                title="[bold cyan]Statistics[/bold cyan]"
            ))

        except Exception as e:
            console.print(f"[red]Error reading database: {e}[/red]")


if __name__ == '__main__':
    main()
