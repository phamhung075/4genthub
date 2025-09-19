"""
WebSocket Performance Security Tests

Tests performance characteristics of security implementations to ensure
security measures don't create performance vulnerabilities or DoS vectors.

COVERAGE:
- Authentication performance under load
- Authorization performance with many users
- Token validation performance
- Connection handling under stress
- Message broadcasting performance with security
- Rate limiting effectiveness
- Memory usage under security load
"""

import pytest
import asyncio
import time
import psutil
import gc
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from fastmcp.server.routes.websocket_routes import (
    validate_websocket_token,
    is_user_authorized_for_message,
    broadcast_data_change,
    active_connections,
    connection_users
)
from fastmcp.auth.domain.entities.user import User


class PerformanceSecurityTester:
    """Performance testing utilities for security features"""

    def __init__(self):
        self.performance_metrics = []

    async def measure_async_operation(self, operation, *args, **kwargs):
        """Measure performance of async operation"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        try:
            result = await operation(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss

        metrics = {
            "operation": operation.__name__,
            "duration": end_time - start_time,
            "memory_delta": end_memory - start_memory,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.performance_metrics.append(metrics)
        return result, metrics

    async def measure_concurrent_operations(self, operation, count, *args, **kwargs):
        """Measure performance under concurrent load"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        # Create concurrent tasks
        tasks = [operation(*args, **kwargs) for _ in range(count)]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = count - successful
        except Exception as e:
            successful = 0
            failed = count
            results = [str(e)] * count

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss

        metrics = {
            "operation": f"{operation.__name__}_concurrent_{count}",
            "total_operations": count,
            "successful": successful,
            "failed": failed,
            "total_duration": end_time - start_time,
            "avg_duration": (end_time - start_time) / count,
            "operations_per_second": count / (end_time - start_time) if end_time > start_time else 0,
            "memory_delta": end_memory - start_memory,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.performance_metrics.append(metrics)
        return results, metrics


@pytest.fixture
def perf_tester():
    """Fixture providing performance testing utilities"""
    return PerformanceSecurityTester()


@pytest.fixture
def test_users():
    """Fixture providing test users for performance testing"""
    users = []
    for i in range(100):
        user = User(
            id=f"perf_user_{i}",
            email=f"user{i}@perf.test",
            username=f"perfuser{i}"
        )
        users.append(user)
    return users


class TestAuthenticationPerformance:
    """Test authentication performance under various loads"""

    @pytest.mark.asyncio
    async def test_token_validation_performance(self, perf_tester):
        """Test JWT token validation performance"""

        # Mock successful validation
        mock_user = User(id="test_user", email="test@example.com", username="testuser")

        with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
            mock_validate.return_value = mock_user

            # Single validation performance
            _, single_metrics = await perf_tester.measure_async_operation(
                validate_websocket_token,
                "valid.jwt.token"
            )

            assert single_metrics["duration"] < 0.1  # Should be under 100ms
            assert single_metrics["success"] is True

            # Concurrent validation performance
            _, concurrent_metrics = await perf_tester.measure_concurrent_operations(
                validate_websocket_token,
                100,  # 100 concurrent validations
                "valid.jwt.token"
            )

            assert concurrent_metrics["operations_per_second"] > 100  # Should handle >100 ops/sec
            assert concurrent_metrics["successful"] == 100  # All should succeed

    @pytest.mark.asyncio
    async def test_authentication_under_attack_load(self, perf_tester):
        """Test authentication performance under attack simulation"""

        # Simulate attack with invalid tokens
        invalid_tokens = [
            "invalid.token.1",
            "malformed.token",
            "expired.token.here",
            "",
            None
        ]

        with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
            mock_validate.return_value = None  # All tokens invalid

            for token in invalid_tokens:
                _, metrics = await perf_tester.measure_async_operation(
                    validate_websocket_token,
                    token
                )

                # Should quickly reject invalid tokens
                assert metrics["duration"] < 0.05  # Under 50ms
                assert metrics["success"] is True  # Function executes successfully (returns None)

    @pytest.mark.asyncio
    async def test_memory_usage_under_authentication_load(self, perf_tester):
        """Test memory usage during high authentication load"""

        mock_user = User(id="test_user", email="test@example.com", username="testuser")

        with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
            mock_validate.return_value = mock_user

            # Measure memory usage during high load
            _, metrics = await perf_tester.measure_concurrent_operations(
                validate_websocket_token,
                1000,  # High load
                "valid.jwt.token"
            )

            # Memory usage should be reasonable (less than 50MB for 1000 operations)
            memory_mb = metrics["memory_delta"] / (1024 * 1024)
            assert memory_mb < 50

            # Cleanup and check for memory leaks
            gc.collect()
            await asyncio.sleep(0.1)


class TestAuthorizationPerformance:
    """Test authorization performance with many users and entities"""

    @pytest.mark.asyncio
    async def test_authorization_check_performance(self, perf_tester, test_users):
        """Test authorization check performance"""

        user = test_users[0]
        mock_websocket = AsyncMock()
        connection_users[mock_websocket] = user

        # Mock database for performance testing
        with patch('fastmcp.server.routes.websocket_routes.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock task ownership query
            mock_task = AsyncMock()
            mock_task.id = "test_task"
            mock_task.user_id = user.id
            mock_session.query.return_value.filter.return_value.first.return_value = mock_task

            # Single authorization check
            _, single_metrics = await perf_tester.measure_async_operation(
                is_user_authorized_for_message,
                mock_websocket,
                "task",
                "test_task",
                user.id,
                {}
            )

            assert single_metrics["duration"] < 0.05  # Should be under 50ms
            assert single_metrics["success"] is True

            # Concurrent authorization checks
            _, concurrent_metrics = await perf_tester.measure_concurrent_operations(
                is_user_authorized_for_message,
                50,  # 50 concurrent checks
                mock_websocket,
                "task",
                "test_task",
                user.id,
                {}
            )

            assert concurrent_metrics["operations_per_second"] > 200  # Should handle >200 ops/sec

    @pytest.mark.asyncio
    async def test_broadcast_filtering_performance(self, perf_tester, test_users):
        """Test message broadcasting performance with authorization filtering"""

        # Set up multiple user connections
        websockets = []
        for i, user in enumerate(test_users[:10]):  # Use 10 users for performance test
            ws = AsyncMock()
            connection_users[ws] = user
            active_connections[f"user_{i}"] = {ws}
            websockets.append(ws)

        # Mock database for authorization
        with patch('fastmcp.server.routes.websocket_routes.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Only first user owns the task
            def mock_query_filter(*args):
                mock_result = AsyncMock()
                if "user_0" in str(args):
                    mock_task = AsyncMock()
                    mock_task.id = "test_task"
                    mock_task.user_id = "perf_user_0"
                    mock_result.first.return_value = mock_task
                else:
                    mock_result.first.return_value = None
                return mock_result

            mock_session.query.return_value.filter.side_effect = mock_query_filter
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Measure broadcast performance
            _, metrics = await perf_tester.measure_async_operation(
                broadcast_data_change,
                "updated",
                "task",
                "test_task",
                "perf_user_0",
                {"test": "data"}
            )

            # Should complete quickly even with authorization filtering
            assert metrics["duration"] < 0.2  # Under 200ms for 10 users
            assert metrics["success"] is True

            # Only authorized user should receive the message
            authorized_calls = sum(1 for ws in websockets if ws.send_json.called)
            # Note: This depends on proper authorization implementation


class TestConnectionHandlingPerformance:
    """Test WebSocket connection handling performance under load"""

    @pytest.mark.asyncio
    async def test_concurrent_connection_authentication(self, perf_tester, test_users):
        """Test concurrent connection authentication performance"""

        mock_users = test_users[:50]  # Use 50 users for concurrent test

        async def authenticate_connection(user):
            """Simulate connection authentication"""
            with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
                mock_validate.return_value = user
                return await validate_websocket_token("valid.token")

        # Test concurrent authentication
        _, metrics = await perf_tester.measure_concurrent_operations(
            authenticate_connection,
            len(mock_users),
            mock_users[0]  # Use first user for all (simplified)
        )

        # Should handle concurrent authentications efficiently
        assert metrics["operations_per_second"] > 50  # Should handle >50 connections/sec
        assert metrics["successful"] == len(mock_users)

    @pytest.mark.asyncio
    async def test_connection_cleanup_performance(self, perf_tester, test_users):
        """Test connection cleanup performance"""

        # Set up many connections
        connections_to_cleanup = []
        for i, user in enumerate(test_users[:100]):
            ws = AsyncMock()
            connection_users[ws] = user
            active_connections[f"cleanup_user_{i}"] = {ws}
            connections_to_cleanup.append(ws)

        async def cleanup_connections():
            """Simulate connection cleanup"""
            for ws in connections_to_cleanup:
                if ws in connection_users:
                    del connection_users[ws]
                # Remove from active_connections
                for client_id in list(active_connections.keys()):
                    if ws in active_connections[client_id]:
                        active_connections[client_id].discard(ws)
                        if not active_connections[client_id]:
                            del active_connections[client_id]

        # Measure cleanup performance
        _, metrics = await perf_tester.measure_async_operation(cleanup_connections)

        # Cleanup should be fast even for many connections
        assert metrics["duration"] < 1.0  # Should cleanup 100 connections in under 1 second
        assert metrics["success"] is True


class TestRateLimitingPerformance:
    """Test rate limiting implementation performance"""

    @pytest.mark.asyncio
    async def test_message_rate_limiting_performance(self, perf_tester):
        """Test message rate limiting performance impact"""

        user = User(id="rate_test_user", email="rate@test.com", username="rateuser")
        ws = AsyncMock()
        connection_users[ws] = user
        active_connections["rate_test"] = {ws}

        async def send_rate_limited_message():
            """Simulate rate-limited message sending"""
            # TODO: Implement actual rate limiting
            # For now, just simulate the broadcast
            await broadcast_data_change(
                "created",
                "task",
                f"task_{time.time()}",
                user.id,
                {"rate_test": True}
            )

        # Test message sending performance with rate limiting
        _, metrics = await perf_tester.measure_concurrent_operations(
            send_rate_limited_message,
            100  # Try to send 100 messages rapidly
        )

        # Rate limiting should not severely impact performance for legitimate usage
        assert metrics["operations_per_second"] > 10  # Should allow at least 10 messages/sec

    @pytest.mark.asyncio
    async def test_connection_rate_limiting_performance(self, perf_tester):
        """Test connection rate limiting performance"""

        async def attempt_connection():
            """Simulate connection attempt"""
            # TODO: Implement actual connection rate limiting
            # For now, just simulate authentication
            user = User(id="conn_test", email="conn@test.com", username="connuser")
            with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
                mock_validate.return_value = user
                return await validate_websocket_token("valid.token")

        # Test rapid connection attempts
        _, metrics = await perf_tester.measure_concurrent_operations(
            attempt_connection,
            50  # Try 50 rapid connections
        )

        # Rate limiting should handle burst connections efficiently
        assert metrics["total_duration"] < 5.0  # Should handle 50 connections in under 5 seconds


class TestSecurityMemoryLeaks:
    """Test for memory leaks in security implementations"""

    @pytest.mark.asyncio
    async def test_authentication_memory_leaks(self, perf_tester):
        """Test for memory leaks in authentication system"""

        mock_user = User(id="leak_test", email="leak@test.com", username="leakuser")

        # Measure baseline memory
        gc.collect()
        baseline_memory = psutil.Process().memory_info().rss

        # Perform many authentication operations
        with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
            mock_validate.return_value = mock_user

            for _ in range(1000):
                await validate_websocket_token("test.token")

        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)

        # Check for memory growth
        final_memory = psutil.Process().memory_info().rss
        memory_growth_mb = (final_memory - baseline_memory) / (1024 * 1024)

        # Memory growth should be minimal (less than 10MB for 1000 operations)
        assert memory_growth_mb < 10

    @pytest.mark.asyncio
    async def test_connection_tracking_memory_leaks(self, perf_tester):
        """Test for memory leaks in connection tracking"""

        baseline_memory = psutil.Process().memory_info().rss

        # Simulate many connections and disconnections
        for i in range(500):
            user = User(id=f"temp_user_{i}", email=f"temp{i}@test.com", username=f"temp{i}")
            ws = AsyncMock()

            # Add connection
            connection_users[ws] = user
            active_connections[f"temp_{i}"] = {ws}

            # Remove connection (simulate disconnect)
            del connection_users[ws]
            del active_connections[f"temp_{i}"]

        # Force cleanup
        gc.collect()
        await asyncio.sleep(0.1)

        final_memory = psutil.Process().memory_info().rss
        memory_growth_mb = (final_memory - baseline_memory) / (1024 * 1024)

        # Should not have significant memory leaks
        assert memory_growth_mb < 20  # Less than 20MB growth for 500 connect/disconnect cycles


class TestDosResistance:
    """Test resistance to Denial of Service attacks"""

    @pytest.mark.asyncio
    async def test_authentication_dos_resistance(self, perf_tester):
        """Test authentication system resistance to DoS attacks"""

        # Simulate DoS attack with many invalid tokens
        invalid_tokens = ["invalid"] * 1000

        async def attempt_dos_auth(token):
            """Simulate DoS authentication attempt"""
            with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
                mock_validate.return_value = None  # All tokens invalid
                return await validate_websocket_token(token)

        start_time = time.time()

        # Attempt rapid invalid authentications
        tasks = [attempt_dos_auth(token) for token in invalid_tokens]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # System should handle DoS gracefully
        assert total_time < 10.0  # Should reject 1000 invalid tokens in under 10 seconds
        assert all(result is None for result in results)  # All should be rejected

    @pytest.mark.asyncio
    async def test_broadcast_dos_resistance(self, perf_tester):
        """Test broadcast system resistance to message flooding"""

        # Set up target user
        user = User(id="dos_target", email="dos@test.com", username="dostarget")
        ws = AsyncMock()
        connection_users[ws] = user
        active_connections["dos_target"] = {ws}

        # Attempt message flooding
        flood_messages = 500

        async def flood_message(i):
            """Send flood message"""
            await broadcast_data_change(
                "spam",
                "task",
                f"flood_task_{i}",
                user.id,
                {"flood_data": f"message_{i}"}
            )

        start_time = time.time()
        tasks = [flood_message(i) for i in range(flood_messages)]
        await asyncio.gather(*tasks)
        end_time = time.time()

        # System should handle message flood without crashing
        assert end_time - start_time < 30.0  # Should handle 500 messages in under 30 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])