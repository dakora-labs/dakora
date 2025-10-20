FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY dakora_server ./dakora_server

# Copy Alembic configuration and migrations
COPY alembic.ini ./
COPY alembic ./alembic

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Install dependencies with Azure support using uv
RUN uv pip install --system --no-cache-dir ".[azure]"

EXPOSE 8000

# Use entrypoint script for DB migrations
ENTRYPOINT ["./entrypoint.sh"]