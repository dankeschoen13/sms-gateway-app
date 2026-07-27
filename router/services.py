from datetime import timedelta
from django.utils import timezone
from .models import Message

def determine_department(message_body):
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

def is_rate_limited(sender_number):
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