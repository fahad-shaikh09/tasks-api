# ============================================================
# AI Agent Dockerfile (OpenShift / CRC)
#
# Runs a Chainlit web UI inside the cluster that connects to
# the MCP server at http://mcp-server:8001/mcp.
#
# Users access it via a browser through an OpenShift Route.
#
# Create BuildConfig (once):
#   oc new-build --binary --strategy=docker --name=agent -n tasks-app
#
# Build:
#   oc start-build agent --from-dir=agent --follow -n tasks-app
# ============================================================

FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv and dependencies
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
COPY pyproject.toml ./
RUN /root/.local/bin/uv pip install --system -r pyproject.toml

COPY main.py ./
COPY public ./public
COPY .chainlit ./.chainlit

RUN chgrp -R 0 /app && chmod -R g=u /app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Chainlit serves a web UI on port 8000
CMD ["chainlit", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
