"""
Unit tests for TokenConsumptionService

Tests the application service layer for token consumption including:
- consume_tokens_for_operation (main entry point)
- consume_tokens (lower-level method)
- add_tokens
- get_balance
- get_usage_stats
- update_quota
- reset_monthly_quota
- check_sufficient_balance
"""

from unittest.mock import AsyncMock, Mock

import pytest

from fastmcp.auth.application.services.token_consumption_service import (
    TokenConsumptionService,
)


@pytest.fixture
def mock_repository():
    """Create mock token balance repository"""
    repo = Mock()

    # Configure async methods
    repo.get_balance = AsyncMock()
    repo.create_balance = AsyncMock()
    repo.consume_tokens = AsyncMock()
    repo.add_tokens = AsyncMock()
    repo.update_quota = AsyncMock()
    repo.reset_monthly_quota = AsyncMock()
    repo.get_usage_stats = AsyncMock()

    return repo


@pytest.fixture
def mock_session():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def service(mock_session, mock_repository):
    """Create TokenConsumptionService with mocked repository"""
    return TokenConsumptionService(mock_session, mock_repository)


class TestTokenConsumptionService:
    """Test suite for TokenConsumptionService"""

    # ============================================================================
    # CONSUME TOKENS FOR OPERATION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_success(self, service, mock_repository):
        """Test successful token consumption for MCP operation"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 5000}
        mock_repository.consume_tokens.return_value = True

        # Execute
        result = await service.consume_tokens_for_operation(
            user_id="user123",
            operation="create_project",  # Costs 10 tokens
        )

        # Verify
        assert result.success is True
        assert result.consumed == 10
        assert result.remaining_balance == 5000
        assert result.operation == "create_project"
        assert result.error_message is None

        # Verify repository calls
        mock_repository.consume_tokens.assert_called_once_with("user123", 10)

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_custom_cost(
        self, service, mock_repository
    ):
        """Test token consumption with custom cost override"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 5000}
        mock_repository.consume_tokens.return_value = True

        # Execute with custom cost
        result = await service.consume_tokens_for_operation(
            user_id="user123",
            operation="create_project",
            custom_cost=25,  # Override default 10 tokens
        )

        # Verify
        assert result.success is True
        assert result.consumed == 25
        mock_repository.consume_tokens.assert_called_once_with("user123", 25)

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_free_operation(
        self, service, mock_repository
    ):
        """Test that free operations don't consume tokens"""
        # Execute (login is free - 0 tokens)
        result = await service.consume_tokens_for_operation(
            user_id="user123", operation="login"
        )

        # Verify
        assert result.success is True
        assert result.consumed == 0
        assert "free" in result.error_message.lower()

        # Repository should NOT be called for free operations
        mock_repository.consume_tokens.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_auto_create_balance(
        self, service, mock_repository
    ):
        """Test auto-creation of balance for new users"""
        # Setup - user has no balance
        mock_repository.get_balance.return_value = None
        mock_repository.create_balance.return_value = None
        mock_repository.consume_tokens.return_value = True

        # Execute
        result = await service.consume_tokens_for_operation(
            user_id="new_user", operation="create_task"
        )

        # Verify balance was auto-created
        mock_repository.create_balance.assert_called_once_with("new_user")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_insufficient_tokens(
        self, service, mock_repository
    ):
        """Test error when user has insufficient tokens"""
        # Setup
        mock_repository.get_balance.side_effect = [
            {"available_tokens": 5000},  # First call (before consume)
            {"available_tokens": 3},  # Second call (after failed consume)
        ]
        mock_repository.consume_tokens.return_value = False

        # Execute (call_agent costs 20 tokens)
        result = await service.consume_tokens_for_operation(
            user_id="user123", operation="call_agent"
        )

        # Verify
        assert result.success is False
        assert result.error_code == "INSUFFICIENT_TOKENS"
        assert "Required: 20, Available: 3" in result.error_message

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_unknown_operation(
        self, service, mock_repository
    ):
        """Test token consumption for unknown operation uses default cost"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 5000}
        mock_repository.consume_tokens.return_value = True

        # Execute with unknown operation (should use default cost of 1)
        result = await service.consume_tokens_for_operation(
            user_id="user123", operation="unknown_operation"
        )

        # Verify default cost of 1 token was used
        assert result.success is True
        assert result.consumed == 1
        mock_repository.consume_tokens.assert_called_once_with("user123", 1)

    @pytest.mark.asyncio
    async def test_consume_tokens_for_operation_error_handling(
        self, service, mock_repository
    ):
        """Test error handling when repository raises exception"""
        # Setup
        mock_repository.get_balance.side_effect = Exception("Database connection error")

        # Execute
        result = await service.consume_tokens_for_operation(
            user_id="user123", operation="create_project"
        )

        # Verify
        assert result.success is False
        assert result.error_code == "CONSUMPTION_ERROR"
        assert "Database connection error" in result.error_message

    # ============================================================================
    # CONSUME TOKENS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_consume_tokens_success(self, service, mock_repository):
        """Test lower-level token consumption"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 1000}
        mock_repository.consume_tokens.return_value = True

        # Execute
        result = await service.consume_tokens(
            user_id="user123", amount=150, operation="custom_operation"
        )

        # Verify
        assert result.success is True
        assert result.consumed == 150
        assert result.remaining_balance == 1000

    @pytest.mark.asyncio
    async def test_consume_tokens_zero_amount(self, service, mock_repository):
        """Test that zero amount is rejected"""
        # Execute
        result = await service.consume_tokens(user_id="user123", amount=0)

        # Verify
        assert result.success is False
        assert result.error_code == "INVALID_AMOUNT"
        assert "must be positive" in result.error_message

    @pytest.mark.asyncio
    async def test_consume_tokens_negative_amount(self, service, mock_repository):
        """Test that negative amount is rejected"""
        # Execute
        result = await service.consume_tokens(user_id="user123", amount=-50)

        # Verify
        assert result.success is False
        assert result.error_code == "INVALID_AMOUNT"

    # ============================================================================
    # ADD TOKENS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_add_tokens_success(self, service, mock_repository):
        """Test adding tokens to user balance"""
        # Setup
        mock_repository.get_balance.side_effect = [
            {"available_tokens": 1000},  # Before add
            {"available_tokens": 1500},  # After add
        ]
        mock_repository.add_tokens.return_value = True

        # Execute
        result = await service.add_tokens(
            user_id="user123", amount=500, reason="Token purchase"
        )

        # Verify
        assert result.success is True
        assert result.new_balance == 1500
        assert result.added == 500
        mock_repository.add_tokens.assert_called_once_with("user123", 500)

    @pytest.mark.asyncio
    async def test_add_tokens_negative_amount(self, service, mock_repository):
        """Test that negative amount is rejected"""
        # Execute
        result = await service.add_tokens(user_id="user123", amount=-100)

        # Verify
        assert result.success is False
        assert "must be positive" in result.error_message

    @pytest.mark.asyncio
    async def test_add_tokens_new_user_auto_create(self, service, mock_repository):
        """Test adding tokens auto-creates balance for new users"""
        # Setup - no existing balance
        mock_repository.get_balance.side_effect = [
            None,  # Before create
            {"available_tokens": 1000},  # After create with initial tokens
        ]
        mock_repository.create_balance.return_value = None

        # Execute
        result = await service.add_tokens(
            user_id="new_user", amount=1000, reason="Welcome bonus"
        )

        # Verify balance was created with initial tokens
        assert result.success is True
        assert result.new_balance == 1000
        mock_repository.create_balance.assert_called_once_with(
            "new_user", initial_tokens=1000
        )

    # ============================================================================
    # GET BALANCE TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_get_balance_exists(self, service, mock_repository):
        """Test getting balance for existing user"""
        # Setup
        mock_repository.get_balance.return_value = {
            "available_tokens": 7500,
            "monthly_quota": 10000,
            "user_id": "user123",
        }

        # Execute
        result = await service.get_balance("user123")

        # Verify
        assert result.success is True
        assert result.balance["available_tokens"] == 7500
        assert result.balance["monthly_quota"] == 10000

    @pytest.mark.asyncio
    async def test_get_balance_auto_create(self, service, mock_repository):
        """Test auto-creation of balance when getting balance"""
        # Setup
        mock_repository.get_balance.side_effect = [
            None,  # First call - no balance
            {"available_tokens": 10000, "monthly_quota": 10000},  # After creation
        ]

        # Execute
        result = await service.get_balance("new_user")

        # Verify
        assert result.success is True
        mock_repository.create_balance.assert_called_once_with("new_user")

    # ============================================================================
    # GET USAGE STATS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, service, mock_repository):
        """Test getting detailed usage statistics"""
        # Setup
        mock_repository.get_usage_stats.return_value = {
            "available_tokens": 8500,
            "monthly_quota": 10000,
            "tokens_consumed_today": 100,
            "tokens_consumed_this_month": 1500,
            "total_tokens_consumed": 5000,
            "usage_percentage": 15.0,
        }

        # Execute
        result = await service.get_usage_stats("user123")

        # Verify
        assert result.success is True
        assert result.balance["tokens_consumed_today"] == 100
        assert result.balance["usage_percentage"] == 15.0

    # ============================================================================
    # UPDATE QUOTA TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_update_quota_success(self, service, mock_repository):
        """Test updating monthly quota"""
        # Setup
        mock_repository.update_quota.return_value = True
        mock_repository.get_balance.return_value = {
            "available_tokens": 20000,
            "monthly_quota": 20000,
        }

        # Execute
        result = await service.update_quota(
            user_id="user123", new_quota=20000, reason="Upgraded plan"
        )

        # Verify
        assert result.success is True
        assert result.new_balance == 20000
        mock_repository.update_quota.assert_called_once_with("user123", 20000)

    @pytest.mark.asyncio
    async def test_update_quota_negative_value(self, service, mock_repository):
        """Test that negative quota is rejected"""
        # Execute
        result = await service.update_quota(user_id="user123", new_quota=-1000)

        # Verify
        assert result.success is False
        assert "cannot be negative" in result.error_message

    # ============================================================================
    # RESET MONTHLY QUOTA TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_reset_monthly_quota_success(self, service, mock_repository):
        """Test manually resetting monthly quota"""
        # Setup
        mock_repository.reset_monthly_quota.return_value = True
        mock_repository.get_balance.return_value = {
            "available_tokens": 10000,
            "monthly_quota": 10000,
        }

        # Execute
        result = await service.reset_monthly_quota("user123")

        # Verify
        assert result.success is True
        assert result.balance["available_tokens"] == 10000
        mock_repository.reset_monthly_quota.assert_called_once_with("user123")

    # ============================================================================
    # CHECK SUFFICIENT BALANCE TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_check_sufficient_balance_has_enough(self, service, mock_repository):
        """Test checking balance when user has sufficient tokens"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 1000}

        # Execute (create_project costs 10 tokens)
        has_sufficient, required, available = await service.check_sufficient_balance(
            user_id="user123", operation="create_project"
        )

        # Verify
        assert has_sufficient is True
        assert required == 10
        assert available == 1000

    @pytest.mark.asyncio
    async def test_check_sufficient_balance_insufficient(
        self, service, mock_repository
    ):
        """Test checking balance when user has insufficient tokens"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 5}

        # Execute (call_agent costs 20 tokens)
        has_sufficient, required, available = await service.check_sufficient_balance(
            user_id="user123", operation="call_agent"
        )

        # Verify
        assert has_sufficient is False
        assert required == 20
        assert available == 5

    @pytest.mark.asyncio
    async def test_check_sufficient_balance_custom_cost(self, service, mock_repository):
        """Test balance check with custom cost override"""
        # Setup
        mock_repository.get_balance.return_value = {"available_tokens": 100}

        # Execute with custom cost
        has_sufficient, required, available = await service.check_sufficient_balance(
            user_id="user123", operation="create_project", custom_cost=150
        )

        # Verify
        assert has_sufficient is False
        assert required == 150
        assert available == 100

    @pytest.mark.asyncio
    async def test_check_sufficient_balance_no_balance(self, service, mock_repository):
        """Test balance check when user has no balance record"""
        # Setup
        mock_repository.get_balance.return_value = None

        # Execute
        has_sufficient, required, available = await service.check_sufficient_balance(
            user_id="user123", operation="create_task"
        )

        # Verify
        assert has_sufficient is False
        assert required == 5  # create_task costs 5
        assert available == 0
