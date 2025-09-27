"""
Context Versioning and Rollback System

Provides version control for context changes with rollback capabilities,
enabling audit trails and recovery from unwanted changes.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import difflib

from ...domain.models.unified_context import ContextLevel
from ..services.unified_context_service import UnifiedContextService

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of context changes"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    ROLLBACK = "rollback"


@dataclass
class ContextVersion:
    """Single version of a context"""
    version_id: str                 # Unique version identifier
    context_level: ContextLevel
    context_id: str
    version_number: int             # Sequential version number
    data: Dict[str, Any]            # Context data at this version
    change_type: ChangeType
    change_summary: str
    changed_by: str                 # User who made the change
    created_at: datetime
    
    # Metadata
    parent_version_id: Optional[str] = None  # Previous version
    child_version_ids: List[str] = field(default_factory=list)
    
    # Delta storage (optional)
    delta: Optional[Dict[str, Any]] = None  # Changes from parent
    is_milestone: bool = False      # Mark important versions
    tags: List[str] = field(default_factory=list)
    
    def get_hash(self) -> str:
        """Generate hash of version data"""
        data_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


@dataclass
class VersionDiff:
    """Difference between two versions"""
    from_version: str
    to_version: str
    added: Dict[str, Any]
    modified: Dict[str, Any]
    removed: List[str]
    unified_diff: str              # Text diff for review


class ContextVersioningService:
    """
    Service for managing context versions and rollback operations.
    """
    
    def __init__(self, context_service: UnifiedContextService):
        self.context_service = context_service
        self.versions: Dict[str, ContextVersion] = {}  # version_id -> version
        self.version_chains: Dict[Tuple[str, str], List[str]] = {}  # (level, context_id) -> [version_ids]
        self.current_versions: Dict[Tuple[str, str], str] = {}  # (level, context_id) -> current_version_id
    
    async def create_version(
        self,
        context_level: ContextLevel,
        context_id: str,
        data: Dict[str, Any],
        change_type: ChangeType,
        change_summary: str,
        changed_by: str,
        is_milestone: bool = False,
        tags: Optional[List[str]] = None
    ) -> ContextVersion:
        """
        Create a new version of a context.
        
        Args:
            context_level: Level of the context
            context_id: Context identifier
            data: Context data for this version
            change_type: Type of change
            change_summary: Description of changes
            changed_by: User making the change
            is_milestone: Mark as milestone version
            tags: Optional tags for the version
        
        Returns:
            Created version
        """
        
        import uuid
        
        # Get current version if exists
        key = (context_level.value, context_id)
        current_version_id = self.current_versions.get(key)
        parent_version = None
        
        if current_version_id:
            parent_version = self.versions.get(current_version_id)
        
        # Determine version number
        version_chain = self.version_chains.get(key, [])
        version_number = len(version_chain) + 1
        
        # Generate version ID
        version_id = f"v_{context_id}_{version_number}_{uuid.uuid4().hex[:8]}"
        
        # Calculate delta if parent exists
        delta = None
        if parent_version:
            delta = self._calculate_delta(parent_version.data, data)
        
        # Create version
        version = ContextVersion(
            version_id=version_id,
            context_level=context_level,
            context_id=context_id,
            version_number=version_number,
            data=data.copy(),  # Deep copy to preserve state
            change_type=change_type,
            change_summary=change_summary,
            changed_by=changed_by,
            created_at=datetime.now(timezone.utc),
            parent_version_id=current_version_id,
            delta=delta,
            is_milestone=is_milestone,
            tags=tags or []
        )
        
        # Update parent's children
        if parent_version:
            parent_version.child_version_ids.append(version_id)
        
        # Store version
        self.versions[version_id] = version
        
        # Update version chain
        if key not in self.version_chains:
            self.version_chains[key] = []
        self.version_chains[key].append(version_id)
        
        # Update current version
        self.current_versions[key] = version_id
        
        logger.info(f"Created version {version_id} for {context_level.value}:{context_id}")
        
        return version
    
    def _calculate_delta(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """Calculate delta between two data states"""
        
        delta = {
            'added': {},
            'modified': {},
            'removed': []
        }
        
        # Find added and modified fields
        for key, value in new_data.items():
            if key not in old_data:
                delta['added'][key] = value
            elif old_data[key] != value:
                delta['modified'][key] = {
                    'old': old_data[key],
                    'new': value
                }
        
        # Find removed fields
        for key in old_data:
            if key not in new_data:
                delta['removed'].append(key)
        
        return delta
    
    async def get_version(
        self,
        version_id: str
    ) -> Optional[ContextVersion]:
        """Get a specific version"""
        return self.versions.get(version_id)
    
    async def get_version_history(
        self,
        context_level: ContextLevel,
        context_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContextVersion]:
        """
        Get version history for a context.
        
        Args:
            context_level: Context level
            context_id: Context identifier
            limit: Maximum versions to return
            offset: Offset for pagination
        
        Returns:
            List of versions in reverse chronological order
        """
        
        key = (context_level.value, context_id)
        version_ids = self.version_chains.get(key, [])
        
        # Reverse for newest first
        version_ids = version_ids[::-1]
        
        # Apply pagination
        version_ids = version_ids[offset:offset + limit]
        
        # Get version objects
        versions = [self.versions[vid] for vid in version_ids if vid in self.versions]
        
        return versions
    
    async def get_diff(
        self,
        from_version_id: str,
        to_version_id: str
    ) -> Optional[VersionDiff]:
        """
        Get difference between two versions.
        
        Args:
            from_version_id: Starting version
            to_version_id: Target version
        
        Returns:
            Difference details
        """
        
        from_version = self.versions.get(from_version_id)
        to_version = self.versions.get(to_version_id)
        
        if not from_version or not to_version:
            return None
        
        # Calculate differences
        added = {}
        modified = {}
        removed = []
        
        for key, value in to_version.data.items():
            if key not in from_version.data:
                added[key] = value
            elif from_version.data[key] != value:
                modified[key] = {
                    'from': from_version.data[key],
                    'to': value
                }
        
        for key in from_version.data:
            if key not in to_version.data:
                removed.append(key)
        
        # Generate unified diff
        from_json = json.dumps(from_version.data, indent=2, sort_keys=True)
        to_json = json.dumps(to_version.data, indent=2, sort_keys=True)
        
        unified_diff = '\n'.join(difflib.unified_diff(
            from_json.splitlines(),
            to_json.splitlines(),
            fromfile=f"Version {from_version.version_number}",
            tofile=f"Version {to_version.version_number}",
            lineterm=''
        ))
        
        return VersionDiff(
            from_version=from_version_id,
            to_version=to_version_id,
            added=added,
            modified=modified,
            removed=removed,
            unified_diff=unified_diff
        )
    
    async def rollback(
        self,
        context_level: ContextLevel,
        context_id: str,
        target_version_id: str,
        user_id: str,
        reason: str
    ) -> ContextVersion:
        """
        Rollback context to a previous version.
        
        Args:
            context_level: Context level
            context_id: Context identifier
            target_version_id: Version to rollback to
            user_id: User performing rollback
            reason: Reason for rollback
        
        Returns:
            New version created by rollback
        """
        
        # Get target version
        target_version = self.versions.get(target_version_id)
        if not target_version:
            raise ValueError(f"Version not found: {target_version_id}")
        
        # Verify it belongs to the same context
        if (target_version.context_level != context_level or 
            target_version.context_id != context_id):
            raise ValueError("Version belongs to different context")
        
        # Create new version with rolled back data
        rollback_version = await self.create_version(
            context_level=context_level,
            context_id=context_id,
            data=target_version.data.copy(),
            change_type=ChangeType.ROLLBACK,
            change_summary=f"Rollback to version {target_version.version_number}: {reason}",
            changed_by=user_id,
            tags=[f"rollback_from_v{target_version.version_number}"]
        )
        
        # Update actual context
        await self.context_service.update_context(
            context_level=context_level,
            context_id=context_id,
            data=target_version.data,
            user_id=user_id
        )
        
        logger.info(f"Rolled back {context_level.value}:{context_id} to version {target_version_id}")
        
        return rollback_version
    
    async def merge_versions(
        self,
        context_level: ContextLevel,
        context_id: str,
        version_ids: List[str],
        merge_strategy: str,
        user_id: str
    ) -> ContextVersion:
        """
        Merge multiple versions (for conflict resolution).
        
        Args:
            context_level: Context level
            context_id: Context identifier
            version_ids: Versions to merge
            merge_strategy: Strategy for merging ('latest_wins', 'union', 'custom')
            user_id: User performing merge
        
        Returns:
            Merged version
        """
        
        if len(version_ids) < 2:
            raise ValueError("Need at least 2 versions to merge")
        
        versions = [self.versions[vid] for vid in version_ids if vid in self.versions]
        
        if not versions:
            raise ValueError("No valid versions found")
        
        # Apply merge strategy
        if merge_strategy == 'latest_wins':
            # Sort by creation time and take latest
            versions.sort(key=lambda v: v.created_at)
            merged_data = versions[-1].data.copy()
        
        elif merge_strategy == 'union':
            # Combine all unique fields
            merged_data = {}
            for version in versions:
                merged_data.update(version.data)
        
        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")
        
        # Create merged version
        merge_version = await self.create_version(
            context_level=context_level,
            context_id=context_id,
            data=merged_data,
            change_type=ChangeType.MERGE,
            change_summary=f"Merged {len(versions)} versions using {merge_strategy}",
            changed_by=user_id,
            tags=[f"merged_v{v.version_number}" for v in versions]
        )
        
        return merge_version
    
    async def tag_version(
        self,
        version_id: str,
        tags: List[str]
    ):
        """Add tags to a version"""
        
        version = self.versions.get(version_id)
        if version:
            version.tags.extend(tags)
            logger.info(f"Tagged version {version_id} with {tags}")
    
    async def get_milestone_versions(
        self,
        context_level: ContextLevel,
        context_id: str
    ) -> List[ContextVersion]:
        """Get all milestone versions for a context"""
        
        key = (context_level.value, context_id)
        version_ids = self.version_chains.get(key, [])
        
        milestones = []
        for vid in version_ids:
            version = self.versions.get(vid)
            if version and version.is_milestone:
                milestones.append(version)
        
        return milestones
    
    async def prune_old_versions(
        self,
        context_level: ContextLevel,
        context_id: str,
        keep_count: int = 100,
        keep_milestones: bool = True
    ) -> int:
        """
        Prune old versions to save space.
        
        Args:
            context_level: Context level
            context_id: Context identifier
            keep_count: Number of recent versions to keep
            keep_milestones: Whether to keep milestone versions
        
        Returns:
            Number of versions pruned
        """
        
        key = (context_level.value, context_id)
        version_ids = self.version_chains.get(key, [])
        
        if len(version_ids) <= keep_count:
            return 0
        
        # Sort by version number
        versions_to_check = version_ids[:-keep_count]
        pruned = 0
        
        for vid in versions_to_check:
            version = self.versions.get(vid)
            if version:
                # Keep milestones if requested
                if keep_milestones and version.is_milestone:
                    continue
                
                # Remove version
                del self.versions[vid]
                self.version_chains[key].remove(vid)
                pruned += 1
        
        logger.info(f"Pruned {pruned} versions for {context_level.value}:{context_id}")
        
        return pruned
    
    async def export_version_history(
        self,
        context_level: ContextLevel,
        context_id: str
    ) -> str:
        """Export version history as JSON"""
        
        versions = await self.get_version_history(
            context_level=context_level,
            context_id=context_id,
            limit=1000
        )
        
        export_data = {
            'context_level': context_level.value,
            'context_id': context_id,
            'export_date': datetime.now(timezone.utc).isoformat(),
            'versions': [
                {
                    'version_id': v.version_id,
                    'version_number': v.version_number,
                    'change_type': v.change_type.value,
                    'change_summary': v.change_summary,
                    'changed_by': v.changed_by,
                    'created_at': v.created_at.isoformat(),
                    'is_milestone': v.is_milestone,
                    'tags': v.tags,
                    'data': v.data
                }
                for v in versions
            ]
        }
        
        return json.dumps(export_data, indent=2)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        
        total_versions = len(self.versions)
        total_size = sum(
            len(json.dumps(v.data)) for v in self.versions.values()
        )
        
        contexts_with_versions = len(self.version_chains)
        
        return {
            'total_versions': total_versions,
            'total_size_bytes': total_size,
            'contexts_tracked': contexts_with_versions,
            'average_versions_per_context': (
                total_versions / contexts_with_versions 
                if contexts_with_versions > 0 else 0
            )
        }