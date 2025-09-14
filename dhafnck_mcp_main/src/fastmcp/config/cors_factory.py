"""
CORS Configuration Factory
Centralized CORS configuration for all FastAPI applications.
Ensures consistent CORS settings across all endpoints.
"""

import os
import logging
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


class CORSFactory:
    """Factory for creating consistent CORS configurations."""

    @staticmethod
    def get_allowed_origins() -> List[str]:
        """
        Get allowed origins from environment variable.
        Returns a list of allowed origins, never returns wildcard when credentials are used.
        """
        cors_origins_str = os.environ.get("CORS_ORIGINS", "")

        if cors_origins_str:
            # Parse comma-separated origins
            origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

            # Security check: If wildcard is requested, log warning
            if "*" in origins:
                logger.warning("Wildcard (*) CORS requested but not recommended with credentials")
                # For development, allow specific localhost origins instead
                origins = [
                    "http://localhost:3800",
                    "http://localhost:3000",
                    "http://127.0.0.1:3800",
                    "http://127.0.0.1:3000"
                ]
                logger.info(f"Using safe localhost origins instead: {origins}")

            logger.info(f"CORS origins configured: {origins}")
            return origins
        else:
            # Default to common development origins
            default_origins = [
                "http://localhost:3800",
                "http://localhost:3000",
                "http://127.0.0.1:3800",
                "http://127.0.0.1:3000"
            ]
            logger.info(f"Using default CORS origins: {default_origins}")
            return default_origins

    @staticmethod
    def configure_cors(app: FastAPI,
                      allow_credentials: bool = True,
                      custom_origins: Optional[List[str]] = None) -> None:
        """
        Configure CORS middleware for a FastAPI application.

        Args:
            app: FastAPI application instance
            allow_credentials: Whether to allow credentials (cookies, auth headers)
            custom_origins: Optional custom origins list (overrides environment)
        """
        # Get origins
        origins = custom_origins or CORSFactory.get_allowed_origins()

        # Security check: Never use wildcard with credentials
        if allow_credentials and "*" in origins:
            logger.error("SECURITY WARNING: Cannot use wildcard (*) with credentials!")
            origins = [o for o in origins if o != "*"]
            if not origins:
                origins = ["http://localhost:3800"]  # Fallback to safe default

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=allow_credentials,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=["*"],  # Allow all headers
            expose_headers=["*"],  # Expose all headers
            max_age=600,  # Cache preflight requests for 10 minutes
        )

        logger.info(f"CORS configured for {len(origins)} origins with credentials={allow_credentials}")

    @staticmethod
    def get_cors_config() -> dict:
        """
        Get CORS configuration as a dictionary.
        Useful for debugging and status endpoints.
        """
        origins = CORSFactory.get_allowed_origins()
        return {
            "allowed_origins": origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["*"],
            "expose_headers": ["*"],
            "max_age": 600,
            "environment_variable": os.environ.get("CORS_ORIGINS", "not set"),
        }


# Singleton instance for easy import
cors_factory = CORSFactory()