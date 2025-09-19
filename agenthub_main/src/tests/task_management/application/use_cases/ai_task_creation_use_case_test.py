"""Test suite for AITaskCreationUseCase"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List
from fastmcp.task_management.application.use_cases.ai_task_creation_use_case import (
    AITaskCreationUseCase, AITaskCreationRequest
)
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest


class TestAITaskCreationRequest:
    """Test cases for AITaskCreationRequest dataclass"""
    
    def test_create_basic_request(self):
        """Test creating a basic AI task creation request"""
        request = AITaskCreationRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch_123"
        )
        
        assert request.title == "Test Task"
        assert request.description == "Test Description"
        assert request.git_branch_id == "branch_123"
        assert request.priority == 'medium'  # Default
        assert request.enable_ai_breakdown is False  # Default
        assert request.enable_smart_assignment is False  # Default
        assert request.enable_auto_subtasks is False  # Default
        assert request.planning_context == 'new_feature'  # Default
    
    def test_create_request_with_ai_options(self):
        """Test creating request with AI enhancement options"""
        request = AITaskCreationRequest(
            title="AI Enhanced Task",
            description="Task with AI features",
            git_branch_id="branch_456",
            priority="high",
            assignees=["dev1", "dev2"],
            enable_ai_breakdown=True,
            enable_smart_assignment=True,
            enable_auto_subtasks=True,
            planning_context="bug_fix",
            ai_requirements="Fix authentication bug and add tests"
        )
        
        assert request.priority == "high"
        assert request.assignees == ["dev1", "dev2"]
        assert request.enable_ai_breakdown is True
        assert request.enable_smart_assignment is True
        assert request.enable_auto_subtasks is True
        assert request.planning_context == "bug_fix"
        assert request.ai_requirements == "Fix authentication bug and add tests"


class TestAITaskCreationUseCase:
    """Test cases for AITaskCreationUseCase"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        return Mock()
    
    @pytest.fixture
    def mock_task_facade(self):
        """Create mock task facade"""
        facade = Mock()
        facade.get_task = Mock(return_value={
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
    def use_case(self, mock_task_repository, mock_task_facade):
        """Create AITaskCreationUseCase instance"""
        return AITaskCreationUseCase(mock_task_repository, mock_task_facade)
    
    @pytest.mark.asyncio
    async def test_execute_basic_task_creation(self, use_case):
        """Test basic task creation without AI enhancements"""
        request = AITaskCreationRequest(
            title="Basic Task",
            description="No AI features",
            git_branch_id="branch_123"
        )
        
        with patch.object(use_case.ai_integration_service, 'enhance_task_creation') as mock_enhance:
            mock_enhance.return_value = {
                'success': True,
                'task': {
                    'id': 'task_123',
                    'title': 'Basic Task'
                },
                'ai_enhanced': False
            }
            
            result = await use_case.execute(request)
            
            assert result['success']
            assert result['task']['title'] == 'Basic Task'
            assert result['ai_enhanced_features']['breakdown_enabled'] is False
            assert result['ai_enhanced_features']['smart_assignment_enabled'] is False
            assert result['ai_enhanced_features']['auto_subtasks_enabled'] is False
            
            # Verify enhance_task_creation was called with correct parameters
            mock_enhance.assert_called_once()
            call_args = mock_enhance.call_args[0][0]
            assert isinstance(call_args, CreateTaskRequest)
            assert call_args.title == "Basic Task"
    
    @pytest.mark.asyncio
    async def test_execute_with_ai_breakdown(self, use_case):
        """Test task creation with AI breakdown enabled"""
        request = AITaskCreationRequest(
            title="Complex Task",
            description="Task needing breakdown",
            git_branch_id="branch_456",
            enable_ai_breakdown=True
        )
        
        with patch.object(use_case.ai_integration_service, 'enhance_task_creation') as mock_enhance:
            mock_enhance.return_value = {
                'success': True,
                'task': {'id': 'task_456', 'title': 'Complex Task'},
                'ai_enhanced': True,
                'ai_enhancements': {
                    'breakdown': {
                        'suggested_subtasks': ['Subtask 1', 'Subtask 2']
                    }
                }
            }
            
            result = await use_case.execute(request)
            
            assert result['success']
            assert result['ai_enhanced']
            assert result['ai_enhanced_features']['breakdown_enabled'] is True
            # Verify enhance_task_creation was called with correct parameters
            mock_enhance.assert_called_once()
            call_args = mock_enhance.call_args[0]
            task_request = call_args[0]
            assert isinstance(task_request, CreateTaskRequest)
            assert task_request.title == "Complex Task"
            assert task_request.description == "Task needing breakdown"
            assert task_request.git_branch_id == "branch_456"
            # Check kwargs
            assert mock_enhance.call_args[1]['enable_ai_breakdown'] is True
            assert mock_enhance.call_args[1]['enable_smart_assignment'] is False
    
    @pytest.mark.asyncio
    async def test_execute_with_smart_assignment(self, use_case):
        """Test task creation with smart agent assignment"""
        request = AITaskCreationRequest(
            title="UI Task",
            description="Build frontend component",
            git_branch_id="branch_789",
            enable_smart_assignment=True
        )
        
        with patch.object(use_case.ai_integration_service, 'enhance_task_creation') as mock_enhance:
            mock_enhance.return_value = {
                'success': True,
                'task': {'id': 'task_789', 'title': 'UI Task'},
                'ai_enhanced': True,
                'ai_enhancements': {
                    'agent_suggestions': {
                        'suggested_agents': ['shadcn-ui-expert-agent'],
                        'confidence': 0.85
                    }
                }
            }
            
            result = await use_case.execute(request)
            
            assert result['success']
            assert result['ai_enhanced_features']['smart_assignment_enabled'] is True
            assert 'agent_suggestions' in result['ai_enhancements']
    
    @pytest.mark.asyncio
    async def test_execute_with_auto_subtasks_and_requirements(self, use_case):
        """Test task creation with auto subtasks and AI requirements"""
        request = AITaskCreationRequest(
            title="Feature Implementation",
            description="Complete feature with AI planning",
            git_branch_id="branch_999",
            enable_auto_subtasks=True,
            ai_requirements="Build user dashboard with charts and filters"
        )
        
        with patch.object(use_case.ai_integration_service, 'enhance_task_creation') as mock_enhance:
            with patch.object(use_case.ai_integration_service, 'create_ai_enhanced_task_plan') as mock_plan:
                mock_enhance.return_value = {
                    'success': True,
                    'task': {'id': 'task_999', 'title': 'Feature Implementation'},
                    'ai_enhanced': True
                }
                
                mock_plan.return_value = {
                    'success': True,
                    'task_plan': {
                        'id': 'plan_123',
                        'total_tasks': 5,
                        'estimated_hours': 20
                    },
                    'ai_insights': {
                        'plan_quality': {'confidence_score': 0.9}
                    }
                }
                
                result = await use_case.execute(request)
                
                assert result['success']
                assert result['ai_enhanced_features']['auto_subtasks_enabled'] is True
                assert result['ai_enhanced_features']['ai_requirements_provided'] is True
                assert 'ai_plan' in result
                assert result['ai_plan']['total_tasks'] == 5
                assert 'ai_planning_insights' in result
                
                # Verify AI plan was created
                mock_plan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_ai_plan_failure(self, use_case):
        """Test handling of AI plan creation failure"""
        request = AITaskCreationRequest(
            title="Failed Plan Task",
            description="This AI plan will fail",
            git_branch_id="branch_fail",
            enable_auto_subtasks=True,
            ai_requirements="Invalid requirements"
        )
        
        with patch.object(use_case.ai_integration_service, 'enhance_task_creation') as mock_enhance:
            with patch.object(use_case.ai_integration_service, 'create_ai_enhanced_task_plan') as mock_plan:
                mock_enhance.return_value = {
                    'success': True,
                    'task': {'id': 'task_fail', 'title': 'Failed Plan Task'}
                }
                
                mock_plan.return_value = {
                    'success': False,
                    'error': 'AI planning failed: Invalid input'
                }
                
                result = await use_case.execute(request)
                
                assert result['success']  # Main task creation succeeded
                assert 'ai_plan_error' in result
                assert 'AI planning failed' in result['ai_plan_error']
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(self, use_case):
        """Test error handling in task creation"""
        request = AITaskCreationRequest(
            title="Error Task",
            description="This will fail",
            git_branch_id="branch_error"
        )
        
        with patch.object(use_case.ai_integration_service, 'enhance_task_creation') as mock_enhance:
            mock_enhance.side_effect = Exception("Task creation error")
            
            result = await use_case.execute(request)
            
            assert not result['success']
            assert 'AI task creation failed' in result['error']
            assert result['error_type'] == 'Exception'
    
    @pytest.mark.asyncio
    async def test_create_full_ai_plan(self, use_case):
        """Test creating a full AI plan"""
        with patch.object(use_case.ai_integration_service, 'create_ai_enhanced_task_plan') as mock_plan:
            mock_plan.return_value = {
                'success': True,
                'task_plan': {
                    'id': 'plan_full',
                    'total_tasks': 10,
                    'required_agents': ['coding-agent', 'test-agent']
                },
                'created_tasks': [
                    {'task_id': 'task_1', 'title': 'Task 1'},
                    {'task_id': 'task_2', 'title': 'Task 2'}
                ]
            }
            
            result = await use_case.create_full_ai_plan(
                requirements="Build complete authentication system",
                title="Auth System",
                description="Full authentication implementation",
                git_branch_id="branch_auth",
                context="security_requirement",
                user_id="user_123"
            )
            
            assert result['success']
            assert result['task_plan']['total_tasks'] == 10
            assert len(result['created_tasks']) == 2
            
            # Verify auto_create_tasks was set to True
            mock_plan.assert_called_with(
                requirements="Build complete authentication system",
                title="Auth System",
                description="Full authentication implementation",
                git_branch_id="branch_auth",
                context="security_requirement",
                auto_create_tasks=True,
                user_id="user_123"
            )
    
    @pytest.mark.asyncio
    async def test_create_full_ai_plan_error(self, use_case):
        """Test error handling in full AI plan creation"""
        with patch.object(use_case.ai_integration_service, 'create_ai_enhanced_task_plan') as mock_plan:
            mock_plan.side_effect = Exception("Planning service error")
            
            result = await use_case.create_full_ai_plan(
                requirements="Test requirements",
                title="Test Plan",
                description="Test",
                git_branch_id="branch_test"
            )
            
            assert not result['success']
            assert 'AI plan creation failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_enhance_existing_task_success(self, use_case, mock_task_facade):
        """Test enhancing an existing task"""
        enhancement_options = {
            'analyze_complexity': True,
            'suggest_optimizations': True,
            'identify_risks': True
        }
        
        with patch.object(use_case.ai_integration_service, 'add_ai_insights_to_task_response') as mock_insights:
            with patch.object(use_case.ai_integration_service, '_generate_task_insights') as mock_generate:
                mock_insights.return_value = {
                    'success': True,
                    'task': {'id': 'task_123', 'title': 'Test Task'},
                    'ai_insights': {'complexity': 'medium'}
                }
                
                mock_generate.return_value = {
                    'complexity_analysis': {'level': 'medium', 'score': 3},
                    'optimization_suggestions': ['Use caching', 'Optimize queries'],
                    'potential_risks': ['Performance issues', 'Security concerns']
                }
                
                result = await use_case.enhance_existing_task('task_123', enhancement_options)
                
                assert result['success']
                assert 'complexity_analysis' in result
                assert result['complexity_analysis']['level'] == 'medium'
                assert 'optimization_suggestions' in result
                assert len(result['optimization_suggestions']) == 2
                assert 'risk_analysis' in result
                assert len(result['risk_analysis']) == 2
    
    @pytest.mark.asyncio
    async def test_enhance_existing_task_not_found(self, use_case, mock_task_facade):
        """Test enhancing a non-existent task"""
        mock_task_facade.get_task.return_value = {
            'success': False,
            'error': 'Task not found'
        }
        
        result = await use_case.enhance_existing_task('nonexistent_task', {})
        
        assert not result['success']
        assert result['error'] == 'Task not found'
    
    @pytest.mark.asyncio
    async def test_enhance_existing_task_error(self, use_case):
        """Test error handling in task enhancement"""
        with patch.object(use_case.task_facade, 'get_task') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            result = await use_case.enhance_existing_task('task_123', {})
            
            assert not result['success']
            assert 'Task enhancement failed' in result['error']