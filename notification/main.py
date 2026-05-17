"""
Notification Microservice

This service subscribes to task events from Kafka via Dapr and creates
human-readable notifications. The frontend fetches notifications from here.

How the Dapr subscription works:
  1. On startup, the Dapr sidecar calls GET /dapr/subscribe on this app
  2. We return a list saying "subscribe to topic 'tasks' on 'kafka-pubsub'"
  3. Dapr subscribes to that Kafka topic on our behalf
  4. When a message arrives in Kafka, Dapr POSTs it to POST /events/tasks
  5. We parse the event, create a notification, and store it in memory

This is a separate microservice from the backend — it demonstrates how
Dapr pub/sub enables event-driven architectures where services communicate
through events rather than direct HTTP calls.
"""

import os
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Notification Service",
    description="Receives task events via Dapr pub/sub and serves notifications",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory notification store.
# In production, you'd use a database (PostgreSQL, Redis, etc.).
# For learning purposes, a simple list is enough to demonstrate the pattern.
notifications: list[dict] = []
notification_counter = 0


# --- Dapr Subscription Endpoints ---

@app.get("/dapr/subscribe")
def dapr_subscribe():
    """
    Dapr calls this endpoint on startup to discover subscriptions.

    We tell Dapr: "subscribe to the 'tasks' topic on 'kafka-pubsub'
    and deliver messages to POST /events/tasks"
    """
    return [
        {
            "pubsubname": os.getenv("DAPR_PUBSUB_NAME", "kafka-pubsub"),
            "topic": os.getenv("DAPR_PUBSUB_TOPIC", "tasks"),
            "route": "/events/tasks",
        }
    ]


def _store_event(event_data: dict) -> str:
    """Build a notification from a raw event payload and store it.

    Shared between the Dapr-delivered path (/events/tasks) and the
    direct-HTTP fallback (/events/direct). Returns the notification message.
    """
    global notification_counter

    event_type = event_data.get("event_type", "unknown")
    task_id = event_data.get("task_id")
    task = event_data.get("task")
    timestamp = event_data.get("timestamp", datetime.now(timezone.utc).isoformat())

    message = _build_message(event_type, task_id, task)

    notification_counter += 1
    notifications.insert(0, {
        "id": notification_counter,
        "message": message,
        "event_type": event_type,
        "task_id": task_id,
        "timestamp": timestamp,
    })
    if len(notifications) > 100:
        notifications.pop()

    return message


@app.post("/events/tasks")
def handle_task_event(request_body: dict):
    """Receives task events delivered by Dapr from Kafka (CloudEvents-wrapped)."""
    message = _store_event(request_body.get("data", {}))
    logger.info(f"Notification created (kafka): {message}")
    # Return SUCCESS to tell Dapr to ACK the message in Kafka
    return {"status": "SUCCESS"}


@app.post("/events/direct")
def handle_direct_event(request_body: dict):
    """Fallback path used when the publisher can't reach Dapr/Kafka.

    Accepts the raw event payload directly (no CloudEvents envelope).
    Schema matches what backend/app/events.py builds.
    """
    message = _store_event(request_body)
    logger.info(f"Notification created (direct): {message}")
    return {"status": "ok"}


def _build_message(event_type: str, task_id: int, task: dict | None) -> str:
    """Build a human-readable notification message from a task event."""
    task_title = f"'{task['title']}'" if task and "title" in task else f"#{task_id}"

    match event_type:
        case "task-created":
            return f"Task {task_title} was created"
        case "task-updated":
            return f"Task {task_title} was updated"
        case "task-deleted":
            return f"Task #{task_id} was deleted"
        case _:
            return f"Unknown event '{event_type}' for task #{task_id}"


# --- REST API for Frontend ---

@app.get("/")
def health():
    """Health check endpoint."""
    return {"service": "notification", "notifications_count": len(notifications)}


@app.get("/notifications")
def get_notifications():
    """Return all notifications (newest first). Called by the frontend."""
    return notifications


@app.delete("/notifications")
def clear_notifications():
    """Clear all notifications."""
    notifications.clear()
    return {"message": "All notifications cleared"}
