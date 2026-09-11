from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .serializers import (
    WebhookPayloadSerializer,
    WebhookSuccessSerializer,
    WebhookError400Serializer,
    WebhookError429Serializer,
)

webhook_swagger_doc = extend_schema(
    summary="Receive incoming SMS (Webhook)",
    description="Endpoint for the SMS provider to push incoming messages.",
    request=WebhookPayloadSerializer,
    responses={
        201: WebhookSuccessSerializer,
        400: WebhookError400Serializer,
        429: WebhookError429Serializer,
    }
)

report_swagger_doc = extend_schema(
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