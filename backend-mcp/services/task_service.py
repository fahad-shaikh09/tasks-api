"""
Task Service Layer

Reusable business logic for task CRUD operations.
Imports models, database, and events from the existing backend to avoid duplication.

This service is called by MCP tools and could also be used by the FastAPI routes
if the backend is later refactored to use a service layer.
"""

import logging
from typing import Optional

from sqlalchemy import func, text
from sqlmodel import Session, select

from app.models import Task, TaskCreate
from app.events import publish_task_event_async

logger = logging.getLogger(__name__)


def _reset_task_sequence_if_empty(session: Session) -> None:
    """If the task table is empty, restart the id sequence at 1.

    Standard Postgres DELETE does not reset sequences — without this, a
    fully-emptied table would still issue id=27, 28, ... on the next
    insert. We only reset when the table is empty so we never collide
    with existing rows. Best-effort: silently no-ops on SQLite or when
    the connection lacks ALTER SEQUENCE privileges.
    """
    try:
        remaining = session.exec(select(func.count()).select_from(Task)).one()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Sequence reset skipped (count failed): {e}")
        return

    if remaining:
        return

    dialect = session.bind.dialect.name if session.bind else ""
    if dialect != "postgresql":
        return

    try:
        # SQLModel/SQLAlchemy auto-creates this sequence name for SERIAL columns.
        session.execute(text("ALTER SEQUENCE task_id_seq RESTART WITH 1"))
        session.commit()
        logger.info("Task table empty — id sequence reset to 1")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Sequence reset skipped (ALTER failed): {e}")


async def create_task(
    session: Session, title: str, description: str, status: Optional[str] = None
) -> Task:
    """Create a new task, persist it, and publish a Kafka event."""
    task_data = TaskCreate(title=title, description=description)
    if status:
        task_data.status = status

    db_task = Task.model_validate(task_data)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    await publish_task_event_async("task-created", db_task.id, db_task.model_dump())
    logger.info(f"Created task {db_task.id}: {db_task.title}")

    return db_task


def list_tasks(
    session: Session,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Task], int]:
    """List tasks with optional filtering and pagination, ordered by id."""
    statement = select(Task)
    count_statement = select(Task)

    if status:
        statement = statement.where(Task.status == status)
        count_statement = count_statement.where(Task.status == status)

    total = len(session.exec(count_statement).all())
    # ORDER BY id is essential — without it Postgres returns rows in an
    # arbitrary order, which makes ids look "random" to the end user.
    tasks = session.exec(
        statement.order_by(Task.id).offset(offset).limit(limit)
    ).all()

    return tasks, total


def get_task(session: Session, task_id: int) -> Optional[Task]:
    """Fetch a single task by ID."""
    return session.get(Task, task_id)


async def update_task(
    session: Session,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Task]:
    """Update an existing task's fields and publish an update event."""
    db_task = session.get(Task, task_id)
    if not db_task:
        return None

    if title is not None:
        db_task.title = title
    if description is not None:
        db_task.description = description
    if status is not None:
        db_task.status = status

    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    await publish_task_event_async("task-updated", db_task.id, db_task.model_dump())
    logger.info(f"Updated task {db_task.id}")

    return db_task


async def delete_task(session: Session, task_id: int) -> bool:
    """Delete a task and publish a deletion event."""
    task = session.get(Task, task_id)
    if not task:
        return False

    session.delete(task)
    session.commit()

    _reset_task_sequence_if_empty(session)

    await publish_task_event_async("task-deleted", task_id, None)
    logger.info(f"Deleted task {task_id}")

    return True
