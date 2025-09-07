-- Authentication System Database Migration
-- Purpose: Add user authentication tables with email/password support
-- Expected features: User registration, login, password reset, session management
-- Created: 2025-08-17

-- 1. Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Authentication fields
    email VARCHAR(254) UNIQUE NOT NULL,
    username VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile fields
    full_name VARCHAR(255),
    
    -- Status and roles (stored as JSON array)
    status VARCHAR(50) NOT NULL DEFAULT 'pending_verification',
    roles JSON DEFAULT '["user"]'::json,
    
    -- Email verification
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    
    -- Login tracking
    last_login_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    
    -- Password management
    password_changed_at TIMESTAMP,
    password_reset_token VARCHAR(255) UNIQUE,
    password_reset_expires TIMESTAMP,
    
    -- Refresh token management
    refresh_token_family VARCHAR(255),
    refresh_token_version INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    -- Project associations (stored as JSON for flexibility)
    project_ids JSON DEFAULT '[]'::json,
    default_project_id UUID,
    
    -- Additional metadata
    metadata JSON DEFAULT '{}'::json,
    
    -- Constraints
    CONSTRAINT check_email_not_empty CHECK (LENGTH(email) > 0),
    CONSTRAINT check_username_not_empty CHECK (LENGTH(username) > 0),
    CONSTRAINT check_valid_status CHECK (status IN ('active', 'inactive', 'suspended', 'pending_verification'))
);

-- 2. Create user_sessions table for session tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session details
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    
    -- Session metadata
    ip_address VARCHAR(45), -- Supports IPv6
    user_agent TEXT,
    device_info JSON DEFAULT '{}'::json,
    
    -- Session lifecycle
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. Create indexes for performance
-- User table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_password_reset_token ON users(password_reset_token) WHERE password_reset_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_refresh_token_family ON users(refresh_token_family) WHERE refresh_token_family IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_email_verified ON users(email_verified, status) WHERE email_verified = TRUE;

-- Session table indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_token ON user_sessions(refresh_token) WHERE refresh_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON user_sessions(is_active, user_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at) WHERE is_active = TRUE;

-- 4. Create audit table for security tracking
CREATE TABLE IF NOT EXISTS auth_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Event details
    event_type VARCHAR(50) NOT NULL, -- login, logout, password_change, password_reset, etc.
    event_status VARCHAR(20) NOT NULL, -- success, failure, blocked
    event_details JSON DEFAULT '{}'::json,
    
    -- Request metadata
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for querying
    CONSTRAINT check_valid_event_type CHECK (event_type IN (
        'login', 'logout', 'register', 'password_change', 
        'password_reset_request', 'password_reset_complete',
        'email_verification', 'account_locked', 'account_unlocked',
        'session_refresh', 'session_revoked'
    )),
    CONSTRAINT check_valid_event_status CHECK (event_status IN ('success', 'failure', 'blocked'))
);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_auth_audit_user_id ON auth_audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_audit_event_type ON auth_audit_log(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_audit_created_at ON auth_audit_log(created_at DESC);

-- 5. Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 6. Create trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. Create function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    UPDATE user_sessions 
    SET is_active = FALSE 
    WHERE expires_at < CURRENT_TIMESTAMP AND is_active = TRUE;
    
    -- Also revoke sessions that have been inactive for more than 30 days
    UPDATE user_sessions
    SET is_active = FALSE, revoked_at = CURRENT_TIMESTAMP
    WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '30 days' AND is_active = TRUE;
END;
$$ language 'plpgsql';

-- 8. Create function to clean up expired password reset tokens
CREATE OR REPLACE FUNCTION cleanup_expired_password_resets()
RETURNS void AS $$
BEGIN
    UPDATE users
    SET password_reset_token = NULL, password_reset_expires = NULL
    WHERE password_reset_expires < CURRENT_TIMESTAMP AND password_reset_token IS NOT NULL;
END;
$$ language 'plpgsql';

-- Note: These tables and functions provide:
-- - Secure user authentication with email/password
-- - Session management with refresh tokens
-- - Password reset functionality
-- - Account locking for security
-- - Audit logging for compliance
-- - Automatic cleanup of expired data
-- - Performance optimization through strategic indexing