"""
User Repository Implementation

This repository handles user persistence using SQLAlchemy.
"""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from ...domain.entities.user import User as DomainUser
from ..database.models import User as UserModel

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user persistence operations"""
    
    def __init__(self, session: Session):
        """
        Initialize user repository
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    async def save(self, user: DomainUser) -> DomainUser:
        """
        Save or update a user
        
        Args:
            user: Domain user entity to save
            
        Returns:
            Saved user entity
            
        Raises:
            IntegrityError: If unique constraint violated
        """
        try:
            # Check if user exists
            if user.id:
                db_user = self.session.query(UserModel).filter_by(id=user.id).first()
                if db_user:
                    # Update existing user
                    for key, value in user.to_dict().items():
                        if hasattr(db_user, key):
                            setattr(db_user, key, value)
                else:
                    # Create new user with ID
                    db_user = UserModel.from_domain(user)
                    self.session.add(db_user)
            else:
                # Create new user without ID
                db_user = UserModel.from_domain(user)
                self.session.add(db_user)
            
            # Don't commit here - let the service/endpoint handle transactions
            self.session.flush()  # Flush to get the ID but don't commit
            
            # CRITICAL FIX: Capture the ID immediately and detach from session
            generated_id = db_user.id
            
            # Expunge the object from the session to prevent any future database access
            self.session.expunge(db_user)
            
            # Create a completely new domain object with no database ties
            # using only the original user data and the generated ID
            from ...domain.entities.user import User as DomainUser
            
            created_user = DomainUser(
                id=str(generated_id),  # Use captured ID
                email=user.email,      # Use original data to avoid database access
                username=user.username,
                password_hash=user.password_hash,
                full_name=user.full_name,
                status=user.status,
                roles=user.roles,
                email_verified=user.email_verified,
                email_verified_at=user.email_verified_at,
                last_login_at=user.last_login_at,
                failed_login_attempts=user.failed_login_attempts,
                locked_until=user.locked_until,
                password_changed_at=user.password_changed_at,
                password_reset_token=user.password_reset_token,
                password_reset_expires=user.password_reset_expires,
                refresh_token_family=user.refresh_token_family,
                refresh_token_version=user.refresh_token_version,
                created_at=user.created_at,
                updated_at=user.updated_at,
                created_by=user.created_by,
                project_ids=user.project_ids,
                default_project_id=user.default_project_id,
                metadata=user.metadata
            )
            
            return created_user
            
        except IntegrityError as e:
            # Don't rollback here - let the service/endpoint handle it
            logger.error(f"Integrity error saving user: {e}")
            raise
        except Exception as e:
            # Don't rollback here - let the service/endpoint handle it
            logger.error(f"Error saving user: {e}")
            raise
    
    async def get_by_id(self, user_id: str) -> Optional[DomainUser]:
        """
        Get user by ID
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User if found, None otherwise
        """
        try:
            db_user = self.session.query(UserModel).filter_by(id=user_id).first()
            return db_user.to_domain() if db_user else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def find_by_id(self, user_id: str) -> Optional[DomainUser]:
        """
        Synchronous method to get user by ID (for compatibility with Supabase auth)
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User if found, None otherwise
        """
        try:
            db_user = self.session.query(UserModel).filter_by(id=user_id).first()
            if not db_user:
                return None
            
            # Create domain object directly to avoid any potential database access
            from ...domain.entities.user import User as DomainUser, UserStatus, UserRole
            
            return DomainUser(
                id=str(db_user.id),
                email=db_user.email,
                username=db_user.username,
                password_hash=db_user.password_hash,
                full_name=db_user.full_name,
                status=UserStatus(db_user.status) if isinstance(db_user.status, str) else db_user.status,
                roles=[UserRole(role) if isinstance(role, str) else role for role in (db_user.roles or [])],
                email_verified=db_user.email_verified,
                email_verified_at=db_user.email_verified_at,
                last_login_at=db_user.last_login_at,
                failed_login_attempts=db_user.failed_login_attempts or 0,
                locked_until=db_user.locked_until,
                password_changed_at=db_user.password_changed_at,
                password_reset_token=db_user.password_reset_token,
                password_reset_expires=db_user.password_reset_expires,
                refresh_token_family=db_user.refresh_token_family,
                refresh_token_version=db_user.refresh_token_version or 0,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
                created_by=db_user.created_by,
                project_ids=db_user.project_ids or [],
                default_project_id=db_user.default_project_id,
                metadata=db_user.metadata or {}
            )
        except Exception as e:
            logger.error(f"Error finding user by ID: {e}")
            return None
    
    async def get_by_email(self, email: str) -> Optional[DomainUser]:
        """
        Get user by email
        
        Args:
            email: User's email address
            
        Returns:
            User if found, None otherwise
        """
        try:
            db_user = self.session.query(UserModel).filter_by(email=email.lower()).first()
            if not db_user:
                return None
            
            # Create domain object directly to avoid any potential database access from to_domain()
            from ...domain.entities.user import User as DomainUser, UserStatus, UserRole
            
            return DomainUser(
                id=str(db_user.id),
                email=db_user.email,
                username=db_user.username,
                password_hash=db_user.password_hash,
                full_name=db_user.full_name,
                status=UserStatus(db_user.status) if isinstance(db_user.status, str) else db_user.status,
                roles=[UserRole(role) if isinstance(role, str) else role for role in (db_user.roles or [])],
                email_verified=db_user.email_verified,
                email_verified_at=db_user.email_verified_at,
                last_login_at=db_user.last_login_at,
                failed_login_attempts=db_user.failed_login_attempts or 0,
                locked_until=db_user.locked_until,
                password_changed_at=db_user.password_changed_at,
                password_reset_token=db_user.password_reset_token,
                password_reset_expires=db_user.password_reset_expires,
                refresh_token_family=db_user.refresh_token_family,
                refresh_token_version=db_user.refresh_token_version or 0,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
                created_by=db_user.created_by,
                project_ids=db_user.project_ids or [],
                default_project_id=db_user.default_project_id,
                metadata=db_user.metadata or {}
            )
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    async def get_by_username(self, username: str) -> Optional[DomainUser]:
        """
        Get user by username
        
        Args:
            username: User's username
            
        Returns:
            User if found, None otherwise
        """
        try:
            db_user = self.session.query(UserModel).filter_by(username=username).first()
            if not db_user:
                return None
            
            # Create domain object directly to avoid any potential database access from to_domain()
            from ...domain.entities.user import User as DomainUser, UserStatus, UserRole
            
            return DomainUser(
                id=str(db_user.id),
                email=db_user.email,
                username=db_user.username,
                password_hash=db_user.password_hash,
                full_name=db_user.full_name,
                status=UserStatus(db_user.status) if isinstance(db_user.status, str) else db_user.status,
                roles=[UserRole(role) if isinstance(role, str) else role for role in (db_user.roles or [])],
                email_verified=db_user.email_verified,
                email_verified_at=db_user.email_verified_at,
                last_login_at=db_user.last_login_at,
                failed_login_attempts=db_user.failed_login_attempts or 0,
                locked_until=db_user.locked_until,
                password_changed_at=db_user.password_changed_at,
                password_reset_token=db_user.password_reset_token,
                password_reset_expires=db_user.password_reset_expires,
                refresh_token_family=db_user.refresh_token_family,
                refresh_token_version=db_user.refresh_token_version or 0,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
                created_by=db_user.created_by,
                project_ids=db_user.project_ids or [],
                default_project_id=db_user.default_project_id,
                metadata=db_user.metadata or {}
            )
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    async def get_by_reset_token(self, reset_token: str) -> Optional[DomainUser]:
        """
        Get user by password reset token
        
        Args:
            reset_token: Password reset token
            
        Returns:
            User if found, None otherwise
        """
        try:
            db_user = self.session.query(UserModel).filter_by(
                password_reset_token=reset_token
            ).first()
            return db_user.to_domain() if db_user else None
        except Exception as e:
            logger.error(f"Error getting user by reset token: {e}")
            return None
    
    async def list_all(self, 
                       limit: int = 100,
                       offset: int = 0,
                       status: Optional[str] = None) -> List[DomainUser]:
        """
        List all users with optional filtering
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            status: Optional status filter
            
        Returns:
            List of users
        """
        try:
            query = self.session.query(UserModel)
            
            if status:
                query = query.filter_by(status=status)
            
            db_users = query.offset(offset).limit(limit).all()
            return [user.to_domain() for user in db_users]
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    async def delete(self, user_id: str) -> bool:
        """
        Delete a user
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            db_user = self.session.query(UserModel).filter_by(id=user_id).first()
            if db_user:
                self.session.delete(db_user)
                # Don't commit here - let the service/endpoint handle transactions
                self.session.flush()
                return True
            return False
        except Exception as e:
            # Don't rollback here - let the service/endpoint handle it
            logger.error(f"Error deleting user: {e}")
            raise  # Re-raise the exception instead of returning False
    
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email
        
        Args:
            email: Email to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.session.query(UserModel).filter_by(
                email=email.lower()
            ).count() > 0
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False
    
    async def exists_by_username(self, username: str) -> bool:
        """
        Check if user exists by username
        
        Args:
            username: Username to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.session.query(UserModel).filter_by(
                username=username
            ).count() > 0
        except Exception as e:
            logger.error(f"Error checking username existence: {e}")
            return False
    
    async def search(self, query: str, limit: int = 50) -> List[DomainUser]:
        """
        Search users by email or username
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching users
        """
        try:
            search_term = f"%{query}%"
            db_users = self.session.query(UserModel).filter(
                or_(
                    UserModel.email.ilike(search_term),
                    UserModel.username.ilike(search_term),
                    UserModel.full_name.ilike(search_term)
                )
            ).limit(limit).all()
            
            return [user.to_domain() for user in db_users]
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []