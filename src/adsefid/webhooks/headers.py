from __future__ import annotations


class WebhookHeaders:
    """Header names used by adsefid.com outgoing webhook deliveries.

    `Flask`/`Werkzeug` (and most Python web frameworks) expose headers through a
    case-insensitive mapping, so these constants work regardless of the wire casing.
    """

    ID = "X-Atlas-Webhook-Id"
    SIGNATURE = "X-Atlas-Webhook-Signature"
    TIMESTAMP = "X-Atlas-Webhook-Timestamp"
    EVENT = "X-Atlas-Webhook-Event"
    ATTEMPT = "X-Atlas-Webhook-Attempt"


class WebhookEventType:
    """The `type` field values a webhook payload can carry, per doc §7.1."""

    RECEIVE = "receive"
    STATUS = "status"
    MESSENGER_STATUS = "messenger.status"
