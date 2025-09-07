#!/usr/bin/env python3
"""
Batch update script to add user context support to all remaining services.

This script provides a template-based approach to update services with
proper user context propagation following the established pattern.
"""

import os
from pathlib import Path
from typing import Dict, List

# Template for services that need user context
SERVICE_UPDATE_TEMPLATE = '''
# Add to imports if not present:
from typing import Optional, Any

# Update __init__ method:
def __init__(self, {existing_params}, user_id: Optional[str] = None):
    {existing_assignments}
    self._user_id = user_id  # Store user context

# Add this method after __init__:
def _get_user_scoped_repository(self, repository: Any) -> Any:
    """Get a user-scoped version of the repository if it supports user context."""
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

# Add this method:
def with_user(self, user_id: str) -> '{class_name}':
    """Create a new service instance scoped to a specific user."""
    return {class_name}({constructor_params}, user_id)

# In methods that use repositories, add:
repo = self._get_user_scoped_repository(self.{repo_name})
# Then use 'repo' instead of 'self.{repo_name}'
'''

# Services that need updates with their specific details
SERVICES_TO_UPDATE = {
    "work_distribution_service.py": {
        "class": "WorkDistributionService",
        "repositories": [],
        "needs_full_update": True
    },
    "dependencie_application_service.py": {
        "class": "DependencieApplicationService", 
        "repositories": ["_task_repository"],
        "needs_full_update": True
    },
    "rule_application_service.py": {
        "class": "RuleApplicationService",
        "repositories": ["_rule_repository"],
        "needs_full_update": True
    },
    "feature_flag_service.py": {
        "class": "FeatureFlagService",
        "repositories": [],
        "needs_full_update": True
    },
    "audit_service.py": {
        "class": "AuditService",
        "repositories": [],
        "needs_full_update": True
    },
    "task_progress_service.py": {
        "class": "TaskProgressService",
        "repositories": ["_task_repository", "_subtask_repository"],
        "needs_full_update": True
    },
    "context_validation_service.py": {
        "class": "ContextValidationService",
        "repositories": [],
        "needs_full_update": True
    },
    "context_inheritance_service.py": {
        "class": "ContextInheritanceService",
        "repositories": [],
        "needs_full_update": True
    },
    "context_delegation_service.py": {
        "class": "ContextDelegationService",
        "repositories": [],
        "needs_full_update": True
    },
    "context_cache_service.py": {
        "class": "ContextCacheService",
        "repositories": [],
        "needs_full_update": True
    },
    "git_branch_service.py": {
        "class": "GitBranchService",
        "repositories": [],
        "needs_full_update": True
    },
    "response_enrichment_service.py": {
        "class": "ResponseEnrichmentService",
        "repositories": [],
        "needs_full_update": True
    },
    "progress_tracking_service.py": {
        "class": "ProgressTrackingService",
        "repositories": ["task_repository", "context_repository"],
        "needs_full_update": True
    },
    "workflow_analysis_service.py": {
        "class": "WorkflowAnalysisService",
        "repositories": [],
        "needs_full_update": True
    },
    "progressive_enforcement_service.py": {
        "class": "ProgressiveEnforcementService",
        "repositories": [],
        "needs_full_update": True
    },
    "parameter_enforcement_service.py": {
        "class": "ParameterEnforcementService",
        "repositories": [],
        "needs_full_update": True
    }
}

# Services that already have partial support (just need with_user method)
SERVICES_NEED_WITH_USER = {
    "vision_analytics_service.py": "VisionAnalyticsService",
    "compliance_service.py": "ComplianceService",
    "task_context_sync_service.py": "TaskContextSyncService",
    "project_management_service.py": "ProjectManagementService",
    "hint_generation_service.py": "HintGenerationService",
    "automated_context_sync_service.py": "AutomatedContextSyncService",
    "unified_context_service.py": "UnifiedContextService"
}

def generate_with_user_method(class_name: str) -> str:
    """Generate just the with_user method for services that already have user_id."""
    return f'''
    def with_user(self, user_id: str) -> '{class_name}':
        """Create a new service instance scoped to a specific user."""
        # Note: Update constructor params based on actual __init__ signature
        return {class_name}(..., user_id=user_id)
'''

def generate_update_instructions() -> Dict[str, str]:
    """Generate specific update instructions for each service."""
    instructions = {}
    
    # Services needing full updates
    for filename, details in SERVICES_TO_UPDATE.items():
        class_name = details['class']
        repos = details['repositories']
        
        instruction = f"""
=== Update Instructions for {filename} ===
Class: {class_name}
Repositories: {', '.join(repos) if repos else 'None'}

1. Add to imports:
   from typing import Optional, Any

2. Update __init__ to add user_id parameter:
   def __init__(self, ..., user_id: Optional[str] = None):
       # existing code...
       self._user_id = user_id  # Store user context

3. Add _get_user_scoped_repository method after __init__

4. Add with_user method

5. In methods using repositories, replace:
   self.{repos[0] if repos else 'repository'}.method()
   With:
   repo = self._get_user_scoped_repository(self.{repos[0] if repos else 'repository'})
   repo.method()
"""
        instructions[filename] = instruction
    
    # Services needing just with_user
    for filename, class_name in SERVICES_NEED_WITH_USER.items():
        instruction = f"""
=== Update Instructions for {filename} ===
Class: {class_name}
Status: Already has user_id, needs with_user method

Add this method:
{generate_with_user_method(class_name)}
"""
        instructions[filename] = instruction
    
    return instructions

def create_update_checklist() -> str:
    """Create a checklist for manual updates."""
    checklist = []
    checklist.append("# Service User Context Update Checklist\n")
    checklist.append("## Services Needing Full Update:\n")
    
    for filename, details in SERVICES_TO_UPDATE.items():
        checklist.append(f"- [ ] {filename} ({details['class']})")
        if details['repositories']:
            checklist.append(f"      Repositories: {', '.join(details['repositories'])}")
    
    checklist.append("\n## Services Needing with_user Method Only:\n")
    for filename, class_name in SERVICES_NEED_WITH_USER.items():
        checklist.append(f"- [ ] {filename} ({class_name})")
    
    checklist.append("\n## Update Pattern Summary:")
    checklist.append("1. Add user_id parameter to __init__")
    checklist.append("2. Store self._user_id = user_id")
    checklist.append("3. Add _get_user_scoped_repository method")
    checklist.append("4. Add with_user method")
    checklist.append("5. Update repository calls to use scoped versions")
    
    return "\n".join(checklist)

def main():
    """Main function to generate update instructions."""
    print("="*60)
    print("Service User Context Update Instructions")
    print("="*60)
    
    # Generate and print instructions
    instructions = generate_update_instructions()
    
    # Print summary
    total_full = len(SERVICES_TO_UPDATE)
    total_partial = len(SERVICES_NEED_WITH_USER)
    total = total_full + total_partial
    
    print(f"\nTotal services to update: {total}")
    print(f"  - Need full update: {total_full}")
    print(f"  - Need with_user only: {total_partial}")
    
    # Create checklist
    checklist = create_update_checklist()
    
    # Save to file
    output_file = Path("SERVICE_UPDATE_CHECKLIST.md")
    with open(output_file, 'w') as f:
        f.write(checklist)
        f.write("\n\n# Detailed Instructions\n\n")
        for filename, instruction in instructions.items():
            f.write(instruction)
            f.write("\n")
    
    print(f"\n✓ Checklist saved to: {output_file}")
    print("\nNext steps:")
    print("1. Review SERVICE_UPDATE_CHECKLIST.md")
    print("2. Update each service following the instructions")
    print("3. Run tests after each update")
    print("4. Update CHANGELOG.md with progress")

if __name__ == "__main__":
    main()