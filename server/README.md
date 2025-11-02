# Dakora Server

FastAPI backend for the Dakora platform.

**Note:** This package is part of the Dakora monorepo and is not meant to be installed directly. Use the [CLI](../cli) or [Docker setup](../docker) instead.

## Development

From monorepo root:

```bash
uv sync
```

Run the server:

```bash
cd server
export PATH="$HOME/.local/bin:$PATH"
uv run uvicorn dakora_server.main:app --reload --port 8000
```

## Documentation

See [CLAUDE.md](../CLAUDE.md) for architecture and development details.