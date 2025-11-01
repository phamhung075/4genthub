"""
Token Consumption Helper for MCP Controllers

This module provides a reusable helper for integrating token consumption
into MCP controllers following clean architecture principles.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ....auth.application.services.token_consumption_service import (
    TokenConsumptionService,
    TokenConsumptionResult
)
from ....auth.infrastructure.repositories.token_balance_repository import TokenBalanceRepository
from .auth_helper import get_authenticated_user_id

logger = logging.getLogger(__name__)


class TokenConsumptionHelper:
    """
    Helper class for MCP controllers to consume tokens before operations.

    This provides a clean, reusable interface for token consumption that:
    - Extracts user_id from authentication context
    - Consumes tokens for the operation
    - Returns standardized error responses
    - Adds token_info to successful responses
    """

    def __init__(self, session: Session):
        """
        Initialize token consumption helper

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self._token_service: Optional[TokenConsumptionService] = None

    @property
    def token_service(self) -> TokenConsumptionService:
        """Lazy-load token service"""
        if self._token_service is None:
            repository = TokenBalanceRepository(self.session)
            self._token_service = TokenConsumptionService(self.session, repository)
        return self._token_service

    async def consume_tokens(
        self,
        operation: str,
        user_id: Optional[str] = None,
        custom_cost: Optional[int] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Consume tokens for an MCP operation

        Args:
            operation: Operation name (e.g., 'create_project', 'call_agent')
            user_id: Optional user ID (will be extracted from auth context if not provided)
            custom_cost: Optional custom token cost (overrides default from config)

        Returns:
            Tuple of (success: bool, error_response: Optional[Dict])
            - If success=True, error_response is None - proceed with operation
            - If success=False, error_response contains the error to return to client
        """
        try:
            # Get authenticated user ID
            authenticated_user_id = get_authenticated_user_id(
                provided_user_id=user_id,
                operation_name=operation
            )

            # Consume tokens
            result: TokenConsumptionResult = await self.token_service.consume_tokens_for_operation(
                user_id=authenticated_user_id,
                operation=operation,
                custom_cost=custom_cost
            )

            if not result.success:
                # Return error response for insufficient tokens or other failures
                error_response = {
                    "success": False,
                    "error": result.error_message,
                    "error_code": result.error_code or "TOKEN_CONSUMPTION_FAILED",
                    "operation": operation
                }

                if result.error_code == "INSUFFICIENT_TOKENS":
                    error_response["status_code"] = 402  # Payment Required

                logger.warning(
                    f"Token consumption failed for {operation}: {result.error_message}"
                )
                return (False, error_response)

            # Success - store result for adding to response later
            logger.debug(
                f"Consumed {result.consumed} tokens for {operation}, "
                f"remaining: {result.remaining_balance}"
            )
            return (True, None)

        except Exception as e:
            logger.error(f"Error in token consumption for {operation}: {e}")
            error_response = {
                "success": False,
                "error": f"Token consumption error: {str(e)}",
                "error_code": "TOKEN_SYSTEM_ERROR",
                "operation": operation
            }
            return (False, error_response)

    async def get_token_info(
        self,
        operation: str,
        user_id: Optional[str] = None,
        custom_cost: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get token consumption info for adding to successful responses

        This method should be called AFTER consume_tokens() succeeds,
        to add token_info to the operation response.

        Args:
            operation: Operation name
            user_id: Optional user ID (will be extracted from auth context if not provided)
            custom_cost: Optional custom token cost

        Returns:
            Dictionary with token info to add to response:
            {
                "consumed": int,
                "remaining_balance": int,
                "operation": str
            }
        """
        try:
            # Get authenticated user ID
            authenticated_user_id = get_authenticated_user_id(
                provided_user_id=user_id,
                operation_name=operation
            )

            # Get current balance
            balance_result = await self.token_service.get_balance(authenticated_user_id)

            if not balance_result.success:
                return {
                    "operation": operation,
                    "error": "Could not retrieve balance info"
                }

            # Get operation cost
            from ....auth.config.token_costs import get_operation_cost
            cost = custom_cost if custom_cost is not None else get_operation_cost(operation, default=1)

            return {
                "consumed": cost,
                "remaining_balance": balance_result.balance.get("available_tokens", 0),
                "operation": operation
            }

        except Exception as e:
            logger.error(f"Error getting token info for {operation}: {e}")
            return {
                "operation": operation,
                "error": str(e)
            }

    async def consume_and_add_info(
        self,
        operation: str,
        response: Dict[str, Any],
        user_id: Optional[str] = None,
        custom_cost: Optional[int] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Consume tokens and add token_info to response in one step

        This is a convenience method that combines consume_tokens() and get_token_info().

        Args:
            operation: Operation name
            response: The response dict to add token_info to
            user_id: Optional user ID
            custom_cost: Optional custom token cost

        Returns:
            Tuple of (success: bool, response: Dict)
            - If success=True, response has token_info added
            - If success=False, response is the error response
        """
        # Try to consume tokens
        success, error_response = await self.consume_tokens(operation, user_id, custom_cost)

        if not success:
            return (False, error_response)

        # Get token info
        token_info = await self.get_token_info(operation, user_id, custom_cost)

        # Add to response
        response["token_info"] = token_info

        return (True, response)


# Convenience function for quick integration
async def consume_tokens_for_operation(
    session: Session,
    operation: str,
    user_id: Optional[str] = None,
    custom_cost: Optional[int] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Standalone function for consuming tokens (no class instance needed)

    Args:
        session: SQLAlchemy database session
        operation: Operation name
        user_id: Optional user ID
        custom_cost: Optional custom token cost

    Returns:
        Tuple of (success: bool, error_response: Optional[Dict])
    """
    helper = TokenConsumptionHelper(session)
    return await helper.consume_tokens(operation, user_id, custom_cost)
