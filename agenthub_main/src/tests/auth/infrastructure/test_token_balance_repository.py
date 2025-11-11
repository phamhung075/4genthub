"""
Unit tests for TokenBalanceRepository

Tests the repository layer for token balance operations including:
- Token consumption (atomic operations)
- Balance queries
- Token additions
- Auto-reset functionality
- Usage statistics
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastmcp.auth.infrastructure.database.models import Base, User, UserTokenBalance
from fastmcp.auth.infrastructure.repositories.token_balance_repository import (
    TokenBalanceRepository,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing"""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(session):
    """Create a test user"""
    user = User(
        id="test-user-123",
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        status="active",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def repository(session):
    """Create TokenBalanceRepository instance"""
    return TokenBalanceRepository(session)


class TestTokenBalanceRepository:
    """Test suite for TokenBalanceRepository"""

    # ============================================================================
    # CREATE BALANCE TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_create_balance_default_values(self, repository, test_user, session):
        """Test creating balance with default 10,000 tokens"""
        result = await repository.create_balance(test_user.id)

        assert result is True

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance is not None
        assert balance.available_tokens == 10000
        assert balance.monthly_quota == 10000
        assert balance.tokens_consumed_today == 0
        assert balance.tokens_consumed_this_month == 0
        assert balance.total_tokens_consumed == 0

    def test_create_balance_custom_initial_tokens(self, repository, test_user, session):
        """Test creating balance with custom initial tokens"""
        result = repository.create_balance(test_user.id, initial_tokens=5000)

        assert result is True

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.available_tokens == 5000
        assert balance.monthly_quota == 10000  # Default quota

    def test_create_balance_duplicate_user(self, repository, test_user):
        """Test creating balance for user that already has one"""
        # Create first balance
        repository.create_balance(test_user.id)

        # Attempt to create duplicate should fail (unique constraint)
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            repository.create_balance(test_user.id)

    # ============================================================================
    # GET BALANCE TESTS
    # ============================================================================

    def test_get_balance_exists(self, repository, test_user):
        """Test getting balance for existing user"""
        repository.create_balance(test_user.id, initial_tokens=7500)

        balance = repository.get_balance(test_user.id)

        assert balance is not None
        assert balance["available_tokens"] == 7500
        assert balance["monthly_quota"] == 10000
        assert "user_id" in balance
        assert "created_at" in balance

    def test_get_balance_not_exists(self, repository):
        """Test getting balance for non-existent user"""
        balance = repository.get_balance("non-existent-user")

        assert balance is None

    # ============================================================================
    # CONSUME TOKENS TESTS
    # ============================================================================

    def test_consume_tokens_success(self, repository, test_user, session):
        """Test successful token consumption"""
        repository.create_balance(test_user.id, initial_tokens=1000)

        result = repository.consume_tokens(test_user.id, 100)

        assert result is True

        # Verify balance updated
        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.available_tokens == 900
        assert balance.tokens_consumed_today == 100
        assert balance.tokens_consumed_this_month == 100
        assert balance.total_tokens_consumed == 100

    def test_consume_tokens_insufficient_balance(self, repository, test_user):
        """Test consuming more tokens than available"""
        repository.create_balance(test_user.id, initial_tokens=50)

        result = repository.consume_tokens(test_user.id, 100)

        assert result is False

    def test_consume_tokens_exact_balance(self, repository, test_user, session):
        """Test consuming exact available balance"""
        repository.create_balance(test_user.id, initial_tokens=100)

        result = repository.consume_tokens(test_user.id, 100)

        assert result is True

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.available_tokens == 0

    def test_consume_tokens_negative_amount(self, repository, test_user):
        """Test consuming negative amount raises error"""
        repository.create_balance(test_user.id)

        with pytest.raises(ValueError, match="Amount must be positive"):
            repository.consume_tokens(test_user.id, -10)

    def test_consume_tokens_zero_amount(self, repository, test_user):
        """Test consuming zero amount raises error"""
        repository.create_balance(test_user.id)

        with pytest.raises(ValueError, match="Amount must be positive"):
            repository.consume_tokens(test_user.id, 0)

    def test_consume_tokens_multiple_operations(self, repository, test_user, session):
        """Test multiple token consumption operations"""
        repository.create_balance(test_user.id, initial_tokens=1000)

        # Consume 100 tokens
        repository.consume_tokens(test_user.id, 100)
        # Consume 200 more tokens
        repository.consume_tokens(test_user.id, 200)
        # Consume 50 more tokens
        repository.consume_tokens(test_user.id, 50)

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.available_tokens == 650
        assert balance.total_tokens_consumed == 350

    # ============================================================================
    # ADD TOKENS TESTS
    # ============================================================================

    def test_add_tokens_success(self, repository, test_user, session):
        """Test adding tokens to balance"""
        repository.create_balance(test_user.id, initial_tokens=500)

        result = repository.add_tokens(test_user.id, 250)

        assert result is True

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.available_tokens == 750

    def test_add_tokens_negative_amount(self, repository, test_user):
        """Test adding negative amount raises error"""
        repository.create_balance(test_user.id)

        with pytest.raises(ValueError, match="Amount must be positive"):
            repository.add_tokens(test_user.id, -100)

    def test_add_tokens_user_not_found(self, repository):
        """Test adding tokens for non-existent user"""
        result = repository.add_tokens("non-existent-user", 100)

        assert result is False

    # ============================================================================
    # AUTO-RESET TESTS
    # ============================================================================

    def test_check_and_auto_reset_not_needed(self, repository, test_user, session):
        """Test auto-reset when not needed (future reset date)"""
        repository.create_balance(test_user.id, initial_tokens=500)

        # Set next_reset_at to future date
        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        balance.next_reset_at = datetime.now(UTC) + timedelta(days=10)
        balance.tokens_consumed_this_month = 300
        session.commit()

        result = repository.check_and_auto_reset(test_user.id)

        assert result is False

        # Balance should not change
        balance_after = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance_after.available_tokens == 500
        assert balance_after.tokens_consumed_this_month == 300

    def test_check_and_auto_reset_needed(self, repository, test_user, session):
        """Test auto-reset when reset date has passed"""
        repository.create_balance(test_user.id, initial_tokens=500)

        # Set next_reset_at to past date
        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        balance.next_reset_at = datetime.now(UTC) - timedelta(days=1)
        balance.tokens_consumed_this_month = 300
        balance.monthly_quota = 10000
        session.commit()

        result = repository.check_and_auto_reset(test_user.id)

        assert result is True

        # Balance should reset to quota
        balance_after = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance_after.available_tokens == 10000
        assert balance_after.tokens_consumed_this_month == 0
        assert balance_after.last_reset_at is not None
        assert balance_after.next_reset_at > datetime.now(UTC)

    # ============================================================================
    # UPDATE QUOTA TESTS
    # ============================================================================

    def test_update_quota_success(self, repository, test_user, session):
        """Test updating monthly quota"""
        repository.create_balance(test_user.id)

        result = repository.update_quota(test_user.id, 20000)

        assert result is True

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.monthly_quota == 20000

    def test_update_quota_user_not_found(self, repository):
        """Test updating quota for non-existent user"""
        result = repository.update_quota("non-existent-user", 20000)

        assert result is False

    # ============================================================================
    # GET USAGE STATS TESTS
    # ============================================================================

    def test_get_usage_stats(self, repository, test_user, session):
        """Test getting usage statistics"""
        repository.create_balance(test_user.id, initial_tokens=8000)

        # Simulate some consumption
        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        balance.tokens_consumed_today = 150
        balance.tokens_consumed_this_month = 450
        balance.total_tokens_consumed = 2000
        session.commit()

        stats = repository.get_usage_stats(test_user.id)

        assert stats is not None
        assert stats["available_tokens"] == 8000
        assert stats["monthly_quota"] == 10000
        assert stats["tokens_consumed_today"] == 150
        assert stats["tokens_consumed_this_month"] == 450
        assert stats["total_tokens_consumed"] == 2000
        assert stats["usage_percentage"] == 45.0  # 450/10000 * 100

    def test_get_usage_stats_user_not_found(self, repository):
        """Test getting stats for non-existent user"""
        stats = repository.get_usage_stats("non-existent-user")

        assert stats is None

    # ============================================================================
    # RESET MONTHLY QUOTA TESTS
    # ============================================================================

    def test_reset_monthly_quota(self, repository, test_user, session):
        """Test manually resetting monthly quota"""
        repository.create_balance(test_user.id, initial_tokens=500)

        # Consume some tokens
        repository.consume_tokens(test_user.id, 300)

        result = repository.reset_monthly_quota(test_user.id)

        assert result is True

        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance.available_tokens == 10000  # Reset to quota
        assert balance.tokens_consumed_this_month == 0
        assert balance.last_reset_at is not None

    # ============================================================================
    # RESET DAILY CONSUMPTION TESTS
    # ============================================================================

    def test_reset_daily_consumption(self, repository, test_user, session):
        """Test resetting daily consumption counter"""
        repository.create_balance(test_user.id)

        # Simulate daily consumption
        balance = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        balance.tokens_consumed_today = 500
        session.commit()

        result = repository.reset_daily_consumption(test_user.id)

        assert result is True

        balance_after = (
            session.query(UserTokenBalance).filter_by(user_id=test_user.id).first()
        )
        assert balance_after.tokens_consumed_today == 0
