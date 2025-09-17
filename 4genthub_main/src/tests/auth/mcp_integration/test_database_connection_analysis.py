from typing import List
"""
Database Connection Analysis Tests

This module contains tests to analyze which repository classes are using
SQLite instead of Supabase and identify the root causes.
"""

import pytest
import os
import logging
from typing import Dict, List, Any
from contextlib import contextmanager
from unittest.mock import Mock, patch, MagicMock

# Import the database configuration and repository classes
from fastmcp.task_management.infrastructure.database.database_config import get_db_config, DatabaseConfig
from fastmcp.task_management.infrastructure.repositories.global_context_repository import GlobalContextRepository
# Note: GlobalContextRepository is already user-scoped internally
# from fastmcp.task_management.infrastructure.repositories.global_context_repository_user_scoped import (
#     GlobalContextRepository as UserScopedGlobalContextRepository
# )
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
from fastmcp.task_management.infrastructure.repositories.base_orm_repository import BaseORMRepository
from fastmcp.task_management.infrastructure.database.supabase_config import get_supabase_config, is_supabase_configured

logger = logging.getLogger(__name__)


class DatabaseConnectionAnalyzer:
    """Analyzer to identify database connection issues in repositories."""
    
    def __init__(self):
        self.analysis_results = {}
        
    def analyze_database_config(self) -> Dict[str, Any]:
        """Analyze the database configuration."""
        results = {
            "config_source": "database_config.py",
            "issues": [],
            "database_type": None,
            "database_url": None,
            "session_factory": None
        }
        
        try:
            # Check environment variables
            db_type = os.getenv("DATABASE_TYPE", "supabase")
            database_url = os.getenv("DATABASE_URL")
            supabase_url = os.getenv("SUPABASE_URL")
            
            results["database_type"] = db_type
            results["env_database_url"] = database_url
            results["env_supabase_url"] = supabase_url
            
            # Try to get database configuration
            try:
                db_config = get_db_config()
                results["config_type"] = db_config.database_type
                results["config_url"] = db_config.database_url
                results["engine_type"] = str(type(db_config.engine)) if db_config.engine else None
                results["session_factory"] = str(type(db_config.SessionLocal)) if db_config.SessionLocal else None
                
                if db_config.engine:
                    engine_url = str(db_config.engine.url)
                    results["actual_engine_url"] = engine_url
                    
                    # Check if using SQLite when should be using PostgreSQL
                    if db_type.lower() == "supabase" and "sqlite" in engine_url.lower():
                        results["issues"].append({
                            "type": "wrong_database",
                            "message": f"Configuration says '{db_type}' but engine URL is SQLite: {engine_url}",
                            "severity": "CRITICAL"
                        })
                    
                    # Check if using PostgreSQL correctly
                    if db_type.lower() == "supabase" and "postgresql" in engine_url.lower():
                        results["status"] = "CORRECT - Using PostgreSQL for Supabase"
                    elif "sqlite" in engine_url.lower():
                        results["status"] = "Using SQLite"
                    else:
                        results["status"] = "Using PostgreSQL"
                        
            except Exception as e:
                results["issues"].append({
                    "type": "config_error",
                    "message": f"Failed to get database config: {str(e)}",
                    "severity": "CRITICAL"
                })
                
            # Check Supabase configuration
            try:
                is_supabase_config = is_supabase_configured()
                results["supabase_configured"] = is_supabase_config
                
                if db_type.lower() == "supabase" and not is_supabase_config:
                    results["issues"].append({
                        "type": "supabase_not_configured",
                        "message": "DATABASE_TYPE=supabase but Supabase environment variables not set",
                        "severity": "CRITICAL"
                    })
                    
            except Exception as e:
                results["issues"].append({
                    "type": "supabase_check_error", 
                    "message": f"Failed to check Supabase config: {str(e)}",
                    "severity": "ERROR"
                })
                
        except Exception as e:
            results["issues"].append({
                "type": "analysis_error",
                "message": f"Failed to analyze database config: {str(e)}",
                "severity": "CRITICAL"
            })
            
        return results
    
    def analyze_repository_session_usage(self, repo_class, repo_name: str) -> Dict[str, Any]:
        """Analyze how a repository class gets its database sessions."""
        results = {
            "repository": repo_name,
            "class_name": repo_class.__name__,
            "issues": [],
            "session_source": None,
            "uses_correct_database": None
        }
        
        try:
            # Check if repository inherits from correct base classes
            base_classes = [cls.__name__ for cls in repo_class.__mro__]
            results["base_classes"] = base_classes
            
            # Check if it uses BaseORMRepository
            if "BaseORMRepository" in base_classes:
                results["uses_base_orm"] = True
                results["session_source"] = "BaseORMRepository.get_db_session() -> get_session() from database_config"
            else:
                results["uses_base_orm"] = False
                
            # Check if it uses BaseUserScopedRepository  
            if "BaseUserScopedRepository" in base_classes:
                results["uses_user_scoped"] = True
            else:
                results["uses_user_scoped"] = False
                
            # Check if it has a custom session factory
            if hasattr(repo_class, '__init__'):
                init_method = repo_class.__init__
                import inspect
                sig = inspect.signature(init_method)
                if 'session_factory' in sig.parameters:
                    results["accepts_session_factory"] = True
                    results["session_source"] = "Custom session_factory parameter"
                else:
                    results["accepts_session_factory"] = False
                    
            # Check methods that get database sessions
            session_methods = []
            for method_name in dir(repo_class):
                if 'session' in method_name.lower():
                    session_methods.append(method_name)
            results["session_methods"] = session_methods
            
            # Look for specific session acquisition patterns
            if hasattr(repo_class, 'get_db_session'):
                results["has_get_db_session"] = True
            else:
                results["has_get_db_session"] = False
                
            # Check for potential issues
            if repo_name == "global_context" and results["accepts_session_factory"]:
                results["issues"].append({
                    "type": "potential_sqlite_usage",
                    "message": f"{repo_name} accepts session_factory which might bypass Supabase config",
                    "severity": "WARNING"
                })
                
        except Exception as e:
            results["issues"].append({
                "type": "analysis_error",
                "message": f"Failed to analyze {repo_name}: {str(e)}",
                "severity": "ERROR"
            })
            
        return results
    
    def analyze_all_repositories(self) -> Dict[str, Any]:
        """Analyze all repository classes."""
        repositories_to_check = {
            "global_context": GlobalContextRepository,
            "global_context_user_scoped": GlobalContextRepository,
            "task_repository": ORMTaskRepository,
            "project_repository": ORMProjectRepository,
            "base_orm": BaseORMRepository
        }
        
        results = {
            "database_config": self.analyze_database_config(),
            "repositories": {}
        }
        
        for repo_name, repo_class in repositories_to_check.items():
            results["repositories"][repo_name] = self.analyze_repository_session_usage(repo_class, repo_name)
            
        return results
    
    def identify_root_causes(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify root causes of database connection issues."""
        root_causes = []
        
        # Check database config issues
        db_config = analysis["database_config"]
        for issue in db_config.get("issues", []):
            if issue["severity"] == "CRITICAL":
                root_causes.append({
                    "category": "Database Configuration",
                    "cause": issue["message"],
                    "impact": "HIGH",
                    "affected_components": "All repositories"
                })
        
        # Check repository-specific issues
        repos = analysis["repositories"]
        for repo_name, repo_info in repos.items():
            for issue in repo_info.get("issues", []):
                if issue["severity"] in ["CRITICAL", "WARNING"]:
                    root_causes.append({
                        "category": "Repository Implementation", 
                        "cause": f"{repo_name}: {issue['message']}",
                        "impact": "MEDIUM" if issue["severity"] == "WARNING" else "HIGH",
                        "affected_components": repo_name
                    })
        
        return root_causes
    
    def generate_fix_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations to fix the issues."""
        recommendations = []
        
        db_config = analysis["database_config"]
        
        # Check if Supabase should be used but isn't configured
        if (db_config.get("database_type") == "supabase" and 
            not db_config.get("supabase_configured")):
            recommendations.append({
                "priority": "HIGH",
                "category": "Environment Configuration",
                "action": "Set Supabase environment variables",
                "details": [
                    "Set SUPABASE_URL to your project URL",
                    "Set SUPABASE_ANON_KEY from dashboard",
                    "Set SUPABASE_DB_PASSWORD for direct connection",
                    "Alternatively, set SUPABASE_DATABASE_URL directly"
                ],
                "files_to_modify": [".env"]
            })
        
        # Check if wrong database is being used
        for issue in db_config.get("issues", []):
            if issue["type"] == "wrong_database":
                recommendations.append({
                    "priority": "CRITICAL",
                    "category": "Database Connection",
                    "action": "Fix database configuration to use Supabase",
                    "details": [
                        "Verify DATABASE_TYPE environment variable is set to 'supabase'",
                        "Ensure Supabase environment variables are correctly configured", 
                        "Check that database_config.py is reading environment correctly",
                        "Verify no test mode or SQLite fallback is being used"
                    ],
                    "files_to_modify": [
                        "4genthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py"
                    ]
                })
        
        # Repository-specific recommendations
        repos = analysis["repositories"]
        global_context_issues = repos.get("global_context", {}).get("issues", [])
        
        if any(issue["type"] == "potential_sqlite_usage" for issue in global_context_issues):
            recommendations.append({
                "priority": "HIGH", 
                "category": "Repository Implementation",
                "action": "Fix global context repository to use correct database",
                "details": [
                    "Ensure global context repository uses get_session() from database_config",
                    "Remove any custom session_factory that might bypass Supabase",
                    "Verify user-scoped repository inherits correct database configuration"
                ],
                "files_to_modify": [
                    "4genthub_main/src/fastmcp/task_management/infrastructure/repositories/global_context_repository.py",
                    "4genthub_main/src/fastmcp/task_management/infrastructure/repositories/global_context_repository_user_scoped.py"
                ]
            })
        
        return recommendations


class TestDatabaseConnectionAnalysis:
    """Test class for database connection analysis."""
    
    def setup_method(self):
        """Set up test environment."""
        self.analyzer = DatabaseConnectionAnalyzer()
    
    def test_database_config_analysis(self):
        """Test analysis of database configuration."""
        results = self.analyzer.analyze_database_config()
        
        assert "database_type" in results
        assert "issues" in results
        
        print(f"Database Config Analysis:")
        print(f"  Type: {results.get('database_type')}")
        print(f"  Status: {results.get('status')}")
        print(f"  Engine URL: {results.get('actual_engine_url')}")
        print(f"  Issues: {len(results.get('issues', []))}")
        
        for issue in results.get("issues", []):
            print(f"    - {issue['severity']}: {issue['message']}")
    
    def test_repository_analysis(self):
        """Test analysis of repository classes."""
        results = self.analyzer.analyze_all_repositories()
        
        assert "database_config" in results
        assert "repositories" in results
        
        print(f"\nRepository Analysis:")
        for repo_name, repo_info in results["repositories"].items():
            print(f"  {repo_name}:")
            print(f"    Class: {repo_info.get('class_name')}")
            print(f"    Session source: {repo_info.get('session_source')}")
            print(f"    Uses BaseORM: {repo_info.get('uses_base_orm')}")
            print(f"    Issues: {len(repo_info.get('issues', []))}")
            
            for issue in repo_info.get("issues", []):
                print(f"      - {issue['severity']}: {issue['message']}")
    
    def test_root_cause_analysis(self):
        """Test identification of root causes."""
        analysis = self.analyzer.analyze_all_repositories()
        root_causes = self.analyzer.identify_root_causes(analysis)
        
        print(f"\nRoot Causes Identified: {len(root_causes)}")
        for i, cause in enumerate(root_causes, 1):
            print(f"  {i}. {cause['category']}: {cause['cause']}")
            print(f"     Impact: {cause['impact']}, Affects: {cause['affected_components']}")
    
    def test_fix_recommendations(self):
        """Test generation of fix recommendations."""
        analysis = self.analyzer.analyze_all_repositories()
        recommendations = self.analyzer.generate_fix_recommendations(analysis)
        
        print(f"\nFix Recommendations: {len(recommendations)}")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec['category']} [{rec['priority']}]: {rec['action']}")
            print(f"     Files to modify: {rec['files_to_modify']}")
            for detail in rec['details']:
                print(f"       - {detail}")
    
    def test_complete_analysis_report(self):
        """Generate a complete analysis report."""
        analysis = self.analyzer.analyze_all_repositories()
        root_causes = self.analyzer.identify_root_causes(analysis)
        recommendations = self.analyzer.generate_fix_recommendations(analysis)
        
        print(f"\n" + "="*80)
        print(f"COMPLETE DATABASE CONNECTION ANALYSIS REPORT")
        print(f"="*80)
        
        print(f"\n1. EXECUTIVE SUMMARY")
        print(f"   - Database Type: {analysis['database_config'].get('database_type')}")
        print(f"   - Critical Issues: {sum(1 for cause in root_causes if cause['impact'] == 'HIGH')}")
        print(f"   - Repositories Analyzed: {len(analysis['repositories'])}")
        print(f"   - Fix Recommendations: {len(recommendations)}")
        
        print(f"\n2. DATABASE CONFIGURATION STATUS")
        db_config = analysis["database_config"]
        print(f"   - Configuration Type: {db_config.get('config_type')}")
        print(f"   - Engine URL: {db_config.get('actual_engine_url')}")
        print(f"   - Supabase Configured: {db_config.get('supabase_configured')}")
        print(f"   - Status: {db_config.get('status')}")
        
        print(f"\n3. REPOSITORY ANALYSIS")
        for repo_name, repo_info in analysis["repositories"].items():
            status = "✅ OK" if not repo_info.get("issues") else "❌ ISSUES"
            print(f"   - {repo_name}: {status}")
            if repo_info.get("issues"):
                for issue in repo_info["issues"]:
                    print(f"     * {issue['severity']}: {issue['message']}")
        
        print(f"\n4. ROOT CAUSES")
        for i, cause in enumerate(root_causes, 1):
            print(f"   {i}. [{cause['impact']}] {cause['cause']}")
        
        print(f"\n5. RECOMMENDATIONS")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. [{rec['priority']}] {rec['action']}")
        
        # Assert that we have meaningful analysis
        assert len(analysis["repositories"]) > 0, "Should analyze at least one repository"
        assert "database_config" in analysis, "Should include database config analysis"


if __name__ == "__main__":
    # Run the analysis directly
    import logging
    logging.basicConfig(level=logging.INFO)
    
    analyzer = DatabaseConnectionAnalyzer()
    test = TestDatabaseConnectionAnalysis()
    test.setup_method()
    
    print("Running database connection analysis...")
    
    try:
        test.test_complete_analysis_report()
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()