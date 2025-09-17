#!/usr/bin/env python3
"""
Comprehensive script to update all code for user isolation migration.
This script identifies all files that need updates and creates a checklist.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set

# Base paths
BASE_PATH = Path(__file__).parent.parent
SRC_PATH = BASE_PATH / "src"
TEST_PATH = BASE_PATH / "src" / "tests"
FRONTEND_PATH = BASE_PATH.parent / "agenthub-frontend"

def find_files_to_update() -> Dict[str, List[str]]:
    """Find all files that need updating for user isolation."""
    
    files_to_update = {
        "repositories": [],
        "services": [],
        "routes": [],
        "models": [],
        "schemas": [],
        "tests": [],
        "frontend": []
    }
    
    # Find repository files
    repo_path = SRC_PATH / "fastmcp" / "task_management" / "infrastructure" / "repositories"
    if repo_path.exists():
        for file in repo_path.rglob("*.py"):
            if "repository" in file.name.lower() and not file.name.startswith("__"):
                files_to_update["repositories"].append(str(file))
    
    # Find service files
    service_path = SRC_PATH / "fastmcp" / "task_management" / "application" / "services"
    if service_path.exists():
        for file in service_path.rglob("*.py"):
            if "service" in file.name.lower() and not file.name.startswith("__"):
                files_to_update["services"].append(str(file))
    
    # Find route files
    routes_path = SRC_PATH / "fastmcp" / "server" / "routes"
    if routes_path.exists():
        for file in routes_path.rglob("*.py"):
            if "route" in file.name.lower() and not file.name.startswith("__"):
                files_to_update["routes"].append(str(file))
    
    # Find model files
    models_path = SRC_PATH / "fastmcp" / "task_management" / "infrastructure" / "database" / "models"
    if models_path.exists():
        for file in models_path.rglob("*.py"):
            if not file.name.startswith("__"):
                files_to_update["models"].append(str(file))
    
    # Find schema files
    schema_paths = [
        SRC_PATH / "fastmcp" / "task_management" / "domain" / "entities",
        SRC_PATH / "fastmcp" / "task_management" / "infrastructure" / "schemas"
    ]
    for schema_path in schema_paths:
        if schema_path.exists():
            for file in schema_path.rglob("*.py"):
                if not file.name.startswith("__"):
                    files_to_update["schemas"].append(str(file))
    
    # Find test files
    if TEST_PATH.exists():
        for file in TEST_PATH.rglob("test_*.py"):
            files_to_update["tests"].append(str(file))
    
    # Find frontend files
    if FRONTEND_PATH.exists():
        frontend_src = FRONTEND_PATH / "src"
        if frontend_src.exists():
            # API service files
            services_dir = frontend_src / "services"
            if services_dir.exists():
                for file in services_dir.rglob("*.ts"):
                    files_to_update["frontend"].append(str(file))
            
            # Component files that might need updates
            components_dir = frontend_src / "components"
            if components_dir.exists():
                for file in components_dir.rglob("*.tsx"):
                    if any(keyword in file.name.lower() for keyword in ["task", "project", "context"]):
                        files_to_update["frontend"].append(str(file))
    
    return files_to_update

def check_file_needs_update(filepath: str) -> Dict[str, bool]:
    """Check what updates a file needs."""
    needs = {
        "user_id_field": False,
        "user_filter": False,
        "auth_check": False,
        "test_coverage": False
    }
    
    if not os.path.exists(filepath):
        return needs
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for user_id field/parameter
    if "user_id" not in content:
        needs["user_id_field"] = True
    
    # Check for user filtering in repositories
    if "repository" in filepath.lower():
        if "apply_user_filter" not in content and "BaseUserScopedRepository" not in content:
            needs["user_filter"] = True
    
    # Check for auth in routes
    if "route" in filepath.lower():
        if "current_user" not in content and "get_current_user" not in content:
            needs["auth_check"] = True
    
    # Check for test coverage
    if "test_" in os.path.basename(filepath):
        if "user_id" not in content:
            needs["test_coverage"] = True
    
    return needs

def generate_update_report(files_to_update: Dict[str, List[str]]) -> str:
    """Generate a detailed report of required updates."""
    report = []
    report.append("=" * 80)
    report.append("USER ISOLATION MIGRATION - CODE UPDATE REPORT")
    report.append("=" * 80)
    report.append("")
    
    total_files = sum(len(files) for files in files_to_update.values())
    report.append(f"Total files to review: {total_files}")
    report.append("")
    
    for category, files in files_to_update.items():
        report.append(f"\n{category.upper()} ({len(files)} files)")
        report.append("-" * 40)
        
        for filepath in sorted(files):
            relative_path = filepath.replace(str(BASE_PATH), "").replace(str(BASE_PATH.parent), "")
            needs = check_file_needs_update(filepath)
            
            updates_needed = [k for k, v in needs.items() if v]
            if updates_needed:
                report.append(f"❌ {relative_path}")
                for update in updates_needed:
                    report.append(f"   - Needs: {update}")
            else:
                report.append(f"✅ {relative_path} (may already be updated)")
    
    report.append("")
    report.append("=" * 80)
    report.append("IMPLEMENTATION CHECKLIST (Follow TDD)")
    report.append("=" * 80)
    report.append("")
    
    checklist = [
        "PHASE 1: Repository Layer (Foundation)",
        "  [ ] Write tests for BaseUserScopedRepository",
        "  [ ] Implement BaseUserScopedRepository",
        "  [ ] Write tests for TaskRepository with user_id",
        "  [ ] Update TaskRepository to use BaseUserScopedRepository",
        "  [ ] Write tests for ProjectRepository with user_id",
        "  [ ] Update ProjectRepository",
        "  [ ] Write tests for Context repositories (all 4 levels)",
        "  [ ] Update all Context repositories",
        "  [ ] Write tests for remaining repositories",
        "  [ ] Update all remaining repositories",
        "",
        "PHASE 2: Service Layer (Business Logic)",
        "  [ ] Write tests for user context in TaskService",
        "  [ ] Update TaskService to accept user_id",
        "  [ ] Write tests for ProjectService",
        "  [ ] Update ProjectService",
        "  [ ] Write tests for ContextService",
        "  [ ] Update ContextService for all levels",
        "  [ ] Write tests for remaining services",
        "  [ ] Update all remaining services",
        "",
        "PHASE 3: API Layer (Authentication)",
        "  [ ] Write tests for JWT authentication middleware",
        "  [ ] Implement authentication middleware",
        "  [ ] Write tests for user extraction from token",
        "  [ ] Implement get_current_user dependency",
        "  [ ] Write tests for task routes with auth",
        "  [ ] Update task routes",
        "  [ ] Write tests for all other routes",
        "  [ ] Update all routes with authentication",
        "",
        "PHASE 4: Database Models",
        "  [ ] Write tests for model user_id fields",
        "  [ ] Update all SQLAlchemy models",
        "  [ ] Write tests for schema validation",
        "  [ ] Update all Pydantic schemas",
        "  [ ] Verify foreign key constraints",
        "",
        "PHASE 5: Frontend (React/TypeScript)",
        "  [ ] Write tests for API client auth headers",
        "  [ ] Update API client to include JWT token",
        "  [ ] Write tests for auth context/provider",
        "  [ ] Implement AuthContext and AuthProvider",
        "  [ ] Write tests for protected routes",
        "  [ ] Implement route protection",
        "  [ ] Write tests for user-scoped components",
        "  [ ] Update all components to handle user data",
        "",
        "PHASE 6: Integration Testing",
        "  [ ] Write multi-user scenario tests",
        "  [ ] Write data isolation tests",
        "  [ ] Write permission boundary tests",
        "  [ ] Write performance tests with filtering",
        "  [ ] Write E2E authentication flow tests",
        "",
        "PHASE 7: Migration Execution",
        "  [ ] Run migration on test database",
        "  [ ] Verify all tables have user_id",
        "  [ ] Check data integrity",
        "  [ ] Run on staging environment",
        "  [ ] Performance testing on staging",
        "  [ ] Run on production",
        "  [ ] Post-migration verification",
        "",
        "PHASE 8: Documentation",
        "  [ ] Update API documentation",
        "  [ ] Update developer guide",
        "  [ ] Create migration runbook",
        "  [ ] Update README files",
        "  [ ] Create troubleshooting guide"
    ]
    
    report.extend(checklist)
    
    return "\n".join(report)

def create_test_templates():
    """Create test template files for TDD."""
    templates_dir = BASE_PATH / "scripts" / "test_templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Repository test template
    repo_test = '''"""Test template for repository with user isolation."""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

class TestRepositoryUserIsolation:
    """Test repository properly filters by user_id."""
    
    def test_create_with_user_id(self):
        """Test that created entities include user_id."""
        # Arrange
        user_id = str(uuid4())
        repository = MyRepository(user_id=user_id)
        
        # Act
        entity = repository.create(data={"name": "test"})
        
        # Assert
        assert entity.user_id == user_id
    
    def test_get_filters_by_user(self):
        """Test that get operations filter by user_id."""
        # Arrange
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        repository = MyRepository(user_id=user_id)
        
        # Create entities for both users
        entity1 = repository.create(data={"name": "user1_item"})
        
        # Switch to other user
        other_repo = MyRepository(user_id=other_user_id)
        entity2 = other_repo.create(data={"name": "user2_item"})
        
        # Act
        user1_items = repository.get_all()
        
        # Assert
        assert len(user1_items) == 1
        assert user1_items[0].user_id == user_id
    
    def test_update_prevents_cross_user_access(self):
        """Test that users cannot update other users' data."""
        # Test implementation here
        pass
    
    def test_delete_prevents_cross_user_access(self):
        """Test that users cannot delete other users' data."""
        # Test implementation here
        pass
'''
    
    with open(templates_dir / "test_repository_template.py", "w") as f:
        f.write(repo_test)
    
    # Service test template
    service_test = '''"""Test template for service with user context."""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

class TestServiceUserContext:
    """Test service properly handles user context."""
    
    def test_service_passes_user_id_to_repository(self):
        """Test that service passes user_id to repository."""
        # Arrange
        user_id = str(uuid4())
        mock_repo = Mock()
        service = MyService(repository=mock_repo, user_id=user_id)
        
        # Act
        service.create_item(data={"name": "test"})
        
        # Assert
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args
        assert "user_id" in call_args.kwargs or user_id in call_args.args
    
    def test_service_validates_user_context(self):
        """Test that service validates user context."""
        # Test implementation here
        pass
'''
    
    with open(templates_dir / "test_service_template.py", "w") as f:
        f.write(service_test)
    
    # Route test template
    route_test = '''"""Test template for routes with authentication."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from uuid import uuid4

class TestRouteAuthentication:
    """Test routes properly handle authentication."""
    
    def test_route_requires_authentication(self, client: TestClient):
        """Test that route requires valid JWT token."""
        # Act - no auth header
        response = client.get("/api/items")
        
        # Assert
        assert response.status_code == 401
    
    def test_route_extracts_user_from_token(self, client: TestClient):
        """Test that route extracts user_id from JWT."""
        # Arrange
        user_id = str(uuid4())
        token = create_test_jwt(user_id=user_id)
        
        # Act
        response = client.get(
            "/api/items",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        # Verify service was called with correct user_id
    
    def test_route_prevents_cross_user_access(self, client: TestClient):
        """Test that users cannot access other users' data."""
        # Test implementation here
        pass
'''
    
    with open(templates_dir / "test_route_template.py", "w") as f:
        f.write(route_test)
    
    print(f"✅ Test templates created in {templates_dir}")

def main():
    """Main execution function."""
    print("Analyzing codebase for user isolation updates...")
    print("")
    
    # Find all files that need updating
    files_to_update = find_files_to_update()
    
    # Generate report
    report = generate_update_report(files_to_update)
    
    # Save report
    report_path = BASE_PATH / "USER_ISOLATION_UPDATE_REPORT.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    print(report)
    print("")
    print(f"📄 Report saved to: {report_path}")
    print("")
    
    # Create test templates
    create_test_templates()
    print("")
    
    print("🚀 NEXT STEPS:")
    print("1. Start with PHASE 1 (Repository Layer)")
    print("2. For each file:")
    print("   a. Write tests FIRST (use templates as guide)")
    print("   b. Run tests (should fail)")
    print("   c. Implement the changes")
    print("   d. Run tests again (should pass)")
    print("3. Move to next phase only after current phase is complete")
    print("")
    print("⚠️  CRITICAL: This migration affects data security.")
    print("   Ensure thorough testing at each step!")

if __name__ == "__main__":
    main()