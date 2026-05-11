"""
Dapr Event Publishing Module

This module publishes task lifecycle events to Kafka via the Dapr sidecar.

How it works:
  1. Your FastAPI app calls publish_task_event() after a CRUD operation
  2. This function POSTs to the Dapr sidecar at localhost:3500
  3. The Dapr sidecar writes the event to the configured Kafka topic
  4. Any service subscribed to that topic receives the event

The Dapr sidecar runs in the same pod as your app (injected by the
sidecar-injector). It's always at localhost:{DAPR_HTTP_PORT}.

Why fire-and-forget?
  The database operation already succeeded. If event publishing fails
  (e.g., Kafka is temporarily down), we log a warning but don't fail
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


def publish_task_event(
    event_type: str, task_id: int, task_data: dict | None = None
):
    """
    Publish a task event to Kafka via the Dapr sidecar.

    Args:
        event_type: One of "task-created", "task-updated", "task-deleted"
        task_id: The ID of the task
        task_data: The task's data as a dict (None for deletes)
    """
    payload = {
        "event_type": event_type,
        "task_id": task_id,
        "task": task_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        # httpx.post() is synchronous — fine here because the Dapr sidecar
        # is localhost, so latency is sub-millisecond. The sidecar handles
        # the async delivery to Kafka.
        response = httpx.post(DAPR_PUBLISH_URL, json=payload, timeout=5.0)
        response.raise_for_status()
        logger.info(f"Published {event_type} event for task {task_id}")
    except Exception as e:
        # Log but don't raise — event publishing should never break the API
        logger.warning(f"Failed to publish {event_type} event: {e}")
