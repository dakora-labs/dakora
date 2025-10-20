# Dakora Server

FastAPI backend for the Dakora Platform.

This package is part of the Dakora monorepo and is not meant to be installed directly.

## Development

From the monorepo root:

```bash
uv sync
```

## Running

```bash
cd server
uvicorn dakora_server.main:app --reload --port 8000
```

## Environment Variables

- `PROMPT_DIR` - Path to prompts directory (default: `/app/prompts`)
- `CONFIG_PATH` - Path to dakora.yaml config file
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

## Docker

This server is designed to run in Docker. See `../docker/docker-compose.yml`.