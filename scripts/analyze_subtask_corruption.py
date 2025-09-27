#!/usr/bin/env python3
"""
Database Analysis Script: Identify corrupted subtask records with wrong parent_task_id

This script analyzes the task_subtasks table to identify records with incorrect
parent_task_id references that don't match existing tasks.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add the src directory to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agenthub_main" / "src"))

def find_database_file() -> str:
    """Find the active database file"""
    possible_paths = [
        PROJECT_ROOT / "agenthub_main" / "database" / "data" / "dhafnck_mcp.db",
        PROJECT_ROOT / "agenthub_main" / "dhafnck_mcp_dev.db",
        PROJECT_ROOT / "agenthub_main" / "database" / "data" / "test" / "test_dhafnck_mcp.db",
        PROJECT_ROOT / "data" / "agenthub.db",  # Docker volume mount
    ]

    for path in possible_paths:
        if path.exists():
            print(f"✅ Found database: {path}")
            return str(path)

    raise FileNotFoundError("No database file found in expected locations")

def analyze_subtask_corruption(db_path: str) -> Dict[str, Any]:
    """
    Analyze the database for corrupted subtask records

    Returns:
        Dictionary with analysis results
    """
    print(f"🔍 Analyzing database: {db_path}")

    results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "database_path": db_path,
        "total_subtasks": 0,
        "total_tasks": 0,
        "corrupted_subtasks": [],
        "orphaned_subtasks": [],
        "valid_subtasks": 0,
        "corruption_summary": {}
    }

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Get total counts
            cursor.execute("SELECT COUNT(*) as count FROM tasks")
            results["total_tasks"] = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM task_subtasks")
            results["total_subtasks"] = cursor.fetchone()["count"]

            print(f"📊 Total tasks: {results['total_tasks']}")
            print(f"📊 Total subtasks: {results['total_subtasks']}")

            if results["total_subtasks"] == 0:
                print("ℹ️ No subtasks found in database")
                results["corruption_summary"] = {
                    "total_corrupted": 0,
                    "orphaned_count": 0,
                    "user_mismatch_count": 0,
                    "valid_count": 0,
                    "corruption_percentage": 0
                }
                return results

            # Find subtasks with invalid parent_task_id references
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
                t.user_id as task_user_id
            FROM task_subtasks s
            LEFT JOIN tasks t ON s.task_id = t.id
            ORDER BY s.created_at DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                subtask_data = {
                    "subtask_id": row["subtask_id"],
                    "parent_task_id": row["parent_task_id"],
                    "subtask_title": row["subtask_title"],
                    "subtask_status": row["subtask_status"],
                    "subtask_user_id": row["subtask_user_id"],
                    "subtask_created_at": row["subtask_created_at"],
                    "task_exists": row["task_exists"] is not None,
                    "task_title": row["task_title"],
                    "task_user_id": row["task_user_id"]
                }

                if not subtask_data["task_exists"]:
                    # Orphaned subtask - parent task doesn't exist
                    results["orphaned_subtasks"].append(subtask_data)
                    print(f"🚨 ORPHANED: Subtask '{subtask_data['subtask_title']}' (ID: {subtask_data['subtask_id']}) "
                          f"references non-existent task {subtask_data['parent_task_id']}")

                elif subtask_data["subtask_user_id"] != subtask_data["task_user_id"]:
                    # User ID mismatch - potential data corruption
                    subtask_data["corruption_type"] = "user_id_mismatch"
                    results["corrupted_subtasks"].append(subtask_data)
                    print(f"⚠️ USER_MISMATCH: Subtask '{subtask_data['subtask_title']}' (ID: {subtask_data['subtask_id']}) "
                          f"user_id '{subtask_data['subtask_user_id']}' != task user_id '{subtask_data['task_user_id']}'")

                else:
                    # Valid subtask
                    results["valid_subtasks"] += 1

            # Generate summary
            total_corrupted = len(results["corrupted_subtasks"]) + len(results["orphaned_subtasks"])
            results["corruption_summary"] = {
                "total_corrupted": total_corrupted,
                "orphaned_count": len(results["orphaned_subtasks"]),
                "user_mismatch_count": len(results["corrupted_subtasks"]),
                "valid_count": results["valid_subtasks"],
                "corruption_percentage": round((total_corrupted / results["total_subtasks"]) * 100, 2) if results["total_subtasks"] > 0 else 0
            }

            print(f"\n📊 CORRUPTION ANALYSIS SUMMARY:")
            print(f"   Valid subtasks: {results['corruption_summary']['valid_count']}")
            print(f"   Orphaned subtasks: {results['corruption_summary']['orphaned_count']}")
            print(f"   User mismatch subtasks: {results['corruption_summary']['user_mismatch_count']}")
            print(f"   Total corrupted: {results['corruption_summary']['total_corrupted']}")
            print(f"   Corruption percentage: {results['corruption_summary']['corruption_percentage']}%")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        results["error"] = str(e)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        results["error"] = str(e)

    return results

def save_analysis_report(results: Dict[str, Any], output_file: str = None) -> str:
    """Save analysis results to a JSON report file"""
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = PROJECT_ROOT / "ai_docs" / "reports-status" / f"subtask_corruption_analysis_{timestamp}.json"

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"📄 Analysis report saved to: {output_file}")
    return str(output_file)

def main():
    """Main analysis function"""
    print("🔍 Starting subtask corruption analysis...")

    try:
        # Find database file
        db_path = find_database_file()

        # Perform analysis
        results = analyze_subtask_corruption(db_path)

        # Save report
        report_file = save_analysis_report(results)

        # Print final summary
        if "error" not in results:
            summary = results["corruption_summary"]
            if summary["total_corrupted"] > 0:
                print(f"\n🚨 CORRUPTION DETECTED:")
                print(f"   {summary['total_corrupted']} corrupted subtask records found")
                print(f"   Corruption rate: {summary['corruption_percentage']}%")
                print(f"   Immediate action required!")
            else:
                print(f"\n✅ NO CORRUPTION DETECTED:")
                print(f"   All {results['total_subtasks']} subtasks are valid")

        print(f"\n📋 Analysis completed. Report saved to: {report_file}")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()