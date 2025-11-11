"""
Token Balance Repository Implementation

This repository handles token balance persistence using SQLAlchemy.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.repositories.token_balance_repository import ITokenBalanceRepository
from ..database.models import UserTokenBalance

logger = logging.getLogger(__name__)


class TokenBalanceRepository(ITokenBalanceRepository):
    """Repository for token balance persistence operations"""

    def __init__(self, session: Session):
        """
        Initialize token balance repository

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    async def get_balance(self, user_id: str) -> dict[str, Any] | None:
        """Get token balance for a user"""
        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                return None

            return {
                "id": balance.id,
                "user_id": balance.user_id,
                "available_tokens": balance.available_tokens,
                "monthly_quota": balance.monthly_quota,
                "tokens_consumed_today": balance.tokens_consumed_today,
                "tokens_consumed_this_month": balance.tokens_consumed_this_month,
                "total_tokens_consumed": balance.total_tokens_consumed,
                "last_reset_at": balance.last_reset_at,
                "next_reset_at": balance.next_reset_at,
                "created_at": balance.created_at,
                "updated_at": balance.updated_at,
            }
        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            raise

    async def create_balance(
        self, user_id: str, initial_tokens: int = 10000, monthly_quota: int = 10000
    ) -> dict[str, Any]:
        """Create new token balance for a user"""
        try:
            # Calculate next reset date (first day of next month)
            now = datetime.now(UTC)
            # First day of next month
            if now.month == 12:
                next_reset = datetime(now.year + 1, 1, 1, tzinfo=UTC)
            else:
                next_reset = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

            balance = UserTokenBalance(
                id=str(uuid.uuid4()),
                user_id=user_id,
                available_tokens=initial_tokens,
                monthly_quota=monthly_quota,
                last_reset_at=now,
                next_reset_at=next_reset,
                tokens_consumed_today=0,
                tokens_consumed_this_month=0,
                total_tokens_consumed=0,
            )

            self.session.add(balance)
            self.session.flush()  # Flush to detect integrity errors

            return {
                "id": balance.id,
                "user_id": balance.user_id,
                "available_tokens": balance.available_tokens,
                "monthly_quota": balance.monthly_quota,
                "tokens_consumed_today": balance.tokens_consumed_today,
                "tokens_consumed_this_month": balance.tokens_consumed_this_month,
                "total_tokens_consumed": balance.total_tokens_consumed,
                "last_reset_at": balance.last_reset_at,
                "next_reset_at": balance.next_reset_at,
                "created_at": balance.created_at,
                "updated_at": balance.updated_at,
            }
        except IntegrityError as e:
            logger.error(f"Balance already exists for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating balance for user {user_id}: {e}")
            raise

    async def consume_tokens(self, user_id: str, amount: int) -> bool:
        """
        Consume tokens from user's balance (atomic operation)

        Returns True if successful, False if insufficient balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        try:
            # Check and perform auto-reset if needed
            await self.check_and_auto_reset(user_id)

            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                logger.warning(f"No balance found for user {user_id}")
                return False

            # Check if sufficient tokens available
            if balance.available_tokens < amount:
                logger.warning(
                    f"Insufficient tokens for user {user_id}: "
                    f"available={balance.available_tokens}, required={amount}"
                )
                return False

            # Atomic update - deduct tokens and update counters
            balance.available_tokens -= amount
            balance.tokens_consumed_today += amount
            balance.tokens_consumed_this_month += amount
            balance.total_tokens_consumed += amount

            self.session.flush()
            logger.info(
                f"Consumed {amount} tokens for user {user_id}, remaining: {balance.available_tokens}"
            )
            return True

        except Exception as e:
            logger.error(f"Error consuming tokens for user {user_id}: {e}")
            raise

    async def add_tokens(self, user_id: str, amount: int) -> bool:
        """Add tokens to user's balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                logger.warning(f"No balance found for user {user_id}")
                return False

            balance.available_tokens += amount
            self.session.flush()

            logger.info(
                f"Added {amount} tokens for user {user_id}, new balance: {balance.available_tokens}"
            )
            return True

        except Exception as e:
            logger.error(f"Error adding tokens for user {user_id}: {e}")
            raise

    async def update_quota(self, user_id: str, new_quota: int) -> bool:
        """Update user's monthly quota"""
        if new_quota < 0:
            raise ValueError("Quota cannot be negative")

        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                logger.warning(f"No balance found for user {user_id}")
                return False

            old_quota = balance.monthly_quota
            balance.monthly_quota = new_quota
            self.session.flush()

            logger.info(f"Updated quota for user {user_id}: {old_quota} -> {new_quota}")
            return True

        except Exception as e:
            logger.error(f"Error updating quota for user {user_id}: {e}")
            raise

    async def get_usage_stats(self, user_id: str) -> dict[str, Any] | None:
        """Get detailed usage statistics for a user"""
        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                return None

            # Calculate utilization percentage
            utilization = 0.0
            if balance.monthly_quota > 0:
                consumed = balance.monthly_quota - balance.available_tokens
                utilization = (consumed / balance.monthly_quota) * 100

            # Calculate days until reset
            days_until_reset = 0
            if balance.next_reset_at:
                delta = balance.next_reset_at - datetime.now(UTC)
                days_until_reset = max(0, delta.days)

            return {
                "user_id": balance.user_id,
                "available_tokens": balance.available_tokens,
                "monthly_quota": balance.monthly_quota,
                "tokens_consumed_today": balance.tokens_consumed_today,
                "tokens_consumed_this_month": balance.tokens_consumed_this_month,
                "total_tokens_consumed": balance.total_tokens_consumed,
                "utilization_percentage": round(utilization, 2),
                "days_until_reset": days_until_reset,
                "last_reset_at": balance.last_reset_at,
                "next_reset_at": balance.next_reset_at,
            }
        except Exception as e:
            logger.error(f"Error getting usage stats for user {user_id}: {e}")
            raise

    async def reset_monthly_quota(self, user_id: str) -> bool:
        """Reset monthly quota for a user"""
        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                logger.warning(f"No balance found for user {user_id}")
                return False

            # Reset tokens and counters
            balance.available_tokens = balance.monthly_quota
            balance.tokens_consumed_this_month = 0
            balance.last_reset_at = datetime.now(UTC)

            # Calculate next reset date
            now = datetime.now(UTC)
            if now.month == 12:
                balance.next_reset_at = datetime(now.year + 1, 1, 1, tzinfo=UTC)
            else:
                balance.next_reset_at = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

            self.session.flush()
            logger.info(
                f"Reset monthly quota for user {user_id}, new balance: {balance.available_tokens}"
            )
            return True

        except Exception as e:
            logger.error(f"Error resetting quota for user {user_id}: {e}")
            raise

    async def reset_daily_consumption(self, user_id: str) -> bool:
        """Reset daily consumption counter"""
        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance:
                logger.warning(f"No balance found for user {user_id}")
                return False

            balance.tokens_consumed_today = 0
            self.session.flush()

            logger.info(f"Reset daily consumption for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error resetting daily consumption for user {user_id}: {e}")
            raise

    async def check_and_auto_reset(self, user_id: str) -> bool:
        """Check if quota should be reset and auto-reset if needed"""
        try:
            balance = (
                self.session.query(UserTokenBalance).filter_by(user_id=user_id).first()
            )

            if not balance or not balance.next_reset_at:
                return False

            now = datetime.now(UTC)

            # Check if it's time to reset
            if now >= balance.next_reset_at:
                await self.reset_monthly_quota(user_id)
                logger.info(f"Auto-reset performed for user {user_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking auto-reset for user {user_id}: {e}")
            raise
