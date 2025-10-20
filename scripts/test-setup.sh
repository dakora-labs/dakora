#!/bin/bash
set -e

echo "🔧 Setting up test environment..."

# Start only the database from docker-compose
echo "📦 Starting PostgreSQL container..."
cd docker && docker-compose up -d db

# Wait for database to be healthy
echo "⏳ Waiting for database to be ready..."
timeout 30 bash -c 'until docker-compose exec -T db pg_isready -U postgres -d dakora; do sleep 1; done'

# Run migrations
echo "🔄 Running database migrations..."
cd ../server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
export PATH="$HOME/.local/bin:$PATH"
uv run alembic upgrade head

echo "✅ Test environment ready!"
echo "   Database: postgresql://postgres:postgres@localhost:5432/dakora"
echo ""
echo "Run tests with:"
echo "   export DATABASE_URL=\"postgresql://postgres:postgres@localhost:5432/dakora\""
echo "   uv run pytest"