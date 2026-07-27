from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Message
import json


@csrf_exempt
def sms_webhook(request):
    if request.method == 'POST':
        try:
            # Django stores raw request data in request.body
            data = json.loads(request.body)

            sender_number = data.get('sender_number')
            message_body = data.get('message_body')

            # Basic validation
            if not sender_number or not message_body:
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            # Save the message to the database
            # (We will inject the rate-limiting and routing logic here later)
            message = Message.objects.create(
                sender_number=sender_number,
                message_body=message_body
            )

            # Return a success response with the new database ID
            return JsonResponse({
                'status': 'success',
                'message_id': message.pk
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    # Reject any non-POST requests
    return JsonResponse({'error': 'Method not allowed'}, status=405)