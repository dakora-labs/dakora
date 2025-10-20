#!/bin/bash
set -e

echo "🚀 Dakora Server Entrypoint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL to be ready..."

    max_attempts=30
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if python -c "
from dakora_server.core.database import create_db_engine, wait_for_db
import sys
engine = create_db_engine()
if wait_for_db(engine, max_retries=1, retry_interval=1):
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null; then
            echo "✅ PostgreSQL is ready!"
            return 0
        fi

        echo "   Attempt $attempt/$max_attempts failed, retrying in 2s..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "❌ Failed to connect to PostgreSQL after $max_attempts attempts"
    return 1
}

# Function to run migrations
run_migrations() {
    echo "🔄 Running database migrations..."

    if alembic upgrade head; then
        echo "✅ Migrations completed successfully"
        return 0
    else
        echo "❌ Migration failed!"
        return 1
    fi
}

# Function to check migration status
check_migrations() {
    echo "📊 Current migration status:"
    alembic current || true
    echo ""
}

# Main execution
main() {
    # Wait for database
    if ! wait_for_postgres; then
        echo "💥 Cannot start server - database connection failed"
        exit 1
    fi

    # Run migrations
    if ! run_migrations; then
        echo "💥 Cannot start server - migration failed"
        exit 1
    fi

    # Show migration status
    check_migrations

    # Start the server
    # Use PORT env var if provided (Render), otherwise default to 8000
    PORT=${PORT:-8000}
    echo "🎯 Starting Dakora Server on port ${PORT}..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
    exec uvicorn dakora_server.main:app --host 0.0.0.0 --port ${PORT}
}

# Run main function
main