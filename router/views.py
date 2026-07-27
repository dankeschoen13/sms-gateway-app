from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import determine_department, is_rate_limited
from .models import Message
import json


@csrf_exempt
def sms_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
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

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)