-- PostgreSQL Initialization Script for Production
-- ================================================

-- Create the production user
CREATE USER agenthub_user WITH PASSWORD 'ChangeThisSecurePassword2025!';

-- Create the production database
CREATE DATABASE agenthub_prod OWNER agenthub_user;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE agenthub_prod TO agenthub_user;

-- Connect to the new database
\c agenthub_prod;

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS public;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO agenthub_user;
GRANT CREATE ON SCHEMA public TO agenthub_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO agenthub_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO agenthub_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO agenthub_user;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Notify completion
\echo 'PostgreSQL production database initialized successfully!'