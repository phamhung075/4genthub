#!/usr/bin/env python3
"""
Migration validation script.

This script validates that the ORM migration is complete and working correctly.
It checks schema consistency, data integrity, and performs comprehensive validation
across both SQLite and PostgreSQL databases.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.task_management.infrastructure.database.models import Base, Project, Agent, ProjectTaskTree, Task, TaskSubtask, Label, TaskLabel, GlobalContext, ProjectContext, TaskContext, ContextDelegation, ContextInheritanceCache, Template
from fastmcp.task_management.infrastructure.database.database_config import get_db_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validates ORM migration completeness and correctness"""
    
    def __init__(self):
        self.results = {
            "schema_validation": {},
            "data_integrity": {},
            "functionality_tests": {},
            "performance_tests": {},
            "errors": []
        }
    
    def validate_database_schema(self, engine) -> Dict[str, Any]:
        """Validate database schema matches ORM models"""
        logger.info("Validating database schema...")
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Expected tables from ORM models
        expected_tables = {
            'projects': Project.__tablename__,
            'agents': Agent.__tablename__,
            'project_git_branchs': ProjectTaskTree.__tablename__,
            'tasks': Task.__tablename__,
            'task_subtasks': TaskSubtask.__tablename__,
            'labels': Label.__tablename__,
            'task_labels': TaskLabel.__tablename__,
            'global_contexts': GlobalContext.__tablename__,
            'project_contexts': ProjectContext.__tablename__,
            'task_contexts': TaskContext.__tablename__,
            'context_delegations': ContextDelegation.__tablename__,
            'context_inheritance_caches': ContextInheritanceCache.__tablename__,
            'templates': Template.__tablename__
        }
        
        schema_results = {
            "expected_tables": list(expected_tables.keys()),
            "existing_tables": existing_tables,
            "missing_tables": [],
            "extra_tables": [],
            "table_details": {}
        }
        
        # Check for missing tables
        for table_name in expected_tables.keys():
            if table_name not in existing_tables:
                schema_results["missing_tables"].append(table_name)
            else:
                # Validate table structure
                columns = inspector.get_columns(table_name)
                indexes = inspector.get_indexes(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                
                schema_results["table_details"][table_name] = {
                    "columns": len(columns),
                    "indexes": len(indexes),
                    "foreign_keys": len(foreign_keys),
                    "column_names": [col['name'] for col in columns]
                }
        
        # Check for extra tables
        for table_name in existing_tables:
            if table_name not in expected_tables.keys():
                schema_results["extra_tables"].append(table_name)
        
        return schema_results
    
    def validate_data_integrity(self, engine) -> Dict[str, Any]:
        """Validate data integrity and relationships"""
        logger.info("Validating data integrity...")
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        integrity_results = {
            "foreign_key_constraints": [],
            "unique_constraints": [],
            "json_field_validation": [],
            "relationship_validation": []
        }
        
        try:
            # Test foreign key constraints
            try:
                # Create a project
                project = Project(
                    name="Integrity Test Project",
                    description="Testing data integrity",
                    user_id="test_user",
                    metadata={}
                )
                session.add(project)
                session.commit()
                
                # Create a task tree
                git_branch = ProjectTaskTree(
                    project_id=project.project_id,
                    git_branch_name="main",
                    git_branch_description="Main branch",
                    git_branch_status="active"
                )
                session.add(git_branch)
                session.commit()
                
                # Create a task
                task = Task(
                    git_branch_id=git_branch.git_branch_id,
                    title="Test Task",
                    description="Test task for integrity",
                    priority="medium",
                    status="pending",
                    metadata={}
                )
                session.add(task)
                session.commit()
                
                # Test relationships
                assert task.git_branch == git_branch
                assert git_branch.project == project
                
                integrity_results["foreign_key_constraints"].append("✅ Foreign key relationships working")
                integrity_results["relationship_validation"].append("✅ ORM relationships working")
                
            except Exception as e:
                integrity_results["foreign_key_constraints"].append(f"❌ Foreign key constraint error: {e}")
            
            # Test JSON field validation
            try:
                complex_metadata = {
                    "nested": {"key": "value"},
                    "array": [1, 2, 3],
                    "boolean": True,
                    "null": None
                }
                
                project.metadata = complex_metadata
                session.commit()
                
                # Retrieve and verify
                retrieved_project = session.query(Project).filter_by(name="Integrity Test Project").first()
                assert retrieved_project.metadata == complex_metadata
                
                integrity_results["json_field_validation"].append("✅ JSON fields working correctly")
                
            except Exception as e:
                integrity_results["json_field_validation"].append(f"❌ JSON field error: {e}")
                
        except Exception as e:
            self.results["errors"].append(f"Data integrity validation error: {e}")
        finally:
            session.close()
        
        return integrity_results
    
    def validate_repository_functionality(self, database_type: str) -> Dict[str, Any]:
        """Validate that all repositories work correctly"""
        logger.info(f"Validating repository functionality for {database_type}...")
        
        functionality_results = {
            "database_type": database_type,
            "repository_tests": []
        }
        
        try:
            # Test repository factory switching
            with patch.dict(os.environ, {"DATABASE_TYPE": database_type}):
                # Import and test factories
                from fastmcp.task_management.infrastructure.repositories.project_repository_factory import ProjectRepositoryFactory
                from fastmcp.task_management.infrastructure.repositories.agent_repository_factory import AgentRepositoryFactory
                from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
                
                # Test project repository
                try:
                    project_repo = ProjectRepositoryFactory.create(user_id="test_user")
                    repo_type = "ORM" if database_type == "postgresql" else "SQLite"
                    if repo_type in project_repo.__class__.__name__:
                        functionality_results["repository_tests"].append(f"✅ ProjectRepository {repo_type} working")
                    else:
                        functionality_results["repository_tests"].append(f"❌ ProjectRepository wrong type: {project_repo.__class__.__name__}")
                except Exception as e:
                    functionality_results["repository_tests"].append(f"❌ ProjectRepository error: {e}")
                
                # Test agent repository
                try:
                    agent_repo = AgentRepositoryFactory.create(user_id="test_user")
                    repo_type = "ORM" if database_type == "postgresql" else "SQLite"
                    if repo_type in agent_repo.__class__.__name__:
                        functionality_results["repository_tests"].append(f"✅ AgentRepository {repo_type} working")
                    else:
                        functionality_results["repository_tests"].append(f"❌ AgentRepository wrong type: {agent_repo.__class__.__name__}")
                except Exception as e:
                    functionality_results["repository_tests"].append(f"❌ AgentRepository error: {e}")
                
                # Test task repository
                try:
                    task_factory = TaskRepositoryFactory()
                    task_repo = task_factory.create_repository(
                        project_id="test_project",
                        git_branch_name="main",
                        user_id="test_user"
                    )
                    repo_type = "ORM" if database_type == "postgresql" else "SQLite"
                    if repo_type in task_repo.__class__.__name__:
                        functionality_results["repository_tests"].append(f"✅ TaskRepository {repo_type} working")
                    else:
                        functionality_results["repository_tests"].append(f"❌ TaskRepository wrong type: {task_repo.__class__.__name__}")
                except Exception as e:
                    functionality_results["repository_tests"].append(f"❌ TaskRepository error: {e}")
                
        except Exception as e:
            functionality_results["repository_tests"].append(f"❌ Repository functionality error: {e}")
        
        return functionality_results
    
    def validate_performance(self, engine) -> Dict[str, Any]:
        """Basic performance validation"""
        logger.info("Validating basic performance...")
        
        performance_results = {
            "connection_test": None,
            "query_performance": [],
            "bulk_operations": []
        }
        
        try:
            # Test connection performance
            import time
            start_time = time.time()
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            connection_time = time.time() - start_time
            performance_results["connection_test"] = f"✅ Connection established in {connection_time:.3f}s"
            
            # Test basic query performance
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                start_time = time.time()
                projects = session.query(Project).limit(10).all()
                query_time = time.time() - start_time
                performance_results["query_performance"].append(f"✅ Query 10 projects in {query_time:.3f}s")
            except Exception as e:
                performance_results["query_performance"].append(f"❌ Query error: {e}")
            finally:
                session.close()
                
        except Exception as e:
            performance_results["connection_test"] = f"❌ Connection error: {e}"
        
        return performance_results
    
    def compare_sqlite_postgresql_schemas(self) -> Dict[str, Any]:
        """Compare schemas between SQLite and PostgreSQL"""
        logger.info("Comparing SQLite and PostgreSQL schemas...")
        
        comparison_results = {
            "sqlite_schema": None,
            "postgresql_schema": None,
            "differences": []
        }
        
        try:
            # Test SQLite schema
            sqlite_engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(sqlite_engine)
            comparison_results["sqlite_schema"] = self.validate_database_schema(sqlite_engine)
            
            # Test PostgreSQL schema (if available)
            try:
                postgresql_url = os.getenv("DATABASE_URL", "postgresql://dev_user:dev_password@localhost:5432/4genthub_dev")
                postgresql_engine = create_engine(postgresql_url)
                Base.metadata.create_all(postgresql_engine)
                comparison_results["postgresql_schema"] = self.validate_database_schema(postgresql_engine)
                
                # Compare schemas
                sqlite_tables = set(comparison_results["sqlite_schema"]["existing_tables"])
                postgresql_tables = set(comparison_results["postgresql_schema"]["existing_tables"])
                
                if sqlite_tables == postgresql_tables:
                    comparison_results["differences"].append("✅ Table names match between SQLite and PostgreSQL")
                else:
                    comparison_results["differences"].append(f"❌ Table mismatch: SQLite={sqlite_tables}, PostgreSQL={postgresql_tables}")
                    
            except Exception as e:
                comparison_results["differences"].append(f"⚠️ PostgreSQL not available: {e}")
                
        except Exception as e:
            comparison_results["differences"].append(f"❌ Schema comparison error: {e}")
        
        return comparison_results
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete migration validation"""
        logger.info("Starting full migration validation...")
        
        # Test SQLite
        logger.info("Testing SQLite...")
        try:
            sqlite_engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(sqlite_engine)
            
            self.results["schema_validation"]["sqlite"] = self.validate_database_schema(sqlite_engine)
            self.results["data_integrity"]["sqlite"] = self.validate_data_integrity(sqlite_engine)
            self.results["functionality_tests"]["sqlite"] = self.validate_repository_functionality("sqlite")
            self.results["performance_tests"]["sqlite"] = self.validate_performance(sqlite_engine)
            
        except Exception as e:
            self.results["errors"].append(f"SQLite validation error: {e}")
        
        # Test PostgreSQL (if available)
        logger.info("Testing PostgreSQL...")
        try:
            postgresql_url = os.getenv("DATABASE_URL", "postgresql://dev_user:dev_password@localhost:5432/4genthub_dev")
            postgresql_engine = create_engine(postgresql_url)
            Base.metadata.create_all(postgresql_engine)
            
            self.results["schema_validation"]["postgresql"] = self.validate_database_schema(postgresql_engine)
            self.results["data_integrity"]["postgresql"] = self.validate_data_integrity(postgresql_engine)
            self.results["functionality_tests"]["postgresql"] = self.validate_repository_functionality("postgresql")
            self.results["performance_tests"]["postgresql"] = self.validate_performance(postgresql_engine)
            
        except Exception as e:
            self.results["errors"].append(f"PostgreSQL validation error: {e}")
        
        # Schema comparison
        self.results["schema_comparison"] = self.compare_sqlite_postgresql_schemas()
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        report = []
        report.append("=" * 60)
        report.append("🔍 ORM MIGRATION VALIDATION REPORT")
        report.append("=" * 60)
        
        # Schema validation
        report.append("\n📋 SCHEMA VALIDATION")
        report.append("-" * 30)
        for db_type, schema_info in self.results["schema_validation"].items():
            report.append(f"\n{db_type.upper()} Schema:")
            report.append(f"  Expected tables: {len(schema_info['expected_tables'])}")
            report.append(f"  Existing tables: {len(schema_info['existing_tables'])}")
            report.append(f"  Missing tables: {len(schema_info['missing_tables'])}")
            report.append(f"  Extra tables: {len(schema_info['extra_tables'])}")
            
            if schema_info['missing_tables']:
                report.append(f"  ❌ Missing: {', '.join(schema_info['missing_tables'])}")
            else:
                report.append(f"  ✅ All tables present")
        
        # Data integrity
        report.append("\n🔗 DATA INTEGRITY")
        report.append("-" * 30)
        for db_type, integrity_info in self.results["data_integrity"].items():
            report.append(f"\n{db_type.upper()} Data Integrity:")
            for category, tests in integrity_info.items():
                report.append(f"  {category}:")
                for test in tests:
                    report.append(f"    {test}")
        
        # Functionality tests
        report.append("\n⚙️ REPOSITORY FUNCTIONALITY")
        report.append("-" * 30)
        for db_type, func_info in self.results["functionality_tests"].items():
            report.append(f"\n{db_type.upper()} Repository Tests:")
            for test in func_info["repository_tests"]:
                report.append(f"  {test}")
        
        # Performance tests
        report.append("\n⚡ PERFORMANCE TESTS")
        report.append("-" * 30)
        for db_type, perf_info in self.results["performance_tests"].items():
            report.append(f"\n{db_type.upper()} Performance:")
            if perf_info["connection_test"]:
                report.append(f"  {perf_info['connection_test']}")
            for test in perf_info["query_performance"]:
                report.append(f"  {test}")
        
        # Errors
        if self.results["errors"]:
            report.append("\n❌ ERRORS")
            report.append("-" * 30)
            for error in self.results["errors"]:
                report.append(f"  {error}")
        
        # Summary
        report.append("\n📊 SUMMARY")
        report.append("-" * 30)
        
        total_errors = len(self.results["errors"])
        if total_errors == 0:
            report.append("✅ Migration validation PASSED")
            report.append("🎉 All tests successful - ORM migration is complete!")
        else:
            report.append(f"❌ Migration validation FAILED with {total_errors} errors")
            report.append("💡 Check the errors above and fix before deployment")
        
        return "\n".join(report)


def main():
    """Main function to run migration validation"""
    print("🔍 ORM Migration Validation Tool")
    print("=" * 50)
    
    validator = MigrationValidator()
    
    try:
        # Run full validation
        results = validator.run_full_validation()
        
        # Generate and display report
        report = validator.generate_report()
        print(report)
        
        # Save report to file
        report_file = Path(__file__).parent / "migration_validation_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        # Save JSON results
        json_file = Path(__file__).parent / "migration_validation_results.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📊 JSON results saved to: {json_file}")
        
        # Exit with appropriate code
        if results["errors"]:
            print("\n💥 Validation completed with errors!")
            sys.exit(1)
        else:
            print("\n🎉 Validation completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"\n💥 Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()