# cascade-api/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY cascade_api/ cascade_api/
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "cascade_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
