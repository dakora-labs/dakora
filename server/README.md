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

### Core Configuration

- `PROMPT_DIR` - Path to prompts directory (default: `/app/prompts`)
- `CONFIG_PATH` - Path to dakora.yaml config file
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Authentication

Authentication configuration (see [Authentication Guide](/guides/authentication)):

- `AUTH_ENABLED` - Enable authentication (default: `false`)
  - `true` - Require authentication for all endpoints
  - `false` - Allow public access (development mode)

**Clerk JWT Configuration** (required when `AUTH_ENABLED=true`):

- `CLERK_JWT_ISSUER` - Clerk JWT issuer URL
  - Example: `https://your-domain.clerk.accounts.prod.liveblocks.io`
- `CLERK_JWKS_URL` - Clerk JSON Web Key Set URL
  - Example: `https://your-domain.clerk.accounts.prod.liveblocks.io/.well-known/jwks.json`

Get these values from your [Clerk Dashboard](https://dashboard.clerk.com) → API Keys

## Docker

This server is designed to run in Docker. See `../docker/docker-compose.yml`.
