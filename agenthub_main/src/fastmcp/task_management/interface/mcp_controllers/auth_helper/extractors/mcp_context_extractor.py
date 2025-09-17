"""MCP Context Extractor for Authentication"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MCPContextExtractor:
    """Extract user ID from MCP authentication context"""
    
    @staticmethod
    def extract_user_id() -> Optional[str]:
        """
        Try to extract user_id from MCP authentication context.
        
        Returns:
            User ID from MCP context or None
        """
        try:
            # Try importing MCP auth context - this may fail if module doesn't exist
            from mcp.server.auth.context import auth_context
            from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
            
            mcp_auth_context = auth_context.get()
            logger.info(f"🎯 MCP auth context type: {type(mcp_auth_context)}")
            
            if isinstance(mcp_auth_context, AuthenticatedUser):
                # We have an AuthenticatedUser from MCP
                if hasattr(mcp_auth_context, 'access_token') and mcp_auth_context.access_token:
                    user_id = mcp_auth_context.access_token.client_id
                    logger.info(f"✅ Got user_id from MCP AuthenticatedUser.access_token: {user_id}")
                    return user_id
                elif hasattr(mcp_auth_context, 'identity'):
                    user_id = mcp_auth_context.identity
                    logger.info(f"✅ Got user_id from MCP AuthenticatedUser.identity: {user_id}")
                    return user_id
            elif mcp_auth_context and hasattr(mcp_auth_context, 'user_id'):
                user_id = mcp_auth_context.user_id
                logger.info(f"✅ Got user_id from MCP auth context: {user_id}")
                return user_id
            elif mcp_auth_context and hasattr(mcp_auth_context, 'client_id'):
                user_id = mcp_auth_context.client_id
                logger.info(f"✅ Got user_id from MCP auth client_id: {user_id}")
                return user_id
            elif mcp_auth_context:
                logger.warning(f"⚠️ MCP auth context available but no user_id/client_id: {dir(mcp_auth_context)}")
            else:
                logger.warning("⚠️ No MCP auth context available")
        except ImportError as e:
            logger.info(f"⚠️ MCP auth context module not available: {e}")
            logger.info("⚠️ This is expected if using DualAuthMiddleware instead of MCP auth system")
        except Exception as e:
            logger.info(f"⚠️ Could not access MCP auth context: {e}")
        
        return None