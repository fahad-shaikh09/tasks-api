"""
Dapr Event Publishing Module

This module publishes task lifecycle events to Kafka via the Dapr sidecar.

How it works:
  1. Your app calls publish_task_event() after a CRUD operation
  2. This function POSTs to the Dapr sidecar at localhost:3500
  3. The Dapr sidecar writes the event to the configured Kafka topic
  4. Any service subscribed to that topic receives the event

The Dapr sidecar runs in the same pod as your app (injected by the
sidecar-injector). It's always at localhost:{DAPR_HTTP_PORT}.

Why fire-and-forget?
  The database operation already succeeded. If event publishing fails
  (e.g., Kafka is temporarily down), we log an error but don't fail
  the API response. The user's task was saved — that's what matters.
"""

import os
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# Dapr sidecar config — these env vars are set automatically by the
# Dapr sidecar (DAPR_HTTP_PORT) or by our Helm chart (PUBSUB_NAME, TOPIC).
DAPR_HTTP_PORT = os.getenv("DAPR_HTTP_PORT", "3500")
DAPR_PUBSUB_NAME = os.getenv("DAPR_PUBSUB_NAME", "kafka-pubsub")
DAPR_PUBSUB_TOPIC = os.getenv("DAPR_PUBSUB_TOPIC", "tasks")

# The Dapr publish URL follows this pattern:
# POST http://localhost:<port>/v1.0/publish/<pubsub-name>/<topic>
DAPR_PUBLISH_URL = (
    f"http://localhost:{DAPR_HTTP_PORT}"
    f"/v1.0/publish/{DAPR_PUBSUB_NAME}/{DAPR_PUBSUB_TOPIC}"
)
DAPR_HEALTHZ_URL = f"http://localhost:{DAPR_HTTP_PORT}/v1.0/healthz"

# Direct-HTTP fallback target. When Dapr publish fails, we POST the same
# payload here so notifications still reach the user even if Kafka is down.
# Kafka remains the primary path; this is a safety net, not a replacement.
NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification:8002"
)
NOTIFICATION_DIRECT_URL = f"{NOTIFICATION_SERVICE_URL}/events/direct"


def _build_payload(
    event_type: str,
    task_id: int,
    task_data: dict | None,
    user_id: str | None = None,
) -> dict:
    return {
        "event_type": event_type,
        "task_id": task_id,
        "task": task_data,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _log_publish_failure(event_type: str, task_id: int, err: Exception) -> None:
    # Surface details that actually help diagnose: URL, status code, body.
    if isinstance(err, httpx.HTTPStatusError):
        logger.error(
            "Dapr publish FAILED for %s task_id=%s url=%s status=%s body=%s",
            event_type,
            task_id,
            DAPR_PUBLISH_URL,
            err.response.status_code,
            err.response.text[:500],
        )
    else:
        logger.error(
            "Dapr publish FAILED for %s task_id=%s url=%s error=%r",
            event_type,
            task_id,
            DAPR_PUBLISH_URL,
            err,
        )


def _direct_post_sync(payload: dict) -> bool:
    try:
        r = httpx.post(NOTIFICATION_DIRECT_URL, json=payload, timeout=5.0)
        r.raise_for_status()
        logger.info("Direct-HTTP fallback OK for %s task_id=%s",
                    payload["event_type"], payload["task_id"])
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Direct-HTTP fallback FAILED url=%s error=%r",
                     NOTIFICATION_DIRECT_URL, e)
        return False


async def _direct_post_async(payload: dict) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(NOTIFICATION_DIRECT_URL, json=payload)
            r.raise_for_status()
        logger.info("Direct-HTTP fallback OK for %s task_id=%s",
                    payload["event_type"], payload["task_id"])
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Direct-HTTP fallback FAILED url=%s error=%r",
                     NOTIFICATION_DIRECT_URL, e)
        return False


def publish_task_event(
    event_type: str,
    task_id: int,
    task_data: dict | None = None,
    user_id: str | None = None,
) -> bool:
    """Publish a task event synchronously. Used by the legacy FastAPI backend.

    Primary path: Dapr → Kafka → notification service.
    If Dapr fails, falls back to a direct HTTP POST to the notification service.
    """
    payload = _build_payload(event_type, task_id, task_data, user_id)
    try:
        response = httpx.post(DAPR_PUBLISH_URL, json=payload, timeout=5.0)
        response.raise_for_status()
        logger.info(
            "Dapr publish OK for %s task_id=%s topic=%s/%s",
            event_type, task_id, DAPR_PUBSUB_NAME, DAPR_PUBSUB_TOPIC,
        )
        return True
    except Exception as e:  # noqa: BLE001
        _log_publish_failure(event_type, task_id, e)
        return _direct_post_sync(payload)


async def publish_task_event_async(
    event_type: str,
    task_id: int,
    task_data: dict | None = None,
    user_id: str | None = None,
) -> bool:
    """Async variant used by the MCP service layer.

    Same Dapr-primary + direct-HTTP-fallback semantics as the sync version.
    """
    payload = _build_payload(event_type, task_id, task_data, user_id)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(DAPR_PUBLISH_URL, json=payload)
            response.raise_for_status()
        logger.info(
            "Dapr publish OK for %s task_id=%s topic=%s/%s",
            event_type, task_id, DAPR_PUBSUB_NAME, DAPR_PUBSUB_TOPIC,
        )
        return True
    except Exception as e:  # noqa: BLE001
        _log_publish_failure(event_type, task_id, e)
        return await _direct_post_async(payload)


async def verify_dapr_publish_ready() -> bool:
    """Probe the Dapr sidecar's health endpoint at startup.

    Logs a loud warning if the sidecar isn't reachable so we know
    immediately (instead of discovering it only when a publish fails).
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(DAPR_HEALTHZ_URL)
            if r.status_code in (200, 204):
                logger.info(
                    "Dapr sidecar reachable — publishing to %s/%s via %s",
                    DAPR_PUBSUB_NAME,
                    DAPR_PUBSUB_TOPIC,
                    DAPR_PUBLISH_URL,
                )
                return True
            logger.warning(
                "Dapr sidecar healthz returned %s (expected 200/204) — events may not publish",
                r.status_code,
            )
            return False
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Dapr sidecar NOT reachable at %s (%r). "
            "Task events will NOT reach Kafka until the sidecar is up. "
            "Check that the pod has the dapr.io/enabled annotation.",
            DAPR_HEALTHZ_URL,
            e,
        )
        return False
