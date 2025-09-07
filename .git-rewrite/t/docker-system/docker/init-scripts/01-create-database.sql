-- Create database if not exists
SELECT 'CREATE DATABASE dhafnck_mcp'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dhafnck_mcp')\gexec

-- Create user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'dhafnck_user') THEN
      CREATE ROLE dhafnck_user LOGIN PASSWORD 'dev_password';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dhafnck_mcp TO dhafnck_user;

-- Connect to the database
\c dhafnck_mcp

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO dhafnck_user;