from typing import Optional
from sqlmodel import Field, SQLModel
from app.core.config import settings


class TaskBase(SQLModel):
    """Base Task model with shared fields"""
    title: str = Field(index=True, max_length=200)
    description: str
    status: str = Field(default=settings.DEFAULT_TASK_STATUS, max_length=50)


class Task(TaskBase, table=True):
    """
    Task model for database table.
    This creates the 'task' table in the database.
    """
    __tablename__ = "task"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Owner of the task — populated from the authenticated session.
    # Indexed because every list/get/update/delete filters by it.
    user_id: str = Field(index=True, max_length=64)


class TaskCreate(TaskBase):
    """Body for creating a new task. user_id is injected server-side."""
    pass


class TaskResponse(TaskBase):
    """API response shape."""
    id: int
    user_id: str
