"""Context Object Extractor for Authentication"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ContextObjectExtractor:
    """Extract user ID from various context object types"""
    
    @staticmethod
    def extract_user_id(context_obj) -> Optional[str]:
        """
        Extract user_id string from various context object types.
        
        Args:
            context_obj: Context object that might contain user_id
            
        Returns:
            User ID string or None if extraction fails
        """
        if context_obj is None:
            return None
        
        # If it's already a string, return it directly
        if isinstance(context_obj, str):
            return context_obj
        
        # Try to extract user_id attribute from context objects
        if hasattr(context_obj, 'user_id'):
            user_id = context_obj.user_id
            logger.info(f"🔧 Extracted user_id from context object: {user_id}")
            return user_id if isinstance(user_id, str) else str(user_id)
        
        # Try to extract id attribute as fallback
        if hasattr(context_obj, 'id'):
            user_id = context_obj.id
            logger.info(f"🔧 Extracted id from context object: {user_id}")
            return user_id if isinstance(user_id, str) else str(user_id)
        
        # If it's a dict-like object, try to get user_id key
        if hasattr(context_obj, 'get'):
            user_id = context_obj.get('user_id')
            if user_id:
                logger.info(f"🔧 Extracted user_id from dict-like object: {user_id}")
                return user_id if isinstance(user_id, str) else str(user_id)
        
        # Log the object type for debugging
        logger.warning(f"⚠️ Could not extract user_id from context object type: {type(context_obj)}")
        if hasattr(context_obj, '__dict__'):
            logger.debug(f"🔍 Context object attributes: {list(context_obj.__dict__.keys())}")
        
        return None