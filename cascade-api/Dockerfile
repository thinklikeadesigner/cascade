# cascade-api/Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY cascade_api/ cascade_api/
COPY cascade-memory/ cascade-memory/
RUN pip install --no-cache-dir .

EXPOSE ${PORT:-8000}

CMD ["sh", "-c", "uvicorn cascade_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
