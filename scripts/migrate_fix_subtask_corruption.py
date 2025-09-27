#!/usr/bin/env python3
"""
Data Migration Script: Fix corrupted subtask records with wrong parent_task_id

This script provides comprehensive data migration capabilities to fix corrupted
subtask records in the task_subtasks table, including:
- Fixing orphaned subtasks (parent_task_id references non-existent tasks)
- Correcting user_id mismatches between subtasks and parent tasks
- Creating backup before migration
- Providing rollback capabilities
- Comprehensive logging and reporting
"""

import os
import sys
import sqlite3
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import argparse
import logging

# Add the src directory to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agenthub_main" / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "subtask_migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SubtaskMigrationError(Exception):
    """Custom exception for migration errors"""
    pass

class SubtaskCorruptionMigrator:
    """
    Handles migration of corrupted subtask records with comprehensive
    backup, validation, and rollback capabilities.
    """

    def __init__(self, db_path: str, dry_run: bool = False):
        """
        Initialize the migrator

        Args:
            db_path: Path to the database file
            dry_run: If True, only analyze without making changes
        """
        self.db_path = Path(db_path)
        self.dry_run = dry_run
        self.backup_path = None
        self.migration_log = []

        if not self.db_path.exists():
            raise SubtaskMigrationError(f"Database file not found: {db_path}")

        logger.info(f"Initialized SubtaskCorruptionMigrator for {db_path}")
        logger.info(f"Dry run mode: {dry_run}")

    def create_backup(self) -> str:
        """
        Create a backup of the database before migration

        Returns:
            Path to the backup file
        """
        if self.dry_run:
            logger.info("🔄 Dry run mode: Skipping backup creation")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        self.backup_path = backup_dir / f"{self.db_path.stem}_backup_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"✅ Database backup created: {self.backup_path}")
            return str(self.backup_path)
        except Exception as e:
            raise SubtaskMigrationError(f"Failed to create backup: {e}")

    def analyze_corruption(self) -> Dict[str, Any]:
        """
        Analyze the database for corruption issues

        Returns:
            Analysis results dictionary
        """
        logger.info("🔍 Analyzing database for subtask corruption...")

        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_subtasks": 0,
            "total_tasks": 0,
            "orphaned_subtasks": [],
            "user_mismatch_subtasks": [],
            "valid_subtasks": 0,
            "corruption_summary": {}
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get total counts
                cursor.execute("SELECT COUNT(*) as count FROM tasks")
                results["total_tasks"] = cursor.fetchone()["count"]

                cursor.execute("SELECT COUNT(*) as count FROM task_subtasks")
                results["total_subtasks"] = cursor.fetchone()["count"]

                logger.info(f"📊 Total tasks: {results['total_tasks']}")
                logger.info(f"📊 Total subtasks: {results['total_subtasks']}")

                if results["total_subtasks"] == 0:
                    logger.info("ℹ️ No subtasks found in database")
                    results["corruption_summary"] = {
                        "total_corrupted": 0,
                        "orphaned_count": 0,
                        "user_mismatch_count": 0,
                        "valid_count": 0,
                        "corruption_percentage": 0
                    }
                    return results

                # Find corrupted subtasks
                query = """
                SELECT
                    s.id as subtask_id,
                    s.task_id as parent_task_id,
                    s.title as subtask_title,
                    s.status as subtask_status,
                    s.user_id as subtask_user_id,
                    s.created_at as subtask_created_at,
                    t.id as task_exists,
                    t.title as task_title,
                    t.user_id as task_user_id,
                    t.git_branch_id as task_git_branch_id
                FROM task_subtasks s
                LEFT JOIN tasks t ON s.task_id = t.id
                ORDER BY s.created_at DESC
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                for row in rows:
                    subtask_data = dict(row)
                    subtask_data["task_exists"] = row["task_exists"] is not None

                    if not subtask_data["task_exists"]:
                        # Orphaned subtask
                        results["orphaned_subtasks"].append(subtask_data)
                        logger.warning(f"🚨 ORPHANED: Subtask '{subtask_data['subtask_title']}' "
                                     f"(ID: {subtask_data['subtask_id']}) references "
                                     f"non-existent task {subtask_data['parent_task_id']}")

                    elif subtask_data["subtask_user_id"] != subtask_data["task_user_id"]:
                        # User ID mismatch
                        subtask_data["corruption_type"] = "user_id_mismatch"
                        results["user_mismatch_subtasks"].append(subtask_data)
                        logger.warning(f"⚠️ USER_MISMATCH: Subtask '{subtask_data['subtask_title']}' "
                                     f"user_id mismatch: {subtask_data['subtask_user_id']} != "
                                     f"{subtask_data['task_user_id']}")

                    else:
                        # Valid subtask
                        results["valid_subtasks"] += 1

                # Generate summary
                total_corrupted = len(results["orphaned_subtasks"]) + len(results["user_mismatch_subtasks"])
                results["corruption_summary"] = {
                    "total_corrupted": total_corrupted,
                    "orphaned_count": len(results["orphaned_subtasks"]),
                    "user_mismatch_count": len(results["user_mismatch_subtasks"]),
                    "valid_count": results["valid_subtasks"],
                    "corruption_percentage": round((total_corrupted / results["total_subtasks"]) * 100, 2) if results["total_subtasks"] > 0 else 0
                }

        except sqlite3.Error as e:
            raise SubtaskMigrationError(f"Database analysis failed: {e}")

        return results

    def fix_orphaned_subtasks(self, orphaned_subtasks: List[Dict]) -> List[Dict]:
        """
        Fix orphaned subtasks by either deleting them or reassigning to valid tasks

        Args:
            orphaned_subtasks: List of orphaned subtask records

        Returns:
            List of migration actions performed
        """
        if not orphaned_subtasks:
            return []

        logger.info(f"🔧 Fixing {len(orphaned_subtasks)} orphaned subtasks...")
        actions = []

        if self.dry_run:
            for subtask in orphaned_subtasks:
                action = {
                    "type": "delete_orphaned",
                    "subtask_id": subtask["subtask_id"],
                    "subtask_title": subtask["subtask_title"],
                    "action": "DELETE (orphaned - no parent task found)",
                    "dry_run": True
                }
                actions.append(action)
                logger.info(f"🔄 DRY RUN: Would delete orphaned subtask {subtask['subtask_id']}")
            return actions

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for subtask in orphaned_subtasks:
                    try:
                        # Delete orphaned subtask
                        cursor.execute(
                            "DELETE FROM task_subtasks WHERE id = ?",
                            (subtask["subtask_id"],)
                        )

                        action = {
                            "type": "delete_orphaned",
                            "subtask_id": subtask["subtask_id"],
                            "subtask_title": subtask["subtask_title"],
                            "action": "DELETED (orphaned)",
                            "timestamp": datetime.now().isoformat()
                        }
                        actions.append(action)
                        self.migration_log.append(action)

                        logger.info(f"✅ Deleted orphaned subtask: {subtask['subtask_id']}")

                    except sqlite3.Error as e:
                        logger.error(f"❌ Failed to delete orphaned subtask {subtask['subtask_id']}: {e}")

                conn.commit()

        except sqlite3.Error as e:
            raise SubtaskMigrationError(f"Failed to fix orphaned subtasks: {e}")

        return actions

    def fix_user_mismatch_subtasks(self, mismatch_subtasks: List[Dict]) -> List[Dict]:
        """
        Fix user ID mismatches by updating subtask user_id to match parent task

        Args:
            mismatch_subtasks: List of subtasks with user ID mismatches

        Returns:
            List of migration actions performed
        """
        if not mismatch_subtasks:
            return []

        logger.info(f"🔧 Fixing {len(mismatch_subtasks)} user ID mismatch subtasks...")
        actions = []

        if self.dry_run:
            for subtask in mismatch_subtasks:
                action = {
                    "type": "fix_user_mismatch",
                    "subtask_id": subtask["subtask_id"],
                    "subtask_title": subtask["subtask_title"],
                    "old_user_id": subtask["subtask_user_id"],
                    "new_user_id": subtask["task_user_id"],
                    "action": f"UPDATE user_id: {subtask['subtask_user_id']} → {subtask['task_user_id']}",
                    "dry_run": True
                }
                actions.append(action)
                logger.info(f"🔄 DRY RUN: Would update subtask {subtask['subtask_id']} user_id")
            return actions

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for subtask in mismatch_subtasks:
                    try:
                        # Update subtask user_id to match parent task
                        cursor.execute(
                            "UPDATE task_subtasks SET user_id = ?, updated_at = ? WHERE id = ?",
                            (subtask["task_user_id"], datetime.now().isoformat(), subtask["subtask_id"])
                        )

                        action = {
                            "type": "fix_user_mismatch",
                            "subtask_id": subtask["subtask_id"],
                            "subtask_title": subtask["subtask_title"],
                            "old_user_id": subtask["subtask_user_id"],
                            "new_user_id": subtask["task_user_id"],
                            "action": f"UPDATED user_id: {subtask['subtask_user_id']} → {subtask['task_user_id']}",
                            "timestamp": datetime.now().isoformat()
                        }
                        actions.append(action)
                        self.migration_log.append(action)

                        logger.info(f"✅ Fixed user mismatch for subtask: {subtask['subtask_id']}")

                    except sqlite3.Error as e:
                        logger.error(f"❌ Failed to fix user mismatch for subtask {subtask['subtask_id']}: {e}")

                conn.commit()

        except sqlite3.Error as e:
            raise SubtaskMigrationError(f"Failed to fix user mismatch subtasks: {e}")

        return actions

    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate the migration by re-analyzing the database

        Returns:
            Validation results
        """
        logger.info("🔍 Validating migration results...")

        post_migration_analysis = self.analyze_corruption()

        validation_result = {
            "validation_timestamp": datetime.now().isoformat(),
            "post_migration_analysis": post_migration_analysis,
            "migration_successful": post_migration_analysis["corruption_summary"]["total_corrupted"] == 0,
            "remaining_issues": post_migration_analysis["corruption_summary"]["total_corrupted"]
        }

        if validation_result["migration_successful"]:
            logger.info("✅ Migration validation successful - no corruption remaining")
        else:
            logger.warning(f"⚠️ Migration validation found {validation_result['remaining_issues']} remaining issues")

        return validation_result

    def rollback(self) -> bool:
        """
        Rollback the migration by restoring from backup

        Returns:
            True if rollback successful
        """
        if not self.backup_path or not Path(self.backup_path).exists():
            logger.error("❌ No backup file found for rollback")
            return False

        try:
            shutil.copy2(self.backup_path, self.db_path)
            logger.info(f"✅ Database rolled back from backup: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False

    def generate_migration_report(self, analysis: Dict, actions: List[Dict],
                                validation: Dict = None) -> str:
        """
        Generate a comprehensive migration report

        Args:
            analysis: Pre-migration analysis results
            actions: Migration actions performed
            validation: Post-migration validation results

        Returns:
            Path to the generated report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = PROJECT_ROOT / "ai_docs" / "reports-status" / f"subtask_migration_report_{timestamp}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "migration_report": {
                "timestamp": datetime.now().isoformat(),
                "database_path": str(self.db_path),
                "backup_path": str(self.backup_path) if self.backup_path else None,
                "dry_run": self.dry_run,
                "pre_migration_analysis": analysis,
                "migration_actions": actions,
                "post_migration_validation": validation,
                "migration_log": self.migration_log
            }
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"📄 Migration report saved to: {report_file}")
        return str(report_file)

def find_database_file() -> str:
    """Find the active database file"""
    possible_paths = [
        PROJECT_ROOT / "agenthub_main" / "database" / "data" / "dhafnck_mcp.db",
        PROJECT_ROOT / "agenthub_main" / "dhafnck_mcp_dev.db",
        PROJECT_ROOT / "data" / "agenthub.db",  # Docker volume mount
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    raise FileNotFoundError("No database file found in expected locations")

def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="Fix corrupted subtask records")
    parser.add_argument("--database", "-d", help="Database file path")
    parser.add_argument("--dry-run", "-n", action="store_true",
                       help="Analyze only, don't make changes")
    parser.add_argument("--rollback", "-r", help="Rollback from backup file")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Force migration without confirmation")

    args = parser.parse_args()

    try:
        # Handle rollback
        if args.rollback:
            if not Path(args.rollback).exists():
                print(f"❌ Backup file not found: {args.rollback}")
                sys.exit(1)

            db_path = find_database_file()
            migrator = SubtaskCorruptionMigrator(db_path)
            migrator.backup_path = args.rollback

            if migrator.rollback():
                print("✅ Rollback completed successfully")
            else:
                print("❌ Rollback failed")
                sys.exit(1)
            return

        # Find database
        db_path = args.database or find_database_file()

        print(f"🔍 Starting subtask corruption migration for: {db_path}")
        print(f"🔄 Dry run mode: {args.dry_run}")

        # Initialize migrator
        migrator = SubtaskCorruptionMigrator(db_path, dry_run=args.dry_run)

        # Create backup
        if not args.dry_run:
            backup_path = migrator.create_backup()
            print(f"✅ Backup created: {backup_path}")

        # Analyze corruption
        analysis = migrator.analyze_corruption()

        if analysis["corruption_summary"]["total_corrupted"] == 0:
            print("✅ No corruption detected - database is clean")
            report_file = migrator.generate_migration_report(analysis, [])
            print(f"📄 Analysis report: {report_file}")
            return

        # Show corruption summary
        summary = analysis["corruption_summary"]
        print(f"\n🚨 CORRUPTION DETECTED:")
        print(f"   Orphaned subtasks: {summary['orphaned_count']}")
        print(f"   User mismatch subtasks: {summary['user_mismatch_count']}")
        print(f"   Total corrupted: {summary['total_corrupted']}")
        print(f"   Corruption rate: {summary['corruption_percentage']}%")

        # Confirm migration
        if not args.dry_run and not args.force:
            response = input("\n❓ Proceed with migration? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled by user")
                return

        # Perform migration
        actions = []

        # Fix orphaned subtasks
        orphaned_actions = migrator.fix_orphaned_subtasks(analysis["orphaned_subtasks"])
        actions.extend(orphaned_actions)

        # Fix user mismatches
        mismatch_actions = migrator.fix_user_mismatch_subtasks(analysis["user_mismatch_subtasks"])
        actions.extend(mismatch_actions)

        # Validate migration
        validation = None
        if not args.dry_run:
            validation = migrator.validate_migration()

        # Generate report
        report_file = migrator.generate_migration_report(analysis, actions, validation)

        # Final summary
        if args.dry_run:
            print(f"\n🔄 DRY RUN COMPLETED:")
            print(f"   Would fix {len(actions)} issues")
        else:
            print(f"\n✅ MIGRATION COMPLETED:")
            print(f"   Fixed {len(actions)} issues")
            if validation and validation["migration_successful"]:
                print("   Database is now clean")
            else:
                print("   ⚠️ Some issues may remain - check report")

        print(f"📄 Full report: {report_file}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()