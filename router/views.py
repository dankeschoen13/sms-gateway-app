from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .services import determine_department, is_rate_limited, prepare_breakdown
from .serializers import WebhookPayloadSerializer
from .models import Message
from .docs import webhook_swagger_doc, report_swagger_doc  # Updated to relative import


@webhook_swagger_doc
@api_view(['POST'])
@csrf_exempt
def sms_webhook(request):
    serializer = WebhookPayloadSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({'error': 'Missing required fields'}, status=400)

    # Extract safely from the serializer, completely dropping the manual checks
    sender_number = serializer.validated_data['sender_number']
    message_body = serializer.validated_data['message_body']

    # 1. Check Rate Limit First
    if is_rate_limited(sender_number):
        Message.objects.create(
            sender_number=sender_number,
            message_body=message_body,
            is_blocked=True
        )
        return Response({'error': 'Too Many Requests'}, status=429)

    # 2. Route the Message
    department = determine_department(message_body)

    # 3. Save the Successful Message
    message = Message.objects.create(
        sender_number=sender_number,
        message_body=message_body,
        department=department,
        is_blocked=False
    )

    return Response({
        'status': 'success',
        'department_routed': department,
        'message_id': message.pk
    }, status=201)


@report_swagger_doc
@api_view(['GET'])
def sms_report(request):
    """
    GET /api/sms/report/?period=daily|weekly|monthly
    Defaults to 'daily' if no parameter is provided.
    """
    period = request.GET.get('period', 'daily').lower()
    today = timezone.localdate()

    if period == 'weekly':
        start_date = today - timedelta(days=7)
    elif period == 'monthly':
        start_date = today - timedelta(days=30)
    elif period == 'daily':
        start_date = today
    else:
        return Response(
            {'error': 'Invalid period parameter. Use daily, weekly, or monthly.'},
            status=400
        )

    total_processed, total_blocked, breakdown = prepare_breakdown(start_date=start_date)

    return Response({
        'period': period,
        'start_date': start_date,
        'total_messages_processed': total_processed,
        'total_rate_limit_rejections': total_blocked,
        'department_breakdown': breakdown
    }, status=200)