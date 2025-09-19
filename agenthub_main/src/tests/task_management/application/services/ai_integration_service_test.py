"""Test suite for AITaskIntegrationService"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from fastmcp.task_management.application.services.ai_integration_service import AITaskIntegrationService
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.ai_task_planning.domain.entities.task_plan import TaskPlan, PlannedTask, TaskType, ExecutionPhase, AgentAssignment


class TestAITaskIntegrationService:
    """Test cases for AITaskIntegrationService"""
    
    @pytest.fixture
    def mock_task_facade(self):
        """Create mock task facade"""
        facade = Mock()
        facade.create_task = Mock(return_value={
            'success': True,
            'task': {
                'id': 'task_123',
                'title': 'Test Task',
                'description': 'Test Description',
                'status': 'todo'
            }
        })
        return facade
    
    @pytest.fixture
    def service(self, mock_task_facade):
        """Create AITaskIntegrationService instance"""
        return AITaskIntegrationService(mock_task_facade)
    
    @pytest.mark.asyncio
    async def test_create_ai_enhanced_task_plan_basic(self, service):
        """Test basic AI-enhanced task plan creation"""
        with patch.object(service.ai_planning_service, 'create_intelligent_plan') as mock_plan:
            # Setup mock plan
            mock_task_plan = Mock(spec=TaskPlan)
            mock_task_plan.id = "plan_123"
            mock_task_plan.title = "AI Plan"
            mock_task_plan.tasks = []
            mock_task_plan.total_estimated_hours = 20.0
            mock_task_plan.estimated_duration_days = 3.0
            mock_task_plan.confidence_score = 0.85
            mock_task_plan.required_agents = {"coding-agent", "test-agent"}
            mock_task_plan.agent_workload = {"coding-agent": 15.0, "test-agent": 5.0}
            
            mock_plan.return_value = mock_task_plan
            
            result = await service.create_ai_enhanced_task_plan(
                requirements="Build user authentication",
                title="Auth System",
                description="Complete authentication implementation",
                git_branch_id="branch_123",
                auto_create_tasks=False
            )
            
            assert result['success']
            assert result['planning_request']['title'] == "Auth System"
            assert result['task_plan']['total_tasks'] == 0
            assert result['task_plan']['confidence_score'] == 0.85
            assert 'ai_insights' in result
    
    @pytest.mark.asyncio
    async def test_create_ai_enhanced_task_plan_with_auto_create(self, service, mock_task_facade):
        """Test AI-enhanced task plan with automatic task creation"""
        with patch.object(service.ai_planning_service, 'create_intelligent_plan') as mock_plan:
            # Setup mock plan with tasks
            mock_task = PlannedTask(
                id="planned_task_1",
                title="Implement Login",
                description="Create login functionality",
                task_type=TaskType.TASK,
                phase=ExecutionPhase.IMPLEMENTATION,
                estimated_hours=8.0,
                agent_assignment=Mock(agent_id="coding-agent")
            )
            
            mock_task_plan = Mock(spec=TaskPlan)
            mock_task_plan.id = "plan_456"
            mock_task_plan.title = "AI Plan with Tasks"
            mock_task_plan.tasks = [mock_task]
            mock_task_plan.total_estimated_hours = 8.0
            mock_task_plan.estimated_duration_days = 1.0
            mock_task_plan.confidence_score = 0.9
            mock_task_plan.required_agents = {"coding-agent"}
            mock_task_plan.agent_workload = {"coding-agent": 8.0}
            
            mock_plan.return_value = mock_task_plan
            
            result = await service.create_ai_enhanced_task_plan(
                requirements="Build user authentication",
                title="Auth System",
                description="Complete authentication implementation",
                git_branch_id="branch_456",
                auto_create_tasks=True,
                user_id="user_789"
            )
            
            assert result['success']
            assert len(result['created_tasks']) == 1
            assert result['created_tasks'][0]['mcp_task_id'] == 'task_123'
            assert mock_task_facade.create_task.called
    
    @pytest.mark.asyncio
    async def test_create_ai_enhanced_task_plan_json_requirements(self, service):
        """Test AI-enhanced task plan with JSON requirements"""
        with patch.object(service.ai_planning_service, 'create_intelligent_plan') as mock_plan:
            mock_task_plan = Mock(spec=TaskPlan)
            mock_task_plan.id = "plan_789"
            mock_task_plan.title = "JSON Plan"
            mock_task_plan.tasks = []
            mock_task_plan.total_estimated_hours = 10.0
            mock_task_plan.estimated_duration_days = 2.0
            mock_task_plan.confidence_score = 0.75
            mock_task_plan.required_agents = {"coding-agent"}
            mock_task_plan.agent_workload = {"coding-agent": 10.0}
            
            mock_plan.return_value = mock_task_plan
            
            requirements_json = json.dumps([
                {'description': 'Implement JWT auth', 'priority': 'high'},
                {'description': 'Add user roles', 'priority': 'medium'}
            ])
            
            result = await service.create_ai_enhanced_task_plan(
                requirements=requirements_json,
                title="Complex Auth",
                description="Advanced authentication",
                git_branch_id="branch_789",
                context="new_feature"
            )

            assert result['success']
            assert result['planning_request']['context'] == "new_feature"
            
            # Verify requirements were parsed correctly
            call_args = mock_plan.call_args[0][0]
            assert len(call_args.requirements) == 2
            assert call_args.requirements[0].description == 'Implement JWT auth'
            assert call_args.requirements[0].priority == 'high'
    
    @pytest.mark.asyncio
    async def test_create_ai_enhanced_task_plan_error_handling(self, service):
        """Test error handling in AI-enhanced task plan creation"""
        with patch.object(service.ai_planning_service, 'create_intelligent_plan') as mock_plan:
            mock_plan.side_effect = Exception("Planning error")
            
            result = await service.create_ai_enhanced_task_plan(
                requirements="Test requirement",
                title="Error Test",
                description="Test error handling",
                git_branch_id="branch_error"
            )
            
            assert not result['success']
            assert 'AI task planning failed' in result['error']
            assert result['error_type'] == 'Exception'
    
    @pytest.mark.asyncio
    async def test_enhance_task_creation_basic(self, service, mock_task_facade):
        """Test basic task creation enhancement"""
        create_request = CreateTaskRequest(
            title="Test Task",
            description="Task to be enhanced",
            status="todo",
            priority="medium",
            git_branch_id="branch_123"
        )
        
        result = await service.enhance_task_creation(create_request)
        
        assert result['success']
        assert result['task']['id'] == 'task_123'
        assert 'ai_enhanced' in result
        assert result['ai_enhanced']
        assert mock_task_facade.create_task.called
    
    @pytest.mark.asyncio
    async def test_enhance_task_creation_with_ai_breakdown(self, service, mock_task_facade):
        """Test task creation with AI breakdown enabled"""
        create_request = CreateTaskRequest(
            title="Complex Task",
            description="Task requiring breakdown",
            status="todo",
            priority="high",
            git_branch_id="branch_123"
        )
        
        result = await service.enhance_task_creation(
            create_request,
            enable_ai_breakdown=True,
            enable_smart_assignment=False
        )
        
        assert result['success']
        assert 'ai_enhancements' in result
        assert 'breakdown' in result['ai_enhancements']
    
    @pytest.mark.asyncio
    async def test_enhance_task_creation_with_smart_assignment(self, service, mock_task_facade):
        """Test task creation with smart agent assignment"""
        create_request = CreateTaskRequest(
            title="UI Component Task",
            description="Create new dashboard component",
            status="todo",
            priority="medium",
            git_branch_id="branch_123"
        )
        
        result = await service.enhance_task_creation(
            create_request,
            enable_ai_breakdown=False,
            enable_smart_assignment=True
        )
        
        assert result['success']
        assert 'ai_enhancements' in result
        assert 'agent_suggestions' in result['ai_enhancements']
        assert 'shadcn-ui-expert-agent' in result['ai_enhancements']['agent_suggestions']['suggested_agents']
    
    @pytest.mark.asyncio
    async def test_enhance_task_creation_failure(self, service, mock_task_facade):
        """Test task creation enhancement when main task creation fails"""
        mock_task_facade.create_task.return_value = {
            'success': False,
            'error': 'Task creation failed'
        }
        
        create_request = CreateTaskRequest(
            title="Failed Task",
            description="This will fail",
            status="todo",
            priority="low",
            git_branch_id="branch_fail"
        )
        
        result = await service.enhance_task_creation(create_request)
        
        assert not result['success']
        assert result['error'] == 'Task creation failed'
    
    @pytest.mark.asyncio
    async def test_add_ai_insights_to_task_response(self, service):
        """Test adding AI insights to task response"""
        task_data = {
            'success': True,
            'task': {
                'id': 'task_123',
                'title': 'Debug authentication issue',
                'description': 'Fix login error in production'
            }
        }
        
        result = await service.add_ai_insights_to_task_response(task_data, action='get')
        
        assert result['success']
        assert 'ai_insights' in result
        assert 'enhanced_by_ai' in result
        assert result['enhanced_by_ai']
        
        insights = result['ai_insights']
        assert 'complexity_analysis' in insights
        assert 'suggested_next_actions' in insights
        assert 'potential_risks' in insights
        assert 'optimization_suggestions' in insights
    
    @pytest.mark.asyncio
    async def test_add_ai_insights_failure_handling(self, service):
        """Test AI insights failure handling"""
        task_data = {
            'success': True,
            'task': {
                'id': 'task_123',
                'title': None,  # This will cause an error
                'description': None
            }
        }
        
        with patch.object(service, '_generate_task_insights', side_effect=Exception("Insights error")):
            result = await service.add_ai_insights_to_task_response(task_data)
            
            # Should return original data on failure
            assert result == task_data
    
    def test_parse_requirements_comma_separated(self, service):
        """Test parsing comma-separated requirements"""
        requirements = "Build login, Add user roles, Write tests"
        
        parsed = service._parse_requirements(requirements)
        
        assert len(parsed) == 3
        assert parsed[0].description == "Build login"
        assert parsed[1].description == "Add user roles"
        assert parsed[2].description == "Write tests"
        assert all(req.priority == "medium" for req in parsed)
    
    def test_parse_requirements_json(self, service):
        """Test parsing JSON requirements"""
        requirements = json.dumps([
            {'description': 'Task 1', 'priority': 'high', 'acceptance_criteria': ['AC1', 'AC2']},
            {'description': 'Task 2', 'priority': 'low'}
        ])
        
        parsed = service._parse_requirements(requirements)
        
        assert len(parsed) == 2
        assert parsed[0].priority == 'high'
        assert len(parsed[0].acceptance_criteria) == 2
        assert parsed[1].priority == 'low'
    
    def test_parse_requirements_invalid_json(self, service):
        """Test parsing invalid JSON falls back to single requirement"""
        requirements = "[{invalid json"
        
        parsed = service._parse_requirements(requirements)
        
        assert len(parsed) == 1
        assert parsed[0].description == "[{invalid json"
        assert parsed[0].priority == 'medium'
    
    def test_analyze_complexity(self, service):
        """Test complexity analysis"""
        # High complexity
        result = service._analyze_complexity(
            "Complex System Integration",
            "Refactor entire architecture for migration"
        )
        assert result['level'] == 'high'
        assert result['score'] >= 4
        
        # Medium complexity
        result = service._analyze_complexity(
            "Implement New Feature",
            "Add user profile update functionality"
        )
        assert result['level'] == 'medium'
        
        # Low complexity
        result = service._analyze_complexity(
            "Fix typo",
            "Correct spelling in documentation"
        )
        assert result['level'] == 'low'
    
    def test_suggest_next_actions(self, service):
        """Test next action suggestions"""
        # Create action
        actions = service._suggest_next_actions('create')
        assert any('acceptance criteria' in action for action in actions)
        
        # Get action
        actions = service._suggest_next_actions('get')
        assert any('progress' in action for action in actions)
        
        # Update action
        actions = service._suggest_next_actions('update')
        assert any('changes' in action for action in actions)
        
        # Unknown action
        actions = service._suggest_next_actions('unknown')
        assert actions == ['Continue with standard workflow']
    
    def test_identify_risks(self, service):
        """Test risk identification"""
        # Integration risk
        risks = service._identify_risks(
            "API Integration",
            "Connect to third-party payment system"
        )
        assert any('complexity' in risk for risk in risks)
        assert any('External dependencies' in risk for risk in risks)
        
        # Security risk
        risks = service._identify_risks(
            "Authentication Update",
            "Implement new security measures"
        )
        assert any('Security' in risk for risk in risks)
        
        # No specific risks
        risks = service._identify_risks(
            "Simple Task",
            "Add button to UI"
        )
        assert risks == ['No significant risks identified']
    
    def test_suggest_optimizations(self, service):
        """Test optimization suggestions"""
        # Performance optimization
        opts = service._suggest_optimizations(
            "Improve Performance",
            "Optimize page load time"
        )
        assert any('caching' in opt for opt in opts)
        
        # UI optimization
        opts = service._suggest_optimizations(
            "Build UI Components",
            "Create reusable frontend elements"
        )
        assert any('reusability' in opt for opt in opts)
        
        # Database optimization
        opts = service._suggest_optimizations(
            "Database Query",
            "Improve query performance"
        )
        assert any('Optimize database' in opt for opt in opts)
    
    @pytest.mark.asyncio
    async def test_suggest_optimal_agents(self, service):
        """Test optimal agent suggestions"""
        # UI task
        result = await service._suggest_optimal_agents("Create dashboard UI component")
        assert 'shadcn-ui-expert-agent' in result['suggested_agents']
        
        # Testing task
        result = await service._suggest_optimal_agents("Write comprehensive test suite")
        assert 'test-orchestrator-agent' in result['suggested_agents']
        
        # Security task
        result = await service._suggest_optimal_agents("Implement authentication security")
        assert 'security-auditor-agent' in result['suggested_agents']
        
        # Debug task
        result = await service._suggest_optimal_agents("Debug production error")
        assert 'debugger-agent' in result['suggested_agents']
        
        # Generic task
        result = await service._suggest_optimal_agents("General implementation task")
        assert 'coding-agent' in result['suggested_agents']
    
    def test_generate_ai_insights(self, service):
        """Test AI insights generation for task plan"""
        mock_plan = Mock()
        mock_plan.confidence_score = 0.85
        mock_plan.risk_level = 'medium'
        mock_plan.tasks = [Mock(), Mock(), Mock(), Mock()]  # 4 tasks
        mock_plan.required_agents = {'agent1', 'agent2'}
        mock_plan.estimated_duration_days = 5
        mock_plan.total_estimated_hours = 40
        
        insights = service._generate_ai_insights(mock_plan)
        
        assert insights['plan_quality']['confidence_score'] == 0.85
        assert insights['plan_quality']['completeness'] == 'High'
        assert len(insights['execution_recommendations']) > 0
        assert len(insights['success_factors']) > 0