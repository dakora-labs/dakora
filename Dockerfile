FROM python:3.11-slim

# Install Node.js for building the web UI
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY dakora ./dakora
COPY playground ./playground
COPY web ./web

# Install Python dependencies and build web UI
RUN pip install --no-cache-dir . && \
    rm -rf /root/.cache && \
    cd web && \
    npm install && \
    npm run build && \
    cd .. && \
    rm -rf web

EXPOSE 8000

ENV PORT=8000

CMD dakora playground --demo --host 0.0.0.0 --port ${PORT} --no-browser