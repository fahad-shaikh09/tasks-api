"""
Notification Microservice

Subscribes to task events from Kafka via Dapr and stores per-user
notifications. The agent's bell proxy and the MCP server fetch
notifications scoped by user_id.

Endpoints:
  GET /dapr/subscribe        — Dapr discovery
  POST /events/tasks         — Dapr CloudEvent delivery from Kafka
  POST /events/direct        — Direct HTTP fallback (same payload shape, no envelope)
  GET /notifications?user_id=X
  DELETE /notifications?user_id=X
  GET /                      — health
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlmodel import Field, Session, SQLModel, create_engine, select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persistence
#
# Notifications were previously held in a process-local list, so a pod
# restart wiped every user's bell. They now live in Postgres alongside
# the task table; the same DATABASE_URL the rest of the stack uses.
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for notification persistence")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Notification(SQLModel, table=True):
    __tablename__ = "notification"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, max_length=64)
    message: str
    event_type: str = Field(max_length=50)
    task_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


app = FastAPI(
    title="Notification Service",
    description="Per-user notifications driven by Kafka task events",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    SQLModel.metadata.create_all(engine)
    logger.info("Notification table verified/created")


# --- Dapr subscription ---

@app.get("/dapr/subscribe")
def dapr_subscribe():
    return [
        {
            "pubsubname": os.getenv("DAPR_PUBSUB_NAME", "kafka-pubsub"),
            "topic": os.getenv("DAPR_PUBSUB_TOPIC", "tasks"),
            "route": "/events/tasks",
        }
    ]


def _build_message(event_type: str, task_id: int, task: dict | None) -> str:
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


def _parse_timestamp(raw: object) -> datetime:
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _store_event(event_data: dict) -> str:
    """Build and persist a notification from a raw event payload.

    Events without a user_id are dropped — there's no one to show them to,
    and storing them globally would leak task activity across users.
    """
    user_id = event_data.get("user_id")
    if not user_id:
        logger.warning("Dropping event with no user_id: %s", event_data)
        return ""

    event_type = event_data.get("event_type", "unknown")
    task_id = event_data.get("task_id")
    task = event_data.get("task")
    timestamp = _parse_timestamp(event_data.get("timestamp"))

    message = _build_message(event_type, task_id, task)

    notification = Notification(
        user_id=user_id,
        message=message,
        event_type=event_type,
        task_id=task_id,
        timestamp=timestamp,
    )
    with Session(engine) as session:
        session.add(notification)
        session.commit()

    return message


@app.post("/events/tasks")
def handle_task_event(request_body: dict):
    """Dapr-delivered events (CloudEvents envelope)."""
    message = _store_event(request_body.get("data", {}))
    logger.info(f"Notification stored (kafka): {message}")
    return {"status": "SUCCESS"}


@app.post("/events/direct")
def handle_direct_event(request_body: dict):
    """Direct HTTP fallback from the MCP server when Dapr publish fails."""
    message = _store_event(request_body)
    logger.info(f"Notification stored (direct): {message}")
    return {"status": "ok"}


# --- Read API ---

@app.get("/")
def health():
    with Session(engine) as session:
        total = len(session.exec(select(Notification.id)).all())
    return {"service": "notification", "notifications_count": total}


@app.get("/notifications")
def get_notifications(user_id: str = Query(..., min_length=1)):
    """Return notifications for the given user, newest first."""
    with Session(engine) as session:
        rows = session.exec(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.id))
        ).all()
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "message": n.message,
            "event_type": n.event_type,
            "task_id": n.task_id,
            "timestamp": n.timestamp.isoformat(),
        }
        for n in rows
    ]


@app.delete("/notifications")
def clear_notifications(user_id: str = Query(..., min_length=1)):
    """Clear notifications for the given user."""
    with Session(engine) as session:
        rows = session.exec(
            select(Notification).where(Notification.user_id == user_id)
        ).all()
        for n in rows:
            session.delete(n)
        session.commit()
    return {"message": f"Cleared {len(rows)} notifications"}
