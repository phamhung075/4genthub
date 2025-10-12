"""Request State Extractor for Authentication"""

import logging

logger = logging.getLogger(__name__)


class RequestStateExtractor:
    """Extract user ID from request state"""

    @staticmethod
    def extract_user_id() -> str | None:
        """
        Try to get user_id from the current request state (set by DualAuthMiddleware).

        Returns:
            User ID from request state or None
        """
        try:
            # Try to get the current request from context
            from fastmcp.server.http_server import _current_http_request

            request = _current_http_request.get()

            logger.info(
                f"🔍 Request state check: request exists = {request is not None}"
            )

            if request and hasattr(request, "state"):
                logger.info(f"🔍 Request has state, attributes: {dir(request.state)}")
                if hasattr(request.state, "user_id"):
                    user_id_obj = request.state.user_id
                    logger.info(
                        f"🎯 Got user_id from request state: {user_id_obj} (type: {type(user_id_obj)})"
                    )

                    # Import extractor for context objects
                    from .context_object_extractor import ContextObjectExtractor

                    # Extract user_id from the context object (handles BackwardCompatUserContext objects)
                    extracted_user_id = ContextObjectExtractor.extract_user_id(
                        user_id_obj
                    )
                    logger.info(f"🔧 Extracted user_id: {extracted_user_id}")

                    if extracted_user_id:
                        logger.info(
                            f"✅ Got user_id from request state: {extracted_user_id}"
                        )
                        return extracted_user_id
                    else:
                        logger.warning("⚠️ Request state user_id could not be extracted")
                else:
                    logger.warning("⚠️ Request state exists but no user_id attribute")
            elif request:
                logger.warning(
                    f"⚠️ Request exists but no state. Request type: {type(request)}"
                )
            else:
                logger.warning("❌ No current HTTP request found in ContextVar")
        except ImportError as e:
            logger.error(f"❌ Could not import _current_http_request: {e}")
        except Exception as e:
            logger.error(f"❌ Error getting user_id from request state: {e}")
            import traceback

            logger.debug(f"Full traceback: {traceback.format_exc()}")

        return None
