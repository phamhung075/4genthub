"""
Unit tests for Rule Management Domain Value Objects
Testing value object immutability, validation, and business logic
Following DDD patterns and principles
"""

import pytest
from dataclasses import FrozenInstanceError
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch
import time

from fastmcp.task_management.domain.value_objects.rule_value_objects import (
    ClientConfig,
    SyncRequest,
    SyncResult,
    RuleConflict,
    CompositionResult,
    CacheEntry,
    RuleHierarchyInfo
)
from fastmcp.task_management.domain.enums.rule_enums import (
    ClientAuthMethod,
    SyncOperation,
    SyncStatus,
    ConflictResolution,
    RuleType,
    RuleFormat
)
from fastmcp.task_management.domain.entities.rule_entity import RuleContent, RuleInheritance


class TestClientConfig:
    """Test suite for ClientConfig value object"""
    
    def test_create_valid_client_config(self):
        """Test creating a valid client configuration"""
        config = ClientConfig(
            client_id="client_123",
            client_name="Test Client",
            auth_method=ClientAuthMethod.TOKEN,
            auth_credentials={"token": "secret_token"},
            sync_permissions=["read", "write"],
            rate_limit=100,
            sync_frequency=300
        )
        
        assert config.client_id == "client_123"
        assert config.client_name == "Test Client"
        assert config.auth_method == ClientAuthMethod.TOKEN
        assert config.rate_limit == 100
        assert config.sync_frequency == 300
        assert config.auto_sync is True
        assert config.conflict_resolution == ConflictResolution.MERGE
    
    def test_client_config_validation_empty_id(self):
        """Test validation rejects empty client ID"""
        with pytest.raises(ValueError, match="Client ID cannot be empty"):
            ClientConfig(
                client_id="",
                client_name="Test Client",
                auth_method=ClientAuthMethod.TOKEN,
                auth_credentials={},
                sync_permissions=[]
            )
    
    def test_client_config_validation_empty_name(self):
        """Test validation rejects empty client name"""
        with pytest.raises(ValueError, match="Client name cannot be empty"):
            ClientConfig(
                client_id="client_123",
                client_name="",
                auth_method=ClientAuthMethod.TOKEN,
                auth_credentials={},
                sync_permissions=[]
            )
    
    def test_client_config_validation_invalid_rate_limit(self):
        """Test validation rejects non-positive rate limit"""
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            ClientConfig(
                client_id="client_123",
                client_name="Test Client",
                auth_method=ClientAuthMethod.TOKEN,
                auth_credentials={},
                sync_permissions=[],
                rate_limit=0
            )
    
    def test_client_config_validation_invalid_sync_frequency(self):
        """Test validation rejects non-positive sync frequency"""
        with pytest.raises(ValueError, match="Sync frequency must be positive"):
            ClientConfig(
                client_id="client_123",
                client_name="Test Client",
                auth_method=ClientAuthMethod.TOKEN,
                auth_credentials={},
                sync_permissions=[],
                sync_frequency=-1
            )
    
    def test_add_permission(self):
        """Test adding permissions to client config"""
        config = ClientConfig(
            client_id="client_123",
            client_name="Test Client",
            auth_method=ClientAuthMethod.TOKEN,
            auth_credentials={},
            sync_permissions=["read"]
        )
        
        config.add_permission("write")
        assert "write" in config.sync_permissions
        
        # Test idempotency
        config.add_permission("write")
        assert config.sync_permissions.count("write") == 1
    
    def test_remove_permission(self):
        """Test removing permissions from client config"""
        config = ClientConfig(
            client_id="client_123",
            client_name="Test Client",
            auth_method=ClientAuthMethod.TOKEN,
            auth_credentials={},
            sync_permissions=["read", "write", "delete"]
        )
        
        config.remove_permission("write")
        assert "write" not in config.sync_permissions
        
        # Test removing non-existent permission (should not raise)
        config.remove_permission("non_existent")
        assert len(config.sync_permissions) == 2
    
    def test_has_permission(self):
        """Test checking permissions"""
        config = ClientConfig(
            client_id="client_123",
            client_name="Test Client",
            auth_method=ClientAuthMethod.TOKEN,
            auth_credentials={},
            sync_permissions=["read", "write"]
        )
        
        assert config.has_permission("read") is True
        assert config.has_permission("write") is True
        assert config.has_permission("delete") is False
    
    def test_can_sync_rule_type(self):
        """Test checking allowed rule types"""
        config = ClientConfig(
            client_id="client_123",
            client_name="Test Client",
            auth_method=ClientAuthMethod.TOKEN,
            auth_credentials={},
            sync_permissions=[],
            allowed_rule_types=[RuleType.CORE, RuleType.PROJECT]
        )
        
        assert config.can_sync_rule_type(RuleType.CORE) is True
        assert config.can_sync_rule_type(RuleType.PROJECT) is True
        assert config.can_sync_rule_type(RuleType.CUSTOM) is False
    
    def test_sync_history_management(self):
        """Test sync history management with size limit"""
        config = ClientConfig(
            client_id="client_123",
            client_name="Test Client",
            auth_method=ClientAuthMethod.TOKEN,
            auth_credentials={},
            sync_permissions=[]
        )
        
        # Add entries to history
        for i in range(150):
            config.add_to_history(f"Entry {i}")
        
        # Should only keep last 100 entries
        assert len(config.sync_history) == 100
        assert config.sync_history[0] == "Entry 50"
        assert config.sync_history[-1] == "Entry 149"


class TestSyncRequest:
    """Test suite for SyncRequest value object"""
    
    def test_create_valid_sync_request(self):
        """Test creating a valid sync request"""
        request = SyncRequest(
            request_id="req_123",
            client_id="client_456",
            operation=SyncOperation.PULL,
            rules={"rule1": "content1"},
            metadata={"version": "1.0"},
            timestamp=1234567890.0
        )
        
        assert pytest_request.request_id == "req_123"
        assert pytest_request.client_id == "client_456"
        assert pytest_request.operation == SyncOperation.PULL
        assert pytest_request.priority == 1
        assert pytest_request.is_high_priority is False
    
    def test_sync_request_validation_empty_request_id(self):
        """Test validation rejects empty request ID"""
        with pytest.raises(ValueError, match="Request ID cannot be empty"):
            SyncRequest(
                request_id="",
                client_id="client_456",
                operation=SyncOperation.PULL,
                rules={},
                metadata={},
                timestamp=1234567890.0
            )
    
    def test_sync_request_validation_empty_client_id(self):
        """Test validation rejects empty client ID"""
        with pytest.raises(ValueError, match="Client ID cannot be empty"):
            SyncRequest(
                request_id="req_123",
                client_id="",
                operation=SyncOperation.PULL,
                rules={},
                metadata={},
                timestamp=1234567890.0
            )
    
    def test_sync_request_validation_invalid_priority(self):
        """Test validation rejects invalid priority"""
        with pytest.raises(ValueError, match="Priority must be at least 1"):
            SyncRequest(
                request_id="req_123",
                client_id="client_456",
                operation=SyncOperation.PULL,
                rules={},
                metadata={},
                timestamp=1234567890.0,
                priority=0
            )
    
    def test_high_priority_request(self):
        """Test high priority request detection"""
        request = SyncRequest(
            request_id="req_123",
            client_id="client_456",
            operation=SyncOperation.PUSH,
            rules={},
            metadata={},
            timestamp=1234567890.0,
            priority=5
        )
        
        assert pytest_request.is_high_priority is True
        
        # Test low priority
        request_low = SyncRequest(
            request_id="req_124",
            client_id="client_456",
            operation=SyncOperation.PULL,
            rules={},
            metadata={},
            timestamp=1234567890.0,
            priority=4
        )
        
        assert request_low.is_high_priority is False


class TestSyncResult:
    """Test suite for SyncResult value object"""
    
    def test_create_valid_sync_result(self):
        """Test creating a valid sync result"""
        result = SyncResult(
            request_id="req_123",
            client_id="client_456",
            status=SyncStatus.COMPLETED,
            operation=SyncOperation.PUSH,
            processed_rules=["rule1", "rule2"],
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=2.5,
            timestamp=1234567890.0,
            changes_applied=2
        )
        
        assert result.request_id == "req_123"
        assert result.status == SyncStatus.COMPLETED
        assert result.is_successful is True
        assert result.has_conflicts is False
        assert result.has_warnings is False
        assert result.changes_applied == 2
    
    def test_sync_result_validation_empty_request_id(self):
        """Test validation rejects empty request ID"""
        with pytest.raises(ValueError, match="Request ID cannot be empty"):
            SyncResult(
                request_id="",
                client_id="client_456",
                status=SyncStatus.COMPLETED,
                operation=SyncOperation.PUSH,
                processed_rules=[],
                conflicts=[],
                errors=[],
                warnings=[],
                sync_duration=1.0,
                timestamp=1234567890.0
            )
    
    def test_sync_result_validation_negative_duration(self):
        """Test validation rejects negative sync duration"""
        with pytest.raises(ValueError, match="Sync duration cannot be negative"):
            SyncResult(
                request_id="req_123",
                client_id="client_456",
                status=SyncStatus.COMPLETED,
                operation=SyncOperation.PUSH,
                processed_rules=[],
                conflicts=[],
                errors=[],
                warnings=[],
                sync_duration=-1.0,
                timestamp=1234567890.0
            )
    
    def test_sync_result_success_detection(self):
        """Test successful sync detection"""
        # Successful result
        result_success = SyncResult(
            request_id="req_123",
            client_id="client_456",
            status=SyncStatus.COMPLETED,
            operation=SyncOperation.PUSH,
            processed_rules=[],
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=1.0,
            timestamp=1234567890.0
        )
        assert result_success.is_successful is True
        
        # Failed due to status
        result_failed = SyncResult(
            request_id="req_124",
            client_id="client_456",
            status=SyncStatus.FAILED,
            operation=SyncOperation.PUSH,
            processed_rules=[],
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=1.0,
            timestamp=1234567890.0
        )
        assert result_failed.is_successful is False
        
        # Failed due to errors
        result_with_errors = SyncResult(
            request_id="req_125",
            client_id="client_456",
            status=SyncStatus.COMPLETED,
            operation=SyncOperation.PUSH,
            processed_rules=[],
            conflicts=[],
            errors=["Error 1"],
            warnings=[],
            sync_duration=1.0,
            timestamp=1234567890.0
        )
        assert result_with_errors.is_successful is False
    
    def test_add_error(self):
        """Test adding errors to sync result"""
        result = SyncResult(
            request_id="req_123",
            client_id="client_456",
            status=SyncStatus.COMPLETED,
            operation=SyncOperation.PUSH,
            processed_rules=[],
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=1.0,
            timestamp=1234567890.0
        )
        
        result.add_error("Error 1")
        assert "Error 1" in result.errors
        
        # Test idempotency
        result.add_error("Error 1")
        assert result.errors.count("Error 1") == 1
    
    def test_add_warning(self):
        """Test adding warnings to sync result"""
        result = SyncResult(
            request_id="req_123",
            client_id="client_456",
            status=SyncStatus.COMPLETED,
            operation=SyncOperation.PUSH,
            processed_rules=[],
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=1.0,
            timestamp=1234567890.0
        )
        
        result.add_warning("Warning 1")
        assert "Warning 1" in result.warnings
        assert result.has_warnings is True
        
        # Test idempotency
        result.add_warning("Warning 1")
        assert result.warnings.count("Warning 1") == 1
    
    def test_add_conflict(self):
        """Test adding conflicts to sync result"""
        result = SyncResult(
            request_id="req_123",
            client_id="client_456",
            status=SyncStatus.COMPLETED,
            operation=SyncOperation.PUSH,
            processed_rules=[],
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=1.0,
            timestamp=1234567890.0
        )
        
        conflict = {"rule": "rule1", "type": "version_mismatch"}
        result.add_conflict(conflict)
        assert conflict in result.conflicts
        assert result.has_conflicts is True


class TestRuleConflict:
    """Test suite for RuleConflict value object"""
    
    def test_create_valid_rule_conflict(self):
        """Test creating a valid rule conflict"""
        conflict = RuleConflict(
            rule_path="/rules/rule1",
            client_version="1.0",
            server_version="1.1",
            conflict_type="version_mismatch",
            client_content="client content",
            server_content="server content",
            suggested_resolution="Use server version",
            auto_resolvable=True
        )
        
        assert conflict.rule_path == "/rules/rule1"
        assert conflict.conflict_type == "version_mismatch"
        assert conflict.auto_resolvable is True
        assert conflict.requires_manual_resolution is False
    
    def test_rule_conflict_validation_empty_path(self):
        """Test validation rejects empty rule path"""
        with pytest.raises(ValueError, match="Rule path cannot be empty"):
            RuleConflict(
                rule_path="",
                client_version="1.0",
                server_version="1.1",
                conflict_type="version_mismatch",
                client_content="content",
                server_content="content",
                suggested_resolution="resolution"
            )
    
    def test_rule_conflict_validation_empty_type(self):
        """Test validation rejects empty conflict type"""
        with pytest.raises(ValueError, match="Conflict type cannot be empty"):
            RuleConflict(
                rule_path="/rules/rule1",
                client_version="1.0",
                server_version="1.1",
                conflict_type="",
                client_content="content",
                server_content="content",
                suggested_resolution="resolution"
            )
    
    def test_manual_resolution_required(self):
        """Test manual resolution requirement detection"""
        conflict_manual = RuleConflict(
            rule_path="/rules/rule1",
            client_version="1.0",
            server_version="1.1",
            conflict_type="complex_merge",
            client_content="content1",
            server_content="content2",
            suggested_resolution="Manual merge required",
            auto_resolvable=False
        )
        
        assert conflict_manual.requires_manual_resolution is True


class TestCompositionResult:
    """Test suite for CompositionResult value object"""
    
    def test_create_valid_composition_result(self):
        """Test creating a valid composition result"""
        mock_inheritance = MagicMock(spec=RuleInheritance)
        
        result = CompositionResult(
            composed_content="Final composed content",
            source_rules=["rule1", "rule2"],
            inheritance_chain=[mock_inheritance],
            conflicts_resolved=["conflict1"],
            composition_metadata={"version": "1.0"},
            success=True
        )
        
        assert result.composed_content == "Final composed content"
        assert len(result.source_rules) == 2
        assert result.has_inheritance is True
        assert result.has_warnings is False
        assert result.success is True
    
    def test_composition_result_validation_empty_content(self):
        """Test validation rejects empty content for successful composition"""
        with pytest.raises(ValueError, match="Successful composition must have content"):
            CompositionResult(
                composed_content="",
                source_rules=["rule1"],
                inheritance_chain=[],
                conflicts_resolved=[],
                composition_metadata={},
                success=True
            )
    
    def test_composition_result_failed_with_empty_content(self):
        """Test failed composition can have empty content"""
        result = CompositionResult(
            composed_content="",
            source_rules=["rule1"],
            inheritance_chain=[],
            conflicts_resolved=[],
            composition_metadata={},
            success=False
        )
        
        assert result.composed_content == ""
        assert result.success is False
    
    def test_add_warning_to_composition(self):
        """Test adding warnings to composition result"""
        result = CompositionResult(
            composed_content="Content",
            source_rules=["rule1"],
            inheritance_chain=[],
            conflicts_resolved=[],
            composition_metadata={}
        )
        
        result.add_warning("Warning 1")
        assert "Warning 1" in result.warnings
        assert result.has_warnings is True
        
        # Test idempotency
        result.add_warning("Warning 1")
        assert result.warnings.count("Warning 1") == 1


class TestCacheEntry:
    """Test suite for CacheEntry value object"""
    
    def test_create_valid_cache_entry(self):
        """Test creating a valid cache entry"""
        mock_content = MagicMock(spec=RuleContent)
        current_time = time.time()
        
        entry = CacheEntry(
            content=mock_content,
            timestamp=current_time,
            access_count=0,
            ttl=3600.0
        )
        
        assert entry.content == mock_content
        assert entry.timestamp == current_time
        assert entry.access_count == 0
        assert entry.ttl == 3600.0
    
    def test_cache_entry_validation_invalid_ttl(self):
        """Test validation rejects non-positive TTL"""
        mock_content = MagicMock(spec=RuleContent)
        
        with pytest.raises(ValueError, match="TTL must be positive"):
            CacheEntry(
                content=mock_content,
                timestamp=time.time(),
                access_count=0,
                ttl=0
            )
    
    def test_cache_entry_validation_negative_access_count(self):
        """Test validation rejects negative access count"""
        mock_content = MagicMock(spec=RuleContent)
        
        with pytest.raises(ValueError, match="Access count cannot be negative"):
            CacheEntry(
                content=mock_content,
                timestamp=time.time(),
                access_count=-1,
                ttl=3600.0
            )
    
    @patch('time.time')
    def test_cache_expiration(self, mock_time):
        """Test cache expiration detection"""
        mock_content = MagicMock(spec=RuleContent)
        
        # Create entry at time 1000
        mock_time.return_value = 1000.0
        entry = CacheEntry(
            content=mock_content,
            timestamp=1000.0,
            access_count=0,
            ttl=3600.0
        )
        
        # Check not expired at time 2000
        mock_time.return_value = 2000.0
        assert entry.is_expired is False
        
        # Check expired at time 5000
        mock_time.return_value = 5000.0
        assert entry.is_expired is True
    
    def test_increment_access_count(self):
        """Test incrementing access count"""
        mock_content = MagicMock(spec=RuleContent)
        
        entry = CacheEntry(
            content=mock_content,
            timestamp=time.time(),
            access_count=0,
            ttl=3600.0
        )
        
        entry.increment_access()
        assert entry.access_count == 1
        
        entry.increment_access()
        assert entry.access_count == 2
    
    @patch('time.time')
    def test_update_timestamp(self, mock_time):
        """Test updating timestamp"""
        mock_content = MagicMock(spec=RuleContent)
        
        # Create entry at time 1000
        mock_time.return_value = 1000.0
        entry = CacheEntry(
            content=mock_content,
            timestamp=1000.0,
            access_count=0,
            ttl=3600.0
        )
        
        # Update timestamp to 2000
        mock_time.return_value = 2000.0
        entry.update_timestamp()
        
        assert entry.timestamp == 2000.0


class TestRuleHierarchyInfo:
    """Test suite for RuleHierarchyInfo value object"""
    
    def test_create_valid_hierarchy_info(self):
        """Test creating valid hierarchy information"""
        info = RuleHierarchyInfo(
            total_rules=50,
            max_depth=5,
            inheritance_relationships=10,
            circular_dependencies=[],
            rule_types_distribution={"system": 20, "project": 30},
            format_distribution={"yaml": 40, "json": 10}
        )
        
        assert info.total_rules == 50
        assert info.max_depth == 5
        assert info.has_circular_dependencies is False
        assert info.is_healthy is True
    
    def test_hierarchy_info_validation_negative_total(self):
        """Test validation rejects negative total rules"""
        with pytest.raises(ValueError, match="Total rules cannot be negative"):
            RuleHierarchyInfo(
                total_rules=-1,
                max_depth=5,
                inheritance_relationships=10,
                circular_dependencies=[],
                rule_types_distribution={},
                format_distribution={}
            )
    
    def test_hierarchy_info_validation_negative_depth(self):
        """Test validation rejects negative max depth"""
        with pytest.raises(ValueError, match="Max depth cannot be negative"):
            RuleHierarchyInfo(
                total_rules=50,
                max_depth=-1,
                inheritance_relationships=10,
                circular_dependencies=[],
                rule_types_distribution={},
                format_distribution={}
            )
    
    def test_circular_dependencies_detection(self):
        """Test circular dependency detection"""
        info = RuleHierarchyInfo(
            total_rules=50,
            max_depth=5,
            inheritance_relationships=10,
            circular_dependencies=[["rule1", "rule2", "rule1"]],
            rule_types_distribution={},
            format_distribution={}
        )
        
        assert info.has_circular_dependencies is True
        assert info.is_healthy is False
    
    def test_healthy_hierarchy(self):
        """Test healthy hierarchy detection"""
        info = RuleHierarchyInfo(
            total_rules=100,
            max_depth=3,
            inheritance_relationships=20,
            circular_dependencies=[],
            rule_types_distribution={"system": 40, "project": 60},
            format_distribution={"yaml": 100}
        )
        
        assert info.has_circular_dependencies is False
        assert info.is_healthy is True


# Test fixtures for complex scenarios
@pytest.fixture
def sample_client_config():
    """Fixture for a sample client configuration"""
    return ClientConfig(
        client_id="test_client",
        client_name="Test Client",
        auth_method=ClientAuthMethod.TOKEN,
        auth_credentials={"token": "test_token"},
        sync_permissions=["read", "write"],
        rate_limit=100,
        sync_frequency=300,
        allowed_rule_types=[RuleType.CORE, RuleType.PROJECT]
    )


@pytest.fixture
def sample_sync_request():
    """Fixture for a sample sync request"""
    return SyncRequest(
        request_id="req_test",
        client_id="test_client",
        operation=SyncOperation.PULL,
        rules={"rule1": {"content": "test"}},
        metadata={"version": "1.0"},
        timestamp=time.time()
    )


@pytest.fixture
def sample_sync_result():
    """Fixture for a sample sync result"""
    return SyncResult(
        request_id="req_test",
        client_id="test_client",
        status=SyncStatus.COMPLETED,
        operation=SyncOperation.PULL,
        processed_rules=["rule1", "rule2"],
        conflicts=[],
        errors=[],
        warnings=[],
        sync_duration=2.5,
        timestamp=time.time(),
        changes_applied=2
    )


class TestValueObjectIntegration:
    """Integration tests for value objects working together"""
    
    def test_sync_workflow(self, sample_client_config, sample_sync_request):
        """Test a complete sync workflow using multiple value objects"""
        # Verify client has permission for operation
        assert sample_client_config.has_permission("read")
        
        # Create sync request
        assert sample_sync_request.client_id == sample_client_config.client_id
        
        # Process sync and create result
        result = SyncResult(
            request_id=sample_sync_request.request_id,
            client_id=sample_sync_request.client_id,
            status=SyncStatus.COMPLETED,
            operation=sample_sync_request.operation,
            processed_rules=list(sample_sync_request.rules.keys()),
            conflicts=[],
            errors=[],
            warnings=[],
            sync_duration=1.5,
            timestamp=time.time()
        )
        
        assert result.is_successful
        assert len(result.processed_rules) == len(sample_sync_request.rules)
        
        # Update client history
        sample_client_config.add_to_history(f"Sync {result.request_id} completed")
        assert f"Sync {result.request_id} completed" in sample_client_config.sync_history
    
    def test_conflict_resolution_workflow(self):
        """Test conflict resolution workflow"""
        # Create a conflict
        conflict = RuleConflict(
            rule_path="/rules/test",
            client_version="1.0",
            server_version="1.1",
            conflict_type="version_mismatch",
            client_content="old content",
            server_content="new content",
            suggested_resolution="Use server version",
            auto_resolvable=True
        )
        
        # Add to sync result
        result = SyncResult(
            request_id="req_conflict",
            client_id="client_test",
            status=SyncStatus.CONFLICT,
            operation=SyncOperation.PUSH,
            processed_rules=["rule1"],
            conflicts=[{
                "path": conflict.rule_path,
                "type": conflict.conflict_type,
                "resolution": conflict.suggested_resolution
            }],
            errors=[],
            warnings=["Conflict detected"],
            sync_duration=3.0,
            timestamp=time.time()
        )
        
        assert result.has_conflicts
        assert result.has_warnings
        assert not result.is_successful
        assert not conflict.requires_manual_resolution
    
    def test_cache_lifecycle(self):
        """Test cache entry lifecycle"""
        mock_content = MagicMock(spec=RuleContent)
        
        # Create cache entry
        entry = CacheEntry(
            content=mock_content,
            timestamp=time.time(),
            access_count=0,
            ttl=1.0  # 1 second TTL for testing
        )
        
        # Access the entry
        entry.increment_access()
        assert entry.access_count == 1
        
        # Check expiration
        assert not entry.is_expired
        
        # Wait for expiration
        time.sleep(1.1)
        assert entry.is_expired
        
        # Update timestamp to refresh
        entry.update_timestamp()
        assert not entry.is_expired