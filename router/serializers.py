from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Valid Payload',
            value={'sender_number': '+639123456789', 'message_body': 'Hello support!'},
            request_only=True
        )
    ]
)

class WebhookPayloadSerializer(serializers.Serializer):
    sender_number = serializers.CharField(required=True)
    message_body = serializers.CharField(required=True)

class WebhookSuccessSerializer(serializers.Serializer):
    status = serializers.CharField(default='success')
    department_routed = serializers.CharField(default='<department>')
    message_id = serializers.CharField(default='<message_id>')

class WebhookError400Serializer(serializers.Serializer):
    error = serializers.CharField(default='Missing required fields')

class WebhookError429Serializer(serializers.Serializer):
    error = serializers.CharField(default='Too Many Requests')