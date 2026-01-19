# Docker Setup Guide

This project supports two Docker configurations for different database setups:

1. **Local PostgreSQL** - Database running in Docker container
2. **Neon PostgreSQL** - Cloud-hosted serverless PostgreSQL

## Configuration Files

```
tasks-api/
├── Dockerfile.local          # For local PostgreSQL setup
├── Dockerfile.neon           # For Neon cloud PostgreSQL
├── docker-compose.yml        # Local development (default)
└── docker-compose.neon.yml   # Neon cloud setup
```

---

## Option 1: Local PostgreSQL (Development)

**Use this for**: Local development with full control over database

### What's Included:
- ✅ FastAPI application container
- ✅ PostgreSQL 16 database container
- ✅ pgAdmin GUI container (port 5050)
- ✅ Persistent data volumes
- ✅ Docker network for service communication

### Quick Start:

```bash
# Start all services (app + db + pgAdmin)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes (delete data)
docker-compose down -v
```

### Access Points:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050
  - Email: `admin@admin.com`
  - Password: `admin`

### Environment Variables:

The application automatically connects to the local PostgreSQL container using:

```bash
DATABASE_URL=postgresql://postgres:postgres@db:5432/tasksdb
SECRET_KEY=dev-secret-key-change-in-production
```

### Database Configuration:

pgAdmin connection settings:
- **Host**: `db` (service name)
- **Port**: `5432`
- **Database**: `tasksdb`
- **Username**: `postgres`
- **Password**: `postgres`

### Development Workflow:

```bash
# 1. Start services
docker-compose up -d

# 2. Check if everything is running
docker-compose ps

# 3. View application logs
docker-compose logs app -f

# 4. View database logs
docker-compose logs db -f

# 5. Access database via pgAdmin
# Open http://localhost:5050

# 6. Rebuild after code changes
docker-compose up -d --build

# 7. Stop services
docker-compose down
```

---

## Option 2: Neon PostgreSQL (Cloud)

**Use this for**: Production deployment or cloud-based development

### What's Included:
- ✅ FastAPI application container
- ✅ Connection to Neon cloud PostgreSQL
- ❌ No local database container (uses Neon)
- ❌ No pgAdmin (use Neon console instead)

### Prerequisites:

1. **Create Neon Account**: https://neon.tech
2. **Create a Neon Project**
3. **Copy Connection String**: Will look like:
   ```
   postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Setup:

1. **Create `.env` file** in project root:

```bash
# .env
DATABASE_URL=postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=your-production-secret-key-here
ENVIRONMENT=production
DEBUG=false
```

2. **Start the application**:

```bash
# Start with Neon configuration
docker-compose -f docker-compose.neon.yml up -d

# View logs
docker-compose -f docker-compose.neon.yml logs -f

# Stop
docker-compose -f docker-compose.neon.yml down
```

### Access Points:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neon Console**: https://console.neon.tech (for database management)

### Advantages of Neon:

- ✅ **Serverless**: Auto-scales, auto-suspends when idle
- ✅ **Branching**: Create database branches for testing
- ✅ **Backups**: Automatic point-in-time recovery
- ✅ **Free Tier**: Generous free tier for development
- ✅ **No Container Management**: No need to run PostgreSQL locally

### Production Deployment:

```bash
# 1. Build image
docker build -f Dockerfile.neon -t fahadshaikh/tasks-api:latest .

# 2. Push to registry
docker push fahadshaikh/tasks-api:latest

# 3. Deploy to server with environment variables
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:password@endpoint.neon.tech/db?sslmode=require" \
  -e SECRET_KEY="your-secret-key" \
  -e ENVIRONMENT="production" \
  fahadshaikh/tasks-api:latest
```

---

## Dockerfile Differences

Both Dockerfiles are nearly identical, with subtle differences:

### Dockerfile.local
- Optimized for local development
- Works with docker-compose.yml
- Connects to local PostgreSQL container

### Dockerfile.neon
- Optimized for cloud deployment
- Works with docker-compose.neon.yml
- Connects to Neon PostgreSQL via connection string
- Suitable for production use

Both use:
- ✅ Multi-stage builds (smaller images)
- ✅ Non-root user (security)
- ✅ Health checks (monitoring)
- ✅ Python 3.13 slim base
- ✅ UV package manager (fast installs)

---

## Comparison

| Feature | Local Setup | Neon Setup |
|---------|-------------|------------|
| **Database Location** | Docker container | Neon cloud |
| **Startup Time** | ~10 seconds | ~2 seconds |
| **Data Persistence** | Docker volumes | Cloud storage |
| **Database GUI** | pgAdmin (included) | Neon Console |
| **Cost** | Free (local) | Free tier available |
| **Scaling** | Manual | Automatic |
| **Backups** | Manual | Automatic |
| **Best For** | Development | Production/Cloud |

---

## Switching Between Setups

### From Local to Neon:

```bash
# 1. Stop local setup
docker-compose down

# 2. Create Neon database
# Visit https://neon.tech and create project

# 3. Create .env file with Neon DATABASE_URL
echo "DATABASE_URL=postgresql://..." > .env

# 4. Start Neon setup
docker-compose -f docker-compose.neon.yml up -d
```

### From Neon to Local:

```bash
# 1. Stop Neon setup
docker-compose -f docker-compose.neon.yml down

# 2. Start local setup
docker-compose up -d

# 3. Data starts fresh (or restore from backup)
```

---

## Troubleshooting

### Local Setup Issues:

**Database connection refused:**
```bash
# Check if database is healthy
docker-compose ps

# View database logs
docker-compose logs db

# Restart services
docker-compose restart
```

**Port already in use:**
```bash
# Check what's using port 5432
lsof -i :5432

# Stop conflicting service or change port in docker-compose.yml
```

### Neon Setup Issues:

**Connection timeout:**
- Check DATABASE_URL is correct
- Ensure `?sslmode=require` is in connection string
- Verify Neon project is active (not suspended)

**Authentication failed:**
- Verify username and password in connection string
- Check Neon console for connection details

---

## Best Practices

### Local Development:
```bash
# Use local setup for day-to-day development
docker-compose up -d

# Regular backups (optional)
docker exec tasks-api-db pg_dump -U postgres tasksdb > backup.sql
```

### Staging/Production:
```bash
# Use Neon setup for deployed environments
docker-compose -f docker-compose.neon.yml up -d

# Use production secrets
# Never commit .env files
# Use environment variables in CI/CD
```

### CI/CD Pipeline:
```bash
# Build
docker build -f Dockerfile.neon -t myapp:$VERSION .

# Test (use test Neon branch)
DATABASE_URL=<neon-test-branch> pytest

# Deploy
docker push myapp:$VERSION
```

---

## Additional Commands

### View all containers:
```bash
docker ps -a
```

### Check container logs:
```bash
# Local setup
docker-compose logs -f app
docker-compose logs -f db

# Neon setup
docker-compose -f docker-compose.neon.yml logs -f app
```

### Rebuild images:
```bash
# Local
docker-compose build --no-cache

# Neon
docker-compose -f docker-compose.neon.yml build --no-cache
```

### Database migrations:
```bash
# Run migrations (both setups)
docker-compose exec app alembic upgrade head
```

---

## Summary

- **Use `docker-compose.yml` (local)** for development with full database control
- **Use `docker-compose.neon.yml` (cloud)** for production or cloud-based development
- Both configurations use the same application code
- Switch between them easily based on your needs
