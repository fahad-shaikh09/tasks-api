import pytest
from fastapi.testclient import TestClient
from main import app, tasks_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_tasks_db():
    """Reset tasks_db before each test"""
    tasks_db.clear()
    yield
    tasks_db.clear()


class TestRootEndpoint:
    def test_read_root(self):
        """Test root endpoint returns task count"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Tasks Count:": 0}

    def test_read_root_with_tasks(self):
        """Test root endpoint with tasks in database"""
        tasks_db.append({"id": 1, "title": "Test", "description": "Test", "status": "pending"})
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Tasks Count:": 1}


class TestGetAllTasks:
    def test_get_tasks_empty(self):
        """Test GET /tasks when no tasks exist"""
        response = client.get("/tasks")
        assert response.status_code == 404
        assert response.json() == {"detail": "No tasks found"}

    def test_get_tasks_success(self):
        """Test GET /tasks returns all tasks"""
        tasks_db.append({"id": 1, "title": "Task 1", "description": "Description 1", "status": "pending"})
        tasks_db.append({"id": 2, "title": "Task 2", "description": "Description 2", "status": "completed"})

        response = client.get("/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["title"] == "Task 1"
        assert response.json()[1]["title"] == "Task 2"


class TestCreateTask:
    def test_create_task_success(self):
        """Test POST /tasks creates a new task"""
        task_data = {
            "title": "New Task",
            "description": "New Description"
        }
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "New Task"
        assert data["description"] == "New Description"
        assert data["status"] == "pending"

        # Verify task was added to database
        assert len(tasks_db) == 1
        assert tasks_db[0]["title"] == "New Task"

    def test_create_multiple_tasks(self):
        """Test creating multiple tasks generates unique IDs"""
        task1 = {"title": "Task 1", "description": "Desc 1"}
        task2 = {"title": "Task 2", "description": "Desc 2"}

        response1 = client.post("/tasks", json=task1)
        response2 = client.post("/tasks", json=task2)

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["id"] == 1
        assert response2.json()["id"] == 2

    def test_create_task_missing_title(self):
        """Test POST /tasks with missing title field"""
        task_data = {"description": "Description only"}
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 422  # Unprocessable Entity

    def test_create_task_missing_description(self):
        """Test POST /tasks with missing description field"""
        task_data = {"title": "Title only"}
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 422

    def test_create_task_empty_fields(self):
        """Test POST /tasks with empty strings"""
        task_data = {"title": "", "description": ""}
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200  # Empty strings are valid


class TestGetTaskById:
    def test_get_task_by_id_success(self):
        """Test GET /tasks/{task_id} returns specific task"""
        tasks_db.append({"id": 1, "title": "Task 1", "description": "Description 1", "status": "pending"})
        tasks_db.append({"id": 2, "title": "Task 2", "description": "Description 2", "status": "completed"})

        response = client.get("/tasks/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["title"] == "Task 1"

    def test_get_task_by_id_not_found(self):
        """Test GET /tasks/{task_id} with non-existent ID"""
        response = client.get("/tasks/999")
        assert response.status_code == 404
        assert response.json() == {"detail": "Task not found"}

    def test_get_task_by_id_invalid_type(self):
        """Test GET /tasks/{task_id} with invalid ID type"""
        response = client.get("/tasks/invalid")
        assert response.status_code == 422  # Validation error


class TestUpdateTask:
    def test_update_task_success(self):
        """Test PUT /tasks/{task_id} updates existing task"""
        tasks_db.append({"id": 1, "title": "Old Title", "description": "Old Description", "status": "pending"})

        update_data = {"title": "Updated Title", "description": "Updated Description"}
        response = client.put("/tasks/1", json=update_data)

        assert response.status_code == 200
        assert response.json()["message"] == "Task updated"
        assert response.json()["task"]["title"] == "Updated Title"
        assert response.json()["task"]["description"] == "Updated Description"

        # Verify database was updated
        assert tasks_db[0]["title"] == "Updated Title"
        assert tasks_db[0]["description"] == "Updated Description"

    def test_update_task_not_found(self):
        """Test PUT /tasks/{task_id} with non-existent ID"""
        update_data = {"title": "New Title", "description": "New Description"}
        response = client.put("/tasks/999", json=update_data)

        assert response.status_code == 404
        assert response.json() == {"detail": "Task not found"}

    def test_update_task_missing_fields(self):
        """Test PUT /tasks/{task_id} with missing fields"""
        tasks_db.append({"id": 1, "title": "Title", "description": "Description", "status": "pending"})

        update_data = {"title": "Only Title"}
        response = client.put("/tasks/1", json=update_data)

        assert response.status_code == 422  # Missing description field

    def test_update_task_preserves_status(self):
        """Test that updating a task preserves its status"""
        tasks_db.append({"id": 1, "title": "Title", "description": "Description", "status": "completed"})

        update_data = {"title": "New Title", "description": "New Description"}
        response = client.put("/tasks/1", json=update_data)

        assert response.status_code == 200
        # Status should remain unchanged
        assert tasks_db[0]["status"] == "completed"


class TestIntegration:
    def test_full_crud_workflow(self):
        """Test complete CRUD workflow"""
        # Create a task
        create_response = client.post("/tasks", json={"title": "Test Task", "description": "Test Description"})
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]

        # Get all tasks
        get_all_response = client.get("/tasks")
        assert get_all_response.status_code == 200
        assert len(get_all_response.json()) == 1

        # Get specific task
        get_one_response = client.get(f"/tasks/{task_id}")
        assert get_one_response.status_code == 200
        assert get_one_response.json()["title"] == "Test Task"

        # Update task
        update_response = client.put(f"/tasks/{task_id}", json={"title": "Updated Task", "description": "Updated Description"})
        assert update_response.status_code == 200
        assert update_response.json()["task"]["title"] == "Updated Task"

        # Verify update
        verify_response = client.get(f"/tasks/{task_id}")
        assert verify_response.json()["title"] == "Updated Task"
