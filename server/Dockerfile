FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
# Install with Azure support for cloud deployments
RUN pip install --no-cache-dir -e ".[azure]"

COPY dakora_server ./dakora_server

EXPOSE 8000

CMD ["uvicorn", "dakora_server.main:app", "--host", "0.0.0.0", "--port", "8000"]