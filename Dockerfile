FROM python:3.11-slim

# Install Node.js for building the web UI
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy web source and build UI first
COPY web ./web
RUN cd web && \
    npm install && \
    npm run build && \
    cd ..

# Now copy Python source (build output is already in playground/)
COPY pyproject.toml README.md ./
COPY dakora ./dakora

# Install Python dependencies and clean up
RUN pip install --no-cache-dir . && \
    rm -rf /root/.cache && \
    rm -rf web

EXPOSE 8000

ENV PORT=8000

CMD dakora playground --demo --host 0.0.0.0 --port ${PORT} --no-build --no-browser