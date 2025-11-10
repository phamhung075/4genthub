"""Token Balance Repository Interface

This repository interface defines the contract for token balance operations
following the Repository pattern in Domain-Driven Design.
"""

from abc import ABC, abstractmethod
from typing import Any


class ITokenBalanceRepository(ABC):
    """Repository interface for UserTokenBalance aggregate"""

    @abstractmethod
    async def get_balance(self, user_id: str) -> dict[str, Any] | None:
        """
        Get token balance for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary with balance data or None if not found
            Contains: available_tokens, monthly_quota, tokens_consumed_today,
                     tokens_consumed_this_month, total_tokens_consumed,
                     last_reset_at, next_reset_at
        """
        pass

    @abstractmethod
    async def create_balance(
        self,
        user_id: str,
        initial_tokens: int = 10000,
        monthly_quota: int = 10000
    ) -> dict[str, Any]:
        """
        Create new token balance for a user

        Args:
            user_id: User identifier
            initial_tokens: Initial token amount (default: 10000)
            monthly_quota: Monthly quota (default: 10000)

        Returns:
            Dictionary with created balance data

        Raises:
            IntegrityError: If balance already exists for user
        """
        pass

    @abstractmethod
    async def consume_tokens(self, user_id: str, amount: int) -> bool:
        """
        Consume tokens from user's balance

        This is an atomic operation that:
        1. Checks if sufficient tokens available
        2. Deducts tokens from available_tokens
        3. Updates consumption counters (daily, monthly, total)

        Args:
            user_id: User identifier
            amount: Number of tokens to consume

        Returns:
            True if tokens consumed successfully, False if insufficient balance

        Raises:
            ValueError: If amount is negative or zero
        """
        pass

    @abstractmethod
    async def add_tokens(self, user_id: str, amount: int) -> bool:
        """
        Add tokens to user's balance

        Args:
            user_id: User identifier
            amount: Number of tokens to add

        Returns:
            True if tokens added successfully, False if user not found

        Raises:
            ValueError: If amount is negative or zero
        """
        pass

    @abstractmethod
    async def update_quota(self, user_id: str, new_quota: int) -> bool:
        """
        Update user's monthly quota

        Args:
            user_id: User identifier
            new_quota: New monthly quota amount

        Returns:
            True if quota updated successfully, False if user not found

        Raises:
            ValueError: If new_quota is negative
        """
        pass

    @abstractmethod
    async def get_usage_stats(self, user_id: str) -> dict[str, Any] | None:
        """
        Get detailed usage statistics for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary with usage statistics or None if not found
            Contains: available_tokens, monthly_quota, tokens_consumed_today,
                     tokens_consumed_this_month, total_tokens_consumed,
                     utilization_percentage, days_until_reset
        """
        pass

    @abstractmethod
    async def reset_monthly_quota(self, user_id: str) -> bool:
        """
        Reset monthly quota for a user

        This operation:
        1. Sets available_tokens = monthly_quota
        2. Resets tokens_consumed_this_month = 0
        3. Updates last_reset_at = now
        4. Calculates next_reset_at (first day of next month)

        Args:
            user_id: User identifier

        Returns:
            True if reset successfully, False if user not found
        """
        pass

    @abstractmethod
    async def reset_daily_consumption(self, user_id: str) -> bool:
        """
        Reset daily consumption counter

        Args:
            user_id: User identifier

        Returns:
            True if reset successfully, False if user not found
        """
        pass

    @abstractmethod
    async def check_and_auto_reset(self, user_id: str) -> bool:
        """
        Check if quota should be reset and auto-reset if needed

        Checks next_reset_at and performs reset if current time >= next_reset_at

        Args:
            user_id: User identifier

        Returns:
            True if reset was performed, False otherwise
        """
        pass
