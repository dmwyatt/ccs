"""Utilities for parsing and filtering by datetime."""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


def parse_relative_time(time_str: str) -> Optional[datetime]:
    """Parse relative time expressions like '15m', '3d', '4h', or '3 days'.

    Args:
        time_str: Time expression like "15m", "3d", "4 hours ago", "3 days"

    Returns:
        datetime object or None if parsing fails

    Examples:
        "15m" or "15 minutes" -> 15 minutes ago from now
        "3d" or "3 days" -> 3 days ago from now
        "4h" or "4 hours ago" -> 4 hours ago from now
        "1w" or "1 week" -> 1 week ago from now
    """
    time_str = time_str.lower().strip()

    # Remove "ago" if present
    time_str = time_str.replace(' ago', '').strip()

    # Pattern: number + optional space + unit
    # Supports: 3d, 3 d, 3 days, 3days, etc.
    pattern = r'(\d+)\s*(minute|minutes|min|mins|m|hour|hours|hr|hrs|h|day|days|d|week|weeks|w|month|months|mo|year|years|y)'
    match = re.match(pattern, time_str)

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    # Map units to timedelta
    if unit in ['minute', 'minutes', 'min', 'mins', 'm']:
        delta = timedelta(minutes=amount)
    elif unit in ['hour', 'hours', 'hr', 'hrs', 'h']:
        delta = timedelta(hours=amount)
    elif unit in ['day', 'days', 'd']:
        delta = timedelta(days=amount)
    elif unit in ['week', 'weeks', 'w']:
        delta = timedelta(weeks=amount)
    elif unit in ['month', 'months', 'mo']:
        delta = timedelta(days=amount * 30)  # Approximate
    elif unit in ['year', 'years', 'y']:
        delta = timedelta(days=amount * 365)  # Approximate
    else:
        return None

    return datetime.now() - delta


def parse_absolute_datetime(date_str: str) -> Optional[datetime]:
    """Parse absolute date/datetime strings.

    Args:
        date_str: Date string in various formats

    Returns:
        datetime object or None if parsing fails

    Supported formats:
        - 2024-01-01
        - 2024-01-01 15:30
        - 2024-01-01T15:30:00
        - 01/01/2024
    """
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%m/%d/%Y',
        '%m/%d/%Y %H:%M',
        '%d/%m/%Y',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def parse_datetime(time_str: str) -> Optional[datetime]:
    """Parse either relative or absolute datetime string.

    Args:
        time_str: Either relative ("3 days") or absolute ("2024-01-01") time

    Returns:
        datetime object or None if parsing fails
    """
    # Try relative first
    result = parse_relative_time(time_str)
    if result:
        return result

    # Try absolute
    return parse_absolute_datetime(time_str)


def filter_by_time_range(
    items: list,
    since: Optional[str] = None,
    before: Optional[str] = None,
    date_key: str = 'created'
) -> list:
    """Filter items by time range.

    Args:
        items: List of items with datetime field
        since: Filter items created since this time (inclusive)
        before: Filter items created before this time (exclusive)
        date_key: Key name for the datetime field in items

    Returns:
        Filtered list of items
    """
    if not since and not before:
        return items

    since_dt = None
    before_dt = None

    if since:
        since_dt = parse_datetime(since)
        if not since_dt:
            raise ValueError(f"Could not parse 'since' time: {since}")

    if before:
        before_dt = parse_datetime(before)
        if not before_dt:
            raise ValueError(f"Could not parse 'before' time: {before}")

    filtered = []
    for item in items:
        item_dt = item.get(date_key)
        if not item_dt:
            continue

        # Convert to datetime if it's not already
        if not isinstance(item_dt, datetime):
            continue

        # Check since (inclusive)
        if since_dt and item_dt < since_dt:
            continue

        # Check before (exclusive)
        if before_dt and item_dt >= before_dt:
            continue

        filtered.append(item)

    return filtered


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '3 hours ago').

    Args:
        dt: datetime to format

    Returns:
        Human-readable relative time string
    """
    now = datetime.now()
    delta = now - dt

    if delta.total_seconds() < 60:
        return "just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta.days < 7:
        return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif delta.days < 365:
        months = delta.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = delta.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
