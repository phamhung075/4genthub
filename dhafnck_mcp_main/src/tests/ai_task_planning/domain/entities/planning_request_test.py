"""Test suite for PlanningRequest domain entity"""

import pytest
from datetime import datetime, timezone, timedelta
from fastmcp.ai_task_planning.domain.entities.planning_request import (
    PlanningRequest, RequirementItem, ComplexityLevel, PlanningContext
)


class TestRequirementItem:
    """Test cases for RequirementItem"""
    
    def test_create_requirement_item(self):
        """Test creating a basic requirement item"""
        req = RequirementItem(
            id="req_1",
            description="Implement user authentication",
            priority="high"
        )
        
        assert req.id == "req_1"
        assert req.description == "Implement user authentication"
        assert req.priority == "high"
        assert req.acceptance_criteria == []
        assert req.constraints == []
        assert req.related_files == []
        assert req.estimated_complexity is None
    
    def test_requirement_item_with_full_details(self):
        """Test creating requirement item with all fields"""
        req = RequirementItem(
            id="req_2",
            description="Add JWT authentication",
            priority="critical",
            acceptance_criteria=["Token expires in 1 hour", "Refresh token support"],
            constraints=["Must use RS256 algorithm"],
            related_files=["auth/jwt.py", "middleware/auth.py"],
            estimated_complexity=ComplexityLevel.MODERATE
        )
        
        assert req.priority == "critical"
        assert len(req.acceptance_criteria) == 2
        assert "Token expires in 1 hour" in req.acceptance_criteria
        assert len(req.constraints) == 1
        assert len(req.related_files) == 2
        assert req.estimated_complexity == ComplexityLevel.MODERATE


class TestPlanningRequest:
    """Test cases for PlanningRequest entity"""
    
    def test_create_basic_planning_request(self):
        """Test creating a basic planning request"""
        request = PlanningRequest(
            id="plan_123",
            title="Add User Authentication",
            description="Implement complete user authentication system"
        )
        
        assert pytest_request.id == "plan_123"
        assert pytest_request.title == "Add User Authentication"
        assert pytest_request.description == "Implement complete user authentication system"
        assert pytest_request.context == PlanningContext.NEW_FEATURE
        assert pytest_request.requirements == []
        assert pytest_request.risk_tolerance == "medium"
        assert isinstance(pytest_request.created_at, datetime)
    
    def test_add_requirement(self):
        """Test adding requirements to planning request"""
        request = PlanningRequest(
            id="plan_123",
            title="Auth System",
            description="Build authentication"
        )
        
        # Add first requirement
        req1 = pytest_request.add_requirement(
            description="Create login endpoint",
            priority="high",
            acceptance_criteria=["Support email/password", "Return JWT token"]
        )
        
        assert req1.id == "plan_123_req_1"
        assert req1.description == "Create login endpoint"
        assert req1.priority == "high"
        assert len(req1.acceptance_criteria) == 2
        assert len(pytest_request.requirements) == 1
        
        # Add second requirement
        req2 = pytest_request.add_requirement(
            description="Create logout endpoint",
            priority="medium"
        )
        
        assert req2.id == "plan_123_req_2"
        assert len(pytest_request.requirements) == 2
    
    def test_add_code_reference(self):
        """Test adding code references"""
        request = PlanningRequest(
            id="plan_123",
            title="Refactor Auth",
            description="Refactor authentication module"
        )
        
        # Add references
        pytest_request.add_code_reference("auth/login.py", ["23-45", "67-89"])
        pytest_request.add_code_reference("auth/jwt.py", ["10-20"])
        pytest_request.add_code_reference("auth/login.py", ["100-120"])
        
        assert len(pytest_request.code_references) == 2
        assert len(pytest_request.code_references["auth/login.py"]) == 3
        assert "23-45" in pytest_request.code_references["auth/login.py"]
        assert "100-120" in pytest_request.code_references["auth/login.py"]
        assert len(pytest_request.code_references["auth/jwt.py"]) == 1
    
    def test_estimate_overall_complexity_empty(self):
        """Test complexity estimation with no requirements"""
        request = PlanningRequest(
            id="plan_123",
            title="Empty Plan",
            description="Plan with no requirements"
        )
        
        complexity = pytest_request.estimate_overall_complexity()
        assert complexity == ComplexityLevel.SIMPLE
    
    def test_estimate_overall_complexity_with_estimates(self):
        """Test complexity estimation with estimated requirements"""
        request = PlanningRequest(
            id="plan_123",
            title="Complex System",
            description="Multi-agent system"
        )
        
        # Add requirements with different complexities
        req1 = RequirementItem(
            id="req_1",
            description="Simple task",
            estimated_complexity=ComplexityLevel.SIMPLE
        )
        req2 = RequirementItem(
            id="req_2",
            description="Complex task",
            estimated_complexity=ComplexityLevel.COMPLEX
        )
        req3 = RequirementItem(
            id="req_3",
            description="Epic task",
            estimated_complexity=ComplexityLevel.EPIC
        )
        
        pytest_request.requirements = [req1, req2, req3]
        
        # Average: (2 + 4 + 5) / 3 = 3.67 -> COMPLEX
        complexity = pytest_request.estimate_overall_complexity()
        assert complexity == ComplexityLevel.COMPLEX
    
    def test_estimate_overall_complexity_heuristics(self):
        """Test complexity estimation using acceptance criteria heuristics"""
        request = PlanningRequest(
            id="plan_123",
            title="Feature Plan",
            description="Feature with varied requirements"
        )
        
        # Add requirements without explicit complexity
        req1 = RequirementItem(
            id="req_1",
            description="Simple requirement",
            acceptance_criteria=["One criterion"]  # 1 criterion -> Simple (2)
        )
        req2 = RequirementItem(
            id="req_2", 
            description="Moderate requirement",
            acceptance_criteria=["Criterion 1", "Criterion 2", "Criterion 3"]  # 3 criteria -> Moderate (3)
        )
        req3 = RequirementItem(
            id="req_3",
            description="Complex requirement",
            acceptance_criteria=["C1", "C2", "C3", "C4", "C5", "C6"]  # 6 criteria -> Complex (4)
        )
        
        pytest_request.requirements = [req1, req2, req3]
        
        # Average: (2 + 3 + 4) / 3 = 3.0 -> MODERATE
        complexity = pytest_request.estimate_overall_complexity()
        assert complexity == ComplexityLevel.MODERATE
    
    def test_planning_request_with_full_context(self):
        """Test creating planning request with all fields"""
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        
        request = PlanningRequest(
            id="plan_456",
            title="Complete Integration",
            description="Integrate with external API",
            context=PlanningContext.INTEGRATION,
            project_id="proj_789",
            git_branch_id="branch_abc",
            user_id="user_xyz",
            deadline=deadline,
            available_agents=["coding-agent", "api-specialist-agent"],
            preferred_approach="RESTful API with retry logic",
            risk_tolerance="low",
            related_tasks=["task_001", "task_002"],
            documentation_refs=["api-docs.md", "integration-guide.md"],
            created_by="user_xyz",
            tags=["api", "integration", "external"]
        )
        
        assert pytest_request.context == PlanningContext.INTEGRATION
        assert pytest_request.project_id == "proj_789"
        assert pytest_request.deadline == deadline
        assert len(pytest_request.available_agents) == 2
        assert "coding-agent" in pytest_request.available_agents
        assert pytest_request.risk_tolerance == "low"
        assert len(pytest_request.tags) == 3
    
    def test_to_dict_serialization(self):
        """Test serializing planning request to dictionary"""
        deadline = datetime.now(timezone.utc) + timedelta(days=5)
        
        request = PlanningRequest(
            id="plan_789",
            title="Serialization Test",
            description="Test dictionary conversion",
            context=PlanningContext.BUG_FIX,
            deadline=deadline,
            created_by="test_user"
        )
        
        # Add a requirement
        pytest_request.add_requirement(
            description="Fix critical bug",
            priority="critical",
            acceptance_criteria=["Bug is fixed", "Tests pass"]
        )
        
        # Add code reference
        pytest_request.add_code_reference("buggy/module.py", ["45-67"])
        
        # Convert to dict
        data = pytest_request.to_dict()
        
        assert data['id'] == "plan_789"
        assert data['title'] == "Serialization Test"
        assert data['context'] == "bug_fix"
        assert data['deadline'] == deadline.isoformat()
        assert data['created_by'] == "test_user"
        assert len(data['requirements']) == 1
        assert data['requirements'][0]['priority'] == "critical"
        assert len(data['requirements'][0]['acceptance_criteria']) == 2
        assert "buggy/module.py" in data['code_references']
    
    def test_from_dict_deserialization(self):
        """Test deserializing planning request from dictionary"""
        deadline = datetime.now(timezone.utc) + timedelta(days=3)
        created_at = datetime.now(timezone.utc)
        
        data = {
            'id': 'plan_999',
            'title': 'Deserialization Test',
            'description': 'Test from dictionary',
            'context': 'refactoring',
            'deadline': deadline.isoformat(),
            'created_at': created_at.isoformat(),
            'created_by': 'test_user',
            'risk_tolerance': 'high',
            'requirements': [
                {
                    'id': 'req_1',
                    'description': 'Refactor module',
                    'priority': 'medium',
                    'acceptance_criteria': ['Clean code', 'Better performance'],
                    'constraints': ['Maintain API compatibility'],
                    'related_files': ['module.py'],
                    'estimated_complexity': 'moderate'
                }
            ],
            'code_references': {
                'module.py': ['100-200', '250-300']
            },
            'tags': ['refactoring', 'performance']
        }
        
        request = PlanningRequest.from_dict(data)
        
        assert pytest_request.id == 'plan_999'
        assert pytest_request.title == 'Deserialization Test'
        assert pytest_request.context == PlanningContext.REFACTORING
        assert pytest_request.deadline.isoformat() == deadline.isoformat()
        assert pytest_request.created_by == 'test_user'
        assert pytest_request.risk_tolerance == 'high'
        assert len(pytest_request.requirements) == 1
        assert pytest_request.requirements[0].estimated_complexity == ComplexityLevel.MODERATE
        assert len(pytest_request.code_references['module.py']) == 2
        assert len(pytest_request.tags) == 2
    
    def test_complexity_level_enum_values(self):
        """Test ComplexityLevel enum values"""
        assert ComplexityLevel.TRIVIAL.value == "trivial"
        assert ComplexityLevel.SIMPLE.value == "simple"
        assert ComplexityLevel.MODERATE.value == "moderate"
        assert ComplexityLevel.COMPLEX.value == "complex"
        assert ComplexityLevel.EPIC.value == "epic"
    
    def test_planning_context_enum_values(self):
        """Test PlanningContext enum values"""
        assert PlanningContext.NEW_FEATURE.value == "new_feature"
        assert PlanningContext.BUG_FIX.value == "bug_fix"
        assert PlanningContext.REFACTORING.value == "refactoring"
        assert PlanningContext.MAINTENANCE.value == "maintenance"
        assert PlanningContext.RESEARCH.value == "research"
        assert PlanningContext.INTEGRATION.value == "integration"