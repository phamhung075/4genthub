"""AI Task Creation Use Case

Use case for creating tasks with AI enhancement capabilities.
Combines traditional task creation with AI planning and insights.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..services.ai_integration_service import AITaskIntegrationService
from ..dtos.task.create_task_request import CreateTaskRequest
from ..facades.task_application_facade import TaskApplicationFacade
from ...domain.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)

@dataclass
class AITaskCreationRequest:
    """Request for AI-enhanced task creation"""
    # Standard task creation fields
    title: str
    description: Optional[str]
    git_branch_id: str
    priority: Optional[str] = 'medium'
    assignees: Optional[list] = None
    estimated_effort: Optional[str] = None
    labels: Optional[list] = None
    dependencies: Optional[list] = None
    user_id: Optional[str] = None
    
    # AI enhancement options
    enable_ai_breakdown: bool = False
    enable_smart_assignment: bool = False
    enable_auto_subtasks: bool = False
    planning_context: str = 'new_feature'
    ai_requirements: Optional[str] = None  # Additional requirements for AI planning

class AITaskCreationUseCase:
    """
    Use case for AI-enhanced task creation.
    
    This use case extends traditional task creation with AI capabilities:
    - Intelligent task breakdown
    - Smart agent assignment
    - Automated subtask generation
    - AI-powered insights
    """
    
    def __init__(self, task_repository: TaskRepository, task_facade: TaskApplicationFacade):
        self.task_repository = task_repository
        self.task_facade = task_facade
        self.ai_integration_service = AITaskIntegrationService(task_facade)
    
    async def execute(self, request: AITaskCreationRequest) -> Dict[str, Any]:
        """
        Execute AI-enhanced task creation.
        
        Args:
            request: AI task creation request with enhancement options
            
        Returns:
            Task creation result with AI insights and enhancements
        """
        try:
            logger.info(f"Creating AI-enhanced task: {request.title}")
            
            # Create standard CreateTaskRequest
            create_request = CreateTaskRequest(
                title=request.title,
                description=request.description,
                git_branch_id=request.git_branch_id,
                priority=request.priority,
                assignees=request.assignees or [],
                estimated_effort=request.estimated_effort,
                labels=request.labels or [],
                dependencies=request.dependencies or [],
                user_id=request.user_id
            )
            
            # Apply AI enhancements
            result = await self.ai_integration_service.enhance_task_creation(
                create_request,
                enable_ai_breakdown=request.enable_ai_breakdown,
                enable_smart_assignment=request.enable_smart_assignment
            )
            
            # If AI requirements provided and auto_subtasks enabled, create a full AI plan
            if request.ai_requirements and request.enable_auto_subtasks:
                logger.info("Creating comprehensive AI task plan")
                
                plan_result = await self.ai_integration_service.create_ai_enhanced_task_plan(
                    requirements=request.ai_requirements,
                    title=request.title,
                    description=request.description or "AI-enhanced task",
                    git_branch_id=request.git_branch_id,
                    context=request.planning_context,
                    auto_create_tasks=False,  # Don't auto-create, we control the process
                    user_id=request.user_id
                )
                
                if plan_result.get('success'):
                    # Add AI plan information to the result
                    result['ai_plan'] = plan_result['task_plan']
                    result['ai_planning_insights'] = plan_result['ai_insights']
                else:
                    logger.warning(f"AI planning failed: {plan_result.get('error')}")
                    result['ai_plan_error'] = plan_result.get('error')
            
            # Add AI enhancement metadata
            result['ai_enhanced_features'] = {
                'breakdown_enabled': request.enable_ai_breakdown,
                'smart_assignment_enabled': request.enable_smart_assignment,
                'auto_subtasks_enabled': request.enable_auto_subtasks,
                'ai_requirements_provided': bool(request.ai_requirements)
            }
            
            logger.info(f"AI-enhanced task creation completed: {result.get('success', False)}")
            return result
            
        except Exception as e:
            logger.error(f"AI task creation failed: {e}")
            return {
                'success': False,
                'error': f'AI task creation failed: {str(e)}',
                'error_type': type(e).__name__
            }
    
    async def create_full_ai_plan(self, requirements: str, title: str,
                                 description: str, git_branch_id: str,
                                 context: str = 'new_feature',
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a full AI-generated task plan.
        
        Args:
            requirements: High-level requirements
            title: Plan title
            description: Plan description
            git_branch_id: Git branch ID
            context: Planning context
            user_id: User ID
            
        Returns:
            Complete AI task plan with created tasks
        """
        try:
            return await self.ai_integration_service.create_ai_enhanced_task_plan(
                requirements=requirements,
                title=title,
                description=description,
                git_branch_id=git_branch_id,
                context=context,
                auto_create_tasks=True,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"Full AI plan creation failed: {e}")
            return {
                'success': False,
                'error': f'AI plan creation failed: {str(e)}'
            }
    
    async def enhance_existing_task(self, task_id: str, enhancement_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing task with AI capabilities.
        
        Args:
            task_id: ID of the task to enhance
            enhancement_options: Options for AI enhancement
            
        Returns:
            Enhancement result with AI insights
        """
        try:
            # Get existing task
            task_result = self.task_facade.get_task(task_id, include_context=True)
            
            if not task_result.get('success'):
                return task_result
            
            task_data = task_result['task']
            
            # Apply AI insights to the existing task data
            enhanced_result = await self.ai_integration_service.add_ai_insights_to_task_response(
                task_result,
                action="enhance"
            )
            
            # Add specific enhancement options
            if enhancement_options.get('analyze_complexity'):
                complexity_analysis = await self._analyze_task_complexity(task_data)
                enhanced_result['complexity_analysis'] = complexity_analysis
            
            if enhancement_options.get('suggest_optimizations'):
                optimizations = await self._suggest_task_optimizations(task_data)
                enhanced_result['optimization_suggestions'] = optimizations
            
            if enhancement_options.get('identify_risks'):
                risk_analysis = await self._identify_task_risks(task_data)
                enhanced_result['risk_analysis'] = risk_analysis
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Task enhancement failed: {e}")
            return {
                'success': False,
                'error': f'Task enhancement failed: {str(e)}'
            }
    
    async def _analyze_task_complexity(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task complexity using AI"""
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        
        # Use AI integration service for complexity analysis
        ai_insights = await self.ai_integration_service._generate_task_insights(
            title, description, 'analyze'
        )
        
        return ai_insights.get('complexity_analysis', {})
    
    async def _suggest_task_optimizations(self, task_data: Dict[str, Any]) -> List[str]:
        """Suggest optimizations for the task"""
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        
        # Use AI integration service for optimization suggestions
        ai_insights = await self.ai_integration_service._generate_task_insights(
            title, description, 'optimize'
        )
        
        return ai_insights.get('optimization_suggestions', [])
    
    async def _identify_task_risks(self, task_data: Dict[str, Any]) -> List[str]:
        """Identify potential risks for the task"""
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        
        # Use AI integration service for risk analysis
        ai_insights = await self.ai_integration_service._generate_task_insights(
            title, description, 'analyze'
        )
        
        return ai_insights.get('potential_risks', [])