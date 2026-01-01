"""Formatters for conversation output."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.padding import Padding
from rich.console import Group

from .utils import get_code_blocks_for_message, normalize_model_name, format_timestamp, truncate_text


class Formatter(ABC):
    """Base class for conversation formatters."""

    @abstractmethod
    def format_conversation(
        self,
        conversation: Dict[str, Any],
        messages: List[Dict[str, Any]],
        **options
    ) -> Any:
        """Format a single conversation with messages.

        Args:
            conversation: Conversation metadata dict
            messages: List of message dicts
            **options: Formatter-specific options (show_code_diff, show_code_details, etc.)

        Returns:
            Formatted output (type depends on formatter implementation)
        """
        pass

    @abstractmethod
    def format_conversation_list(
        self,
        conversations: List[Dict[str, Any]]
    ) -> Any:
        """Format a list of conversations (for list/search commands).

        Args:
            conversations: List of conversation metadata dicts

        Returns:
            Formatted output (type depends on formatter implementation)
        """
        pass


class MarkdownFormatter(Formatter):
    """Markdown formatter for document export and agent consumption."""

    def format_conversation(
        self,
        conversation: Dict[str, Any],
        messages: List[Dict[str, Any]],
        show_empty: bool = False,
        **options  # Ignore other options like show_code_diff
    ) -> str:
        """Format conversation as markdown document.

        Args:
            conversation: Conversation metadata
            messages: List of messages
            show_empty: Whether to include empty messages

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header section
        title = conversation.get('name', '(no title)')
        lines.append(f"# {title}\n")

        subtitle = conversation.get('subtitle', '')
        if subtitle:
            lines.append(f"_{subtitle}_\n")

        # Metadata
        composer_id = conversation.get('composerId', 'unknown')
        created_at_raw = conversation.get('createdAt', 'unknown')
        status = conversation.get('status', 'unknown')

        # Format timestamp (convert from milliseconds to datetime string)
        if isinstance(created_at_raw, int):
            from datetime import datetime
            created_at = datetime.fromtimestamp(created_at_raw / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            created_at = created_at_raw

        lines.append(f"**ID:** {composer_id}\n")
        lines.append(f"**Created:** {created_at}\n")
        lines.append(f"**Status:** {status}\n")
        lines.append(f"**Messages:** {len(messages)}\n")
        lines.append("---\n")

        # Messages section
        for i, msg in enumerate(messages, 1):
            # Skip empty messages unless show_empty is True
            # Consider messages with only whitespace as empty
            text = msg.get('text', '')
            has_content = text.strip() if text else False
            if not has_content and not show_empty:
                continue

            msg_type = msg['type'].upper()
            created = msg.get('created', '')
            lines.append(f"## {i}. {msg_type} - {created}\n")

            # Message text
            text = msg.get('text', '')
            if text:
                lines.append(f"{text}\n")
            else:
                lines.append("*(empty message)*\n")

            # Code blocks metadata
            if msg.get('suggested_code_blocks'):
                count = len(msg['suggested_code_blocks'])
                lines.append(f"*Code blocks: {count}*\n")

            lines.append("")  # Extra newline between messages

        return "\n".join(lines)

    def format_conversation_list(
        self,
        conversations: List[Dict[str, Any]]
    ) -> str:
        """Format conversation list as markdown table.

        Args:
            conversations: List of conversation metadata

        Returns:
            Markdown table string
        """
        lines = []
        lines.append("# Cursor Conversations\n")
        lines.append(f"**Total:** {len(conversations)}\n")

        # Table header
        lines.append("| Title | Subtitle | Created | Messages | ID |")
        lines.append("|-------|----------|---------|----------|-----|")

        # Table rows
        for conv in conversations:
            # Escape pipe characters for markdown table
            title = conv.get('title', '(no title)').replace('|', '\\|')
            subtitle = conv.get('subtitle', '').replace('|', '\\|')

            # Format created date
            created = conv.get('created')
            if created:
                created_str = created.strftime("%Y-%m-%d %H:%M")
            else:
                created_str = "Unknown"

            msg_count = conv.get('message_count', 0)
            conv_id = conv.get('id', '')[:12] + "..."

            lines.append(f"| {title} | {subtitle} | {created_str} | {msg_count} | {conv_id} |")

        return "\n".join(lines)


class RichFormatter(Formatter):
    """Rich terminal formatter with colors and styling."""

    def format_conversation(
        self,
        conversation: Dict[str, Any],
        messages: List[Dict[str, Any]],
        show_code_diff: bool = False,
        show_code_details: bool = False,
        show_empty: bool = False,
        db = None  # Database instance for fetching diff data
    ) -> Group:
        """Format conversation as Rich chat bubbles.

        Args:
            conversation: Conversation metadata
            messages: List of messages
            show_code_diff: Whether to show code diffs
            show_code_details: Whether to show detailed code block info
            show_empty: Whether to show empty messages
            db: Database instance (needed for fetching diff data)

        Returns:
            Rich Group object containing all panels
        """
        renderables = []

        # Header panel
        title = conversation.get('name', '(no title)')
        subtitle = conversation.get('subtitle', '')
        composer_id = conversation.get('composerId', 'unknown')
        created_at_raw = conversation.get('createdAt', 'unknown')
        status = conversation.get('status', 'unknown')
        model_name = conversation.get('modelConfig', {}).get('modelName', 'unknown')

        # Format timestamp (convert from milliseconds to datetime string)
        if isinstance(created_at_raw, int):
            from datetime import datetime
            created_at = datetime.fromtimestamp(created_at_raw / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            created_at = created_at_raw

        title_display = f"[bold cyan]{title}[/bold cyan]"
        if subtitle:
            title_display += f"\n[dim]{subtitle}[/dim]"

        header_panel = Panel.fit(
            f"{title_display}\n\n"
            f"[bold]ID:[/bold] {composer_id}\n"
            f"[bold]Created:[/bold] {created_at}\n"
            f"[bold]Status:[/bold] {status}\n"
            f"[bold]Messages:[/bold] {len(messages)}\n"
            f"[bold]Model:[/bold] {model_name}",
            title="[bold cyan]Conversation[/bold cyan]"
        )
        renderables.append(header_panel)
        renderables.append("")  # Spacing

        # Extract code block data from conversation
        code_block_data = conversation.get('codeBlockData', {})

        # Normalize model name for assistant label
        model_display_name = normalize_model_name(model_name)

        # Process messages
        for i, msg in enumerate(messages, 1):
            created = msg.get('created', '')
            timestamp = format_timestamp(created)

            # Check for code blocks associated with this message
            code_blocks = get_code_blocks_for_message(msg['id'], code_block_data)

            # Skip empty messages unless --show-empty is set
            # Consider messages with only whitespace as empty
            text = msg.get('text', '')
            has_content = text.strip() if text else False
            is_empty = not has_content and not code_blocks
            if is_empty and not show_empty:
                continue

            # Determine speaker label and styling
            if msg['type'] == 'user':
                speaker = "You"
                color = "green"
            else:
                speaker = model_display_name
                color = "blue"

            # Build message content as a list of renderables
            message_renderables = []

            # Add markdown-rendered text if present
            if msg.get('text'):
                message_renderables.append(Markdown(msg['text']))

            # Show code blocks (can appear with or without text)
            if code_blocks:
                if msg.get('text'):
                    message_renderables.append("")  # Add spacing

                code_block_info = []
                for cb in code_blocks:
                    summary = f"[cyan]📝 Code edit: {cb['file']} ({cb['language']}) - {cb['status']}[/cyan]"
                    code_block_info.append(summary)

                    if show_code_details:
                        code_block_info.append(f"  [dim]Full path: {cb['full_path']}[/dim]")
                        code_block_info.append(f"  [dim]Diff ID: {cb['diff_id']}[/dim]")
                        if cb['created_at']:
                            code_block_info.append(f"  [dim]Created: {cb['created_at']}[/dim]")

                    if show_code_diff and cb['diff_id'] and db:
                        diff_data = db.get_code_block_diff(composer_id, cb['diff_id'])
                        if diff_data:
                            code_block_info.append(f"\n[yellow]Diff for {cb['file']}:[/yellow]")
                            # Display the diff content from newModelDiffWrtV0
                            new_diffs = diff_data.get('newModelDiffWrtV0', [])
                            if new_diffs:
                                for change in new_diffs:
                                    start_line = change['original']['startLineNumber']
                                    end_line = change['original']['endLineNumberExclusive']
                                    modified_lines = change['modified']

                                    # Show the line range
                                    if end_line > start_line:
                                        code_block_info.append(f"[dim]Lines {start_line}-{end_line-1}:[/dim]")
                                    else:
                                        code_block_info.append(f"[dim]Line {start_line}:[/dim]")

                                    # Show the added/modified lines
                                    for line in modified_lines:
                                        code_block_info.append(f"[green]+ {line}[/green]")
                            else:
                                code_block_info.append("[dim]No diff changes available[/dim]")

                message_renderables.append("\n".join(code_block_info))

            # Show metadata if present
            if msg.get('suggested_code_blocks'):
                message_renderables.append(f"\n[yellow]Suggested code blocks: {len(msg['suggested_code_blocks'])}[/yellow]")

            if msg.get('tool_results'):
                message_renderables.append(f"[yellow]Tool results: {len(msg['tool_results'])}[/yellow]")

            # Create the chat bubble content
            if message_renderables:
                content = Group(*message_renderables)
            else:
                content = "[dim](empty message)[/dim]"

            title_text = speaker
            if timestamp:
                title_text += f" • {timestamp}"

            # Create the panel
            panel = Panel(
                content,
                title=title_text,
                title_align="left",
                border_style=color,
                padding=(0, 1),
            )

            # For assistant messages, add left padding to create indent effect
            if msg['type'] == 'user':
                renderables.append(panel)
            else:
                # Assistant message - wrap in padding for indent
                padded_panel = Padding(panel, (0, 0, 0, 2))  # (top, right, bottom, left)
                renderables.append(padded_panel)

        return Group(*renderables)

    def format_conversation_list(
        self,
        conversations: List[Dict[str, Any]]
    ) -> Table:
        """Format conversation list as Rich table.

        Args:
            conversations: List of conversation metadata

        Returns:
            Rich Table object
        """
        table = Table(title=f"Cursor Conversations ({len(conversations)} found)")

        # Add columns with styling
        table.add_column("Title", style="cyan bold", no_wrap=False)
        table.add_column("Subtitle", style="dim", no_wrap=False)
        table.add_column("Created", style="green")
        table.add_column("Msgs", justify="right", style="blue")
        table.add_column("ID", style="dim", no_wrap=True)

        # Add rows
        for conv in conversations:
            # Format created date
            created = conv.get('created')
            if created:
                created_str = created.strftime("%Y-%m-%d %H:%M")
            else:
                created_str = "Unknown"

            # Truncate long text fields
            title = truncate_text(conv.get('title', '(no title)'), 50)
            subtitle = truncate_text(conv.get('subtitle', ''), 30)
            conv_id = conv.get('id', '')[:12] + "..."

            table.add_row(
                title,
                subtitle,
                created_str,
                str(conv.get('message_count', 0)),
                conv_id,
            )

        return table
