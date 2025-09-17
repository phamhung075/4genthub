-- PostgreSQL Initialization Script for Production
-- ================================================

-- Create the production user
CREATE USER 4genthub_user WITH PASSWORD 'ChangeThisSecurePassword2025!';

-- Create the production database
CREATE DATABASE 4genthub_prod OWNER 4genthub_user;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE 4genthub_prod TO 4genthub_user;

-- Connect to the new database
\c 4genthub_prod;

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS public;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO 4genthub_user;
GRANT CREATE ON SCHEMA public TO 4genthub_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO 4genthub_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO 4genthub_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO 4genthub_user;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Notify completion
\echo 'PostgreSQL production database initialized successfully!'