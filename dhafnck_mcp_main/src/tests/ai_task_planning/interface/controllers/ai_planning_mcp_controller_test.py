"""Test suite for AITaskPlanningMCPController"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastmcp.ai_task_planning.interface.controllers.ai_planning_mcp_controller import AITaskPlanningMCPController
from fastmcp.ai_task_planning.domain.entities.planning_request import PlanningContext
from fastmcp.ai_task_planning.domain.entities.task_plan import TaskPlan, PlannedTask, TaskType, ExecutionPhase


class TestAITaskPlanningMCPController:
    """Test cases for AITaskPlanningMCPController"""
    
    @pytest.fixture
    def controller(self):
        """Create AITaskPlanningMCPController instance"""
        return AITaskPlanningMCPController()
    
    @pytest.mark.asyncio
    async def test_create_ai_plan_missing_required_params(self, controller):
        """Test create_ai_plan with missing required parameters"""
        # Test missing title
        result = await controller.create_ai_plan(
            description="Test description",
            requirements="requirement1,requirement2",
            git_branch_id="branch_123"
        )
        
        assert not result['success']
        assert 'Missing required parameter: title' in result['error']
        assert 'required_parameters' in result
        
        # Test missing git_branch_id
        result = await controller.create_ai_plan(
            title="Test Plan",
            description="Test description",
            requirements="requirement1"
        )
        
        assert not result['success']
        assert 'Missing required parameter: git_branch_id' in result['error']
    
    @pytest.mark.asyncio
    async def test_create_ai_plan_with_comma_separated_requirements(self, controller):
        """Test create_ai_plan with comma-separated requirements"""
        with patch.object(controller.planning_service, 'create_intelligent_plan') as mock_plan:
            with patch.object(controller.planning_service, 'execute_plan_with_mcp') as mock_execute:
                # Setup mocks
                mock_task_plan = Mock(spec=TaskPlan)
                mock_task_plan.id = "plan_123"
                mock_task_plan.title = "AI Plan: Test"
                mock_task_plan.description = "Test plan"
                mock_task_plan.tasks = []
                mock_task_plan.total_estimated_hours = 10.0
                mock_task_plan.estimated_duration_days = 2.0
                mock_task_plan.confidence_score = 0.8
                mock_task_plan.risk_level = "medium"
                mock_task_plan.required_agents = {"coding-agent"}
                mock_task_plan.execution_phases = [ExecutionPhase.IMPLEMENTATION]
                mock_task_plan.parallel_execution_groups = []
                mock_task_plan.critical_path = []
                mock_task_plan.agent_workload = {"coding-agent": 10.0}
                mock_task_plan.created_at = datetime.now(timezone.utc)
                
                mock_plan.return_value = mock_task_plan
                mock_execute.return_value = {
                    'success': True,
                    'created_tasks': [],
                    'failed_tasks': []
                }
                
                result = await controller.create_ai_plan(
                    title="Test Plan",
                    description="Test description",
                    requirements="Implement login, Add user profile, Write tests",
                    git_branch_id="branch_123",
                    project_id="proj_456"
                )
                
                assert result['success']
                assert result['planning_request']['title'] == "Test Plan"
                assert result['planning_request']['requirements_count'] == 3
                assert result['task_plan']['id'] == "plan_123"
                
                # Verify planning request was created correctly
                call_args = mock_plan.call_args[0][0]
                assert len(call_args.requirements) == 3
                assert call_args.requirements[0].description == "Implement login"
                assert call_args.requirements[1].description == "Add user profile"
                assert call_args.requirements[2].description == "Write tests"
    
    @pytest.mark.asyncio
    async def test_create_ai_plan_with_json_requirements(self, controller):
        """Test create_ai_plan with JSON format requirements"""
        with patch.object(controller.planning_service, 'create_intelligent_plan') as mock_plan:
            with patch.object(controller.planning_service, 'execute_plan_with_mcp') as mock_execute:
                # Setup mocks
                mock_task_plan = Mock(spec=TaskPlan)
                mock_task_plan.id = "plan_456"
                mock_task_plan.title = "AI Plan: Complex"
                mock_task_plan.description = "Complex plan"
                mock_task_plan.tasks = []
                mock_task_plan.total_estimated_hours = 20.0
                mock_task_plan.estimated_duration_days = 3.0
                mock_task_plan.confidence_score = 0.85
                mock_task_plan.risk_level = "low"
                mock_task_plan.required_agents = {"coding-agent", "test-agent"}
                mock_task_plan.execution_phases = [ExecutionPhase.ARCHITECTURE, ExecutionPhase.IMPLEMENTATION]
                mock_task_plan.parallel_execution_groups = [["task1", "task2"]]
                mock_task_plan.critical_path = ["task1"]
                mock_task_plan.agent_workload = {"coding-agent": 15.0, "test-agent": 5.0}
                mock_task_plan.created_at = datetime.now(timezone.utc)
                
                mock_plan.return_value = mock_task_plan
                mock_execute.return_value = {
                    'success': True,
                    'created_tasks': [{'task_id': 'task_1'}],
                    'failed_tasks': []
                }
                
                requirements_json = json.dumps([
                    {
                        'description': 'Implement authentication',
                        'priority': 'high',
                        'acceptance_criteria': ['Login works', 'Logout works'],
                        'constraints': ['Use JWT'],
                        'related_files': ['auth.py']
                    },
                    {
                        'description': 'Add user dashboard',
                        'priority': 'medium'
                    }
                ])
                
                result = await controller.create_ai_plan(
                    title="Complex Plan",
                    description="Complex system",
                    requirements=requirements_json,
                    git_branch_id="branch_789",
                    context="new_feature",
                    deadline=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    preferred_approach="Microservices",
                    risk_tolerance="low"
                )
                
                assert result['success']
                assert result['planning_request']['context'] == "new_feature"
                assert len(result['recommendations']) >= 0
                
                # Verify detailed requirement parsing
                call_args = mock_plan.call_args[0][0]
                assert len(call_args.requirements) == 2
                assert call_args.requirements[0].priority == "high"
                assert len(call_args.requirements[0].acceptance_criteria) == 2
                assert call_args.requirements[0].related_files == ['auth.py']
    
    @pytest.mark.asyncio
    async def test_create_ai_plan_with_invalid_json(self, controller):
        """Test create_ai_plan with invalid JSON requirements"""
        result = await controller.create_ai_plan(
            title="Test Plan",
            description="Test description",
            requirements='[{"invalid json}',
            git_branch_id="branch_123"
        )
        
        assert not result['success']
        assert 'Invalid JSON format' in result['error']
    
    @pytest.mark.asyncio
    async def test_create_ai_plan_with_invalid_deadline(self, controller):
        """Test create_ai_plan with invalid deadline format"""
        result = await controller.create_ai_plan(
            title="Test Plan",
            description="Test description",
            requirements="requirement1",
            git_branch_id="branch_123",
            deadline="not-a-date"
        )
        
        assert not result['success']
        assert 'Invalid deadline format' in result['error']
    
    @pytest.mark.asyncio
    async def test_create_ai_plan_exception_handling(self, controller):
        """Test create_ai_plan exception handling"""
        with patch.object(controller.planning_service, 'create_intelligent_plan') as mock_plan:
            mock_plan.side_effect = Exception("Planning service error")
            
            result = await controller.create_ai_plan(
                title="Test Plan",
                description="Test description",
                requirements="requirement1",
                git_branch_id="branch_123"
            )
            
            assert not result['success']
            assert 'AI planning failed' in result['error']
            assert 'Planning service error' in result['error']
            assert result['error_type'] == 'Exception'
    
    @pytest.mark.asyncio
    async def test_analyze_requirements_basic(self, controller):
        """Test basic requirement analysis"""
        result = await controller.analyze_requirements(
            requirements="Implement user login, Add password reset, Write security tests"
        )
        
        assert result['success']
        assert result['analysis']['total_requirements'] == 3
        assert 'pattern_distribution' in result['analysis']
        assert 'agent_recommendations' in result['analysis']
        assert 'detailed_analysis' in result
        assert len(result['detailed_analysis']) == 3
    
    @pytest.mark.asyncio
    async def test_analyze_requirements_json_format(self, controller):
        """Test requirement analysis with JSON format"""
        requirements_json = json.dumps([
            {
                'description': 'Build REST API',
                'priority': 'high',
                'acceptance_criteria': ['Support CRUD operations']
            },
            {
                'description': 'Add database schema',
                'priority': 'medium'
            }
        ])
        
        result = await controller.analyze_requirements(requirements=requirements_json)
        
        assert result['success']
        assert result['analysis']['total_requirements'] == 2
        
        # Check detailed analysis
        detailed = result['detailed_analysis']
        assert detailed[0]['description'] == 'Build REST API'
        assert 'api_integration' in detailed[0]['detected_patterns'] or 'crud_operations' in detailed[0]['detected_patterns']
    
    @pytest.mark.asyncio
    async def test_analyze_requirements_missing_param(self, controller):
        """Test requirement analysis with missing parameter"""
        result = await controller.analyze_requirements()
        
        assert not result['success']
        assert 'Missing required parameter: requirements' in result['error']
    
    @pytest.mark.asyncio
    async def test_estimate_effort_basic(self, controller):
        """Test basic effort estimation"""
        result = await controller.estimate_effort(
            requirements="Simple CRUD operations, Basic UI, Write tests"
        )
        
        assert result['success']
        assert 'effort_estimate' in result
        assert 'total_hours' in result['effort_estimate']
        assert 'total_days' in result['effort_estimate']
        assert 'total_weeks' in result['effort_estimate']
        assert 'confidence_level' in result['effort_estimate']
    
    @pytest.mark.asyncio
    async def test_estimate_effort_with_breakdown(self, controller):
        """Test effort estimation with detailed breakdown"""
        result = await controller.estimate_effort(
            requirements="Complex authentication system, API integration",
            include_breakdown=True
        )
        
        assert result['success']
        assert 'detailed_breakdown' in result
        assert len(result['detailed_breakdown']) > 0
    
    @pytest.mark.asyncio
    async def test_suggest_agents_basic(self, controller):
        """Test basic agent suggestions"""
        result = await controller.suggest_agents(
            requirements="Build UI components, Write frontend tests, Create responsive design"
        )
        
        assert result['success']
        assert 'agent_suggestions' in result
        assert 'recommended_agents' in result['agent_suggestions']
        assert 'primary_agents' in result['agent_suggestions']
        assert 'workload_distribution' in result['agent_suggestions']
        assert 'ui-specialist-agent' in result['agent_suggestions']['recommended_agents']
    
    @pytest.mark.asyncio
    async def test_suggest_agents_with_filter(self, controller):
        """Test agent suggestions with available agents filter"""
        result = await controller.suggest_agents(
            requirements="Build API, Add authentication, Deploy to cloud",
            available_agents="coding-agent,devops-agent"
        )
        
        assert result['success']
        agents = result['agent_suggestions']['recommended_agents']
        
        # Should only include available agents
        for agent in agents:
            assert agent in ['coding-agent', 'devops-agent']
    
    @pytest.mark.asyncio
    async def test_get_plan_status(self, controller):
        """Test get_plan_status placeholder"""
        result = await controller.get_plan_status(plan_id="plan_123")
        
        assert result['success']
        assert 'not yet implemented' in result['message']
        assert 'available_operations' in result
    
    @pytest.mark.asyncio
    async def test_validate_plan(self, controller):
        """Test validate_plan placeholder"""
        result = await controller.validate_plan(
            plan_data='{"tasks": [], "dependencies": []}'
        )
        
        assert result['success']
        assert 'not yet implemented' in result['message']
        assert 'available_validations' in result
    
    def test_generate_recommendations(self, controller):
        """Test recommendation generation"""
        # Mock task plan with various conditions
        mock_plan = Mock()
        mock_plan.confidence_score = 0.5  # Low confidence
        mock_plan.total_estimated_hours = 100  # Large project
        mock_plan.required_agents = set(['agent1', 'agent2', 'agent3', 'agent4', 'agent5', 'agent6'])  # Many agents
        mock_plan.risk_level = 'high'
        mock_plan.agent_workload = {
            'agent1': 50,  # Overloaded
            'agent2': 30,
            'agent3': 45   # Overloaded
        }
        
        recommendations = controller._generate_recommendations(mock_plan)
        
        assert len(recommendations) > 0
        assert any('detailed requirements' in r for r in recommendations)  # Low confidence
        assert any('smaller phases' in r for r in recommendations)  # Large project
        assert any('coordination' in r for r in recommendations)  # Many agents
        assert any('High risk' in r for r in recommendations)  # High risk
        assert any('overloaded' in r for r in recommendations)  # Overloaded agents
    
    def test_calculate_estimation_confidence(self, controller):
        """Test confidence level calculation"""
        # High confidence scenario
        analysis = {
            'pattern_distribution': {'pattern1': 1, 'pattern2': 2, 'pattern3': 1},
            'total_estimated_hours': 50
        }
        confidence = controller._calculate_estimation_confidence(analysis)
        assert confidence == 'high'
        
        # Medium confidence scenario
        analysis = {
            'pattern_distribution': {'pattern1': 1, 'pattern2': 1},
            'total_estimated_hours': 150
        }
        confidence = controller._calculate_estimation_confidence(analysis)
        assert confidence == 'medium'
        
        # Low confidence scenario
        analysis = {
            'pattern_distribution': {'pattern1': 1},
            'total_estimated_hours': 300
        }
        confidence = controller._calculate_estimation_confidence(analysis)
        assert confidence == 'low'
    
    def test_estimate_agent_workload(self, controller):
        """Test agent workload estimation"""
        agent_recommendations = {
            'coding-agent': 4,
            'test-agent': 2,
            'ui-agent': 2
        }
        total_hours = 40
        
        workload = controller._estimate_agent_workload(agent_recommendations, total_hours)
        
        assert workload['coding-agent'] == 20.0  # 4/8 * 40
        assert workload['test-agent'] == 10.0    # 2/8 * 40
        assert workload['ui-agent'] == 10.0      # 2/8 * 40
        
        # Test empty recommendations
        empty_workload = controller._estimate_agent_workload({}, 40)
        assert empty_workload == {}
    
    def test_identify_specialization_needs(self, controller):
        """Test specialization identification"""
        pattern_distribution = {
            'user_authentication': 2,
            'api_integration': 1,
            'database_schema': 3,
            'testing_requirement': 1,
            'unknown_pattern': 1  # Should be ignored
        }
        
        specializations = controller._identify_specialization_needs(pattern_distribution)
        
        assert 'Security expertise' in specializations
        assert 'API and integration knowledge' in specializations
        assert 'Database design expertise' in specializations
        assert 'Testing and QA expertise' in specializations
        assert len(specializations) == 4  # Only known patterns