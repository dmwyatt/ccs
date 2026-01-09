"""Statistics computation for conversation data."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import statistics


@dataclass
class StatResult:
    """Container for a set of computed statistics."""

    count: int = 0
    total: int = 0
    mean: float = 0.0
    median: float = 0.0
    stdev: float = 0.0
    min: int = 0
    max: int = 0
    p25: int = 0
    p75: int = 0
    p90: int = 0

    # Distribution buckets (customizable)
    distribution: Dict[str, int] = field(default_factory=dict)

    # Metadata about what was computed
    label: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ConversationStats:
    """Compute statistics from conversation data.

    Designed to be extensible - add new stat computations by adding methods
    that operate on the conversations list.
    """

    # Default distribution buckets for message counts
    DEFAULT_BUCKETS = [
        ("1-5", 1, 5),
        ("6-15", 6, 15),
        ("16-30", 16, 30),
        ("31-50", 31, 50),
        ("51-100", 51, 100),
        ("100+", 101, float('inf')),
    ]

    def __init__(self, conversations: List[Dict[str, Any]]):
        """Initialize with conversation data.

        Args:
            conversations: List of conversation dicts from CursorDatabase.list_conversations()
        """
        self.conversations = conversations

    def compute(
        self,
        metric: str = "message_count",
        label: str = "",
        buckets: Optional[List[tuple]] = None,
    ) -> StatResult:
        """Compute statistics for a given metric.

        Args:
            metric: The conversation field to compute stats on (default: message_count)
            label: Optional label for this stat result
            buckets: Custom distribution buckets as list of (name, min, max) tuples

        Returns:
            StatResult with computed statistics
        """
        if not self.conversations:
            return StatResult(label=label)

        values = [c.get(metric, 0) for c in self.conversations]
        buckets = buckets or self.DEFAULT_BUCKETS

        result = StatResult(
            count=len(values),
            total=sum(values),
            mean=statistics.mean(values),
            median=statistics.median(values),
            stdev=statistics.stdev(values) if len(values) > 1 else 0.0,
            min=min(values),
            max=max(values),
            label=label,
        )

        # Percentiles
        sorted_values = sorted(values)
        n = len(sorted_values)
        result.p25 = sorted_values[int(n * 0.25)] if n >= 4 else result.median
        result.p75 = sorted_values[int(n * 0.75)] if n >= 4 else result.median
        result.p90 = sorted_values[int(n * 0.90)] if n >= 10 else result.max

        # Date range
        dates = [c['created'] for c in self.conversations if c.get('created')]
        if dates:
            result.start_date = min(dates)
            result.end_date = max(dates)

        # Distribution
        result.distribution = self._compute_distribution(values, buckets)

        return result

    def _compute_distribution(
        self,
        values: List[int],
        buckets: List[tuple]
    ) -> Dict[str, int]:
        """Compute distribution across buckets.

        Args:
            values: List of numeric values
            buckets: List of (name, min, max) tuples

        Returns:
            Dict mapping bucket name to count
        """
        distribution = {name: 0 for name, _, _ in buckets}

        for v in values:
            for name, low, high in buckets:
                if low <= v <= high:
                    distribution[name] += 1
                    break

        return distribution

    def by_period(
        self,
        period: str = "week",
        metric: str = "message_count",
        num_periods: int = 4,
        reference_date: Optional[datetime] = None,
    ) -> List[StatResult]:
        """Compute statistics grouped by time period.

        Args:
            period: Time period grouping ("week" or "day")
            metric: The field to compute stats on
            num_periods: Number of periods to include
            reference_date: Reference date (default: now)

        Returns:
            List of StatResult, one per period (most recent first)
        """
        ref = reference_date or datetime.now()
        results = []

        for i in range(num_periods):
            start, end, label = self._get_period_bounds(ref, period, i)

            # Filter conversations to this period
            period_convs = [
                c for c in self.conversations
                if c.get('created') and start <= c['created'] <= end
            ]

            # Compute stats for this period
            period_stats = ConversationStats(period_convs)
            result = period_stats.compute(metric=metric, label=label)
            result.start_date = start
            result.end_date = end
            results.append(result)

        return results

    def _get_period_bounds(
        self,
        reference: datetime,
        period: str,
        offset: int
    ) -> tuple:
        """Get the start/end bounds for a period.

        Args:
            reference: Reference datetime
            period: "week" or "day"
            offset: Number of periods back from reference

        Returns:
            Tuple of (start_datetime, end_datetime, label)
        """
        if period == "week":
            # Week runs Mon-Sun
            days_since_monday = reference.weekday()
            current_monday = reference.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days_since_monday)

            start = current_monday - timedelta(weeks=offset)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            if offset == 0:
                label = "Current week"
            elif offset == 1:
                label = "Last week"
            else:
                label = f"{offset} weeks ago"

            label += f" ({start.strftime('%b %d')} - {end.strftime('%b %d')})"

        elif period == "day":
            day_start = reference.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=offset)

            start = day_start
            end = day_start + timedelta(hours=23, minutes=59, seconds=59)

            if offset == 0:
                label = f"Today ({start.strftime('%b %d')})"
            elif offset == 1:
                label = f"Yesterday ({start.strftime('%b %d')})"
            else:
                label = start.strftime('%a %b %d')
        else:
            raise ValueError(f"Unknown period: {period}")

        return start, end, label

    def top_conversations(
        self,
        metric: str = "message_count",
        n: int = 5,
        descending: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get top N conversations by a metric.

        Args:
            metric: Field to sort by
            n: Number of results
            descending: Sort descending (True) or ascending (False)

        Returns:
            List of conversation dicts
        """
        sorted_convs = sorted(
            self.conversations,
            key=lambda c: c.get(metric, 0),
            reverse=descending,
        )
        return sorted_convs[:n]
