FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] ships libpq in the wheel, so no system build deps are needed.
# Install dependencies first for better layer caching.
COPY pyproject.toml ./
COPY app ./app
RUN pip install -e ".[dev]"

# Copy the rest (alembic.ini, tests, worker, eval, scripts).
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
