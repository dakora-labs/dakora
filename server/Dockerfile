FROM python:3.11-slim

WORKDIR /app

# Copy project files first
COPY pyproject.toml .
COPY dakora_server ./dakora_server

# Install with Azure support for cloud deployments
RUN pip install --no-cache-dir ".[azure]"

EXPOSE 8000

CMD ["uvicorn", "dakora_server.main:app", "--host", "0.0.0.0", "--port", "8000"]