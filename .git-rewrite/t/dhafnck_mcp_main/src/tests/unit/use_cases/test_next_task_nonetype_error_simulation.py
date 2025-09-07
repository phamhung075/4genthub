"""Test to simulate the NoneType error that would occur without the fix

This test demonstrates the error that would occur if we didn't have
proper null safety checks in the _apply_filters method.
"""

import pytest
from unittest.mock import MagicMock
from typing import List, Optional


class BrokenNextTaskUseCase:
    """Simulated broken version without null safety checks"""
    
    def _apply_filters_broken(self, tasks: List, assignee: Optional[str], project_id: Optional[str], 
                             labels: Optional[List[str]]) -> List:
        """BROKEN VERSION: Apply filters WITHOUT null safety - this will cause NoneType errors"""
        if not tasks:
            return []
            
        filtered_tasks = list(tasks)
        
        if assignee:
            # THIS WILL FAIL if task.assignees is None
            filtered_tasks = [task for task in filtered_tasks if assignee in task.assignees]
        
        if labels:
            # THIS WILL FAIL if task.labels is None
            filtered_tasks = [task for task in filtered_tasks 
                            if any(label in task.labels for label in labels)]
        
        return filtered_tasks


def test_demonstrates_nonetype_error():
    """This test demonstrates the NoneType error that would occur without proper null checks"""
    # Create a task with None assignees
    task = MagicMock()
    task.assignees = None  # This will cause the error
    task.labels = None
    
    broken_use_case = BrokenNextTaskUseCase()
    
    # This should raise TypeError: argument of type 'NoneType' is not iterable
    with pytest.raises(TypeError, match="argument of type 'NoneType' is not iterable"):
        broken_use_case._apply_filters_broken([task], assignee="user1", project_id=None, labels=None)
    
    # Same error with labels
    with pytest.raises(TypeError, match="argument of type 'NoneType' is not iterable"):
        broken_use_case._apply_filters_broken([task], assignee=None, project_id=None, labels=["bug"])