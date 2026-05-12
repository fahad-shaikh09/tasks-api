"""
Task Service Layer

Reusable business logic for task CRUD operations.
Imports models, database, and events from the existing backend to avoid duplication.

This service is called by MCP tools and could also be used by the FastAPI routes
if the backend is later refactored to use a service layer.
"""

import logging
from typing import Optional

from sqlmodel import Session, select

from app.models import Task, TaskCreate
from app.events import publish_task_event

logger = logging.getLogger(__name__)


def create_task(session: Session, title: str, description: str, status: Optional[str] = None) -> Task:
    """
    Create a new task, persist it, and publish a Kafka event.

    Args:
        session: Active database session.
        title: Task title.
        description: Task description.
        status: Optional status override (defaults to config DEFAULT_TASK_STATUS).

    Returns:
        The created Task with its database-assigned ID.
    """
    task_data = TaskCreate(title=title, description=description)
    if status:
        task_data.status = status

    db_task = Task.model_validate(task_data)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    publish_task_event("task-created", db_task.id, db_task.model_dump())
    logger.info(f"Created task {db_task.id}: {db_task.title}")

    return db_task


def list_tasks(
    session: Session,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Task], int]:
    """
    List tasks with optional filtering and pagination.

    Args:
        session: Active database session.
        status: Filter by task status (e.g. "pending", "completed").
        limit: Max number of tasks to return.
        offset: Number of tasks to skip.

    Returns:
        Tuple of (tasks list, total count matching the filter).
    """
    statement = select(Task)
    count_statement = select(Task)

    if status:
        statement = statement.where(Task.status == status)
        count_statement = count_statement.where(Task.status == status)

    total = len(session.exec(count_statement).all())
    tasks = session.exec(statement.offset(offset).limit(limit)).all()

    return tasks, total


def get_task(session: Session, task_id: int) -> Optional[Task]:
    """
    Fetch a single task by ID.

    Returns:
        The Task if found, None otherwise.
    """
    return session.get(Task, task_id)


def update_task(
    session: Session,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Task]:
    """
    Update an existing task's fields and publish an update event.

    Only provided (non-None) fields are updated.

    Returns:
        The updated Task, or None if not found.
    """
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

    publish_task_event("task-updated", db_task.id, db_task.model_dump())
    logger.info(f"Updated task {db_task.id}")

    return db_task


def delete_task(session: Session, task_id: int) -> bool:
    """
    Delete a task and publish a deletion event.

    Returns:
        True if the task was found and deleted, False if not found.
    """
    task = session.get(Task, task_id)
    if not task:
        return False

    session.delete(task)
    session.commit()

    publish_task_event("task-deleted", task_id, None)
    logger.info(f"Deleted task {task_id}")

    return True
