"""
Test Suite for Context Versioning System

Tests version control functionality including version creation, rollback,
merging, diff generation, and storage management.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from fastmcp.task_management.application.use_cases.context_versioning import (
    ContextVersioningService,
    ContextVersion,
    VersionDiff,
    ChangeType
)
from fastmcp.task_management.domain.models.unified_context import ContextLevel


class TestContextVersioningService:
    """Test suite for ContextVersioningService"""
    
    @pytest.fixture
    def mock_context_service(self):
        """Create mock context service"""
        service = Mock()
        service.update_context = AsyncMock()
        service.get_context = AsyncMock()
        return service
    
    @pytest.fixture
    def versioning_service(self, mock_context_service):
        """Create versioning service instance"""
        return ContextVersioningService(mock_context_service)
    
    def create_test_data(self, version: int = 1) -> Dict[str, Any]:
        """Create test context data"""
        return {
            "name": f"Test Context v{version}",
            "description": f"Version {version} of test context",
            "settings": {
                "enabled": True,
                "timeout": 30 * version,
                "features": [f"feature_{i}" for i in range(version)]
            },
            "metadata": {
                "version": version,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    
    @pytest.mark.asyncio
    async def test_create_first_version(self, versioning_service):
        """Test creating the first version of a context"""
        data = self.create_test_data(1)
        
        version = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data,
            change_type=ChangeType.CREATE,
            change_summary="Initial creation",
            changed_by="user1",
            is_milestone=True,
            tags=["initial", "v1.0"]
        )
        
        assert version.version_number == 1
        assert version.context_level == ContextLevel.PROJECT
        assert version.context_id == "proj_1"
        assert version.data == data
        assert version.change_type == ChangeType.CREATE
        assert version.changed_by == "user1"
        assert version.is_milestone is True
        assert "initial" in version.tags
        assert version.parent_version_id is None
        assert version.delta is None
    
    @pytest.mark.asyncio
    async def test_create_subsequent_version(self, versioning_service):
        """Test creating subsequent versions with delta tracking"""
        # Create first version
        data_v1 = self.create_test_data(1)
        version1 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v1,
            change_type=ChangeType.CREATE,
            change_summary="Initial",
            changed_by="user1"
        )
        
        # Create second version with changes
        data_v2 = self.create_test_data(2)
        data_v2["new_field"] = "added"
        data_v2["settings"]["enabled"] = False  # Modified
        
        version2 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v2,
            change_type=ChangeType.UPDATE,
            change_summary="Updated settings",
            changed_by="user2"
        )
        
        assert version2.version_number == 2
        assert version2.parent_version_id == version1.version_id
        assert version2.delta is not None
        
        # Check delta
        assert "new_field" in version2.delta["added"]
        assert "settings" in version2.delta["modified"]
        assert version2.delta["modified"]["settings"]["old"]["enabled"] is True
        assert version2.delta["modified"]["settings"]["new"]["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_get_version(self, versioning_service):
        """Test retrieving a specific version"""
        # Create a version
        version = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"test": "data"},
            change_type=ChangeType.CREATE,
            change_summary="Test",
            changed_by="user1"
        )
        
        # Retrieve it
        retrieved = await versioning_service.get_version(version.version_id)
        
        assert retrieved == version
        assert retrieved.version_id == version.version_id
    
    @pytest.mark.asyncio
    async def test_get_version_not_found(self, versioning_service):
        """Test retrieving non-existent version"""
        result = await versioning_service.get_version("non_existent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_version_history(self, versioning_service):
        """Test retrieving version history"""
        # Create multiple versions
        for i in range(5):
            await versioning_service.create_version(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                data=self.create_test_data(i + 1),
                change_type=ChangeType.UPDATE if i > 0 else ChangeType.CREATE,
                change_summary=f"Version {i + 1}",
                changed_by=f"user{i + 1}"
            )
        
        # Get history
        history = await versioning_service.get_version_history(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            limit=3,
            offset=0
        )
        
        # Should return in reverse chronological order
        assert len(history) == 3
        assert history[0].version_number == 5
        assert history[1].version_number == 4
        assert history[2].version_number == 3
    
    @pytest.mark.asyncio
    async def test_get_version_history_pagination(self, versioning_service):
        """Test version history pagination"""
        # Create 10 versions
        for i in range(10):
            await versioning_service.create_version(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                data={"version": i + 1},
                change_type=ChangeType.UPDATE,
                change_summary=f"v{i + 1}",
                changed_by="user1"
            )
        
        # Get different pages
        page1 = await versioning_service.get_version_history(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            limit=5,
            offset=0
        )
        
        page2 = await versioning_service.get_version_history(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            limit=5,
            offset=5
        )
        
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].version_number == 10
        assert page2[0].version_number == 5
    
    @pytest.mark.asyncio
    async def test_get_diff(self, versioning_service):
        """Test getting diff between versions"""
        # Create two versions
        data_v1 = {
            "name": "Original",
            "value": 10,
            "items": ["a", "b"],
            "removed_field": "will be removed"
        }
        
        version1 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v1,
            change_type=ChangeType.CREATE,
            change_summary="v1",
            changed_by="user1"
        )
        
        data_v2 = {
            "name": "Modified",  # Changed
            "value": 20,  # Changed
            "items": ["a", "b", "c"],  # Added item
            "new_field": "added"  # Added
            # removed_field is gone
        }
        
        version2 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v2,
            change_type=ChangeType.UPDATE,
            change_summary="v2",
            changed_by="user1"
        )
        
        # Get diff
        diff = await versioning_service.get_diff(
            from_version_id=version1.version_id,
            to_version_id=version2.version_id
        )
        
        assert diff is not None
        assert diff.from_version == version1.version_id
        assert diff.to_version == version2.version_id
        
        # Check changes
        assert "new_field" in diff.added
        assert diff.added["new_field"] == "added"
        
        assert "name" in diff.modified
        assert diff.modified["name"]["from"] == "Original"
        assert diff.modified["name"]["to"] == "Modified"
        
        assert "removed_field" in diff.removed
        
        # Check unified diff is generated
        assert len(diff.unified_diff) > 0
        assert "Original" in diff.unified_diff
        assert "Modified" in diff.unified_diff
    
    @pytest.mark.asyncio
    async def test_get_diff_invalid_versions(self, versioning_service):
        """Test getting diff with invalid version IDs"""
        diff = await versioning_service.get_diff(
            from_version_id="invalid1",
            to_version_id="invalid2"
        )
        
        assert diff is None
    
    @pytest.mark.asyncio
    async def test_rollback(self, versioning_service, mock_context_service):
        """Test rolling back to a previous version"""
        # Create versions
        data_v1 = {"version": 1, "stable": True}
        version1 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v1,
            change_type=ChangeType.CREATE,
            change_summary="v1",
            changed_by="user1"
        )
        
        data_v2 = {"version": 2, "stable": False, "experimental": True}
        version2 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v2,
            change_type=ChangeType.UPDATE,
            change_summary="v2",
            changed_by="user1"
        )
        
        # Rollback to v1
        rollback_version = await versioning_service.rollback(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            target_version_id=version1.version_id,
            user_id="user2",
            reason="v2 has issues"
        )
        
        assert rollback_version.version_number == 3
        assert rollback_version.change_type == ChangeType.ROLLBACK
        assert rollback_version.data == data_v1
        assert "Rollback to version 1" in rollback_version.change_summary
        assert "v2 has issues" in rollback_version.change_summary
        assert f"rollback_from_v{version1.version_number}" in rollback_version.tags
        
        # Verify context was updated
        mock_context_service.update_context.assert_called_once_with(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_v1,
            user_id="user2"
        )
    
    @pytest.mark.asyncio
    async def test_rollback_invalid_version(self, versioning_service):
        """Test rollback to non-existent version"""
        with pytest.raises(ValueError, match="Version not found"):
            await versioning_service.rollback(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                target_version_id="invalid",
                user_id="user1",
                reason="test"
            )
    
    @pytest.mark.asyncio
    async def test_rollback_wrong_context(self, versioning_service):
        """Test rollback to version from different context"""
        # Create version for one context
        version = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"test": "data"},
            change_type=ChangeType.CREATE,
            change_summary="v1",
            changed_by="user1"
        )
        
        # Try to rollback different context
        with pytest.raises(ValueError, match="Version belongs to different context"):
            await versioning_service.rollback(
                context_level=ContextLevel.PROJECT,
                context_id="proj_2",  # Different context
                target_version_id=version.version_id,
                user_id="user1",
                reason="test"
            )
    
    @pytest.mark.asyncio
    async def test_merge_versions_latest_wins(self, versioning_service):
        """Test merging versions with latest_wins strategy"""
        # Create base version
        base_data = {"base": True, "value": 0}
        base_version = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=base_data,
            change_type=ChangeType.CREATE,
            change_summary="base",
            changed_by="user1"
        )
        
        # Create conflicting versions
        data_a = {"base": False, "value": 1, "branch": "A"}
        version_a = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_a,
            change_type=ChangeType.UPDATE,
            change_summary="branch A",
            changed_by="user1"
        )
        
        data_b = {"base": False, "value": 2, "branch": "B"}
        version_b = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_b,
            change_type=ChangeType.UPDATE,
            change_summary="branch B",
            changed_by="user2"
        )
        
        # Merge with latest_wins
        merged = await versioning_service.merge_versions(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            version_ids=[version_a.version_id, version_b.version_id],
            merge_strategy="latest_wins",
            user_id="user3"
        )
        
        assert merged.change_type == ChangeType.MERGE
        assert merged.data == data_b  # Latest version wins
        assert "Merged 2 versions using latest_wins" in merged.change_summary
    
    @pytest.mark.asyncio
    async def test_merge_versions_union(self, versioning_service):
        """Test merging versions with union strategy"""
        # Create versions with different fields
        data_a = {"field_a": "value_a", "common": "from_a"}
        version_a = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_a,
            change_type=ChangeType.CREATE,
            change_summary="v1",
            changed_by="user1"
        )
        
        data_b = {"field_b": "value_b", "common": "from_b"}
        version_b = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data=data_b,
            change_type=ChangeType.UPDATE,
            change_summary="v2",
            changed_by="user2"
        )
        
        # Merge with union
        merged = await versioning_service.merge_versions(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            version_ids=[version_a.version_id, version_b.version_id],
            merge_strategy="union",
            user_id="user3"
        )
        
        # Union should combine all fields
        assert merged.data["field_a"] == "value_a"
        assert merged.data["field_b"] == "value_b"
        assert merged.data["common"] == "from_b"  # Later version overwrites
    
    @pytest.mark.asyncio
    async def test_merge_versions_invalid_strategy(self, versioning_service):
        """Test merge with invalid strategy"""
        # Create first version
        version1 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"field_a": "value_a"},
            change_type=ChangeType.CREATE,
            change_summary="v1",
            changed_by="user1"
        )

        # Create second version to meet minimum requirement for merge
        version2 = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={"field_b": "value_b"},
            change_type=ChangeType.UPDATE,
            change_summary="v2",
            changed_by="user1"
        )

        with pytest.raises(ValueError, match="Unknown merge strategy"):
            await versioning_service.merge_versions(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                version_ids=[version1.version_id, version2.version_id],
                merge_strategy="invalid_strategy",
                user_id="user1"
            )
    
    @pytest.mark.asyncio
    async def test_merge_versions_insufficient_versions(self, versioning_service):
        """Test merge with too few versions"""
        with pytest.raises(ValueError, match="Need at least 2 versions"):
            await versioning_service.merge_versions(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                version_ids=["single_version"],
                merge_strategy="latest_wins",
                user_id="user1"
            )
    
    @pytest.mark.asyncio
    async def test_tag_version(self, versioning_service):
        """Test adding tags to a version"""
        version = await versioning_service.create_version(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            data={},
            change_type=ChangeType.CREATE,
            change_summary="v1",
            changed_by="user1",
            tags=["initial"]
        )
        
        # Add more tags
        await versioning_service.tag_version(
            version_id=version.version_id,
            tags=["stable", "production"]
        )
        
        assert "initial" in version.tags
        assert "stable" in version.tags
        assert "production" in version.tags
    
    @pytest.mark.asyncio
    async def test_get_milestone_versions(self, versioning_service):
        """Test retrieving only milestone versions"""
        # Create mix of regular and milestone versions
        for i in range(5):
            await versioning_service.create_version(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                data={"version": i + 1},
                change_type=ChangeType.UPDATE if i > 0 else ChangeType.CREATE,
                change_summary=f"v{i + 1}",
                changed_by="user1",
                is_milestone=(i % 2 == 0)  # Even versions are milestones
            )
        
        milestones = await versioning_service.get_milestone_versions(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1"
        )
        
        assert len(milestones) == 3  # versions 1, 3, 5
        assert all(v.is_milestone for v in milestones)
        assert [v.version_number for v in milestones] == [1, 3, 5]
    
    @pytest.mark.asyncio
    async def test_prune_old_versions(self, versioning_service):
        """Test pruning old versions"""
        # Create many versions
        for i in range(10):
            await versioning_service.create_version(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                data={"version": i + 1},
                change_type=ChangeType.UPDATE if i > 0 else ChangeType.CREATE,
                change_summary=f"v{i + 1}",
                changed_by="user1",
                is_milestone=(i == 2)  # Version 3 is milestone
            )
        
        # Prune keeping only 5 recent versions
        pruned_count = await versioning_service.prune_old_versions(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            keep_count=5,
            keep_milestones=True
        )
        
        assert pruned_count == 4  # Should prune 4 versions (keeping milestone)
        
        # Check remaining versions
        history = await versioning_service.get_version_history(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            limit=100
        )
        
        assert len(history) == 6  # 5 recent + 1 milestone
        assert any(v.version_number == 3 for v in history)  # Milestone kept
    
    @pytest.mark.asyncio
    async def test_export_version_history(self, versioning_service):
        """Test exporting version history as JSON"""
        # Create some versions
        for i in range(3):
            await versioning_service.create_version(
                context_level=ContextLevel.PROJECT,
                context_id="proj_1",
                data=self.create_test_data(i + 1),
                change_type=ChangeType.UPDATE if i > 0 else ChangeType.CREATE,
                change_summary=f"Version {i + 1}",
                changed_by=f"user{i + 1}",
                is_milestone=(i == 1),
                tags=[f"v{i + 1}"]
            )
        
        # Export
        json_str = await versioning_service.export_version_history(
            context_level=ContextLevel.PROJECT,
            context_id="proj_1"
        )
        
        export_data = json.loads(json_str)
        
        assert export_data["context_level"] == "project"
        assert export_data["context_id"] == "proj_1"
        assert "export_date" in export_data
        assert len(export_data["versions"]) == 3
        
        # Check version data
        for i, version in enumerate(export_data["versions"]):
            assert "version_id" in version
            assert version["version_number"] == 3 - i  # Reverse order
            assert "change_type" in version
            assert "data" in version
            assert "tags" in version
    
    def test_get_storage_stats(self, versioning_service):
        """Test getting storage statistics"""
        stats = versioning_service.get_storage_stats()
        
        assert "total_versions" in stats
        assert "total_size_bytes" in stats
        assert "contexts_tracked" in stats
        assert "average_versions_per_context" in stats
        
        assert stats["total_versions"] == 0
        assert stats["total_size_bytes"] == 0
    
    def test_context_version_hash(self):
        """Test version hash generation"""
        version = ContextVersion(
            version_id="v1",
            context_level=ContextLevel.PROJECT,
            context_id="proj_1",
            version_number=1,
            data={"key": "value", "number": 42},
            change_type=ChangeType.CREATE,
            change_summary="Test",
            changed_by="user1",
            created_at=datetime.now(timezone.utc)
        )
        
        hash1 = version.get_hash()
        hash2 = version.get_hash()
        
        # Hash should be consistent
        assert hash1 == hash2
        
        # Modify data
        version.data["key"] = "different"
        hash3 = version.get_hash()
        
        # Hash should change
        assert hash3 != hash1
    
    def test_calculate_delta(self, versioning_service):
        """Test delta calculation between data states"""
        old_data = {
            "unchanged": "same",
            "modified": "old_value",
            "removed": "will_be_removed",
            "nested": {
                "value": 1
            }
        }
        
        new_data = {
            "unchanged": "same",
            "modified": "new_value",
            "added": "new_field",
            "nested": {
                "value": 2
            }
        }
        
        delta = versioning_service._calculate_delta(old_data, new_data)
        
        assert delta["added"] == {"added": "new_field"}
        assert "modified" in delta["modified"]
        assert delta["modified"]["modified"]["old"] == "old_value"
        assert delta["modified"]["modified"]["new"] == "new_value"
        assert "removed" in delta["removed"]