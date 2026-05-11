import os
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import httpx

# Backend API URL - configurable via environment variable
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Notification service URL - the frontend fetches notifications from here
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8002")

app = FastAPI(title="Tasks Frontend", description="Frontend UI for Tasks API")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request):
    """Home page - displays all tasks"""
    tasks = []
    error = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/tasks")
            if response.status_code == 200:
                tasks = response.json()
    except httpx.RequestError as e:
        error = f"Could not connect to backend: {str(e)}"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"tasks": tasks, "error": error},
    )


@app.get("/tasks/new")
async def new_task_form(request: Request):
    """Display form to create a new task"""
    return templates.TemplateResponse(
        request=request,
        name="task_form.html",
        context={"task": None, "action": "Create"},
    )


@app.post("/tasks/new")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form("")
):
    """Create a new task"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/tasks",
                json={"title": title, "description": description}
            )
            if response.status_code == 200:
                return RedirectResponse(url="/", status_code=303)
            else:
                error = response.json().get("detail", "Failed to create task")
                return templates.TemplateResponse(
                    request=request,
                    name="task_form.html",
                    context={"task": None, "action": "Create", "error": error},
                )
    except httpx.RequestError as e:
        return templates.TemplateResponse(
            request=request,
            name="task_form.html",
            context={"task": None, "action": "Create", "error": str(e)},
        )


@app.get("/tasks/{task_id}/edit")
async def edit_task_form(request: Request, task_id: int):
    """Display form to edit a task"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/tasks/{task_id}")
            if response.status_code == 200:
                task = response.json()
                return templates.TemplateResponse(
                    request=request,
                    name="task_form.html",
                    context={"task": task, "action": "Update"},
                )
            else:
                raise HTTPException(status_code=404, detail="Task not found")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/{task_id}/edit")
async def update_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str = Form("")
):
    """Update an existing task"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{BACKEND_URL}/tasks/{task_id}",
                json={"title": title, "description": description}
            )
            if response.status_code == 200:
                return RedirectResponse(url="/", status_code=303)
            else:
                error = response.json().get("detail", "Failed to update task")
                task = {"id": task_id, "title": title, "description": description}
                return templates.TemplateResponse(
                    request=request,
                    name="task_form.html",
                    context={"task": task, "action": "Update", "error": error},
                )
    except httpx.RequestError as e:
        task = {"id": task_id, "title": title, "description": description}
        return templates.TemplateResponse(
            request=request,
            name="task_form.html",
            context={"task": task, "action": "Update", "error": str(e)},
        )


@app.post("/tasks/{task_id}/delete")
async def delete_task(task_id: int):
    """Delete a task"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BACKEND_URL}/tasks/{task_id}")
            if response.status_code == 200:
                return RedirectResponse(url="/", status_code=303)
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to delete task")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notification-count")
async def notification_count():
    """Returns the notification count for the navbar badge."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NOTIFICATION_URL}/notifications", timeout=3.0)
            if response.status_code == 200:
                return {"count": len(response.json())}
    except httpx.RequestError:
        pass
    return {"count": 0}


@app.delete("/api/notification-count")
async def clear_notifications_api():
    """Clear all notifications (called from dropdown)."""
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(f"{NOTIFICATION_URL}/notifications", timeout=3.0)
    except httpx.RequestError:
        pass
    return {"status": "ok"}


@app.get("/notifications/data")
async def notifications_data():
    """Returns notifications as JSON for the dropdown panel."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NOTIFICATION_URL}/notifications", timeout=3.0)
            if response.status_code == 200:
                return response.json()
    except httpx.RequestError:
        pass
    return []


@app.get("/notifications")
async def notifications(request: Request):
    """Notifications page - fetches from the notification microservice"""
    notif_list = []
    error = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NOTIFICATION_URL}/notifications")
            if response.status_code == 200:
                notif_list = response.json()
    except httpx.RequestError as e:
        error = f"Could not connect to notification service: {str(e)}"

    return templates.TemplateResponse(
        request=request,
        name="notifications.html",
        context={"notifications": notif_list, "error": error},
    )


@app.post("/notifications/clear")
async def clear_notifications():
    """Clear all notifications"""
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(f"{NOTIFICATION_URL}/notifications")
    except httpx.RequestError:
        pass
    return RedirectResponse(url="/notifications", status_code=303)


@app.get("/tasks/{task_id}")
async def view_task(request: Request, task_id: int):
    """View a single task"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/tasks/{task_id}")
            if response.status_code == 200:
                task = response.json()
                return templates.TemplateResponse(
                    request=request,
                    name="task_detail.html",
                    context={"task": task},
                )
            else:
                raise HTTPException(status_code=404, detail="Task not found")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))
