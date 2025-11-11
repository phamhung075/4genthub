"""
Unit tests for TokenConsumptionHelper

Tests the MCP controller integration helper including:
- Token consumption with auto-authentication
- Token info generation for responses
- Consume and add info convenience method
- Error handling and response formatting
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from fastmcp.auth.application.services.token_consumption_service import (
    TokenBalanceResult,
    TokenConsumptionResult,
)
from fastmcp.task_management.interface.mcp_controllers.token_consumption_helper import (
    TokenConsumptionHelper,
    consume_tokens_for_operation,
)


@pytest.fixture
def mock_session():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def mock_token_service():
    """Create mock TokenConsumptionService"""
    service = Mock()
    service.consume_tokens_for_operation = AsyncMock()
    service.get_balance = AsyncMock()
    return service


@pytest.fixture
def helper(mock_session):
    """Create TokenConsumptionHelper instance"""
    return TokenConsumptionHelper(mock_session)


class TestTokenConsumptionHelper:
    """Test suite for TokenConsumptionHelper"""

    # ============================================================================
    # CONSUME TOKENS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_tokens_success(self, mock_auth, helper, mock_token_service):
        """Test successful token consumption with authentication"""
        # Setup
        mock_auth.return_value = "auth-user-123"
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=True,
                remaining_balance=9990,
                consumed=10,
                operation="create_project",
            )
        )

        # Execute
        success, error_response = await helper.consume_tokens(
            operation="create_project",
            user_id=None,  # Should auto-extract from auth
        )

        # Verify
        assert success is True
        assert error_response is None

        # Verify auth extraction was called
        mock_auth.assert_called_once_with(
            provided_user_id=None, operation_name="create_project"
        )

        # Verify service was called with authenticated user
        mock_token_service.consume_tokens_for_operation.assert_called_once_with(
            user_id="auth-user-123", operation="create_project", custom_cost=None
        )

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_tokens_with_provided_user_id(
        self, mock_auth, helper, mock_token_service
    ):
        """Test token consumption with explicitly provided user_id"""
        # Setup
        mock_auth.return_value = "provided-user-456"
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=True,
                remaining_balance=9995,
                consumed=5,
                operation="create_branch",
            )
        )

        # Execute with explicit user_id
        success, error_response = await helper.consume_tokens(
            operation="create_branch", user_id="provided-user-456"
        )

        # Verify
        assert success is True
        mock_auth.assert_called_once_with(
            provided_user_id="provided-user-456", operation_name="create_branch"
        )

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_tokens_insufficient_tokens(
        self, mock_auth, helper, mock_token_service
    ):
        """Test error response when user has insufficient tokens"""
        # Setup
        mock_auth.return_value = "user-123"
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=False,
                error_message="Insufficient tokens. Required: 20, Available: 5",
                error_code="INSUFFICIENT_TOKENS",
                operation="call_agent",
            )
        )

        # Execute
        success, error_response = await helper.consume_tokens(operation="call_agent")

        # Verify
        assert success is False
        assert error_response is not None
        assert error_response["success"] is False
        assert (
            error_response["error"] == "Insufficient tokens. Required: 20, Available: 5"
        )
        assert error_response["error_code"] == "INSUFFICIENT_TOKENS"
        assert error_response["status_code"] == 402  # Payment Required
        assert error_response["operation"] == "call_agent"

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_tokens_system_error(
        self, mock_auth, helper, mock_token_service
    ):
        """Test error response for generic system errors"""
        # Setup
        mock_auth.return_value = "user-123"
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=False,
                error_message="Database connection error",
                error_code="CONSUMPTION_ERROR",
                operation="create_task",
            )
        )

        # Execute
        success, error_response = await helper.consume_tokens(operation="create_task")

        # Verify
        assert success is False
        assert error_response["error_code"] == "CONSUMPTION_ERROR"
        assert "status_code" not in error_response  # Only INSUFFICIENT_TOKENS gets 402

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_tokens_custom_cost(
        self, mock_auth, helper, mock_token_service
    ):
        """Test token consumption with custom cost override"""
        # Setup
        mock_auth.return_value = "user-123"
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=True,
                remaining_balance=9950,
                consumed=50,
                operation="special_operation",
            )
        )

        # Execute with custom cost
        success, error_response = await helper.consume_tokens(
            operation="special_operation", custom_cost=50
        )

        # Verify
        assert success is True
        mock_token_service.consume_tokens_for_operation.assert_called_once_with(
            user_id="user-123", operation="special_operation", custom_cost=50
        )

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_tokens_exception_handling(
        self, mock_auth, helper, mock_token_service
    ):
        """Test exception handling in consume_tokens"""
        # Setup
        mock_auth.side_effect = Exception("Authentication failed")
        helper._token_service = mock_token_service

        # Execute
        success, error_response = await helper.consume_tokens(
            operation="create_project"
        )

        # Verify
        assert success is False
        assert error_response["error_code"] == "TOKEN_SYSTEM_ERROR"
        assert "Authentication failed" in error_response["error"]

    # ============================================================================
    # GET TOKEN INFO TESTS
    # ============================================================================

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_operation_cost"
    )
    async def test_get_token_info_success(
        self, mock_get_cost, mock_auth, helper, mock_token_service
    ):
        """Test getting token info for successful operations"""
        # Setup
        mock_auth.return_value = "user-123"
        mock_get_cost.return_value = 10  # create_project cost
        helper._token_service = mock_token_service

        mock_token_service.get_balance.return_value = TokenBalanceResult(
            success=True, balance={"available_tokens": 9990}
        )

        # Execute
        token_info = await helper.get_token_info(operation="create_project")

        # Verify
        assert token_info["consumed"] == 10
        assert token_info["remaining_balance"] == 9990
        assert token_info["operation"] == "create_project"
        assert "error" not in token_info

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_operation_cost"
    )
    async def test_get_token_info_balance_error(
        self, mock_get_cost, mock_auth, helper, mock_token_service
    ):
        """Test get_token_info when balance retrieval fails"""
        # Setup
        mock_auth.return_value = "user-123"
        mock_get_cost.return_value = 5
        helper._token_service = mock_token_service

        mock_token_service.get_balance.return_value = TokenBalanceResult(
            success=False, error_message="User not found"
        )

        # Execute
        token_info = await helper.get_token_info(operation="create_task")

        # Verify
        assert token_info["operation"] == "create_task"
        assert token_info["error"] == "Could not retrieve balance info"

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_operation_cost"
    )
    async def test_get_token_info_custom_cost(
        self, mock_get_cost, mock_auth, helper, mock_token_service
    ):
        """Test get_token_info with custom cost"""
        # Setup
        mock_auth.return_value = "user-123"
        helper._token_service = mock_token_service

        mock_token_service.get_balance.return_value = TokenBalanceResult(
            success=True, balance={"available_tokens": 9900}
        )

        # Execute with custom cost (should override get_operation_cost)
        token_info = await helper.get_token_info(
            operation="custom_operation", custom_cost=100
        )

        # Verify custom cost was used
        assert token_info["consumed"] == 100
        assert (
            mock_get_cost.call_count == 0
        )  # Should not be called when custom_cost provided

    # ============================================================================
    # CONSUME AND ADD INFO TESTS
    # ============================================================================

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_operation_cost"
    )
    async def test_consume_and_add_info_success(
        self, mock_get_cost, mock_auth, helper, mock_token_service
    ):
        """Test one-step consume and add info method"""
        # Setup
        mock_auth.return_value = "user-123"
        mock_get_cost.return_value = 5
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=True,
                remaining_balance=9995,
                consumed=5,
                operation="create_branch",
            )
        )

        mock_token_service.get_balance.return_value = TokenBalanceResult(
            success=True, balance={"available_tokens": 9995}
        )

        # Execute
        response = {"success": True, "branch": {"id": "branch-123"}}
        success, final_response = await helper.consume_and_add_info(
            operation="create_branch", response=response
        )

        # Verify
        assert success is True
        assert final_response["success"] is True
        assert final_response["branch"]["id"] == "branch-123"
        assert "token_info" in final_response
        assert final_response["token_info"]["consumed"] == 5
        assert final_response["token_info"]["remaining_balance"] == 9995

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    async def test_consume_and_add_info_insufficient_tokens(
        self, mock_auth, helper, mock_token_service
    ):
        """Test consume_and_add_info when tokens are insufficient"""
        # Setup
        mock_auth.return_value = "user-123"
        helper._token_service = mock_token_service

        mock_token_service.consume_tokens_for_operation.return_value = (
            TokenConsumptionResult(
                success=False,
                error_message="Insufficient tokens. Required: 20, Available: 10",
                error_code="INSUFFICIENT_TOKENS",
                operation="call_agent",
            )
        )

        # Execute
        response = {"success": True, "agent_response": "..."}
        success, final_response = await helper.consume_and_add_info(
            operation="call_agent", response=response
        )

        # Verify
        assert success is False
        assert final_response["success"] is False
        assert final_response["error_code"] == "INSUFFICIENT_TOKENS"
        assert (
            "token_info" not in final_response
        )  # Should not add token_info on failure

    # ============================================================================
    # STANDALONE FUNCTION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.get_authenticated_user_id"
    )
    @patch(
        "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.TokenConsumptionHelper"
    )
    async def test_standalone_consume_tokens_for_operation(
        self, mock_helper_class, mock_auth
    ):
        """Test standalone convenience function"""
        # Setup
        mock_auth.return_value = "user-123"
        mock_helper_instance = Mock()
        mock_helper_instance.consume_tokens = AsyncMock(return_value=(True, None))
        mock_helper_class.return_value = mock_helper_instance

        mock_session = Mock()

        # Execute
        success, error_response = await consume_tokens_for_operation(
            session=mock_session, operation="create_task", user_id="user-123"
        )

        # Verify
        assert success is True
        assert error_response is None
        mock_helper_class.assert_called_once_with(mock_session)
        mock_helper_instance.consume_tokens.assert_called_once_with(
            "create_task", "user-123", None
        )

    # ============================================================================
    # LAZY LOADING TESTS
    # ============================================================================

    def test_token_service_lazy_loading(self, helper):
        """Test that token service is lazy-loaded"""
        # Initially, service should be None
        assert helper._token_service is None

        # Access property should trigger lazy load
        with patch(
            "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.TokenConsumptionService"
        ) as mock_service_class:
            with patch(
                "fastmcp.task_management.interface.mcp_controllers.token_consumption_helper.TokenBalanceRepository"
            ) as mock_repo_class:
                service = helper.token_service

                # Verify repository and service were created
                mock_repo_class.assert_called_once()
                mock_service_class.assert_called_once()

                # Second access should return same instance (not create new one)
                service2 = helper.token_service
                assert service is service2
                assert mock_service_class.call_count == 1  # Still only called once
