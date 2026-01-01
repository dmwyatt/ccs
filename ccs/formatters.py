"""Formatters for conversation output."""

import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.padding import Padding
from rich.console import Group

from .utils import get_code_blocks_for_message, normalize_model_name, format_timestamp, truncate_text, get_model_style


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

        # Extract code block data from conversation (needed for counting visible messages)
        code_block_data = conversation.get('codeBlockData', {})

        # Count visible messages (non-empty text or has code blocks, or all if show_empty)
        if show_empty:
            visible_count = len(messages)
        else:
            visible_count = 0
            for msg in messages:
                has_content = (msg.get('text') or '').strip()
                has_code_blocks = bool(get_code_blocks_for_message(msg['id'], code_block_data))
                if has_content or has_code_blocks:
                    visible_count += 1

        lines.append(f"**ID:** {composer_id}\n")
        lines.append(f"**Created:** {created_at}\n")
        lines.append(f"**Status:** {status}\n")
        lines.append(f"**Messages:** {visible_count}\n")
        lines.append("---\n")

        # Pre-compute effective model for each message by propagating explicit selections
        # Before any explicit selection, we don't know the model so use None
        current_model = None
        effective_models = []
        for msg in messages:
            msg_model = msg.get('model')
            if msg_model and msg_model != 'default':
                current_model = msg_model
            effective_models.append(current_model)

        # Messages section
        for i, msg in enumerate(messages, 1):
            # Skip empty messages unless show_empty is True
            # A message is empty if it has no text AND no code blocks
            text = msg.get('text', '')
            has_content = text.strip() if text else False
            code_blocks = get_code_blocks_for_message(msg['id'], code_block_data)
            is_empty = not has_content and not code_blocks
            if is_empty and not show_empty:
                continue

            # Determine speaker/type label
            if msg['type'] == 'user':
                speaker = "USER"
            else:
                effective_model = effective_models[i - 1]
                if effective_model:
                    speaker = normalize_model_name(effective_model)
                else:
                    speaker = "ASSISTANT"  # Unknown model before first explicit selection

            created = msg.get('created', '')
            lines.append(f"## {i}. {speaker} - {created}\n")

            # Message text
            text = msg.get('text', '')
            if text:
                lines.append(f"{text}\n")
            else:
                lines.append("*(empty message)*\n")

            # Code blocks metadata
            if code_blocks:
                lines.append(f"*Code blocks: {len(code_blocks)}*\n")

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
        show_thinking: bool = False,
        show_tool_calls: bool = False,
        db = None  # Database instance for fetching diff data
    ) -> Group:
        """Format conversation as Rich chat bubbles.

        Args:
            conversation: Conversation metadata
            messages: List of messages
            show_code_diff: Whether to show code diffs
            show_code_details: Whether to show detailed code block info
            show_empty: Whether to show empty messages
            show_thinking: Whether to expand thinking/reasoning traces
            show_tool_calls: Whether to expand tool call details
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

        # Extract code block data from conversation (needed for counting visible messages)
        code_block_data = conversation.get('codeBlockData', {})

        # Count visible messages (non-empty text, code blocks, thinking, or tool calls)
        if show_empty:
            visible_count = len(messages)
        else:
            visible_count = 0
            for msg in messages:
                has_content = (msg.get('text') or '').strip()
                has_code_blocks = bool(get_code_blocks_for_message(msg['id'], code_block_data))
                has_thinking = bool(msg.get('thinking'))
                has_tool_call = bool(msg.get('tool_call'))
                if has_content or has_code_blocks or has_thinking or has_tool_call:
                    visible_count += 1

        title_display = f"[bold cyan]{title}[/bold cyan]"
        if subtitle:
            title_display += f"\n[dim]{subtitle}[/dim]"

        header_panel = Panel.fit(
            f"{title_display}\n\n"
            f"[bold]ID:[/bold] {composer_id}\n"
            f"[bold]Created:[/bold] {created_at}\n"
            f"[bold]Status:[/bold] {status}\n"
            f"[bold]Messages:[/bold] {visible_count}\n"
            f"[bold]Model:[/bold] {model_name}",
            title="[bold cyan]Conversation[/bold cyan]"
        )
        renderables.append(header_panel)
        renderables.append("")  # Spacing

        # Pre-compute effective model for each message by propagating explicit selections
        # When a user explicitly selects a model, it persists until they select another
        # Before any explicit selection, we don't know the model so use None
        current_model = None
        effective_models = []
        for msg in messages:
            msg_model = msg.get('model')
            if msg_model and msg_model != 'default':
                # Explicit selection - update current model
                current_model = msg_model
            effective_models.append(current_model)

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
            has_thinking = bool(msg.get('thinking'))
            has_tool_call = bool(msg.get('tool_call'))
            is_empty = not has_content and not code_blocks and not has_thinking and not has_tool_call
            if is_empty and not show_empty:
                continue

            # Determine speaker label and styling
            if msg['type'] == 'user':
                speaker = "You"
                border_color = "green"
            else:
                # Use the pre-computed effective model (handles propagation of explicit selections)
                effective_model = effective_models[i - 1]
                style = get_model_style(effective_model)
                model_color = style['color']
                icon = style['icon']
                if effective_model:
                    model_name_display = normalize_model_name(effective_model)
                else:
                    model_name_display = "Assistant"
                # Apply color only to the model name, not the whole border
                speaker = f"[{model_color}]{icon} {model_name_display}[/{model_color}]"
                border_color = "blue"

            # Build message content as a list of renderables
            message_renderables = []

            # Add markdown-rendered text if present
            if msg.get('text'):
                message_renderables.append(Markdown(msg['text']))

            # Show thinking traces (reasoning/extended thinking)
            if msg.get('thinking'):
                if message_renderables:
                    message_renderables.append("")  # Add spacing
                duration_ms = msg.get('thinking_duration_ms')
                duration_str = f" ({duration_ms}ms)" if duration_ms else ""
                if show_thinking:
                    # Expanded view - show full thinking content
                    thinking_content = msg['thinking']
                    message_renderables.append(
                        Panel(
                            Markdown(thinking_content),
                            title=f"[magenta]💭 Thinking{duration_str}[/magenta]",
                            title_align="left",
                            border_style="magenta",
                            padding=(0, 1),
                        )
                    )
                else:
                    # Collapsed view - just show summary
                    thinking_preview = msg['thinking'][:100].replace('\n', ' ')
                    if len(msg['thinking']) > 100:
                        thinking_preview += "..."
                    message_renderables.append(
                        f"[magenta]💭 Thinking{duration_str}:[/magenta] [dim]{thinking_preview}[/dim]"
                    )

            # Show tool calls (actual tool invocations)
            if msg.get('tool_call'):
                if message_renderables:
                    message_renderables.append("")  # Add spacing
                tool_data = msg['tool_call']
                tool_name = tool_data.get('name', 'unknown')
                tool_status = tool_data.get('status', 'unknown')
                if show_tool_calls:
                    # Expanded view - show full tool call details
                    tool_info_lines = [f"[bold]Tool:[/bold] {tool_name}"]
                    tool_info_lines.append(f"[bold]Status:[/bold] {tool_status}")

                    # Show the command/args
                    raw_args = tool_data.get('rawArgs')
                    if raw_args:
                        try:
                            args_data = json.loads(raw_args)
                            if 'command' in args_data:
                                tool_info_lines.append(f"[bold]Command:[/bold] {args_data['command']}")
                            if 'explanation' in args_data:
                                tool_info_lines.append(f"[bold]Explanation:[/bold] {args_data['explanation']}")
                        except (json.JSONDecodeError, TypeError):
                            tool_info_lines.append(f"[bold]Args:[/bold] {raw_args[:200]}...")

                    # Show result summary
                    result = tool_data.get('result')
                    if result:
                        try:
                            result_data = json.loads(result)
                            output = result_data.get('output', '')
                            if output:
                                # Truncate long output
                                if len(output) > 500:
                                    output = output[:500] + "\n... (truncated)"
                                tool_info_lines.append(f"\n[bold]Output:[/bold]\n{output}")
                        except (json.JSONDecodeError, TypeError):
                            tool_info_lines.append(f"[bold]Result:[/bold] {result[:200]}...")

                    message_renderables.append(
                        Panel(
                            "\n".join(tool_info_lines),
                            title=f"[yellow]🔧 Tool Call[/yellow]",
                            title_align="left",
                            border_style="yellow",
                            padding=(0, 1),
                        )
                    )
                else:
                    # Collapsed view - just show tool name and status
                    # Try to extract command for terminal commands
                    command_preview = ""
                    raw_args = tool_data.get('rawArgs')
                    if raw_args:
                        try:
                            args_data = json.loads(raw_args)
                            if 'command' in args_data:
                                cmd = args_data['command']
                                if len(cmd) > 60:
                                    cmd = cmd[:60] + "..."
                                command_preview = f": {cmd}"
                        except (json.JSONDecodeError, TypeError):
                            pass
                    message_renderables.append(
                        f"[yellow]🔧 {tool_name}{command_preview}[/yellow] [dim]({tool_status})[/dim]"
                    )

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
                border_style=border_color,
                padding=(0, 1),
            )

            # Add padding to create chat bubble effect
            # User messages: pad right, Assistant messages: pad left
            bubble_indent = 4
            if msg['type'] == 'user':
                padded_panel = Padding(panel, (0, bubble_indent, 0, 0))  # (top, right, bottom, left)
            else:
                padded_panel = Padding(panel, (0, 0, 0, bubble_indent))
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
