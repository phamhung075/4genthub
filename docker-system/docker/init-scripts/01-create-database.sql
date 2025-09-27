-- Create database if not exists
SELECT 'CREATE DATABASE agenthub'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agenthub')\gexec

-- Create user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'agenthub_user') THEN
      CREATE ROLE agenthub_user LOGIN PASSWORD 'dev_password';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agenthub TO agenthub_user;

-- Connect to the database
\c agenthub

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO agenthub_user;