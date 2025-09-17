#!/usr/bin/env python3
"""
Script to update remaining service classes with user context support.

This script analyzes service files and adds user context propagation
following the established pattern.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

# Service files that need updating
SERVICES_TO_UPDATE = [
    "vision_analytics_service.py",
    "work_distribution_service.py",
    "dependencie_application_service.py",
    "rule_application_service.py",
    "feature_flag_service.py",
    "compliance_service.py",
    "dependency_resolver_service.py",
    "audit_service.py",
    "task_progress_service.py",
    "task_context_sync_service.py",
    "context_validation_service.py",
    "context_inheritance_service.py",
    "context_delegation_service.py",
    "context_cache_service.py",
    "git_branch_service.py",
    "project_management_service.py",
    "response_enrichment_service.py",
    "progress_tracking_service.py",
    "hint_generation_service.py",
    "workflow_analysis_service.py",
    "progressive_enforcement_service.py",
    "parameter_enforcement_service.py",
    "automated_context_sync_service.py",
    "unified_context_service.py"
]

SERVICE_DIR = Path("src/fastmcp/task_management/application/services")

def analyze_service_file(filepath: Path) -> dict:
    """Analyze a service file to determine what updates are needed."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    analysis = {
        'filepath': filepath,
        'has_user_id': 'user_id' in content,
        'has_init': '__init__' in content,
        'has_with_user': 'with_user' in content,
        'has_get_user_scoped': '_get_user_scoped_repository' in content,
        'repositories': extract_repositories(content),
        'class_name': extract_class_name(content)
    }
    
    return analysis

def extract_class_name(content: str) -> Optional[str]:
    """Extract the main service class name from the file."""
    match = re.search(r'class\s+(\w+Service)\s*[\(:]', content)
    return match.group(1) if match else None

def extract_repositories(content: str) -> List[str]:
    """Extract repository names from __init__ method."""
    repositories = []
    
    # Find __init__ method
    init_match = re.search(r'def __init__\(self[^)]*\):', content)
    if not init_match:
        return repositories
    
    # Look for repository parameters
    init_section = content[init_match.start():init_match.end() + 500]
    repo_matches = re.findall(r'(\w+_repository)\s*[,)=]', init_section)
    repositories.extend(repo_matches)
    
    # Look for repository assignments
    assignment_matches = re.findall(r'self\.(_?\w+_repository)\s*=', content)
    repositories.extend(assignment_matches)
    
    return list(set(repositories))

def generate_user_context_code(class_name: str, repositories: List[str]) -> dict:
    """Generate the code snippets needed to add user context support."""
    
    # Generate __init__ update
    init_params = ["self"] + [f"{repo}=None" for repo in repositories]
    init_params.append("user_id: Optional[str] = None")
    
    init_code = f"""    def __init__({', '.join(init_params)}):
        {chr(10).join(f'self.{repo} = {repo}' for repo in repositories)}
        self._user_id = user_id  # Store user context
"""
    
    # Generate _get_user_scoped_repository method
    scoped_method = """    
    def _get_user_scoped_repository(self, repository: Any) -> Any:
        \"\"\"Get a user-scoped version of the repository if it supports user context.\"\"\"
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository
"""
    
    # Generate with_user method
    with_user_params = ', '.join([f"self.{repo}" for repo in repositories])
    with_user_method = f"""    
    def with_user(self, user_id: str) -> '{class_name}':
        \"\"\"Create a new service instance scoped to a specific user.\"\"\"
        return {class_name}({with_user_params}, user_id)
"""
    
    return {
        'init_update': init_code,
        'scoped_method': scoped_method,
        'with_user_method': with_user_method
    }

def update_service_file(filepath: Path, analysis: dict) -> bool:
    """Update a service file with user context support."""
    if analysis['has_user_id'] and analysis['has_with_user']:
        print(f"✓ {filepath.name} already has user context support")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if Optional import is present
    if 'from typing import' in content and 'Optional' not in content:
        # Add Optional to imports
        content = re.sub(
            r'from typing import ([^)]+)',
            r'from typing import \1, Optional',
            content,
            count=1
        )
    elif 'from typing import' not in content:
        # Add typing import
        content = "from typing import Optional, Any\n" + content
    
    class_name = analysis['class_name']
    if not class_name:
        print(f"✗ Could not find class name in {filepath.name}")
        return False
    
    # Generate the code updates
    code_updates = generate_user_context_code(class_name, analysis['repositories'])
    
    # Add user_id parameter to __init__
    if not analysis['has_user_id']:
        # Find __init__ method and add user_id parameter
        init_pattern = r'(def __init__\([^)]*)\):'
        init_replacement = r'\1, user_id: Optional[str] = None):'
        content = re.sub(init_pattern, init_replacement, content)
        
        # Add self._user_id assignment
        init_body_pattern = r'(def __init__[^:]+:\s*\n)'
        init_body_replacement = r'\1        self._user_id = user_id  # Store user context\n'
        content = re.sub(init_body_pattern, init_body_replacement, content)
    
    # Add _get_user_scoped_repository method if not present
    if not analysis['has_get_user_scoped']:
        # Find a good place to insert it (after __init__)
        class_pattern = f'class {class_name}[^:]*:\s*\n.*?def __init__[^:]+:[^\\n]+\\n(?:[^\\n]+\\n)*?'
        match = re.search(class_pattern, content, re.DOTALL)
        if match:
            insertion_point = match.end()
            content = content[:insertion_point] + code_updates['scoped_method'] + "\n" + content[insertion_point:]
    
    # Add with_user method if not present
    if not analysis['has_with_user']:
        # Insert after _get_user_scoped_repository or __init__
        if '_get_user_scoped_repository' in content:
            pattern = r'(def _get_user_scoped_repository[^:]+:[^}]+return repository\s*\n)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                insertion_point = match.end()
                content = content[:insertion_point] + code_updates['with_user_method'] + "\n" + content[insertion_point:]
        else:
            # Insert after __init__
            pattern = r'(def __init__[^:]+:[^}]+\n\s*\n)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                insertion_point = match.end()
                content = content[:insertion_point] + code_updates['with_user_method'] + "\n" + content[insertion_point:]
    
    # Save the updated file
    print(f"✓ Updating {filepath.name} with user context support")
    # Uncomment to actually write files:
    # with open(filepath, 'w') as f:
    #     f.write(content)
    
    return True

def generate_summary_report(analyses: List[dict]) -> str:
    """Generate a summary report of the updates needed."""
    report = []
    report.append("# Service User Context Update Report\n")
    report.append(f"Total services analyzed: {len(analyses)}\n")
    
    needs_update = [a for a in analyses if not (a['has_user_id'] and a['has_with_user'])]
    already_updated = [a for a in analyses if a['has_user_id'] and a['has_with_user']]
    
    report.append(f"Services needing update: {len(needs_update)}")
    report.append(f"Services already updated: {len(already_updated)}\n")
    
    report.append("## Services Needing Update:")
    for analysis in needs_update:
        report.append(f"- {analysis['filepath'].name}")
        report.append(f"  - Class: {analysis['class_name']}")
        report.append(f"  - Repositories: {', '.join(analysis['repositories'])}")
        report.append(f"  - Has user_id: {analysis['has_user_id']}")
        report.append(f"  - Has with_user: {analysis['has_with_user']}")
        report.append("")
    
    report.append("## Services Already Updated:")
    for analysis in already_updated:
        report.append(f"- {analysis['filepath'].name}")
    
    report.append("\n## Update Pattern:")
    report.append("```python")
    report.append("class ServiceName:")
    report.append("    def __init__(self, repo1=None, repo2=None, user_id: Optional[str] = None):")
    report.append("        self._user_id = user_id")
    report.append("    ")
    report.append("    def _get_user_scoped_repository(self, repository: Any) -> Any:")
    report.append("        # Returns user-scoped repository")
    report.append("    ")
    report.append("    def with_user(self, user_id: str) -> 'ServiceName':")
    report.append("        # Returns user-scoped service instance")
    report.append("```")
    
    return "\n".join(report)

def main():
    """Main function to update services with user context."""
    print("Analyzing service files for user context updates...\n")
    
    analyses = []
    
    for service_file in SERVICES_TO_UPDATE:
        filepath = SERVICE_DIR / service_file
        if filepath.exists():
            analysis = analyze_service_file(filepath)
            analyses.append(analysis)
            
            # Show analysis for each file
            print(f"Analyzing {service_file}:")
            print(f"  - Class: {analysis['class_name']}")
            print(f"  - Has user_id: {analysis['has_user_id']}")
            print(f"  - Has with_user: {analysis['has_with_user']}")
            print(f"  - Repositories: {', '.join(analysis['repositories'])}")
            print()
        else:
            print(f"✗ File not found: {filepath}")
    
    # Generate and print summary report
    report = generate_summary_report(analyses)
    print("\n" + "="*60)
    print(report)
    
    # Ask user if they want to apply updates
    # response = input("\nDo you want to apply these updates? (y/n): ")
    # if response.lower() == 'y':
    #     for analysis in analyses:
    #         update_service_file(analysis['filepath'], analysis)
    #     print("\n✓ Updates applied successfully!")
    # else:
    #     print("\n✗ Updates cancelled")

if __name__ == "__main__":
    main()