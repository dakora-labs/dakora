FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY dakora ./dakora
COPY playground ./playground

RUN pip install --no-cache-dir . && \
    rm -rf /root/.cache

EXPOSE 8000

ENV PORT=8000

CMD dakora playground --demo --host 0.0.0.0 --port ${PORT} --no-browser