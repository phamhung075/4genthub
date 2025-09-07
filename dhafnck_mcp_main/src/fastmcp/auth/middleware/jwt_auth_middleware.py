"""
JWT Authentication Middleware

This module provides middleware for extracting and validating JWT tokens
and creating user-scoped repositories and services.
"""

import logging
from typing import Optional, Tuple, Any
from functools import wraps
from sqlalchemy.orm import Session
import jwt
from jwt import InvalidTokenError

logger = logging.getLogger(__name__)


class JWTAuthMiddleware:
    """Middleware for JWT authentication and user context management."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", enabled: bool = True):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.enabled = enabled  # Add enabled attribute for compatibility
        
        # Enhanced debug logging for JWT secret
        logger.info(f"🔐 JWTAuthMiddleware initialized with secret length: {len(secret_key)} chars")
        logger.debug(f"🔐 JWTAuthMiddleware secret (first 10 chars): {secret_key[:10]}...")
        if secret_key == "default-secret-key-change-in-production":
            logger.warning("⚠️ JWTAuthMiddleware using default fallback secret key!")
    
    def extract_user_from_token(self, token: str) -> Optional[str]:
        """
        Extract user_id from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID if valid token, None otherwise
        """
        try:
            # Remove Bearer prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Enhanced debug logging for token validation
            logger.debug(f"🔍 JWTAuthMiddleware attempting token decode with secret length: {len(self.secret_key)}")
            logger.debug(f"🔍 Token length: {len(token)} chars")
            
            # Try to decode token with audience validation for Supabase tokens
            payload = None
            
            # First try with "authenticated" audience (Supabase tokens)
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                    audience="authenticated",
                    options={"verify_iss": False}  # Don't verify issuer for Supabase
                )
                logger.debug("✅ Token validated with audience='authenticated' (Supabase)")
            except jwt.InvalidAudienceError:
                logger.debug("Token doesn't have 'authenticated' audience, trying without audience")
            except Exception as e:
                logger.debug(f"Failed with audience='authenticated': {e}")
            
            # If that fails, try without audience validation (local tokens)
            if not payload:
                try:
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.algorithm],
                        options={"verify_aud": False}  # Skip audience check
                    )
                    logger.debug("✅ Token validated without audience check (local token)")
                except Exception as e:
                    logger.error(f"Failed without audience check: {e}")
                    raise
            
            logger.debug(f"✅ JWTAuthMiddleware successfully decoded token")
            
            # Extract user_id from payload
            user_id = payload.get("sub") or payload.get("user_id")
            
            if not user_id:
                logger.warning("JWT token missing user_id/sub claim")
                return None
            
            logger.debug(f"Extracted user_id {user_id} from JWT token")
            return user_id
            
        except InvalidTokenError as e:
            logger.error(f"❌ JWTAuthMiddleware - Invalid JWT token: {e}")
            logger.error(f"❌ Using secret length: {len(self.secret_key)}, algorithm: {self.algorithm}")
            logger.error(f"❌ Token (first 50 chars): {token[:50]}...")
            return None
        except Exception as e:
            logger.error(f"❌ JWTAuthMiddleware - Error extracting user from token: {e}")
            return None
    
    def get_auth_status(self) -> dict:
        """
        Get authentication system status.
        
        Returns:
            Authentication status and configuration
        """
        return {
            "enabled": self.enabled,
            "algorithm": self.algorithm,
            "secret_configured": self.secret_key != "default-secret-key-change-in-production",
            "middleware": "JWTAuthMiddleware",
            "features": {
                "jwt_validation": True,
                "supabase_tokens": True,
                "local_tokens": True,
                "audience_validation": True
            }
        }
    
    def create_user_scoped_repository(
        self,
        repository_class: type,
        session: Session,
        user_id: str,
        **kwargs
    ) -> Any:
        """
        Create a user-scoped repository instance.
        
        Args:
            repository_class: Repository class to instantiate
            session: Database session
            user_id: User ID for scoping
            **kwargs: Additional arguments for repository constructor
            
        Returns:
            User-scoped repository instance
        """
        # Check if repository supports user scoping
        if hasattr(repository_class, '__init__'):
            init_signature = repository_class.__init__.__code__.co_varnames
            if 'user_id' in init_signature:
                # Repository accepts user_id in constructor
                return repository_class(session=session, user_id=user_id, **kwargs)
        
        # Try to create repository and then apply user scoping
        repo = repository_class(session=session, **kwargs)
        
        if hasattr(repo, 'with_user'):
            # Repository has with_user method
            return repo.with_user(user_id)
        elif hasattr(repo, 'user_id'):
            # Repository has user_id property
            repo.user_id = user_id
            return repo
        else:
            # Repository doesn't support user scoping
            logger.warning(f"Repository {repository_class.__name__} doesn't support user scoping")
            return repo
    
    def create_user_scoped_service(
        self,
        service_class: type,
        user_id: str,
        **dependencies
    ) -> Any:
        """
        Create a user-scoped service instance.
        
        Args:
            service_class: Service class to instantiate
            user_id: User ID for scoping
            **dependencies: Service dependencies
            
        Returns:
            User-scoped service instance
        """
        # Check if service supports user scoping in constructor
        if hasattr(service_class, '__init__'):
            init_signature = service_class.__init__.__code__.co_varnames
            if 'user_id' in init_signature:
                # Service accepts user_id in constructor
                return service_class(user_id=user_id, **dependencies)
        
        # Try to create service and then apply user scoping
        service = service_class(**dependencies)
        
        if hasattr(service, 'with_user'):
            # Service has with_user method
            return service.with_user(user_id)
        elif hasattr(service, '_user_id'):
            # Service has _user_id property
            service._user_id = user_id
            return service
        else:
            # Service doesn't support user scoping
            logger.warning(f"Service {service_class.__name__} doesn't support user scoping")
            return service
    
    def require_auth(self, func):
        """
        Decorator to require authentication for a route.
        
        This decorator extracts the user_id from the JWT token
        and passes it to the route handler.
        """
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return {"error": "Authorization header missing"}, 401
            
            # Extract user_id from token
            user_id = self.extract_user_from_token(auth_header)
            if not user_id:
                return {"error": "Invalid or expired token"}, 401
            
            # Add user_id to kwargs
            kwargs['user_id'] = user_id
            
            # Call the original function
            return await func(request, *args, **kwargs)
        
        return wrapper


class UserContextManager:
    """Manager for propagating user context through the application."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._scoped_repositories = {}
        self._scoped_services = {}
    
    def get_repository(self, repository_class: type, session: Session, **kwargs) -> Any:
        """
        Get or create a user-scoped repository.
        
        Uses caching to avoid creating multiple instances.
        """
        cache_key = f"{repository_class.__name__}_{id(session)}"
        
        if cache_key not in self._scoped_repositories:
            middleware = JWTAuthMiddleware("dummy_key")  # Key not needed for this operation
            repo = middleware.create_user_scoped_repository(
                repository_class,
                session,
                self.user_id,
                **kwargs
            )
            self._scoped_repositories[cache_key] = repo
        
        return self._scoped_repositories[cache_key]
    
    def get_service(self, service_class: type, **dependencies) -> Any:
        """
        Get or create a user-scoped service.
        
        Uses caching to avoid creating multiple instances.
        """
        cache_key = service_class.__name__
        
        if cache_key not in self._scoped_services:
            middleware = JWTAuthMiddleware("dummy_key")  # Key not needed for this operation
            service = middleware.create_user_scoped_service(
                service_class,
                self.user_id,
                **dependencies
            )
            self._scoped_services[cache_key] = service
        
        return self._scoped_services[cache_key]
    
    def clear_cache(self):
        """Clear cached repositories and services."""
        self._scoped_repositories.clear()
        self._scoped_services.clear()


def create_auth_middleware(secret_key: str, algorithm: str = "HS256") -> JWTAuthMiddleware:
    """
    Factory function to create JWT authentication middleware.
    
    Args:
        secret_key: Secret key for JWT signing
        algorithm: JWT signing algorithm
        
    Returns:
        Configured JWTAuthMiddleware instance
    """
    return JWTAuthMiddleware(secret_key, algorithm)