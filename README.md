# Tasks API

A RESTful API built with FastAPI for managing tasks with PostgreSQL database persistence. This project includes comprehensive pytest test coverage and demonstrates production-ready CRUD operations.

## Features

- ✅ Create, read, update, delete tasks
- ✅ PostgreSQL database with Neon hosting
- ✅ SQLModel ORM for type-safe database operations
- ✅ Environment-based configuration with pydantic-settings
- ✅ CORS middleware support
- ✅ Comprehensive test coverage with pytest
- ✅ FastAPI automatic documentation (Swagger UI)
- ✅ Request/response validation with Pydantic
- ✅ Automatic database table creation on startup

## Project Structure

```
tasks-api/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py      # Settings and environment configuration
│   │   └── database.py    # Database engine and session management
│   └── models/
│       ├── __init__.py
│       └── task.py        # SQLModel database models
├── main.py                # FastAPI application with endpoints
├── test_main.py           # Pytest test suite
├── .env                   # Environment variables (not in git)
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── pyproject.toml         # Project dependencies
├── uv.lock                # Lock file for dependencies
└── README.md              # This file
```

## Setup Instructions

You can run this application in two ways:
1. **Local Development** - Python virtual environment
2. **Docker** - Containerized with Neon or Local PostgreSQL

### Prerequisites

- Python 3.13+
- uv (Python package manager)
- PostgreSQL database (we use [Neon](https://neon.tech) - serverless Postgres)
- Docker (optional - for containerized deployment)

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
   uv add pydantic-settings
   uv add sqlmodel
   uv add psycopg2-binary
   ```

5. **Set up PostgreSQL database:**
   - Create a PostgreSQL database (recommended: [Neon](https://neon.tech) for free serverless Postgres)
   - Copy the connection string (format: `postgresql://user:password@host:port/dbname`)

6. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set your database connection:
   ```bash
   DATABASE_URL=postgresql://your-user:your-password@your-host:5432/your-database
   ```

7. **Database tables will be created automatically** when you first run the application.

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

## Docker Deployment

This project supports Docker deployment with two database configurations:

### 🐳 Quick Start with Docker:

**Option 1: Local PostgreSQL (Development)**
```bash
# Start app + PostgreSQL + pgAdmin
docker-compose up -d

# Access:
# - API: http://localhost:8000
# - pgAdmin: http://localhost:5050 (admin@admin.com / admin)
```

**Option 2: Neon PostgreSQL (Cloud/Production)**
```bash
# Create .env file with Neon DATABASE_URL
echo "DATABASE_URL=postgresql://user:pass@endpoint.neon.tech/db?sslmode=require" > .env

# Start app only (connects to Neon)
docker-compose -f docker-compose.neon.yml up -d
```

### 📦 Pre-built Docker Images:

Pull from Docker Hub (if published):
```bash
# For Neon PostgreSQL
docker pull <username>/<repo>:v1-neon

# For Local PostgreSQL
docker pull <username>/<repo>:v1-local-db
```

### 🚀 Build and Push New Versions:

Use the automated script to build and push both images:
```bash
./build-and-push.sh
# Enter your Docker Hub username and repository name
# Script auto-detects latest version and increments by 1
```

### 📚 Complete Docker Documentation:

See **[DOCKER-SETUP.md](./DOCKER-SETUP.md)** for:
- Detailed setup instructions
- Dockerfile differences (Dockerfile.neon vs Dockerfile.local)
- docker-compose configurations
- Troubleshooting guide
- Switching between Neon and Local PostgreSQL

## API Endpoints

### Root
- `GET /` - Get task count

### Tasks
- `GET /tasks` - Get all tasks
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get a specific task by ID
- `PUT /tasks/{task_id}` - Update an existing task
- `DELETE /tasks/{task_id}` - Delete a task by ID

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

## Database Setup

This application uses **PostgreSQL** for data persistence. We recommend using [Neon](https://neon.tech) for free serverless PostgreSQL hosting.

### Quick Database Setup with Neon:

1. Go to [https://neon.tech](https://neon.tech) and sign up
2. Create a new project
3. Copy the connection string (looks like: `postgresql://user:pass@host/dbname`)
4. Add it to your `.env` file as `DATABASE_URL`

### Database Connection String Format:

```
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
```

### What Happens on Startup:

When you start the application, it will:
1. Connect to your PostgreSQL database
2. Automatically create the `task` table if it doesn't exist
3. Start accepting requests

No manual database migrations needed for this project!

## Environment Configuration

This project uses **pydantic-settings** for environment-based configuration. Settings can be configured through environment variables or a `.env` file.

### Configuration Files

- **`app/core/config.py`** - Settings class with all configurable options
- **`.env.example`** - Template showing all available environment variables
- **`.env`** - Your actual configuration (git-ignored)

### Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `PROJECT_NAME` | "Tasks API" | Name of the project |
| `VERSION` | "1.0.0" | API version |
| `DESCRIPTION` | "A FastAPI application..." | API description |
| `HOST` | "0.0.0.0" | Server host |
| `PORT` | 8000 | Server port |
| `ALLOWED_ORIGINS` | `["http://localhost:3000", ...]` | CORS allowed origins |
| `ENVIRONMENT` | "development" | Environment (development/staging/production) |
| `DEBUG` | True | Debug mode |
| `DATABASE_URL` | **Required** | PostgreSQL connection string |
| `SECRET_KEY` | (change in production!) | Secret key for JWT tokens |
| `ALGORITHM` | "HS256" | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Token expiration time |
| `MAX_TASKS_PER_USER` | 100 | Maximum tasks per user |
| `DEFAULT_TASK_STATUS` | "pending" | Default status for new tasks |

### How to Use Settings

**In your code:**
```python
from app.core.config import settings

# Access any setting
print(settings.PROJECT_NAME)  # "Tasks API"
print(settings.DEFAULT_TASK_STATUS)  # "pending"
```

**Override via .env file:**
```bash
# .env
PROJECT_NAME=My Custom Tasks API
DEFAULT_TASK_STATUS=todo
MAX_TASKS_PER_USER=50
```

**Override via environment variables:**
```bash
export PROJECT_NAME="Production Tasks API"
export DEBUG=false
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### Key Features of pydantic-settings

✅ **Type validation** - All settings are type-checked automatically
✅ **Default values** - Sensible defaults for all settings
✅ **Auto .env loading** - Automatically loads from `.env` file
✅ **Environment variables** - Can override with ENV vars
✅ **IDE support** - Full autocomplete and type hints

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
- **SQLModel** - SQL databases in Python with type safety (combines SQLAlchemy + Pydantic)
- **PostgreSQL** - Production-grade relational database
- **Neon** - Serverless Postgres hosting platform
- **Pydantic Settings** - Environment-based configuration management
- **Pytest** - Testing framework
- **Uvicorn** - ASGI server for running FastAPI
- **uv** - Fast Python package manager

## Database Architecture

### SQLModel Models

The project uses **SQLModel** which combines SQLAlchemy and Pydantic:

- **`TaskBase`** - Base model with shared fields
- **`Task`** - Database table model (with `table=True`)
- **`TaskCreate`** - Request model for creating tasks
- **`TaskResponse`** - Response model for API responses

### Database Session Management

- Database sessions are managed using FastAPI's dependency injection
- `get_session()` provides a session per request
- Automatic rollback on errors
- Connection pooling with `pool_pre_ping` for reliability

### Automatic Table Creation

Tables are created automatically on application startup via the `@app.on_event("startup")` decorator.

## Development Notes

- Tasks are persisted in PostgreSQL database (survive server restarts)
- Database connection uses connection pooling for performance
- SQL queries are logged in debug mode (set `DEBUG=true` in `.env`)
- Task IDs are auto-generated by PostgreSQL using sequences
- Default task status is configurable via `DEFAULT_TASK_STATUS` environment variable

## Future Enhancements

- [ ] Implement task status transitions (pending → in_progress → completed)
- [ ] Add task filtering and search capabilities
- [ ] Add authentication and user management
- [ ] Add task due dates and priorities
- [ ] Implement soft delete (archive) functionality
- [ ] Add database migrations with Alembic
- [ ] Add pagination for large task lists
- [ ] Add task assignment to users
- [ ] Implement task categories/tags

## License

MIT

## Author

Fahad
