from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.core.config import settings
from app.core.database import create_db_and_tables, get_session
from app.models import Task, TaskCreate, TaskResponse


# Initialize FastAPI with settings from config
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event - create database tables
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
        
# Root endpoint
@app.get("/")
def read_root(session: Session = Depends(get_session)):
    statement = select(Task)
    tasks = session.exec(statement).all()
    return {"Tasks Count": len(tasks)}

# Get all tasks
@app.get("/tasks", response_model=list[TaskResponse])
def read_tasks(session: Session = Depends(get_session)):
    statement = select(Task)
    tasks = session.exec(statement).all()
    return tasks

# Create a new task
@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, session: Session = Depends(get_session)):
    # Convert TaskCreate to Task (database model)
    db_task = Task.model_validate(task)

    # Add to database
    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    return db_task
        
        
# Get a specific task by ID
@app.get("/tasks/{task_id}", response_model=TaskResponse)
def read_task_by_id(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task




# Update an existing task
@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: TaskCreate, session: Session = Depends(get_session)):
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task fields
    db_task.title = task.title
    db_task.description = task.description

    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    return db_task

# Delete a task
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session.delete(task)
    session.commit()

    return {"message": "Task deleted"}

