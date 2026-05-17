"""
Task Service Layer

Per-user scoped CRUD operations. Every function takes the calling user's
id and filters/asserts ownership accordingly. The MCP server's auth
middleware is responsible for supplying the user_id.
"""

import logging
from typing import Optional

from sqlalchemy import func, text
from sqlmodel import Session, select

from app.models import Task, TaskCreate
from app.events import publish_task_event_async

logger = logging.getLogger(__name__)


def _reset_task_sequence_if_empty(session: Session) -> None:
    """If the task table is globally empty, restart the id sequence at 1.

    Best-effort: silently no-ops on SQLite or when the connection lacks
    ALTER SEQUENCE privileges.
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
        session.execute(text("ALTER SEQUENCE task_id_seq RESTART WITH 1"))
        session.commit()
        logger.info("Task table empty — id sequence reset to 1")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Sequence reset skipped (ALTER failed): {e}")


async def create_task(
    session: Session,
    user_id: str,
    title: str,
    description: str,
    status: Optional[str] = None,
) -> Task:
    """Create a new task owned by user_id, persist it, and publish an event."""
    task_data = TaskCreate(title=title, description=description)
    if status:
        task_data.status = status

    db_task = Task.model_validate(task_data, update={"user_id": user_id})
    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    await publish_task_event_async(
        "task-created", db_task.id, db_task.model_dump(), user_id=user_id
    )
    logger.info(f"Created task {db_task.id} for user {user_id}: {db_task.title}")

    return db_task


def list_tasks(
    session: Session,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Task], int]:
    """List tasks belonging to user_id, ordered by id."""
    statement = select(Task).where(Task.user_id == user_id)
    count_statement = select(Task).where(Task.user_id == user_id)

    if status:
        statement = statement.where(Task.status == status)
        count_statement = count_statement.where(Task.status == status)

    total = len(session.exec(count_statement).all())
    tasks = session.exec(
        statement.order_by(Task.id).offset(offset).limit(limit)
    ).all()

    return tasks, total


def get_task(session: Session, user_id: str, task_id: int) -> Optional[Task]:
    """Fetch a task by id only if it belongs to user_id."""
    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
        return None
    return task


async def update_task(
    session: Session,
    user_id: str,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Task]:
    """Update a task only if it belongs to user_id; publish an event."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.user_id != user_id:
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

    await publish_task_event_async(
        "task-updated", db_task.id, db_task.model_dump(), user_id=user_id
    )
    logger.info(f"Updated task {db_task.id} for user {user_id}")

    return db_task


async def delete_task(session: Session, user_id: str, task_id: int) -> bool:
    """Delete a task only if it belongs to user_id; publish an event."""
    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
        return False

    session.delete(task)
    session.commit()

    _reset_task_sequence_if_empty(session)

    await publish_task_event_async(
        "task-deleted", task_id, None, user_id=user_id
    )
    logger.info(f"Deleted task {task_id} for user {user_id}")

    return True
