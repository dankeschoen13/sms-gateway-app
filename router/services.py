from datetime import timedelta, date, datetime
from django.utils import timezone
from django.db.models import Count
from .models import Message

def determine_department(message_body: str) -> str:
    """
    Scans the message body for keywords and returns a department string.
    """
    text = message_body.lower()

    if any(word in text for word in ['support', 'broken', 'issue']):
        return "Support"
    elif any(word in text for word in ['pay', 'billing', 'charge', 'invoice']):
        return "Billing"
    elif any(word in text for word in ['cancel', 'stop', 'unsubscribe']):
        return "Cancellations"

    return "General"

def is_rate_limited(sender_number: str) -> bool:
    """
    Implements a sliding window rate limit using the database.

    Returns True if the sender has exceeded 5 messages in the last 10 seconds.
    """

    time_window_start = timezone.now() - timedelta(seconds=10)

    # The double underscore `__gte` means "Greater Than or Equal to" in Django ORM
    recent_message_count = Message.objects.filter(
        sender_number=sender_number,
        timestamp__gte=time_window_start
    ).count()

    if recent_message_count >= 5:
        return True

    return False

def prepare_breakdown(
        start_date: date | datetime, end_date: date | datetime | None = None
) -> tuple[int, int, dict[str, int]]:
    """
    Prepares breakdown of messages based on a given time period.

    Returns the total processed, total blocked and the distribution of messages across categories.
    """

    if end_date:
        messages = Message.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lt=end_date
        )
    else:
        messages = Message.objects.filter(
            timestamp__date__gte=start_date
        )

    total_processed = messages.count()
    total_blocked = messages.filter(is_blocked=True).count()

    department_counts = (
        messages
        .filter(is_blocked=False)
        .values('department')
        .annotate(count=Count('id'))
    )

    breakdown = {
        item['department']: item['count']
        for item in department_counts
        if item['department']
    }

    return total_processed, total_blocked, breakdown