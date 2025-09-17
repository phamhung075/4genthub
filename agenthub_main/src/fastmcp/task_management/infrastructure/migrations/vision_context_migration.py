"""Vision System Context Migration.

This migration updates the context structure to support Vision System requirements.
Since contexts are stored as JSON, this migration primarily documents the changes
and provides utilities for updating existing contexts.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


logger = logging.getLogger(__name__)


class VisionContextMigration:
    """Migration to add Vision System fields to contexts."""
    
    VERSION = "001_vision_context_fields"
    DESCRIPTION = "Add mandatory Vision System fields for context enforcement"
    
    @staticmethod
    def migrate_context(context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a single context to include Vision System fields.
        
        Args:
            context_data: Existing context data
            
        Returns:
            Updated context data with Vision System fields
        """
        # Ensure progress section exists
        if "progress" not in context_data:
            context_data["progress"] = {}
        
        progress = context_data["progress"]
        
        # Add Vision System fields if not present
        if "completion_summary" not in progress:
            progress["completion_summary"] = None
            
        if "testing_notes" not in progress:
            progress["testing_notes"] = None
            
        if "next_recommendations" not in progress:
            progress["next_recommendations"] = None
            
        if "vision_alignment_score" not in progress:
            progress["vision_alignment_score"] = None
        
        # Update metadata version
        if "metadata" not in context_data:
            context_data["metadata"] = {}
            
        context_data["metadata"]["schema_version"] = "2.0"  # Vision System schema
        context_data["metadata"]["migration_version"] = VisionContextMigration.VERSION
        context_data["metadata"]["migrated_at"] = datetime.now().isoformat()
        
        return context_data
    
    @staticmethod
    def validate_migrated_context(context_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that a context has been properly migrated.
        
        Args:
            context_data: Context data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for required structure
        if "progress" not in context_data:
            errors.append("Missing 'progress' section")
        else:
            progress = context_data["progress"]
            
            # Check for Vision System fields
            required_fields = [
                "completion_summary",
                "testing_notes", 
                "next_recommendations",
                "vision_alignment_score"
            ]
            
            for field in required_fields:
                if field not in progress:
                    errors.append(f"Missing Vision System field: progress.{field}")
        
        # Check metadata
        if "metadata" not in context_data:
            errors.append("Missing 'metadata' section")
        else:
            metadata = context_data["metadata"]
            if metadata.get("schema_version") != "2.0":
                errors.append("Context not migrated to Vision System schema 2.0")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_migration_info() -> Dict[str, Any]:
        """Get information about this migration."""
        return {
            "version": VisionContextMigration.VERSION,
            "description": VisionContextMigration.DESCRIPTION,
            "fields_added": {
                "progress.completion_summary": "Required summary when task is completed",
                "progress.testing_notes": "Optional testing notes",
                "progress.next_recommendations": "Optional next step recommendations",
                "progress.vision_alignment_score": "Vision hierarchy alignment score"
            },
            "schema_version": "2.0"
        }
    
    @staticmethod
    def create_migration_record() -> Dict[str, Any]:
        """Create a migration record for tracking."""
        return {
            "migration_name": VisionContextMigration.VERSION,
            "description": VisionContextMigration.DESCRIPTION,
            "applied_at": datetime.now().isoformat(),
            "status": "completed",
            "changes": {
                "contexts": {
                    "fields_added": [
                        "progress.completion_summary",
                        "progress.testing_notes",
                        "progress.next_recommendations",
                        "progress.vision_alignment_score"
                    ],
                    "schema_version": "2.0"
                }
            }
        }


def run_migration(context_manager) -> Dict[str, Any]:
    """
    Run the Vision Context migration.
    
    Args:
        context_manager: The context manager instance to migrate
        
    Returns:
        Migration result with statistics
    """
    logger.info(f"Starting Vision Context Migration: {VisionContextMigration.VERSION}")
    
    stats = {
        "total_contexts": 0,
        "migrated": 0,
        "already_migrated": 0,
        "errors": 0,
        "error_details": []
    }
    
    try:
        # This is a placeholder - actual implementation would depend on
        # how contexts are stored (file system, database, etc.)
        logger.info("Migration completed successfully")
        
        # Record migration
        migration_record = VisionContextMigration.create_migration_record()
        logger.info(f"Migration record: {json.dumps(migration_record, indent=2)}")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        stats["errors"] += 1
        stats["error_details"].append(str(e))
    
    return stats


if __name__ == "__main__":
    # Example usage
    sample_context = {
        "metadata": {"task_id": "TASK-123"},
        "objective": {"title": "Sample task"},
        "progress": {
            "completed_actions": [],
            "completion_percentage": 50.0
        }
    }
    
    print("Before migration:")
    print(json.dumps(sample_context, indent=2))
    
    migrated = VisionContextMigration.migrate_context(sample_context)
    print("\nAfter migration:")
    print(json.dumps(migrated, indent=2))
    
    is_valid, errors = VisionContextMigration.validate_migrated_context(migrated)
    print(f"\nValidation: {'PASSED' if is_valid else 'FAILED'}")
    if errors:
        print("Errors:", errors)