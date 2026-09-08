"""Python client SDK for the adsefid.com SMS Web Service API (doc v1.11.0)."""

from .async_client import AdsefidAsyncClient
from .client import AdsefidClient
from .config import SDK_VERSION, ClientConfig
from .enums import (
    LineSelector,
    TemplateParameterType,
    TemplateState,
    WebServiceMessageStatus,
    WebServiceResponseCode,
)
from .exceptions import (
    AdsefidApiError,
    AdsefidError,
    AdsefidRateLimitError,
    AdsefidTransportError,
    AdsefidValidationError,
    AdsefidWebhookVerificationError,
)
from .webhooks import (
    MessengerStatusWebhookEvent,
    ReceiveWebhookEvent,
    ReceiveWebhookItem,
    StatusWebhookEvent,
    StatusWebhookItem,
    WebhookEvent,
    WebhookEventType,
    WebhookHeaders,
    verify_and_parse_webhook,
)

__version__ = SDK_VERSION

__all__ = [
    "__version__",
    "AdsefidClient",
    "AdsefidAsyncClient",
    "ClientConfig",
    "LineSelector",
    "TemplateParameterType",
    "TemplateState",
    "WebServiceMessageStatus",
    "WebServiceResponseCode",
    "AdsefidError",
    "AdsefidValidationError",
    "AdsefidApiError",
    "AdsefidRateLimitError",
    "AdsefidTransportError",
    "AdsefidWebhookVerificationError",
    "MessengerStatusWebhookEvent",
    "ReceiveWebhookEvent",
    "ReceiveWebhookItem",
    "StatusWebhookEvent",
    "StatusWebhookItem",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookHeaders",
    "verify_and_parse_webhook",
]
