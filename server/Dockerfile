FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY dakora_server ./dakora_server

# Install dependencies with Azure support using uv
RUN uv pip install --system --no-cache-dir ".[azure]"

EXPOSE 8000

CMD ["uvicorn", "dakora_server.main:app", "--host", "0.0.0.0", "--port", "8000"]