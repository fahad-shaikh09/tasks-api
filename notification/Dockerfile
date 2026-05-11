FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY . .

RUN chgrp -R 0 /app && chmod -R g+rwX /app

# Use venv directly — avoids uv cache permission issues on OpenShift
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8002

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
