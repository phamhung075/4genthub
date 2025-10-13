#!/bin/bash
# Wrapper script for PostgreSQL initialization
# This script runs before init.sql and creates the application user with the correct password

set -e

# Get the password from environment variable (set by Docker Compose)
APP_PASSWORD="${DATABASE_PASSWORD:-agenthub_pass}"

echo "Creating agenthub_user with password from DATABASE_PASSWORD environment variable..."

# Create the user if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agenthub_user') THEN
          CREATE ROLE agenthub_user LOGIN PASSWORD '$APP_PASSWORD';
          RAISE NOTICE 'Created agenthub_user role with password from environment';
       ELSE
          -- Update password if user already exists
          ALTER ROLE agenthub_user WITH PASSWORD '$APP_PASSWORD';
          RAISE NOTICE 'Updated agenthub_user password from environment';
       END IF;
    END
    \$\$;

    -- Grant database privileges
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO agenthub_user;

    -- Grant schema privileges (needed for creating types and tables)
    GRANT ALL PRIVILEGES ON SCHEMA public TO agenthub_user;
    GRANT ALL PRIVILEGES ON SCHEMA mcp TO agenthub_user;

    -- Grant privileges on all existing objects
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agenthub_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agenthub_user;
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO agenthub_user;
EOSQL

echo "agenthub_user configured successfully with schema permissions"
