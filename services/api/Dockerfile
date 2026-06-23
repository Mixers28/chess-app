# Production image for the Chess API. Non-root runtime, no dev deps.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# App source + migrations.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

# Run as non-root.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Graceful shutdown is handled by uvicorn on SIGTERM. Migrations are run as an
# explicit release step (see deploy/coolify), not on container start.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
