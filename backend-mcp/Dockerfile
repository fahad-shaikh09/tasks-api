# ============================================================
# MCP Server Dockerfile (OpenShift / CRC)
#
# Build context is the project root (sent via oc start-build)
# so we can COPY from both backend/ and backend-mcp/.
#
# Create BuildConfig (once):
#   oc new-build --binary --strategy=docker --name=mcp-server -n tasks-app
#
# Build and push to internal registry:
#   oc start-build mcp-server --from-dir=. --follow -n tasks-app
# ============================================================

# =========================
# Builder stage
# =========================
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy dependency file and install
COPY backend-mcp/pyproject.toml ./
RUN /root/.local/bin/uv pip install --system -r pyproject.toml

# =========================
# Runtime stage
# =========================
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the shared backend app/ package (models, database, config, events)
COPY backend/app/ ./app/

# Copy MCP server code
COPY backend-mcp/server.py ./server.py
COPY backend-mcp/middleware.py ./middleware.py
COPY backend-mcp/auth_context.py ./auth_context.py
COPY backend-mcp/services/ ./services/
COPY backend-mcp/tools/ ./tools/

RUN chgrp -R 0 /app && chmod -R g=u /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8001

# Run in streamable HTTP mode for K8s (agents connect over the network)
CMD ["python", "server.py", "--transport", "streamable-http", "--port", "8001"]
