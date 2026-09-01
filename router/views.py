from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .services import determine_department, is_rate_limited, prepare_breakdown
from .models import Message


@extend_schema(
    summary="Receive incoming SMS (Webhook)",
    description="Endpoint for the SMS provider to push incoming messages.",
    request=inline_serializer(
        name='WebhookPayload',
        fields={
            'sender': serializers.CharField(),
            'message': serializers.CharField(),
        }
    ),
    examples=[
        OpenApiExample(
            'Valid Payload',
            value={'sender_number': '+639123456789', 'message_body': 'Hello support!'},
            request_only=True
        )
    ],
    responses={
        201: inline_serializer(
            name='WebhookSuccess',
            fields={'status': serializers.CharField(default='success')}
        ),
        400: inline_serializer(
            name='WebhookError',
            fields={'error': serializers.CharField(default='Missing required fields')}
        ),
        429: inline_serializer(
            name='WebhookTooManyRequests',
            fields={'error': serializers.CharField(default='Too Many Requests')}
        ),
        405: inline_serializer(
            name='WebhookInvalidMethod',
            fields={'error': serializers.CharField(default='Method not allowed')}
        )
    }
)
@api_view(['POST'])
@csrf_exempt
def sms_webhook(request):
    if request.method == 'POST':

        sender_number = request.data.get('sender_number')
        message_body = request.data.get('message_body')

        if not sender_number or not message_body:
            return Response({'error': 'Missing required fields'}, status=400)

        # 1. Check Rate Limit First ---
        # Still log the blocked attempt for our later analysis
        if is_rate_limited(sender_number):
            Message.objects.create(
                sender_number=sender_number,
                message_body=message_body,
                is_blocked=True
            )
            return Response({'error': 'Too Many Requests'}, status=429)

        # 2. Route the Message ---
        department = determine_department(message_body)

        # 3. Save the Successful Message ---
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

    return Response({'error': 'Method not allowed'}, status=405)


@extend_schema(
    summary="Retrieve SMS routing statistics",
    description="Generates an aggregated report of processed and rate-limited messages over a rolling time window.",
    parameters=[
        OpenApiParameter(
            name='period',
            type=OpenApiTypes.STR,
            location='query',
            description="The rolling time window for the report. Defaults to 'daily'.",
            enum=['daily', 'weekly', 'monthly'],
            default='daily',
        )
    ]
)
@api_view(['GET'])
def sms_report(request):
    """
    GET /api/sms/report/?period=daily|weekly|monthly
    Defaults to 'daily' if no parameter is provided.
    """
    if request.method == 'GET':

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

    return Response({'error': 'Method not allowed'}, status=405)



