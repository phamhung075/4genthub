#!/bin/bash

# Script to start PostgreSQL test database

echo "🐘 Starting PostgreSQL test database..."

# Navigate to the directory containing docker-compose.test.yml
cd "$(dirname "$0")/.." || exit 1

# Start PostgreSQL using docker-compose
docker-compose -f docker-compose.test.yml up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose -f docker-compose.test.yml exec -T postgres-test pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo -n "."
    sleep 1
done

# Show connection info
echo ""
echo "📊 PostgreSQL Test Database Information:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: 4genthub_test"
echo "   User: postgres"
echo "   Password: test"
echo ""
echo "🔗 Connection URL:"
echo "   postgresql://postgres:test@localhost:5432/4genthub_test"
echo ""
echo "To stop the database, run: docker-compose -f docker-compose.test.yml down"