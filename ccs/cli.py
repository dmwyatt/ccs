"""Command-line interface for ccs (Cursor Conversation Search)."""

import click
from rich.console import Console
from rich.panel import Panel

from .database import CursorDatabase, get_cursor_db_path
from .formatters import RichFormatter, MarkdownFormatter


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
@click.option('--format', 'output_format', type=click.Choice(['rich', 'markdown']), default='rich')
def list(show_all: bool, include_empty: bool, limit: int, since: str, before: str, output_format: str):
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

        # Use formatter based on output format
        if output_format == 'rich':
            formatter = RichFormatter()
            table = formatter.format_conversation_list(conversations)
            console.print(table)
        else:  # markdown
            formatter = MarkdownFormatter()
            output = formatter.format_conversation_list(conversations)
            print(output)

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


@main.command()
@click.argument('query')
@click.option('--format', 'output_format', type=click.Choice(['rich', 'markdown']), default='rich')
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

        # Use formatter based on output format
        if output_format == 'rich':
            formatter = RichFormatter()
            output = formatter.format_conversation(
                conversation=conversation,
                messages=messages,
                show_code_diff=show_code_diff,
                show_code_details=show_code_details,
                show_empty=show_empty,
                db=db
            )
            console.print(output)
        else:  # markdown
            formatter = MarkdownFormatter()
            output = formatter.format_conversation(
                conversation=conversation,
                messages=messages,
                show_empty=show_empty
            )
            print(output)  # Plain print for piping

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
@click.option('--format', 'output_format', type=click.Choice(['rich', 'markdown']), default='rich')
@click.option('--search-diffs', is_flag=True, help='Also search in code diffs (file paths and diff content)')
def search(query: str, include_empty: bool, since: str, before: str, output_format: str, search_diffs: bool):
    """Search conversations by text content."""
    try:
        db = CursorDatabase()
        results = db.search_conversations(query, since=since, before=before, include_empty=include_empty, search_diffs=search_diffs)

        if not results:
            console.print(f"[yellow]No conversations found matching '{query}'[/yellow]")
            return

        # Use formatter based on output format
        if output_format == 'rich':
            formatter = RichFormatter()
            table = formatter.format_conversation_list(results)
            # Customize title for search context
            table.title = f"Search Results for '{query}' ({len(results)} found)"
            console.print(table)
        else:  # markdown
            formatter = MarkdownFormatter()
            output = formatter.format_conversation_list(results)
            # Prepend search query to output
            output = f"# Search Results for '{query}'\n\n" + output
            print(output)

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
