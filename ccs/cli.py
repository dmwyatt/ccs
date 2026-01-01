"""Command-line interface for ccs (Cursor Conversation Search)."""

import json
import sqlite3

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


@main.command(name='check-db')
def check_db():
    """Validate that the Cursor database matches expected schema.

    Checks database structure, key patterns, and JSON field expectations
    against what ccs requires.
    """
    db_path = get_cursor_db_path()

    console.print(Panel.fit(
        "[bold cyan]Cursor Database Schema Validator[/bold cyan]\n"
        "Checking if the database matches expected structure..."
    ))
    console.print()

    issues = []
    warnings = []

    # 1. Check database exists
    console.print("[bold]1. Database Location[/bold]")
    console.print(f"   Path: {db_path}")
    if not db_path.exists():
        console.print("   [red]✗ Database not found[/red]")
        issues.append("Database file does not exist")
        _print_check_db_summary(issues, warnings)
        return
    console.print(f"   [green]✓ Database exists[/green] ({db_path.stat().st_size / 1024:.2f} KB)")
    console.print()

    # 2. Check database connection and table structure
    console.print("[bold]2. Database Structure[/bold]")
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        console.print("   [green]✓ Can open read-only connection[/green]")

        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cursorDiskKV'")
        if not cursor.fetchone():
            console.print("   [red]✗ Table 'cursorDiskKV' not found[/red]")
            issues.append("Required table 'cursorDiskKV' not found")
            conn.close()
            _print_check_db_summary(issues, warnings)
            return
        console.print("   [green]✓ Table 'cursorDiskKV' exists[/green]")

        # Check columns
        cursor.execute("PRAGMA table_info(cursorDiskKV)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        expected_cols = ['key', 'value']
        for col in expected_cols:
            if col in columns:
                console.print(f"   [green]✓ Column '{col}' exists[/green] (type: {columns[col]})")
            else:
                console.print(f"   [red]✗ Column '{col}' not found[/red]")
                issues.append(f"Required column '{col}' not found")
        console.print()

        # 3. Check key patterns
        console.print("[bold]3. Key Patterns[/bold]")
        key_patterns = {
            'composerData:%': ('Conversation metadata', True),
            'bubbleId:%': ('Messages', True),
            'codeBlockDiff:%': ('Code diffs', False),  # Optional - may not exist if no diffs
        }

        for pattern, (description, required) in key_patterns.items():
            cursor.execute(f"SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE ?", (pattern,))
            count = cursor.fetchone()[0]
            if count > 0:
                console.print(f"   [green]✓ {description}[/green] ({count} records matching '{pattern}')")
            elif required:
                console.print(f"   [red]✗ {description}[/red] (no records matching '{pattern}')")
                issues.append(f"No records found for required pattern '{pattern}'")
            else:
                console.print(f"   [yellow]○ {description}[/yellow] (no records matching '{pattern}' - optional)")
        console.print()

        # 4. Validate JSON schema for sample records
        console.print("[bold]4. JSON Schema Validation[/bold]")

        # Check composerData schema
        console.print("   [bold]composerData:[/bold]")
        cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%' LIMIT 5")
        composer_rows = cursor.fetchall()
        composer_fields = {
            'required': ['composerId'],
            'expected': ['createdAt', 'name', 'status', 'text'],
            'optional': ['subtitle', 'modelConfig', 'isArchived', 'totalLinesAdded', 'totalLinesRemoved', 'codeBlockData']
        }
        if composer_rows:
            _validate_json_schema(composer_rows, composer_fields, console, warnings, "composerData")
        else:
            console.print("      [yellow]No records to validate[/yellow]")

        # Check bubbleId schema
        console.print("   [bold]bubbleId:[/bold]")
        cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' LIMIT 5")
        bubble_rows = cursor.fetchall()
        bubble_fields = {
            'required': ['bubbleId', 'type'],
            'expected': ['createdAt', 'text'],
            'optional': ['richText', 'toolResults', 'suggestedCodeBlocks', 'images', 'capabilities', 'context', 'modelInfo']
        }
        if bubble_rows:
            _validate_json_schema(bubble_rows, bubble_fields, console, warnings, "bubbleId")
        else:
            console.print("      [yellow]No records to validate[/yellow]")

        # Check codeBlockDiff schema
        console.print("   [bold]codeBlockDiff:[/bold]")
        cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'codeBlockDiff:%' LIMIT 5")
        diff_rows = cursor.fetchall()
        diff_fields = {
            'required': [],
            'expected': ['originalText', 'modifiedText'],
            'optional': []
        }
        if diff_rows:
            _validate_json_schema(diff_rows, diff_fields, console, warnings, "codeBlockDiff")
        else:
            console.print("      [dim]No records to validate (no code diffs)[/dim]")

        conn.close()
        console.print()

    except sqlite3.Error as e:
        console.print(f"   [red]✗ Database error: {e}[/red]")
        issues.append(f"Database error: {e}")

    _print_check_db_summary(issues, warnings)


def _validate_json_schema(rows: list, field_spec: dict, console: Console, warnings: list, record_type: str):
    """Validate JSON records against expected schema."""
    found_fields = set()
    missing_required = set()
    missing_expected = set()

    for key, value in rows:
        try:
            data = json.loads(value)
            found_fields.update(data.keys())

            for field in field_spec['required']:
                if field not in data:
                    missing_required.add(field)
            for field in field_spec['expected']:
                if field not in data:
                    missing_expected.add(field)
        except json.JSONDecodeError:
            warnings.append(f"Invalid JSON in {key}")

    # Report required fields
    for field in field_spec['required']:
        if field in missing_required:
            console.print(f"      [red]✗ Missing required field '{field}'[/red]")
            warnings.append(f"{record_type}: Missing required field '{field}'")
        else:
            console.print(f"      [green]✓ Required field '{field}'[/green]")

    # Report expected fields
    for field in field_spec['expected']:
        if field in missing_expected:
            console.print(f"      [yellow]○ Missing expected field '{field}' in some records[/yellow]")
        else:
            console.print(f"      [green]✓ Expected field '{field}'[/green]")

    # Report new/unknown fields
    all_known = set(field_spec['required'] + field_spec['expected'] + field_spec['optional'])
    unknown_fields = found_fields - all_known
    if unknown_fields:
        console.print(f"      [cyan]ℹ New fields found: {', '.join(sorted(unknown_fields))}[/cyan]")


def _print_check_db_summary(issues: list, warnings: list):
    """Print summary of database check."""
    console.print()
    if issues:
        console.print(Panel.fit(
            "[red bold]Schema validation failed![/red bold]\n\n" +
            "[red]Issues:[/red]\n" +
            "\n".join(f"  • {issue}" for issue in issues) +
            ("\n\n[yellow]Warnings:[/yellow]\n" + "\n".join(f"  • {w}" for w in warnings) if warnings else ""),
            title="[red]Result[/red]"
        ))
    elif warnings:
        console.print(Panel.fit(
            "[yellow bold]Schema validation passed with warnings[/yellow bold]\n\n" +
            "[yellow]Warnings:[/yellow]\n" +
            "\n".join(f"  • {w}" for w in warnings),
            title="[yellow]Result[/yellow]"
        ))
    else:
        console.print(Panel.fit(
            "[green bold]Schema validation passed![/green bold]\n\n"
            "The Cursor database structure matches what ccs expects.",
            title="[green]Result[/green]"
        ))


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
