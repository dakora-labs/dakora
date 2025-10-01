FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir uv && \
    uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "dakora.cli", "playground", "--demo", "--host", "0.0.0.0", "--port", "8000", "--no-build", "--no-browser"]