FROM python:3.13-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# copy dependency files
COPY pyproject.toml uv.lock ./

RUN /root/.local/bin/uv sync --frozen --no-dev


# =========================
# Runtime stage
# =========================
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# =========================
# COPY ONLY REQUIRED CODE
# =========================

COPY app/ ./app/
COPY main.py ./main.py

# DO NOT COPY everything else

RUN chgrp -R 0 /app && chmod -R g=u /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
