# Tasks API

A RESTful API built with FastAPI for managing tasks. This project includes comprehensive pytest test coverage and demonstrates CRUD operations.

## Features

- Create, read, update tasks
- In-memory task storage
- Comprehensive test coverage with pytest
- FastAPI automatic documentation
- Request/response validation with Pydantic

## Project Structure

```
tasks-api/
├── main.py           # FastAPI application with endpoints
├── test_main.py      # Pytest test suite
├── pyproject.toml    # Project dependencies
├── uv.lock           # Lock file for dependencies
└── README.md         # This file
```

## Setup Instructions

### Prerequisites

- Python 3.13+
- uv (Python package manager)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd tasks-api
   ```

2. **Create virtual environment:**
   ```bash
   uv venv
   ```

3. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   uv add "fastapi[standard]"
   uv add pytest
   ```

## Running the Application

### Start the development server:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Command breakdown:**
- `main:app` - Import the `app` object from `main.py`
- `--host 0.0.0.0` - Make server accessible from any network interface
- `--port 8000` - Run on port 8000
- `--reload` - Auto-reload on code changes (development only)

The API will be available at: `http://localhost:8000`

### Alternative (FastAPI CLI):

```bash
uv run fastapi dev main.py
```

### Access the interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Endpoints

### Root
- `GET /` - Get task count

### Tasks
- `GET /tasks` - Get all tasks
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get a specific task by ID
- `PUT /tasks/{task_id}` - Update an existing task

### Example Request - Create Task

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Buy groceries",
    "description": "Milk, eggs, bread"
  }'
```

### Example Response

```json
{
  "id": 1,
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "status": "pending"
}
```

## Running Tests

### Run all tests:

```bash
uv run pytest test_main.py -v
```

### Run tests with coverage:

```bash
uv run pytest test_main.py -v --cov=main
```

### Run specific test class:

```bash
uv run pytest test_main.py::TestCreateTask -v
```

### Run specific test:

```bash
uv run pytest test_main.py::TestCreateTask::test_create_task_success -v
```

## Test Coverage

The test suite includes 17 tests covering:

- ✅ Root endpoint
- ✅ Get all tasks (empty and with data)
- ✅ Create task (success, validation errors, edge cases)
- ✅ Get task by ID (success, not found, invalid ID)
- ✅ Update task (success, not found, validation)
- ✅ Full CRUD workflow integration test

## Key Learnings: Pytest Fixtures & Yield

### What are Fixtures?

**Fixtures** are functions that set up conditions before tests run and optionally clean up afterward. They help avoid code duplication and ensure test isolation.

### Key Points about Fixtures:

1. **Fixtures are reusable setup functions**
   - Marked with `@pytest.fixture` decorator
   - Can be passed to tests as parameters

2. **`yield` keyword splits setup and cleanup**
   - Code **before `yield`** = Setup (runs before test)
   - Code **after `yield`** = Cleanup (runs after test)
   - The value passed to `yield` is what the test receives

3. **`autouse=True` runs fixtures automatically**
   - No need to pass fixture as parameter to tests
   - Runs before every test in the scope
   - Perfect for common setup/cleanup (like resetting database)

4. **Fixture Scopes**
   - `function` (default) - Runs once per test function
   - `class` - Runs once per test class
   - `module` - Runs once per test file
   - `session` - Runs once for entire test session

### Example from This Project:

```python
@pytest.fixture(autouse=True)
def reset_tasks_db():
    """Reset tasks_db before each test"""
    tasks_db.clear()  # ← Setup: Clear database before test
    yield             # ← Test runs here
    tasks_db.clear()  # ← Cleanup: Clear database after test
```

**Why `autouse=True`?**
- Every test needs a clean `tasks_db`
- Saves us from passing `reset_tasks_db` to every test function
- Ensures test isolation (tests don't affect each other)

### Fixture Flow:

```
Test starts
    ↓
Setup code (before yield) runs
    ↓
Test function executes
    ↓
Cleanup code (after yield) runs
    ↓
Test ends
```

### When to Use `autouse=True`:

✅ **Use when:**
- All tests need the same setup/cleanup
- Example: Resetting database, clearing cache, mocking time

❌ **Don't use when:**
- Only some tests need the fixture
- Example: Only specific tests need a database connection

## Technologies Used

- **FastAPI** - Modern web framework for building APIs
- **Pydantic** - Data validation using Python type hints
- **Pytest** - Testing framework
- **Uvicorn** - ASGI server for running FastAPI
- **uv** - Fast Python package manager

## Development Notes

- Tasks are stored in-memory (lost on server restart)
- For production, consider using a database (PostgreSQL, MongoDB, etc.)
- Task IDs are auto-generated based on list length
- Default task status is "pending"

## Future Enhancements

- [ ] Add DELETE endpoint for tasks
- [ ] Implement task status transitions (pending → in_progress → completed)
- [ ] Add database persistence (SQLite, PostgreSQL)
- [ ] Add task filtering and search
- [ ] Add authentication and user management
- [ ] Add task due dates and priorities

## License

MIT

## Author

Fahad
