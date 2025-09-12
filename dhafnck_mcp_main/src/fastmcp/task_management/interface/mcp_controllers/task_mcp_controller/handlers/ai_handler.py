"""AI Handler for Task MCP Controller

Handles AI-enhanced task operations including AI planning, smart task creation,
and AI-powered insights.
"""

import logging
from typing import Dict, Any, Optional

from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes
from ....application.services.ai_integration_service import AITaskIntegrationService
from ....application.use_cases.ai_task_creation_use_case import AITaskCreationUseCase, AITaskCreationRequest

logger = logging.getLogger(__name__)

class AIHandler:
    """Handler for AI-enhanced task operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    async def ai_plan(self, facade, **kwargs) -> Dict[str, Any]:
        """
        Create an AI-generated task plan from requirements.
        
        Parameters:
        - requirements (str): Requirements description or JSON
        - title (str): Plan title
        - description (str): Plan description
        - git_branch_id (str): Git branch ID
        - context (str, optional): Planning context (new_feature, bug_fix, etc.)
        - auto_create_tasks (bool, optional): Whether to create MCP tasks automatically
        - user_id (str, optional): User ID for task creation
        """
        try:
            # Validate required parameters
            required_params = ['requirements', 'title', 'git_branch_id']
            for param in required_params:
                if not kwargs.get(param):
                    return self._response_formatter.create_error_response(
                        operation="ai_plan",
                        error=f"Missing required parameter: {param}",
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        details={"required_parameters": required_params}
                    )
            
            # Initialize AI integration service
            ai_service = AITaskIntegrationService(facade)
            
            # Execute AI planning
            result = await ai_service.create_ai_enhanced_task_plan(
                requirements=kwargs['requirements'],
                title=kwargs['title'],
                description=kwargs.get('description', 'AI-generated task plan'),
                git_branch_id=kwargs['git_branch_id'],
                context=kwargs.get('context', 'new_feature'),
                auto_create_tasks=kwargs.get('auto_create_tasks', True),
                user_id=kwargs.get('user_id')
            )
            
            if result.get('success'):
                return self._response_formatter.create_success_response(
                    operation="ai_plan",
                    data=result,
                    message="AI task plan created successfully"
                )
            else:
                return self._response_formatter.create_error_response(
                    operation="ai_plan",
                    error=result.get('error', 'AI planning failed'),
                    error_code=ErrorCodes.OPERATION_FAILED
                )
        
        except Exception as e:
            logger.error(f"AI plan operation failed: {e}")
            return self._response_formatter.create_error_response(
                operation="ai_plan",
                error=f"AI planning failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    async def ai_create(self, facade, **kwargs) -> Dict[str, Any]:
        """
        Create a task with AI enhancements.
        
        Parameters:
        - title (str): Task title
        - description (str, optional): Task description
        - git_branch_id (str): Git branch ID
        - priority (str, optional): Task priority
        - assignees (list, optional): Task assignees
        - enable_ai_breakdown (bool, optional): Enable AI task breakdown
        - enable_smart_assignment (bool, optional): Enable AI agent assignment
        - enable_auto_subtasks (bool, optional): Enable automatic subtask creation
        - ai_requirements (str, optional): Additional AI requirements
        - planning_context (str, optional): Planning context
        - user_id (str, optional): User ID
        """
        try:
            # Validate required parameters
            if not kwargs.get('title'):
                return self._response_formatter.create_error_response(
                    operation="ai_create",
                    error="Missing required parameter: title",
                    error_code=ErrorCodes.VALIDATION_ERROR
                )
            
            if not kwargs.get('git_branch_id'):
                return self._response_formatter.create_error_response(
                    operation="ai_create",
                    error="Missing required parameter: git_branch_id",
                    error_code=ErrorCodes.VALIDATION_ERROR
                )
            
            # Create AI task creation request
            ai_request = AITaskCreationRequest(
                title=kwargs['title'],
                description=kwargs.get('description'),
                git_branch_id=kwargs['git_branch_id'],
                priority=kwargs.get('priority', 'medium'),
                assignees=kwargs.get('assignees', []),
                estimated_effort=kwargs.get('estimated_effort'),
                labels=kwargs.get('labels', []),
                dependencies=kwargs.get('dependencies', []),
                user_id=kwargs.get('user_id'),
                enable_ai_breakdown=kwargs.get('enable_ai_breakdown', False),
                enable_smart_assignment=kwargs.get('enable_smart_assignment', False),
                enable_auto_subtasks=kwargs.get('enable_auto_subtasks', False),
                planning_context=kwargs.get('planning_context', 'new_feature'),
                ai_requirements=kwargs.get('ai_requirements')
            )
            
            # Initialize AI use case
            task_repository = facade._task_repository
            ai_use_case = AITaskCreationUseCase(task_repository, facade)
            
            # Execute AI-enhanced task creation
            result = await ai_use_case.execute(ai_request)
            
            if result.get('success'):
                return self._response_formatter.create_success_response(
                    operation="ai_create",
                    data=result,
                    message="AI-enhanced task created successfully"
                )
            else:
                return self._response_formatter.create_error_response(
                    operation="ai_create",
                    error=result.get('error', 'AI task creation failed'),
                    error_code=ErrorCodes.OPERATION_FAILED
                )
        
        except Exception as e:
            logger.error(f"AI create operation failed: {e}")
            return self._response_formatter.create_error_response(
                operation="ai_create",
                error=f"AI task creation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    async def ai_enhance(self, facade, **kwargs) -> Dict[str, Any]:
        """
        Enhance an existing task with AI insights.
        
        Parameters:
        - task_id (str): Task ID to enhance
        - analyze_complexity (bool, optional): Analyze task complexity
        - suggest_optimizations (bool, optional): Suggest optimizations
        - identify_risks (bool, optional): Identify potential risks
        """
        try:
            task_id = kwargs.get('task_id')
            if not task_id:
                return self._response_formatter.create_error_response(
                    operation="ai_enhance",
                    error="Missing required parameter: task_id",
                    error_code=ErrorCodes.VALIDATION_ERROR
                )
            
            # Initialize AI use case
            task_repository = facade._task_repository
            ai_use_case = AITaskCreationUseCase(task_repository, facade)
            
            # Set enhancement options
            enhancement_options = {
                'analyze_complexity': kwargs.get('analyze_complexity', True),
                'suggest_optimizations': kwargs.get('suggest_optimizations', True),
                'identify_risks': kwargs.get('identify_risks', True)
            }
            
            # Execute AI enhancement
            result = await ai_use_case.enhance_existing_task(task_id, enhancement_options)
            
            if result.get('success'):
                return self._response_formatter.create_success_response(
                    operation="ai_enhance",
                    data=result,
                    message="Task enhanced with AI insights"
                )
            else:
                return self._response_formatter.create_error_response(
                    operation="ai_enhance",
                    error=result.get('error', 'AI enhancement failed'),
                    error_code=ErrorCodes.OPERATION_FAILED
                )
        
        except Exception as e:
            logger.error(f"AI enhance operation failed: {e}")
            return self._response_formatter.create_error_response(
                operation="ai_enhance",
                error=f"AI enhancement failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    async def ai_analyze(self, facade, **kwargs) -> Dict[str, Any]:
        """
        Analyze requirements without creating tasks.
        
        Parameters:
        - requirements (str): Requirements to analyze
        - context (str, optional): Analysis context
        """
        try:
            requirements = kwargs.get('requirements')
            if not requirements:
                return self._response_formatter.create_error_response(
                    operation="ai_analyze",
                    error="Missing required parameter: requirements",
                    error_code=ErrorCodes.VALIDATION_ERROR
                )
            
            # Initialize AI integration service
            ai_service = AITaskIntegrationService(facade)
            
            # Use the requirement analyzer directly
            requirement_items = ai_service._parse_requirements(requirements)
            analyzed_requirements = ai_service.ai_planning_service.requirement_analyzer.analyze_requirements_batch(
                requirement_items
            )
            
            # Generate insights
            insights = ai_service.ai_planning_service.requirement_analyzer.generate_planning_insights(
                analyzed_requirements
            )
            
            analysis_result = {
                'total_requirements': len(analyzed_requirements),
                'analysis_summary': insights,
                'detailed_analysis': [
                    {
                        'requirement_id': analysis.original_requirement.id,
                        'description': analysis.original_requirement.description,
                        'detected_patterns': [p.value for p in analysis.detected_patterns],
                        'suggested_agents': analysis.suggested_agents,
                        'estimated_hours': analysis.estimated_effort_hours,
                        'risk_factors': analysis.risk_factors,
                        'technical_considerations': analysis.technical_considerations
                    } for analysis in analyzed_requirements
                ]
            }
            
            return self._response_formatter.create_success_response(
                operation="ai_analyze",
                data=analysis_result,
                message="Requirements analyzed successfully"
            )
        
        except Exception as e:
            logger.error(f"AI analyze operation failed: {e}")
            return self._response_formatter.create_error_response(
                operation="ai_analyze",
                error=f"Requirements analysis failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    async def ai_suggest_agents(self, facade, **kwargs) -> Dict[str, Any]:
        """
        Suggest optimal agents for requirements.
        
        Parameters:
        - requirements (str): Requirements to analyze
        - available_agents (str, optional): Available agents (comma-separated)
        """
        try:
            requirements = kwargs.get('requirements')
            if not requirements:
                return self._response_formatter.create_error_response(
                    operation="ai_suggest_agents",
                    error="Missing required parameter: requirements",
                    error_code=ErrorCodes.VALIDATION_ERROR
                )
            
            # Initialize AI integration service
            ai_service = AITaskIntegrationService(facade)
            
            # Analyze requirements to get agent suggestions
            requirement_items = ai_service._parse_requirements(requirements)
            analyzed_requirements = ai_service.ai_planning_service.requirement_analyzer.analyze_requirements_batch(
                requirement_items
            )
            insights = ai_service.ai_planning_service.requirement_analyzer.generate_planning_insights(
                analyzed_requirements
            )
            
            agent_recommendations = insights.get('agent_recommendations', {})
            
            # Filter by available agents if specified
            available_agents = kwargs.get('available_agents')
            if available_agents:
                available_list = [agent.strip() for agent in available_agents.split(',')]
                agent_recommendations = {
                    agent: count for agent, count in agent_recommendations.items()
                    if agent in available_list
                }
            
            suggestion_result = {
                'recommended_agents': agent_recommendations,
                'primary_agents': list(dict(sorted(agent_recommendations.items(), 
                                                 key=lambda x: x[1], reverse=True)[:3]).keys()),
                'team_size_recommendation': len(agent_recommendations),
                'specialization_needs': self._identify_specialization_needs(insights.get('pattern_distribution', {}))
            }
            
            return self._response_formatter.create_success_response(
                operation="ai_suggest_agents",
                data=suggestion_result,
                message="Agent suggestions generated successfully"
            )
        
        except Exception as e:
            logger.error(f"AI suggest agents operation failed: {e}")
            return self._response_formatter.create_error_response(
                operation="ai_suggest_agents",
                error=f"Agent suggestion failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    def _identify_specialization_needs(self, pattern_distribution: Dict[str, int]) -> List[str]:
        """Identify required specializations based on patterns"""
        
        specialization_map = {
            'user_authentication': 'Security expertise',
            'api_integration': 'API and integration knowledge',
            'ui_component': 'Frontend and UI/UX skills',
            'database_schema': 'Database design expertise',
            'performance_requirement': 'Performance optimization skills',
            'deployment': 'DevOps and deployment knowledge',
            'testing_requirement': 'Testing and QA expertise'
        }
        
        specializations = []
        for pattern, count in pattern_distribution.items():
            if count > 0 and pattern in specialization_map:
                specializations.append(specialization_map[pattern])
        
        return specializations