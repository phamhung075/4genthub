"""
Token Consumption Service - Application Layer

This service orchestrates token consumption operations including consuming tokens,
adding tokens, getting balance, and managing quotas.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ...config.token_costs import get_operation_cost
from ...domain.repositories.token_balance_repository import ITokenBalanceRepository
from ...infrastructure.repositories.token_balance_repository import (
    TokenBalanceRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class TokenConsumptionResult:
    """Result of a token consumption attempt"""
    success: bool
    remaining_balance: int | None = None
    consumed: int | None = None
    error_message: str | None = None
    error_code: str | None = None
    operation: str | None = None


@dataclass
class TokenBalanceResult:
    """Result of getting token balance"""
    success: bool
    balance: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class TokenAdditionResult:
    """Result of adding tokens"""
    success: bool
    new_balance: int | None = None
    added: int | None = None
    error_message: str | None = None


class TokenConsumptionService:
    """
    Token Consumption Service

    This service handles all token-related operations including:
    - Consuming tokens for MCP operations
    - Adding tokens to user balances
    - Getting token balance and usage statistics
    - Managing quotas and resets
    """

    def __init__(self, session: Session, token_repository: ITokenBalanceRepository | None = None):
        """
        Initialize token consumption service

        Args:
            session: SQLAlchemy database session
            token_repository: Token balance repository (optional, will create if not provided)
        """
        self.session = session
        self.token_repository = token_repository or TokenBalanceRepository(session)

    async def consume_tokens_for_operation(
        self,
        user_id: str,
        operation: str,
        custom_cost: int | None = None
    ) -> TokenConsumptionResult:
        """
        Consume tokens for a specific MCP operation

        This is the main method used by MCP controllers.
        It determines the cost based on operation type and consumes tokens.

        Args:
            user_id: User identifier
            operation: Operation name (e.g., 'create_project', 'call_agent')
            custom_cost: Override the default cost for this operation (optional)

        Returns:
            TokenConsumptionResult with success status and balance information
        """
        try:
            # Determine token cost
            cost = custom_cost if custom_cost is not None else get_operation_cost(operation, default=1)

            # Skip if operation is free
            if cost == 0:
                return TokenConsumptionResult(
                    success=True,
                    consumed=0,
                    operation=operation,
                    error_message="Operation is free - no tokens consumed"
                )

            # Ensure user has a token balance record
            balance = await self.token_repository.get_balance(user_id)
            if not balance:
                # Auto-create balance for new users
                logger.info(f"Creating token balance for user {user_id}")
                await self.token_repository.create_balance(user_id)

            # Consume tokens
            success = await self.token_repository.consume_tokens(user_id, cost)

            if not success:
                # Get current balance for error message
                balance = await self.token_repository.get_balance(user_id)
                available = balance["available_tokens"] if balance else 0

                return TokenConsumptionResult(
                    success=False,
                    error_message=f"Insufficient tokens. Required: {cost}, Available: {available}",
                    error_code="INSUFFICIENT_TOKENS",
                    operation=operation
                )

            # Get updated balance
            balance = await self.token_repository.get_balance(user_id)

            logger.info(
                f"Consumed {cost} tokens for {operation} (user: {user_id}, "
                f"remaining: {balance['available_tokens']})"
            )

            return TokenConsumptionResult(
                success=True,
                remaining_balance=balance["available_tokens"],
                consumed=cost,
                operation=operation
            )

        except Exception as e:
            logger.error(f"Error consuming tokens for user {user_id}, operation {operation}: {e}")
            return TokenConsumptionResult(
                success=False,
                error_message=f"Token consumption failed: {str(e)}",
                error_code="CONSUMPTION_ERROR",
                operation=operation
            )

    async def consume_tokens(
        self,
        user_id: str,
        amount: int,
        operation: str | None = None
    ) -> TokenConsumptionResult:
        """
        Consume a specific amount of tokens

        Lower-level method for consuming arbitrary token amounts.

        Args:
            user_id: User identifier
            amount: Number of tokens to consume
            operation: Operation name for logging (optional)

        Returns:
            TokenConsumptionResult with success status and balance information
        """
        try:
            if amount <= 0:
                return TokenConsumptionResult(
                    success=False,
                    error_message="Token amount must be positive",
                    error_code="INVALID_AMOUNT"
                )

            # Ensure user has a token balance record
            balance = await self.token_repository.get_balance(user_id)
            if not balance:
                await self.token_repository.create_balance(user_id)

            # Consume tokens
            success = await self.token_repository.consume_tokens(user_id, amount)

            if not success:
                balance = await self.token_repository.get_balance(user_id)
                available = balance["available_tokens"] if balance else 0

                return TokenConsumptionResult(
                    success=False,
                    error_message=f"Insufficient tokens. Required: {amount}, Available: {available}",
                    error_code="INSUFFICIENT_TOKENS",
                    operation=operation
                )

            # Get updated balance
            balance = await self.token_repository.get_balance(user_id)

            return TokenConsumptionResult(
                success=True,
                remaining_balance=balance["available_tokens"],
                consumed=amount,
                operation=operation
            )

        except Exception as e:
            logger.error(f"Error consuming tokens for user {user_id}: {e}")
            return TokenConsumptionResult(
                success=False,
                error_message=f"Token consumption failed: {str(e)}",
                error_code="CONSUMPTION_ERROR"
            )

    async def add_tokens(
        self,
        user_id: str,
        amount: int,
        reason: str | None = None
    ) -> TokenAdditionResult:
        """
        Add tokens to user's balance

        Used for:
        - Token purchases
        - Admin grants
        - Promotional credits
        - Refunds

        Args:
            user_id: User identifier
            amount: Number of tokens to add
            reason: Reason for adding tokens (for logging)

        Returns:
            TokenAdditionResult with new balance
        """
        try:
            if amount <= 0:
                return TokenAdditionResult(
                    success=False,
                    error_message="Token amount must be positive"
                )

            # Ensure user has a token balance record
            balance = await self.token_repository.get_balance(user_id)
            if not balance:
                await self.token_repository.create_balance(user_id, initial_tokens=amount)
                balance = await self.token_repository.get_balance(user_id)
                logger.info(f"Created balance with {amount} tokens for user {user_id} - {reason or 'No reason'}")
            else:
                # Add tokens
                success = await self.token_repository.add_tokens(user_id, amount)
                if not success:
                    return TokenAdditionResult(
                        success=False,
                        error_message="Failed to add tokens - user not found"
                    )

                balance = await self.token_repository.get_balance(user_id)
                logger.info(f"Added {amount} tokens for user {user_id} - {reason or 'No reason'}")

            return TokenAdditionResult(
                success=True,
                new_balance=balance["available_tokens"],
                added=amount
            )

        except Exception as e:
            logger.error(f"Error adding tokens for user {user_id}: {e}")
            return TokenAdditionResult(
                success=False,
                error_message=f"Failed to add tokens: {str(e)}"
            )

    async def get_balance(self, user_id: str) -> TokenBalanceResult:
        """
        Get user's token balance

        Args:
            user_id: User identifier

        Returns:
            TokenBalanceResult with balance information
        """
        try:
            balance = await self.token_repository.get_balance(user_id)

            if not balance:
                # Auto-create balance for new users
                await self.token_repository.create_balance(user_id)
                balance = await self.token_repository.get_balance(user_id)

            return TokenBalanceResult(
                success=True,
                balance=balance
            )

        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            return TokenBalanceResult(
                success=False,
                error_message=f"Failed to get balance: {str(e)}"
            )

    async def get_usage_stats(self, user_id: str) -> TokenBalanceResult:
        """
        Get detailed usage statistics for a user

        Args:
            user_id: User identifier

        Returns:
            TokenBalanceResult with detailed usage statistics
        """
        try:
            stats = await self.token_repository.get_usage_stats(user_id)

            if not stats:
                # Auto-create balance for new users
                await self.token_repository.create_balance(user_id)
                stats = await self.token_repository.get_usage_stats(user_id)

            return TokenBalanceResult(
                success=True,
                balance=stats
            )

        except Exception as e:
            logger.error(f"Error getting usage stats for user {user_id}: {e}")
            return TokenBalanceResult(
                success=False,
                error_message=f"Failed to get usage stats: {str(e)}"
            )

    async def update_quota(
        self,
        user_id: str,
        new_quota: int,
        reason: str | None = None
    ) -> TokenAdditionResult:
        """
        Update user's monthly quota

        Args:
            user_id: User identifier
            new_quota: New monthly quota amount
            reason: Reason for quota change (for logging)

        Returns:
            TokenAdditionResult with success status
        """
        try:
            if new_quota < 0:
                return TokenAdditionResult(
                    success=False,
                    error_message="Quota cannot be negative"
                )

            success = await self.token_repository.update_quota(user_id, new_quota)

            if not success:
                return TokenAdditionResult(
                    success=False,
                    error_message="Failed to update quota - user not found"
                )

            logger.info(f"Updated quota for user {user_id} to {new_quota} - {reason or 'No reason'}")

            balance = await self.token_repository.get_balance(user_id)
            return TokenAdditionResult(
                success=True,
                new_balance=balance["available_tokens"]
            )

        except Exception as e:
            logger.error(f"Error updating quota for user {user_id}: {e}")
            return TokenAdditionResult(
                success=False,
                error_message=f"Failed to update quota: {str(e)}"
            )

    async def reset_monthly_quota(self, user_id: str) -> TokenBalanceResult:
        """
        Manually reset monthly quota for a user

        Args:
            user_id: User identifier

        Returns:
            TokenBalanceResult with updated balance
        """
        try:
            success = await self.token_repository.reset_monthly_quota(user_id)

            if not success:
                return TokenBalanceResult(
                    success=False,
                    error_message="Failed to reset quota - user not found"
                )

            balance = await self.token_repository.get_balance(user_id)
            logger.info(f"Manually reset monthly quota for user {user_id}")

            return TokenBalanceResult(
                success=True,
                balance=balance
            )

        except Exception as e:
            logger.error(f"Error resetting quota for user {user_id}: {e}")
            return TokenBalanceResult(
                success=False,
                error_message=f"Failed to reset quota: {str(e)}"
            )

    async def check_sufficient_balance(
        self,
        user_id: str,
        operation: str,
        custom_cost: int | None = None
    ) -> tuple[bool, int, int]:
        """
        Check if user has sufficient balance for an operation

        Useful for pre-flight checks before expensive operations.

        Args:
            user_id: User identifier
            operation: Operation name
            custom_cost: Override the default cost (optional)

        Returns:
            Tuple of (has_sufficient_balance, required_cost, available_balance)
        """
        try:
            cost = custom_cost if custom_cost is not None else get_operation_cost(operation, default=1)

            balance = await self.token_repository.get_balance(user_id)
            if not balance:
                return (False, cost, 0)

            available = balance["available_tokens"]
            return (available >= cost, cost, available)

        except Exception as e:
            logger.error(f"Error checking balance for user {user_id}: {e}")
            return (False, 0, 0)
