"""
Email Token Repository

Handles storage and retrieval of email verification and password reset tokens.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
import json

logger = logging.getLogger(__name__)

Base = declarative_base()


class EmailTokenModel(Base):
    """SQLAlchemy model for email tokens"""
    __tablename__ = "email_tokens"
    
    token = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    token_type = Column(String(50), nullable=False)  # 'verification', 'password_reset'
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)
    token_metadata = Column(Text, nullable=True)  # JSON string for additional data
    user_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)


@dataclass
class EmailToken:
    """Email token data class"""
    token: str
    email: str
    token_type: str
    token_hash: str
    expires_at: datetime
    created_at: datetime
    used_at: Optional[datetime] = None
    is_used: bool = False
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class EmailTokenRepository:
    """Repository for managing email tokens"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize repository with database connection"""
        if database_url is None:
            # Use database URL from environment or default to SQLite
            database_url = os.getenv(
                "DATABASE_URL", 
                "sqlite:///./email_tokens.db"
            )
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        
        logger.info("Email token repository initialized")
    
    def _model_to_token(self, model: EmailTokenModel) -> EmailToken:
        """Convert SQLAlchemy model to EmailToken"""
        metadata = None
        if model.token_metadata:
            try:
                metadata = json.loads(model.token_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON metadata for token {model.token}")
        
        return EmailToken(
            token=model.token,
            email=model.email,
            token_type=model.token_type,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            created_at=model.created_at,
            used_at=model.used_at,
            is_used=model.is_used,
            metadata=metadata,
            user_id=model.user_id,
            ip_address=model.ip_address,
            user_agent=model.user_agent
        )
    
    def _token_to_model(self, token: EmailToken) -> EmailTokenModel:
        """Convert EmailToken to SQLAlchemy model"""
        metadata_json = None
        if token.metadata:
            try:
                metadata_json = json.dumps(token.metadata)
            except (TypeError, ValueError):
                logger.warning(f"Cannot serialize metadata for token {token.token}")
        
        return EmailTokenModel(
            token=token.token,
            email=token.email,
            token_type=token.token_type,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            created_at=token.created_at,
            used_at=token.used_at,
            is_used=token.is_used,
            token_metadata=metadata_json,
            user_id=token.user_id,
            ip_address=token.ip_address,
            user_agent=token.user_agent
        )
    
    def save_token(self, token: EmailToken) -> bool:
        """Save email token to database"""
        try:
            with self.SessionLocal() as session:
                model = self._token_to_model(token)
                session.add(model)
                session.commit()
                logger.info(f"Saved email token for {token.email} (type: {token.token_type})")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to save email token: {e}")
            return False
    
    def get_token(self, token: str) -> Optional[EmailToken]:
        """Get email token by token string"""
        try:
            with self.SessionLocal() as session:
                model = session.query(EmailTokenModel).filter_by(token=token).first()
                if model:
                    return self._model_to_token(model)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Failed to get email token: {e}")
            return None
    
    def get_tokens_by_email(
        self, 
        email: str, 
        token_type: Optional[str] = None,
        include_used: bool = False
    ) -> List[EmailToken]:
        """Get email tokens by email address"""
        try:
            with self.SessionLocal() as session:
                query = session.query(EmailTokenModel).filter_by(email=email)
                
                if token_type:
                    query = query.filter_by(token_type=token_type)
                
                if not include_used:
                    query = query.filter_by(is_used=False)
                
                models = query.order_by(EmailTokenModel.created_at.desc()).all()
                return [self._model_to_token(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(f"Failed to get email tokens: {e}")
            return []
    
    def mark_token_used(self, token: str, used_at: Optional[datetime] = None) -> bool:
        """Mark token as used"""
        if used_at is None:
            used_at = datetime.now(timezone.utc)
        
        try:
            with self.SessionLocal() as session:
                session.query(EmailTokenModel).filter_by(token=token).update({
                    'is_used': True,
                    'used_at': used_at
                })
                session.commit()
                logger.info(f"Marked token as used: {token}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to mark token as used: {e}")
            return False
    
    def delete_token(self, token: str) -> bool:
        """Delete email token"""
        try:
            with self.SessionLocal() as session:
                deleted = session.query(EmailTokenModel).filter_by(token=token).delete()
                session.commit()
                if deleted:
                    logger.info(f"Deleted email token: {token}")
                return deleted > 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete email token: {e}")
            return False
    
    def cleanup_expired_tokens(self, older_than_days: int = 7) -> int:
        """Clean up expired and old tokens"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        try:
            with self.SessionLocal() as session:
                # Delete tokens that are either expired or older than cutoff
                deleted = session.query(EmailTokenModel).filter(
                    (EmailTokenModel.expires_at < datetime.now(timezone.utc)) |
                    (EmailTokenModel.created_at < cutoff_date)
                ).delete(synchronize_session=False)
                
                session.commit()
                logger.info(f"Cleaned up {deleted} expired/old email tokens")
                return deleted
        except SQLAlchemyError as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0
    
    def validate_token(
        self, 
        token: str, 
        email: str, 
        token_type: str,
        mark_used: bool = True
    ) -> Optional[EmailToken]:
        """Validate email token and optionally mark as used"""
        try:
            with self.SessionLocal() as session:
                model = session.query(EmailTokenModel).filter_by(
                    token=token,
                    email=email,
                    token_type=token_type
                ).first()
                
                if not model:
                    logger.warning(f"Token not found: {token}")
                    return None
                
                token_obj = self._model_to_token(model)
                
                # Check if token is already used
                if token_obj.is_used:
                    logger.warning(f"Token already used: {token}")
                    return None
                
                # Check if token is expired
                # Handle both naive and aware datetimes
                expires_at = token_obj.expires_at
                if expires_at.tzinfo is None:
                    # If naive, assume UTC
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < datetime.now(timezone.utc):
                    logger.warning(f"Token expired: {token}")
                    return None
                
                # Mark as used if requested
                if mark_used:
                    model.is_used = True
                    model.used_at = datetime.now(timezone.utc)
                    session.commit()
                    token_obj.is_used = True
                    token_obj.used_at = model.used_at
                
                logger.info(f"Token validated successfully: {token}")
                return token_obj
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to validate token: {e}")
            return None
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        try:
            with self.SessionLocal() as session:
                total_tokens = session.query(EmailTokenModel).count()
                used_tokens = session.query(EmailTokenModel).filter_by(is_used=True).count()
                expired_tokens = session.query(EmailTokenModel).filter(
                    EmailTokenModel.expires_at < datetime.now(timezone.utc)
                ).count()
                
                # Token counts by type
                verification_tokens = session.query(EmailTokenModel).filter_by(
                    token_type='verification'
                ).count()
                reset_tokens = session.query(EmailTokenModel).filter_by(
                    token_type='password_reset'
                ).count()
                
                return {
                    "total_tokens": total_tokens,
                    "used_tokens": used_tokens,
                    "expired_tokens": expired_tokens,
                    "active_tokens": total_tokens - used_tokens - expired_tokens,
                    "verification_tokens": verification_tokens,
                    "reset_tokens": reset_tokens,
                    "usage_rate": (used_tokens / total_tokens * 100) if total_tokens > 0 else 0
                }
        except SQLAlchemyError as e:
            logger.error(f"Failed to get token stats: {e}")
            return {}


# Global repository instance
_token_repository: Optional[EmailTokenRepository] = None


def get_email_token_repository() -> EmailTokenRepository:
    """Get global email token repository instance"""
    global _token_repository
    if _token_repository is None:
        _token_repository = EmailTokenRepository()
    return _token_repository