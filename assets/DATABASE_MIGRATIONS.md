# Database Migrations Guide

Dakora uses **Alembic** for database migrations with **SQLAlchemy Core** and **PostgreSQL**. This guide covers everything you need to know to work with database schema changes.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup](#setup)
- [Creating Migrations](#creating-migrations)
- [Common Migration Tasks](#common-migration-tasks)
- [Alembic Commands Reference](#alembic-commands-reference)
- [Development Workflow](#development-workflow)
- [Production Deployment](#production-deployment)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

---

## Overview

### What are Database Migrations?

Database migrations are version-controlled changes to your database schema. Instead of manually running SQL scripts, migrations:

- Track schema changes in version control (git)
- Apply changes automatically during deployment
- Support rollback to previous versions
- Ensure consistency across environments (local, staging, production)

### Migration Lifecycle

```
1. Define schema in database.py (SQLAlchemy Core)
2. Create migration file (alembic revision)
3. Write upgrade() and downgrade() logic
4. Test locally (alembic upgrade head)
5. Commit to git
6. Deploy → Migrations run automatically ✅
```

---

## Architecture

### Components

- **PostgreSQL** - Database engine (local: Docker, production: Supabase)
- **SQLAlchemy Core** - Python SQL toolkit (we use Core, not ORM)
- **Alembic** - Migration tool for schema versioning
- **database.py** - Source of truth for table definitions
- **alembic/versions/** - Migration scripts directory

### How It Works

**Local (Docker Compose):**
1. `docker-compose up` starts PostgreSQL with healthcheck
2. API container waits for DB to be healthy
3. `entrypoint.sh` runs `alembic upgrade head` automatically
4. Server starts after migrations complete

**Production (Render):**
1. Push code to GitHub
2. Render triggers deployment
3. **Pre-deploy command** runs: `alembic upgrade head`
4. New service version deploys only after successful migration
5. Zero downtime, safe rollouts

### File Structure

```
server/
├── dakora_server/core/
│   └── database.py              # Table definitions (source of truth)
├── alembic/
│   ├── versions/                # Migration scripts
│   │   └── 8f97975fec5c_*.py   # Individual migrations
│   ├── env.py                   # Alembic environment config
│   └── script.py.mako           # Migration template
├── alembic.ini                  # Alembic configuration
└── entrypoint.sh                # Docker entrypoint with auto-migration
```

---

## Setup

### Prerequisites

```bash
# Ensure dependencies are installed
cd server
export PATH="$HOME/.local/bin:$PATH" && uv sync
```

### Environment Variables

```bash
# Local development (Docker Compose)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"

# Production (Supabase)
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres"
```

### Verify Setup

```bash
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"

# Check current migration version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic current

# View migration history
export PATH="$HOME/.local/bin:$PATH" && uv run alembic history --verbose
```

---

## Creating Migrations

### Basic Workflow

**Step 1: Update `database.py`**

Define your table schema using SQLAlchemy Core:

```python
# server/dakora_server/core/database.py

from sqlalchemy import Table, Column, Integer, String, DateTime, text

# Add new table definition
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("name", String(255)),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)
```

**Step 2: Create Migration File**

```bash
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "Add users table"
```

This creates: `server/alembic/versions/abc123_add_users_table.py`

**Step 3: Edit Migration**

```python
# server/alembic/versions/abc123_add_users_table.py

def upgrade() -> None:
    """Add users table."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])


def downgrade() -> None:
    """Remove users table."""
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
```

**Step 4: Test Migration**

```bash
# Apply migration
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head

# Verify it worked
docker exec dakora-db psql -U postgres -d dakora -c "\dt"
docker exec dakora-db psql -U postgres -d dakora -c "\d users"

# Test rollback
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1

# Re-apply
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
```

**Step 5: Commit and Deploy**

```bash
git add server/dakora_server/core/database.py
git add server/alembic/versions/abc123_add_users_table.py
git commit -m "feat: add users table"
git push
```

---

## Common Migration Tasks

### 1. Add a New Table

**database.py:**
```python
api_keys_table = Table(
    "api_keys",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("key_hash", String(255), nullable=False, unique=True),
    Column("name", String(255)),
    Column("workspace_id", Integer, nullable=False),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)
```

**Migration:**
```python
def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index('ix_api_keys_workspace', 'api_keys', ['workspace_id'])

def downgrade() -> None:
    op.drop_index('ix_api_keys_workspace', table_name='api_keys')
    op.drop_table('api_keys')
```

### 2. Add Column to Existing Table

**database.py:**
```python
# Add to logs_table definition
Column("error", Text),
```

**Migration:**
```python
def upgrade() -> None:
    """Add error column to logs table."""
    op.add_column('logs', sa.Column('error', sa.Text(), nullable=True))

def downgrade() -> None:
    """Remove error column."""
    op.drop_column('logs', 'error')
```

### 3. Add Index

**Migration:**
```python
def upgrade() -> None:
    """Add index on logs.provider for faster filtering."""
    op.create_index('ix_logs_provider', 'logs', ['provider'])

def downgrade() -> None:
    """Remove index."""
    op.drop_index('ix_logs_provider', table_name='logs')
```

### 4. Rename Column

**Migration:**
```python
def upgrade() -> None:
    """Rename column."""
    op.alter_column('logs', 'cost', new_column_name='cost_deprecated')

def downgrade() -> None:
    """Revert rename."""
    op.alter_column('logs', 'cost_deprecated', new_column_name='cost')
```

### 5. Change Column Type

**Migration:**
```python
def upgrade() -> None:
    """Change column type."""
    # PostgreSQL syntax
    op.alter_column('logs', 'latency_ms',
                   type_=sa.BigInteger(),
                   existing_type=sa.Integer())

def downgrade() -> None:
    """Revert type change."""
    op.alter_column('logs', 'latency_ms',
                   type_=sa.Integer(),
                   existing_type=sa.BigInteger())
```

### 6. Add Foreign Key

**Migration:**
```python
def upgrade() -> None:
    """Add foreign key constraint."""
    op.create_foreign_key(
        'fk_logs_user_id',      # Constraint name
        'logs',                  # Source table
        'users',                 # Target table
        ['user_id'],             # Source column
        ['id'],                  # Target column
        ondelete='CASCADE'       # Optional: cascade deletes
    )

def downgrade() -> None:
    """Remove foreign key."""
    op.drop_constraint('fk_logs_user_id', 'logs', type_='foreignkey')
```

### 7. Complex Multi-Change Migration

**Migration:**
```python
def upgrade() -> None:
    """Add workspace support to logs."""
    # Add new column
    op.add_column('logs', sa.Column('workspace_id', sa.Integer(), nullable=True))

    # Create index
    op.create_index('ix_logs_workspace', 'logs', ['workspace_id'])

    # Backfill data (all existing logs → default workspace)
    op.execute("UPDATE logs SET workspace_id = 1 WHERE workspace_id IS NULL")

    # Make column non-nullable after backfill
    op.alter_column('logs', 'workspace_id', nullable=False)

    # Add foreign key
    op.create_foreign_key('fk_logs_workspace', 'logs', 'workspaces',
                         ['workspace_id'], ['id'])

def downgrade() -> None:
    """Remove workspace support."""
    op.drop_constraint('fk_logs_workspace', 'logs', type_='foreignkey')
    op.drop_index('ix_logs_workspace', table_name='logs')
    op.drop_column('logs', 'workspace_id')
```

### 8. Data Migration

**Migration:**
```python
from sqlalchemy import table, column

def upgrade() -> None:
    """Add status column and backfill from error column."""
    # Add column with default
    op.add_column('logs', sa.Column('status', sa.String(20),
                                   server_default='success'))

    # Backfill: Set status='error' where error is not null
    logs = table('logs', column('status'), column('error'))
    op.execute(
        logs.update()
        .where(logs.c.error != None)
        .values(status='error')
    )

def downgrade() -> None:
    """Remove status column."""
    op.drop_column('logs', 'status')
```

---

## Alembic Commands Reference

### Essential Commands

```bash
# Set database URL (required for all commands)
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"

# Check current migration version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic current

# View migration history
export PATH="$HOME/.local/bin:$PATH" && uv run alembic history

# View detailed history
export PATH="$HOME/.local/bin:$PATH" && uv run alembic history --verbose

# Create new migration
export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "description"

# Apply all pending migrations
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head

# Upgrade by 1 version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade +1

# Downgrade by 1 version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1

# Downgrade to specific version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade abc123

# Show SQL without running (dry-run)
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head --sql

# Mark as applied without running (⚠️ use with caution)
export PATH="$HOME/.local/bin:$PATH" && uv run alembic stamp head
```

### Database Inspection (via psql)

```bash
# List all tables
docker exec dakora-db psql -U postgres -d dakora -c "\dt"

# Describe table schema
docker exec dakora-db psql -U postgres -d dakora -c "\d logs"

# List indexes
docker exec dakora-db psql -U postgres -d dakora -c "\di"

# Check Alembic version
docker exec dakora-db psql -U postgres -d dakora -c "SELECT * FROM alembic_version;"

# Query table data
docker exec dakora-db psql -U postgres -d dakora -c "SELECT * FROM logs LIMIT 5;"
```

---

## Development Workflow

### Standard Development Process

**1. Create Feature Branch**
```bash
git checkout -b feature/add-user-auth
```

**2. Define Schema**
```python
# server/dakora_server/core/database.py
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("clerk_user_id", String(255), unique=True, nullable=False),
    Column("email", String(255), nullable=False),
    Column("name", String(255)),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)
```

**3. Create and Edit Migration**
```bash
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "Add users table"
# Edit the generated migration file...
```

**4. Test Locally**
```bash
# Start fresh database
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up -d

# Verify migration ran
docker logs dakora-api | grep "Migration"
docker exec dakora-db psql -U postgres -d dakora -c "\d users"

# Test rollback
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1
docker exec dakora-db psql -U postgres -d dakora -c "\dt"

# Re-apply
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
```

**5. Write Tests**
```python
# server/tests/test_database.py
def test_users_table_exists(test_engine):
    """Test users table was created."""
    with get_connection(test_engine) as conn:
        result = conn.execute(text("SELECT * FROM users LIMIT 0"))
        assert result is not None
```

**6. Commit and Push**
```bash
git add server/dakora_server/core/database.py
git add server/alembic/versions/
git add server/tests/test_database.py
git commit -m "feat: add users table for authentication"
git push origin feature/add-user-auth
```

**7. Deploy**
- Create PR → Review → Merge to main
- Render deployment triggers automatically
- Pre-deploy command runs migrations
- New version deploys after successful migration

---

## Production Deployment

### Render Configuration

Migrations run automatically via `preDeployCommand` in `render.yaml`:

```yaml
services:
  - type: web
    name: dakora-api
    preDeployCommand: "cd /app && alembic upgrade head"
    # ... rest of config
```

### Supabase Setup

1. **Create Supabase Project**
   - Go to https://supabase.com
   - Create new project

2. **Get Connection String**
   - Dashboard → Project Settings → Database
   - Copy "Connection String" (URI format)

3. **Add to Render**
   - Dashboard → Environment → Add Variable
   - Key: `DATABASE_URL`
   - Value: `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres`

4. **Deploy**
   - Push to GitHub
   - Render automatically runs migrations
   - Check deployment logs for migration status

### Deployment Safety

**What Happens on Deploy:**
```
1. Render pulls latest code
2. Builds Docker image
3. Runs: alembic upgrade head (pre-deploy)
   ├─ If migrations succeed → Deploy new version ✅
   └─ If migrations fail → Abort deployment ❌
4. New service version starts
5. Old version stays running until new version is healthy
```

**Zero Downtime Deployment:**
- Migrations run before code deployment
- Old version continues serving requests
- New version only receives traffic after health checks pass
- Database schema is always compatible with running code

---

## Best Practices

### 1. Always Write Downgrade Logic

**✅ Good:**
```python
def upgrade():
    op.add_column('logs', sa.Column('new_field', sa.String(100)))

def downgrade():
    op.drop_column('logs', 'new_field')
```

**❌ Bad:**
```python
def downgrade():
    pass  # No rollback possible!
```

### 2. Keep Migrations Small and Focused

**✅ Good:**
```python
# Migration 1: Add users table
# Migration 2: Add workspaces table
# Migration 3: Add user-workspace relationship
```

**❌ Bad:**
```python
# Migration 1: Add 10 tables with 50 columns
```

### 3. Test with Empty Database

```bash
# Create fresh test database
docker exec dakora-db psql -U postgres -c "DROP DATABASE IF EXISTS dakora_test;"
docker exec dakora-db psql -U postgres -c "CREATE DATABASE dakora_test;"

# Run all migrations from scratch
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora_test"
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head

# Verify complete schema
docker exec dakora-db psql -U postgres -d dakora_test -c "\dt"
```

### 4. Make Migrations Idempotent

Use `IF NOT EXISTS` and `IF EXISTS` where possible:

```python
def upgrade():
    # Safe to run multiple times
    op.execute("CREATE INDEX IF NOT EXISTS ix_logs_provider ON logs(provider)")
```

### 5. Handle Data Migrations Carefully

**Strategy: Three-Step Migration for Non-Nullable Columns**

```python
# Migration 1: Add column as nullable
def upgrade():
    op.add_column('logs', sa.Column('workspace_id', sa.Integer(), nullable=True))

# Migration 2: Backfill data
def upgrade():
    op.execute("UPDATE logs SET workspace_id = 1 WHERE workspace_id IS NULL")

# Migration 3: Make column non-nullable
def upgrade():
    op.alter_column('logs', 'workspace_id', nullable=False)
```

### 6. Document Complex Migrations

```python
def upgrade() -> None:
    """
    Add workspace support to logs table.

    This migration:
    1. Adds workspace_id column (nullable initially)
    2. Backfills all existing logs to default workspace (id=1)
    3. Makes workspace_id non-nullable
    4. Adds foreign key constraint

    IMPORTANT: Requires default workspace to exist before running.
    Run: INSERT INTO workspaces (id, slug, name) VALUES (1, 'default', 'Default');
    """
    # ... implementation
```

### 7. Version Control Best Practices

```bash
# ✅ Commit migration files with feature code
git add server/dakora_server/core/database.py
git add server/alembic/versions/abc123_add_users.py
git commit -m "feat: add user authentication tables"

# ❌ Don't commit migrations separately from schema changes
```

### 8. Avoid Breaking Changes

**Safe Schema Changes:**
- ✅ Add new tables
- ✅ Add nullable columns
- ✅ Add indexes
- ✅ Rename columns (with care)

**Breaking Changes (avoid in production):**
- ❌ Drop columns with data
- ❌ Change column types incompatibly
- ❌ Add non-nullable columns without defaults
- ❌ Drop tables with data

---

## Troubleshooting

### Migration Failed

**Symptom:** Deployment fails, logs show migration error

**Solution:**
```bash
# Check migration status
export PATH="$HOME/.local/bin:$PATH" && uv run alembic current

# View SQL that would be executed
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head --sql

# Fix migration file and redeploy
```

### Database Out of Sync

**Symptom:** `alembic current` shows wrong version

**Solution:**
```bash
# Check actual database state
docker exec dakora-db psql -U postgres -d dakora -c "\dt"

# Check Alembic version table
docker exec dakora-db psql -U postgres -d dakora -c "SELECT * FROM alembic_version;"

# Option 1: Force mark as correct version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic stamp head

# Option 2: Reset and re-migrate
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade base
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
```

### Migration Stuck

**Symptom:** Migration hangs or times out

**Solution:**
```bash
# Check for table locks
docker exec dakora-db psql -U postgres -d dakora -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Kill blocking queries (if safe)
docker exec dakora-db psql -U postgres -d dakora -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND pid != pg_backend_pid();"

# Retry migration
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
```

### Connection Refused

**Symptom:** `psycopg2.OperationalError: connection refused`

**Solution:**
```bash
# Check database is running
docker ps | grep dakora-db

# Check DATABASE_URL is correct
echo $DATABASE_URL

# Test connection
docker exec dakora-db psql -U postgres -d dakora -c "SELECT 1;"

# Restart database
docker-compose -f docker/docker-compose.yml restart db
```

### Schema Drift

**Symptom:** Production schema differs from migrations

**Solution:**
```bash
# Generate SQL for current migration state
export DATABASE_URL="postgresql://production-url"
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head --sql > schema.sql

# Compare with production
docker exec dakora-db pg_dump -U postgres -d dakora --schema-only > production.sql
diff schema.sql production.sql
```

---

## Quick Reference

### Migration Cheat Sheet

```bash
# Setup
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"

# Create migration
export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "description"

# Apply migrations
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head

# Rollback one version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1

# Check status
export PATH="$HOME/.local/bin:$PATH" && uv run alembic current

# View history
export PATH="$HOME/.local/bin:$PATH" && uv run alembic history --verbose

# Dry run (show SQL)
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head --sql
```

### Common SQLAlchemy Types

```python
from sqlalchemy import Integer, String, Text, Float, DateTime, Boolean, JSON

Column("id", Integer, primary_key=True, autoincrement=True)
Column("name", String(255), nullable=False)
Column("email", String(255), unique=True)
Column("bio", Text)
Column("price", Float)
Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP"))
Column("is_active", Boolean, default=True)
Column("metadata", JSON)  # or JSONB for PostgreSQL-specific
```

### Migration Template

```python
"""Description of what this migration does

Revision ID: abc123
Revises: xyz789
Create Date: 2025-01-20 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'abc123'
down_revision: Union[str, Sequence[str], None] = 'xyz789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema changes."""
    pass


def downgrade() -> None:
    """Revert schema changes."""
    pass
```

---

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Core Tutorial](https://docs.sqlalchemy.org/en/20/core/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Database Guide](https://supabase.com/docs/guides/database)

---

## Support

For questions or issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Alembic documentation](https://alembic.sqlalchemy.org/)
3. Open an issue on GitHub

**Happy migrating!** 🚀