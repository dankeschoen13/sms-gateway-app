from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from .services import determine_department, is_rate_limited, prepare_breakdown
from .models import Message
import json


@csrf_exempt
def sms_webhook(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        sender_number = data.get('sender_number')
        message_body = data.get('message_body')

        if not sender_number or not message_body:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # 1. Check Rate Limit First ---
        # Still log the blocked attempt for our later analysis
        if is_rate_limited(sender_number):
            Message.objects.create(
                sender_number=sender_number,
                message_body=message_body,
                is_blocked=True
            )
            return JsonResponse({'error': 'Too Many Requests'}, status=429)

        # 2. Route the Message ---
        department = determine_department(message_body)

        # 3. Save the Successful Message ---
        message = Message.objects.create(
            sender_number=sender_number,
            message_body=message_body,
            department=department,
            is_blocked=False
        )

        return JsonResponse({
            'status': 'success',
            'department_routed': department,
            'message_id': message.pk
        }, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def daily_report(request):
    """
    GET endpoint returning aggregated stats for today's SMS traffic.
    """
    if request.method == 'GET':

        today = timezone.localdate()

        total_processed, total_blocked, breakdown = prepare_breakdown(start_date=today)

        return JsonResponse({
            'date': f'{today}',
            'total_messages_processed': total_processed,
            'total_rate_limit_rejections': total_blocked,
            'department_breakdown': breakdown
        }, status=200)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

def weekly_report(request):

    if request.method == 'GET':

        start_date = timezone.localdate() - timedelta(days=7)

        total_processed, total_blocked, breakdown = prepare_breakdown(start_date=start_date)

        return JsonResponse({
            'date': f'Week starting {start_date}',
            'total_messages_processed': total_processed,
            'total_rate_limit_rejections': total_blocked,
            'department_breakdown': breakdown
        }, status=200)

    return JsonResponse({'error': 'Method not allowed'}, status=405)




