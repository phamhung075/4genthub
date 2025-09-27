"""AI Planning MCP Controller

MCP controller for AI task planning operations.
Integrates the AI planning engine with the existing MCP server.
"""

import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...domain.entities.planning_request import PlanningRequest, RequirementItem, PlanningContext
from ...application.services.ai_planning_service import AITaskPlanningService

class AITaskPlanningMCPController:
    """MCP controller for AI task planning operations"""
    
    def __init__(self):
        self.planning_service = AITaskPlanningService()
    
    async def create_ai_plan(self, **kwargs) -> Dict[str, Any]:
        """
        Create an AI-generated task plan from requirements.
        
        Parameters:
        - title (str): Title of the planning request
        - description (str): Description of what needs to be accomplished
        - requirements (str): JSON string or comma-separated list of requirements
        - git_branch_id (str): Git branch ID for the plan
        - project_id (str, optional): Project ID
        - context (str, optional): Planning context (new_feature, bug_fix, etc.)
        - deadline (str, optional): ISO date string for deadline
        - preferred_approach (str, optional): Preferred implementation approach
        - risk_tolerance (str, optional): Risk tolerance level (low, medium, high)
        - user_id (str, optional): User ID for the request
        """
        
        try:
            # Validate required parameters
            required_params = ['title', 'description', 'requirements', 'git_branch_id']
            for param in required_params:
                if param not in kwargs:
                    return {
                        'success': False,
                        'error': f'Missing required parameter: {param}',
                        'required_parameters': required_params
                    }
                # Allow empty string for requirements (will result in 0 requirements)
                if param != 'requirements' and not kwargs[param]:
                    return {
                        'success': False,
                        'error': f'Missing required parameter: {param}',
                        'required_parameters': required_params
                    }
            
            # Parse requirements
            requirements_data = kwargs['requirements']
            if isinstance(requirements_data, str):
                if requirements_data.startswith('[') or requirements_data.startswith('{'):
                    # JSON format
                    try:
                        requirements_list = json.loads(requirements_data)
                    except json.JSONDecodeError:
                        return {
                            'success': False,
                            'error': 'Invalid JSON format for requirements'
                        }
                else:
                    # Comma-separated format
                    requirements_list = [
                        {'description': req.strip(), 'priority': 'medium'}
                        for req in requirements_data.split(',') if req.strip()
                    ]
            elif isinstance(requirements_data, list):
                requirements_list = requirements_data
            else:
                return {
                    'success': False,
                    'error': 'Requirements must be JSON string, comma-separated string, or list'
                }
            
            # Create requirement items
            requirement_items = []
            for i, req_data in enumerate(requirements_list):
                if isinstance(req_data, str):
                    req_data = {'description': req_data, 'priority': 'medium'}
                
                requirement_item = RequirementItem(
                    id=f"req_{i+1}",
                    description=req_data.get('description', ''),
                    priority=req_data.get('priority', 'medium'),
                    acceptance_criteria=req_data.get('acceptance_criteria', []),
                    constraints=req_data.get('constraints', []),
                    related_files=req_data.get('related_files', [])
                )
                requirement_items.append(requirement_item)
            
            # Parse optional parameters
            context = PlanningContext(kwargs.get('context', 'new_feature'))
            deadline = None
            if kwargs.get('deadline'):
                try:
                    deadline = datetime.fromisoformat(kwargs['deadline'].replace('Z', '+00:00'))
                except ValueError:
                    return {
                        'success': False,
                        'error': 'Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                    }
            
            # Create planning request
            planning_request = PlanningRequest(
                id=str(uuid.uuid4()),
                title=kwargs['title'],
                description=kwargs['description'],
                requirements=requirement_items,
                context=context,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs['git_branch_id'],
                user_id=kwargs.get('user_id'),
                deadline=deadline,
                preferred_approach=kwargs.get('preferred_approach'),
                risk_tolerance=kwargs.get('risk_tolerance', 'medium')
            )
            
            # Generate AI plan
            task_plan = await self.planning_service.create_intelligent_plan(planning_request)
            
            # Execute plan (create MCP tasks)
            execution_result = await self.planning_service.execute_plan_with_mcp(
                task_plan, kwargs['git_branch_id']
            )
            
            return {
                'success': True,
                'planning_request': {
                    'id': planning_request.id,
                    'title': planning_request.title,
                    'description': planning_request.description,
                    'requirements_count': len(planning_request.requirements),
                    'context': planning_request.context.value,
                    'estimated_complexity': planning_request.estimate_overall_complexity().value
                },
                'task_plan': {
                    'id': task_plan.id,
                    'title': task_plan.title,
                    'description': task_plan.description,
                    'total_tasks': len(task_plan.tasks),
                    'total_estimated_hours': task_plan.total_estimated_hours,
                    'estimated_duration_days': task_plan.estimated_duration_days,
                    'confidence_score': task_plan.confidence_score,
                    'risk_level': task_plan.risk_level,
                    'required_agents': list(task_plan.required_agents),
                    'execution_phases': [phase.value for phase in task_plan.execution_phases],
                    'parallel_execution_groups': task_plan.parallel_execution_groups,
                    'critical_path': task_plan.critical_path,
                    'agent_workload': task_plan.agent_workload
                },
                'execution_result': execution_result,
                'recommendations': self._generate_recommendations(task_plan),
                'created_at': task_plan.created_at.isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI planning failed: {str(e)}',
                'error_type': type(e).__name__
            }
    
    async def get_plan_status(self, **kwargs) -> Dict[str, Any]:
        """
        Get status of an AI-generated plan.
        
        Parameters:
        - plan_id (str): ID of the task plan
        """
        
        # For now, return a placeholder response
        # In full implementation, this would query stored plans
        return {
            'success': True,
            'message': 'Plan status tracking not yet implemented',
            'available_operations': [
                'create_ai_plan',
                'analyze_requirements', 
                'estimate_effort',
                'suggest_agents',
                'validate_plan'
            ]
        }
    
    async def analyze_requirements(self, **kwargs) -> Dict[str, Any]:
        """
        Analyze requirements without creating a full plan.
        
        Parameters:
        - requirements (str): JSON string or comma-separated requirements
        - context (str, optional): Planning context
        """
        
        try:
            if 'requirements' not in kwargs:
                return {
                    'success': False,
                    'error': 'Missing required parameter: requirements'
                }
            
            # Parse requirements (similar to create_ai_plan)
            requirements_data = kwargs['requirements']
            if isinstance(requirements_data, str):
                if requirements_data.startswith('[') or requirements_data.startswith('{'):
                    # JSON format - try to parse, fall back to comma-separated on error
                    try:
                        requirements_list = json.loads(requirements_data)
                    except json.JSONDecodeError:
                        # Fall back to comma-separated parsing
                        requirements_list = [
                            {'description': req.strip(), 'priority': 'medium'}
                            for req in requirements_data.split(',') if req.strip()
                        ]
                else:
                    requirements_list = [
                        {'description': req.strip(), 'priority': 'medium'}
                        for req in requirements_data.split(',') if req.strip()
                    ]
            else:
                requirements_list = requirements_data
            
            # Create requirement items
            requirement_items = []
            for i, req_data in enumerate(requirements_list):
                if isinstance(req_data, str):
                    req_data = {'description': req_data, 'priority': 'medium'}
                
                requirement_item = RequirementItem(
                    id=f"req_{i+1}",
                    description=req_data.get('description', ''),
                    priority=req_data.get('priority', 'medium'),
                    acceptance_criteria=req_data.get('acceptance_criteria', []),
                    constraints=req_data.get('constraints', [])
                )
                requirement_items.append(requirement_item)
            
            # Analyze requirements
            analyzed_requirements = self.planning_service.requirement_analyzer.analyze_requirements_batch(
                requirement_items
            )
            
            # Generate insights
            insights = self.planning_service.requirement_analyzer.generate_planning_insights(
                analyzed_requirements
            )
            
            return {
                'success': True,
                'analysis': {
                    'total_requirements': len(analyzed_requirements),
                    'total_estimated_hours': insights['total_estimated_hours'],
                    'pattern_distribution': insights['pattern_distribution'],
                    'agent_recommendations': insights['agent_recommendations'],
                    'complexity_distribution': insights['complexity_distribution'],
                    'risk_summary': insights['risk_summary'],
                    'suggested_phases': insights['suggested_phases']
                },
                'detailed_analysis': [
                    {
                        'requirement_id': analysis.original_requirement.id,
                        'description': analysis.original_requirement.description,
                        'detected_patterns': [p.value for p in analysis.detected_patterns],
                        'suggested_agents': analysis.suggested_agents,
                        'estimated_hours': analysis.estimated_effort_hours,
                        'risk_factors': analysis.risk_factors,
                        'technical_considerations': analysis.technical_considerations,
                        'complexity_indicators': analysis.complexity_indicators
                    } for analysis in analyzed_requirements
                ]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Requirement analysis failed: {str(e)}',
                'error_type': type(e).__name__
            }
    
    async def estimate_effort(self, **kwargs) -> Dict[str, Any]:
        """
        Estimate effort for a set of requirements.
        
        Parameters:
        - requirements (str): Requirements to analyze
        - include_breakdown (bool, optional): Include detailed breakdown
        """
        
        try:
            # Reuse requirement analysis
            analysis_result = await self.analyze_requirements(**kwargs)
            
            if not analysis_result['success']:
                return analysis_result
            
            analysis = analysis_result['analysis']
            include_breakdown = kwargs.get('include_breakdown', False)
            
            result = {
                'success': True,
                'effort_estimate': {
                    'total_hours': analysis['total_estimated_hours'],
                    'total_days': round(analysis['total_estimated_hours'] / 8, 1),
                    'total_weeks': round(analysis['total_estimated_hours'] / 40, 1),
                    'complexity_breakdown': analysis['complexity_distribution'],
                    'confidence_level': self._calculate_estimation_confidence(analysis)
                }
            }
            
            if include_breakdown:
                result['detailed_breakdown'] = analysis_result['detailed_analysis']
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Effort estimation failed: {str(e)}'
            }
    
    async def suggest_agents(self, **kwargs) -> Dict[str, Any]:
        """
        Suggest optimal agents for requirements.
        
        Parameters:
        - requirements (str): Requirements to analyze
        - available_agents (str, optional): Comma-separated list of available agents
        """
        
        try:
            analysis_result = await self.analyze_requirements(**kwargs)
            
            if not analysis_result['success']:
                return analysis_result
            
            agent_recommendations = analysis_result['analysis']['agent_recommendations']
            
            # Filter by available agents if specified
            available_agents = None
            if kwargs.get('available_agents'):
                available_agents = [agent.strip() for agent in kwargs['available_agents'].split(',')]
                if available_agents:
                    agent_recommendations = {
                        agent: count for agent, count in agent_recommendations.items()
                        if agent in available_agents
                    }
            
            return {
                'success': True,
                'agent_suggestions': {
                    'recommended_agents': agent_recommendations,
                    'primary_agents': list(dict(sorted(agent_recommendations.items(), 
                                                    key=lambda x: x[1], reverse=True)[:3]).keys()),
                    'workload_distribution': self._estimate_agent_workload(
                        agent_recommendations, analysis_result['analysis']['total_estimated_hours']
                    ),
                    'team_size_recommendation': len(agent_recommendations),
                    'specialization_needs': self._identify_specialization_needs(
                        analysis_result['analysis']['pattern_distribution']
                    )
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Agent suggestion failed: {str(e)}'
            }
    
    async def validate_plan(self, **kwargs) -> Dict[str, Any]:
        """
        Validate a task plan for consistency.
        
        Parameters:
        - plan_data (str): JSON representation of the plan to validate
        """
        
        # Placeholder for plan validation
        return {
            'success': True,
            'message': 'Plan validation not yet implemented',
            'available_validations': [
                'dependency_cycles',
                'agent_availability',
                'resource_conflicts',
                'timeline_feasibility',
                'requirement_coverage'
            ]
        }
    
    def _generate_recommendations(self, task_plan) -> List[str]:
        """Generate recommendations based on the task plan"""
        recommendations = []
        
        if task_plan.confidence_score < 0.6:
            recommendations.append("Consider adding more detailed requirements to improve plan accuracy")
        
        if task_plan.total_estimated_hours > 80:
            recommendations.append("Large project - consider breaking into smaller phases")
        
        if len(task_plan.required_agents) > 5:
            recommendations.append("Many agents required - ensure coordination mechanisms are in place")
        
        if task_plan.risk_level in ['high', 'critical']:
            recommendations.append("High risk project - implement additional monitoring and checkpoints")
        
        agent_workload = task_plan.agent_workload
        overloaded_agents = [agent for agent, hours in agent_workload.items() if hours > 40]
        if overloaded_agents:
            recommendations.append(f"Agents may be overloaded: {', '.join(overloaded_agents)}")
        
        return recommendations
    
    def _calculate_estimation_confidence(self, analysis: Dict[str, Any]) -> str:
        """Calculate confidence level for effort estimation"""
        
        pattern_count = len(analysis['pattern_distribution'])
        total_hours = analysis['total_estimated_hours']
        
        if pattern_count >= 3 and 10 <= total_hours <= 100:
            return 'high'
        elif pattern_count >= 2 and 5 <= total_hours <= 200:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_agent_workload(self, agent_recommendations: Dict[str, int], 
                                total_hours: float) -> Dict[str, float]:
        """Estimate workload distribution among agents"""
        
        total_weight = sum(agent_recommendations.values())
        if total_weight == 0:
            return {}
        
        return {
            agent: round((count / total_weight) * total_hours, 1)
            for agent, count in agent_recommendations.items()
        }
    
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