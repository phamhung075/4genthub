"""Test to verify the parameter mismatch issue between controller and facade"""

import inspect
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

def test_facade_signature_shows_git_branch_id():
    """Verify that the facade expects git_branch_id parameter"""
    # Get the signature of the facade's get_next_task method
    sig = inspect.signature(TaskApplicationFacade.get_next_task)
    
    # Print the parameters for debugging
    print(f"\nFacade get_next_task parameters: {list(sig.parameters.keys())}")
    
    # Verify git_branch_id is expected
    assert 'git_branch_id' in sig.parameters, "Facade expects git_branch_id parameter"
    
    # Verify git_branch_name is NOT expected
    assert 'git_branch_name' not in sig.parameters, "Facade should NOT have git_branch_name parameter"

def test_controller_code_review():
    """Review the controller code to identify the mismatch"""
    controller_code = """
    # From task_mcp_controller.py _handle_next_task method:
    async def _run_async():
        return await facade.get_next_task(
            include_context=include_context,
            user_id=user_id,
            project_id=project_id,
            git_branch_name=git_branch_name,  # <-- WRONG! Should be git_branch_id
            assignee=None,
            labels=None
        )
    """
    
    facade_signature = """
    # From task_application_facade.py:
    async def get_next_task(self, include_context: bool = True, user_id: str = "default_id", 
                           project_id: str = "", git_branch_id: str = "main",   # <-- Expects git_branch_id
                           assignee: Optional[str] = None, labels: Optional[List[str]] = None)
    """
    
    print("\nController passes: git_branch_name")
    print("Facade expects: git_branch_id")
    print("\nThis mismatch causes TypeError!")
    
    # This test documents the issue
    assert True

if __name__ == "__main__":
    test_facade_signature_shows_git_branch_id()
    test_controller_code_review()