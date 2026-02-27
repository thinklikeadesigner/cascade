# cascade-api/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY cascade_api/ cascade_api/

EXPOSE 8000

CMD ["uvicorn", "cascade_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
