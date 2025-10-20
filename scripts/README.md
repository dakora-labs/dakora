# Test Setup Scripts

## Running Tests Locally

### Option 1: Use Docker Compose (Recommended)

```bash
# Start PostgreSQL from docker-compose
./scripts/test-setup.sh

# Run tests
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
uv run pytest server/tests/ -v

# Stop PostgreSQL when done
cd docker && docker-compose down
```

### Option 2: Manual Setup

If you already have PostgreSQL running locally:

```bash
# Run migrations
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
uv run alembic upgrade head

# Run tests
cd ..
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
uv run pytest server/tests/ -v
```

## Test Categories

- **Unit tests**: Fast, mocked dependencies
  ```bash
  uv run pytest -m "not integration"
  ```

- **Integration tests**: Require PostgreSQL database
  ```bash
  export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
  uv run pytest -m integration
  ```

- **All tests**:
  ```bash
  export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
  uv run pytest
  ```

## CI/CD

GitHub Actions automatically:
1. Starts PostgreSQL service container
2. Runs migrations via `alembic upgrade head`
3. Executes all tests (unit + integration)

## Database Setup

The project uses:
- **Local/CI**: PostgreSQL 15 with database name `dakora`
- **Migrations**: Alembic manages schema changes
- **Connection**: `postgresql://postgres:postgres@localhost:5432/dakora`