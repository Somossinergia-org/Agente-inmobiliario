"""Sistema de webhooks para notificar eventos a sistemas externos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

import httpx


class WebhookEvent(Enum):
    LEAD_CREATED = "lead.created"
    LEAD_QUALIFIED = "lead.qualified"
    LEAD_SCORE_CHANGED = "lead.score_changed"
    LEAD_CONVERTED = "lead.converted"
    LEAD_HOT = "lead.hot"
    LEAD_ASSIGNED = "lead.assigned"
    VISIT_SCHEDULED = "visit.scheduled"
    MESSAGE_RECEIVED = "message.received"
    PROPERTY_MATCHED = "property.matched"


@dataclass
class WebhookConfig:
    """Configuración de un webhook."""
    id: str
    url: str
    events: list[WebhookEvent]
    active: bool = True
    secret: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    failure_count: int = 0
    last_triggered: Optional[datetime] = None


@dataclass
class WebhookDelivery:
    """Registro de un envío de webhook."""
    id: str
    webhook_id: str
    event: str
    payload: dict
    status_code: int | None = None
    response_body: str = ""
    success: bool = False
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class WebhookManager:
    """Gestor de webhooks para notificaciones en tiempo real."""

    def __init__(self):
        self.webhooks: dict[str, WebhookConfig] = {}
        self.deliveries: list[WebhookDelivery] = []
        self._max_retries = 3
        self._max_failures = 10

    def register_webhook(
        self,
        url: str,
        events: list[str],
        secret: str = "",
        description: str = "",
    ) -> WebhookConfig:
        """Registra un nuevo webhook."""
        webhook_id = f"WH-{uuid4().hex[:6].upper()}"
        event_list = []
        for e in events:
            try:
                event_list.append(WebhookEvent(e))
            except ValueError:
                continue

        webhook = WebhookConfig(
            id=webhook_id,
            url=url,
            events=event_list,
            secret=secret,
            description=description,
        )
        self.webhooks[webhook_id] = webhook
        return webhook

    def unregister_webhook(self, webhook_id: str) -> bool:
        return self.webhooks.pop(webhook_id, None) is not None

    def list_webhooks(self) -> list[dict]:
        return [
            {
                "id": wh.id,
                "url": wh.url,
                "events": [e.value for e in wh.events],
                "active": wh.active,
                "description": wh.description,
                "failure_count": wh.failure_count,
                "last_triggered": wh.last_triggered.isoformat() if wh.last_triggered else None,
            }
            for wh in self.webhooks.values()
        ]

    async def trigger(self, event: str, payload: dict) -> list[WebhookDelivery]:
        """Dispara un evento a todos los webhooks suscritos."""
        try:
            webhook_event = WebhookEvent(event)
        except ValueError:
            return []

        deliveries = []
        for wh in self.webhooks.values():
            if not wh.active:
                continue
            if wh.failure_count >= self._max_failures:
                wh.active = False
                continue
            if webhook_event not in wh.events:
                continue

            delivery = await self._send(wh, event, payload)
            deliveries.append(delivery)

        return deliveries

    def trigger_sync(self, event: str, payload: dict) -> list[dict]:
        """Versión síncrona para registrar el evento (no envía HTTP, solo registra)."""
        try:
            webhook_event = WebhookEvent(event)
        except ValueError:
            return []

        results = []
        for wh in self.webhooks.values():
            if not wh.active or webhook_event not in wh.events:
                continue
            if wh.failure_count >= self._max_failures:
                wh.active = False
                continue

            delivery = WebhookDelivery(
                id=f"DEL-{uuid4().hex[:6].upper()}",
                webhook_id=wh.id,
                event=event,
                payload=payload,
                success=True,  # Queued
                status_code=None,
            )
            self.deliveries.append(delivery)
            wh.last_triggered = datetime.now()
            results.append({
                "delivery_id": delivery.id,
                "webhook_id": wh.id,
                "event": event,
                "status": "queued",
            })

        return results

    async def _send(self, webhook: WebhookConfig, event: str, payload: dict) -> WebhookDelivery:
        """Envía el payload al webhook."""
        delivery_id = f"DEL-{uuid4().hex[:6].upper()}"

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
        }
        if webhook.secret:
            headers["X-Webhook-Secret"] = webhook.secret

        body = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": payload,
        }

        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event=event,
            payload=body,
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook.url, json=body, headers=headers)
                delivery.status_code = response.status_code
                delivery.response_body = response.text[:500]
                delivery.success = 200 <= response.status_code < 300

                if delivery.success:
                    webhook.failure_count = 0
                else:
                    webhook.failure_count += 1
        except Exception as e:
            delivery.error = str(e)
            delivery.success = False
            webhook.failure_count += 1

        webhook.last_triggered = datetime.now()
        self.deliveries.append(delivery)
        return delivery

    def get_deliveries(self, webhook_id: str | None = None, limit: int = 50) -> list[dict]:
        """Obtiene historial de envíos."""
        deliveries = self.deliveries
        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]

        return [
            {
                "id": d.id,
                "webhook_id": d.webhook_id,
                "event": d.event,
                "success": d.success,
                "status_code": d.status_code,
                "error": d.error,
                "timestamp": d.timestamp.isoformat(),
            }
            for d in deliveries[-limit:]
        ]
