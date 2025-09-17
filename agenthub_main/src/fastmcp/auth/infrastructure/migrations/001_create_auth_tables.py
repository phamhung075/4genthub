"""
Authentication Tables Migration

This migration creates the users and user_sessions tables for authentication.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


def upgrade():
    """Create authentication tables"""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, default=str(uuid.uuid4())),
        sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('username', sa.String(150), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False, default='pending_verification'),
        sa.Column('roles', sa.JSON, default=list),
        sa.Column('email_verified', sa.Boolean, default=False),
        sa.Column('email_verified_at', sa.DateTime),
        sa.Column('last_login_at', sa.DateTime),
        sa.Column('failed_login_attempts', sa.Integer, default=0),
        sa.Column('locked_until', sa.DateTime),
        sa.Column('password_changed_at', sa.DateTime),
        sa.Column('password_reset_token', sa.String(255), unique=True),
        sa.Column('password_reset_expires', sa.DateTime),
        sa.Column('refresh_token_family', sa.String(255)),
        sa.Column('refresh_token_version', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(255)),
        sa.Column('project_ids', sa.JSON, default=list),
        sa.Column('default_project_id', postgresql.UUID(as_uuid=False)),
        sa.Column('metadata', sa.JSON, default=dict),
    )
    
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, default=str(uuid.uuid4())),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_token', sa.String(255), unique=True, nullable=False),
        sa.Column('refresh_token', sa.String(255), unique=True),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('device_info', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('revoked_at', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    
    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_status', 'users', ['status'])
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'])
    op.create_index('ix_users_refresh_token_family', 'users', ['refresh_token_family'])
    
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_session_token', 'user_sessions', ['session_token'])
    op.create_index('ix_user_sessions_refresh_token', 'user_sessions', ['refresh_token'])
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'])
    
    # Add check constraints
    op.create_check_constraint(
        'check_email_not_empty',
        'users',
        'length(email) > 0'
    )
    
    op.create_check_constraint(
        'check_username_not_empty',
        'users',
        'length(username) > 0'
    )


def downgrade():
    """Drop authentication tables"""
    op.drop_table('user_sessions')
    op.drop_table('users')