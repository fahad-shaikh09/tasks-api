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


class TaskCreate(TaskBase):
    """
    Model for creating a new task.
    Used for POST requests - doesn't include ID or status (uses default).
    """
    pass


class TaskResponse(TaskBase):
    """
    Model for task responses.
    Used for API responses - includes the ID.
    """
    id: int
