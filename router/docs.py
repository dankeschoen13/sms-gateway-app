from drf_spectacular.utils import extend_schema
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