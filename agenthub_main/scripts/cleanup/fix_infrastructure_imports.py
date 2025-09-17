#!/usr/bin/env python3
"""
Automated Fix for DDD Infrastructure Import Violations

This script fixes common infrastructure import patterns in the application layer
by replacing them with domain interface imports.
"""

import os
import re
import glob
from pathlib import Path

# Define the base path
BASE_PATH = Path(__file__).parent / "agenthub_main/src/fastmcp/task_management/application"

# Define import replacements
IMPORT_REPLACEMENTS = [
    # Event store imports
    (
        r'from \.\.\.infrastructure\.event_store import (.+)',
        r'from ...domain.interfaces.event_store import \1'
    ),
    # Notification service imports
    (
        r'from \.\.\.infrastructure\.notification_service import (.+)',
        r'from ...domain.interfaces.notification_service import \1'
    ),
    # Cache imports
    (
        r'from \.\.\.infrastructure\.cache\.context_cache import (.+)',
        r'from ...domain.interfaces.cache_service import ICacheService'
    ),
    # Repository factory imports
    (
        r'from \.\.\.infrastructure\.repositories\.repository_factory import (.+)',
        r'from ...domain.interfaces.repository_factory import IRepositoryFactory'
    ),
    (
        r'from \.\.\.infrastructure\.repositories\.task_repository_factory import (.+)',
        r'from ...domain.interfaces.repository_factory import ITaskRepositoryFactory'
    ),
    (
        r'from \.\.\.infrastructure\.repositories\.project_repository_factory import (.+)',
        r'from ...domain.interfaces.repository_factory import IProjectRepositoryFactory'
    ),
    (
        r'from \.\.\.infrastructure\.repositories\.git_branch_repository_factory import (.+)',
        r'from ...domain.interfaces.repository_factory import IGitBranchRepositoryFactory'
    ),
    (
        r'from \.\.\.infrastructure\.repositories\.task_context_repository import (.+)',
        r'from ...domain.interfaces.repository_factory import IContextRepository'
    ),
    # Event bus imports
    (
        r'from \.\.\.infrastructure\.event_bus import (.+)',
        r'from ...domain.interfaces.event_bus import \1'
    ),
    # Database config imports
    (
        r'from \.\.\.infrastructure\.database\.database_config import (.+)',
        r'from ...domain.interfaces.database_session import IDatabaseSessionFactory'
    ),
    # Database models imports (these need special handling)
    (
        r'from \.\.\.infrastructure\.database\.models import (.+)',
        r'# TODO: Replace direct model import with domain entity: \1'
    ),
    # Logging imports
    (
        r'from \.\.\.infrastructure\.logging import (.+)',
        r'from ...domain.interfaces.logging_service import ILoggingService'
    ),
    # Monitoring imports
    (
        r'from \.\.\.infrastructure\.monitoring\.process_monitor import (.+)',
        r'from ...domain.interfaces.monitoring_service import IProcessMonitor'
    ),
    # Validation imports
    (
        r'from \.\.\.infrastructure\.validation\.document_validator import (.+)',
        r'from ...domain.interfaces.validation_service import IDocumentValidator'
    ),
    # Utility imports
    (
        r'from \.\.\.infrastructure\.utilities\.path_resolver import (.+)',
        r'from ...domain.interfaces.utility_service import IPathResolver'
    ),
    (
        r'from \.\.\.infrastructure\.services\.agent_doc_generator import (.+)',
        r'from ...domain.interfaces.utility_service import IAgentDocGenerator'
    ),
]

# Code block replacements for common patterns
CODE_REPLACEMENTS = [
    # EventStore() -> DomainServiceFactory.get_event_store()
    (
        r'EventStore\(\)',
        r'DomainServiceFactory.get_event_store()'
    ),
    # ContextCache() -> DomainServiceFactory.get_cache_service()
    (
        r'ContextCache\(\)',
        r'DomainServiceFactory.get_cache_service()'
    ),
    # RepositoryFactory() -> DomainServiceFactory.get_repository_factory()
    (
        r'RepositoryFactory\(\)',
        r'DomainServiceFactory.get_repository_factory()'
    ),
    # get_db_session() -> DomainServiceFactory.get_database_session_factory().create_session()
    (
        r'get_db_session\(\)',
        r'DomainServiceFactory.get_database_session_factory().create_session()'
    ),
]

def add_domain_service_import(content: str) -> str:
    """Add DomainServiceFactory import if needed"""
    if 'DomainServiceFactory' in content and 'from ..services.domain_service_factory import DomainServiceFactory' not in content:
        # Find the last import line and add after it
        lines = content.split('\n')
        import_line_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                import_line_idx = i
        
        # Insert the import after the last import
        lines.insert(import_line_idx + 1, 'from ..services.domain_service_factory import DomainServiceFactory')
        content = '\n'.join(lines)
    
    return content

def fix_file(file_path: Path) -> bool:
    """Fix infrastructure imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        modified = False
        
        # Apply import replacements
        for pattern, replacement in IMPORT_REPLACEMENTS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                modified = True
                content = new_content
        
        # Apply code replacements
        for pattern, replacement in CODE_REPLACEMENTS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                modified = True
                content = new_content
        
        # Add domain service import if needed
        if modified:
            content = add_domain_service_import(content)
        
        # Write back if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"⏭️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all files"""
    print("🔧 Starting DDD Infrastructure Import Fixes...")
    
    if not BASE_PATH.exists():
        print(f"❌ Application layer path does not exist: {BASE_PATH}")
        return
    
    # Find all Python files in application layer
    python_files = list(BASE_PATH.rglob("*.py"))
    print(f"📁 Found {len(python_files)} Python files in application layer")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_file(file_path):
            fixed_count += 1
    
    print(f"\n✨ Completed! Fixed {fixed_count} files out of {len(python_files)} total files.")
    print("\n🧪 Run the DDD compliance test to verify fixes:")
    print("cd agenthub_main/src && python -m pytest tests/architecture/test_factory_layer_compliance.py::TestFactoryLayerCompliance::test_no_direct_infrastructure_imports_in_application -v")

if __name__ == "__main__":
    main()