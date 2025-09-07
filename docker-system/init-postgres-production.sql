-- PostgreSQL Initialization Script for Production
-- ================================================

-- Create the production user
CREATE USER dhafnck_user WITH PASSWORD 'ChangeThisSecurePassword2025!';

-- Create the production database
CREATE DATABASE dhafnck_mcp_prod OWNER dhafnck_user;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE dhafnck_mcp_prod TO dhafnck_user;

-- Connect to the new database
\c dhafnck_mcp_prod;

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS public;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO dhafnck_user;
GRANT CREATE ON SCHEMA public TO dhafnck_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dhafnck_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dhafnck_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO dhafnck_user;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Notify completion
\echo 'PostgreSQL production database initialized successfully!'