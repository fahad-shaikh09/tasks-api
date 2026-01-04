from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()


tasks_db = []

# Pydantic models for request and response
class TaskCreate(BaseModel):
        title: str
        description: str   
        
class TaskResponse(BaseModel):
        id: int
        title: str
        description: str        
        status: str
        
# Root endpoint
@app.get("/")
def read_root():
    return {"Tasks Count:": len(tasks_db)}

# Get all tasks
@app.get("/tasks")
def read_tasks():
    if not tasks_db:
        raise HTTPException(status_code=404, detail="No tasks found")
    return tasks_db

# Create a new task
@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate):
    # Generate new ID
    new_id = len(tasks_db) + 1

    # Create task with all required fields
    new_task = {
        "id": new_id,
        "title": task.title,
        "description": task.description,
        "status": "pending"  # default status
    }

    tasks_db.append(new_task)

    # Return just the task (not wrapped in message)
    return new_task
        
        
# Get a specific task by ID
@app.get("/tasks/{task_id}")
def read_task_by_id(task_id: int):
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")




# Update an existing task
@app.put("/tasks/{task_id}")
def update_task(task: TaskCreate, task_id: int):
    for t in tasks_db:
        if t["id"] == task_id:
            t["title"] = task.title
            t["description"] = task.description
            return {"message": "Task updated", "task": t}
    raise HTTPException(status_code=404, detail="Task not found")

# Delete a task
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    for task in tasks_db:
        if task["id"] == task_id:
            tasks_db.remove(task)
            return {"message": "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")

