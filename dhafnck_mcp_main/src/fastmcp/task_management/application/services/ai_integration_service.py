"""AI Integration Service

Bridge between AI planning engine and MCP task management system.
Provides seamless integration for AI-enhanced task operations.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ....ai_task_planning.application.services.ai_planning_service import AITaskPlanningService
from ....ai_task_planning.domain.entities.planning_request import PlanningRequest, RequirementItem, PlanningContext
from ....ai_task_planning.domain.entities.task_plan import TaskPlan, PlannedTask
from ..dtos.task.create_task_request import CreateTaskRequest
from ..facades.task_application_facade import TaskApplicationFacade

logger = logging.getLogger(__name__)

class AITaskIntegrationService:
    """
    Service that integrates AI task planning with the existing MCP task management system.
    
    This service acts as a bridge between:
    - AI Planning Engine (ai_task_planning module)
    - MCP Task Management System (task_management module)
    """
    
    def __init__(self, task_facade: TaskApplicationFacade):
        self.task_facade = task_facade
        self.ai_planning_service = AITaskPlanningService(task_facade)
        
    async def create_ai_enhanced_task_plan(self, requirements: str, title: str, 
                                          description: str, git_branch_id: str,
                                          context: str = 'new_feature',
                                          auto_create_tasks: bool = True,
                                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create an AI-enhanced task plan and optionally create MCP tasks.
        
        Args:
            requirements: High-level requirements (JSON or comma-separated)
            title: Plan title
            description: Plan description  
            git_branch_id: Git branch ID for task creation
            context: Planning context (new_feature, bug_fix, etc.)
            auto_create_tasks: Whether to automatically create MCP tasks
            user_id: User ID for task creation
            
        Returns:
            Dictionary with plan details and created tasks
        """
        try:
            # Parse requirements into structured format
            requirement_items = self._parse_requirements(requirements)
            
            # Create planning request
            planning_request = PlanningRequest(
                id=str(uuid.uuid4()),
                title=title,
                description=description,
                requirements=requirement_items,
                context=PlanningContext(context),
                git_branch_id=git_branch_id,
                user_id=user_id
            )
            
            # Generate AI task plan
            task_plan = await self.ai_planning_service.create_intelligent_plan(planning_request)
            
            logger.info(f"Generated AI task plan with {len(task_plan.tasks)} tasks")
            
            # Optionally create MCP tasks
            created_tasks = []
            if auto_create_tasks:
                created_tasks = await self._create_mcp_tasks_from_plan(task_plan, git_branch_id, user_id)
            
            return {
                'success': True,
                'planning_request': {
                    'id': planning_request.id,
                    'title': planning_request.title,
                    'description': planning_request.description,
                    'requirements_count': len(planning_request.requirements),
                    'context': planning_request.context.value
                },
                'task_plan': {
                    'id': task_plan.id,
                    'title': task_plan.title,
                    'total_tasks': len(task_plan.tasks),
                    'total_estimated_hours': task_plan.total_estimated_hours,
                    'estimated_duration_days': task_plan.estimated_duration_days,
                    'confidence_score': task_plan.confidence_score,
                    'required_agents': list(task_plan.required_agents),
                    'agent_workload': task_plan.agent_workload
                },
                'created_tasks': created_tasks,
                'ai_insights': self._generate_ai_insights(task_plan)
            }
            
        except Exception as e:
            logger.error(f"AI task plan creation failed: {e}")
            return {
                'success': False,
                'error': f'AI task planning failed: {str(e)}',
                'error_type': type(e).__name__
            }
    
    async def enhance_task_creation(self, create_request: CreateTaskRequest, 
                                   enable_ai_breakdown: bool = False,
                                   enable_smart_assignment: bool = False) -> Dict[str, Any]:
        """
        Enhance task creation with AI capabilities.
        
        Args:
            create_request: Original task creation request
            enable_ai_breakdown: Whether to use AI for task breakdown
            enable_smart_assignment: Whether to use AI for agent assignment
            
        Returns:
            Enhanced task creation result with AI insights
        """
        try:
            # Create the main task first
            main_task_result = self.task_facade.create_task(create_request)
            
            if not main_task_result.get('success'):
                return main_task_result
            
            main_task_id = main_task_result['task']['id']
            logger.info(f"Created main task {main_task_id}, applying AI enhancements")
            
            ai_enhancements = {}
            
            # Apply AI breakdown if requested
            if enable_ai_breakdown and create_request.description:
                breakdown_result = await self._generate_task_breakdown(
                    create_request.description,
                    main_task_id,
                    create_request.git_branch_id
                )
                ai_enhancements['breakdown'] = breakdown_result
            
            # Apply smart agent assignment if requested
            if enable_smart_assignment:
                assignment_result = await self._suggest_optimal_agents(
                    create_request.title + " " + (create_request.description or "")
                )
                ai_enhancements['agent_suggestions'] = assignment_result
            
            # Add AI insights to the response
            main_task_result['ai_enhancements'] = ai_enhancements
            main_task_result['ai_enhanced'] = True
            
            return main_task_result
            
        except Exception as e:
            logger.error(f"AI task enhancement failed: {e}")
            return {
                'success': False,
                'error': f'AI enhancement failed: {str(e)}'
            }
    
    async def add_ai_insights_to_task_response(self, task_data: Dict[str, Any], 
                                              action: str = "get") -> Dict[str, Any]:
        """
        Add AI insights to existing task response.
        
        Args:
            task_data: Existing task data
            action: MCP action being performed
            
        Returns:
            Task data enhanced with AI insights
        """
        try:
            if not task_data.get('success') or not task_data.get('task'):
                return task_data
            
            task = task_data['task']
            task_title = task.get('title', '')
            task_description = task.get('description', '')
            
            # Generate AI insights based on task content
            insights = await self._generate_task_insights(task_title, task_description, action)
            
            # Add insights to response
            task_data['ai_insights'] = insights
            task_data['enhanced_by_ai'] = True
            
            return task_data
            
        except Exception as e:
            logger.warning(f"Failed to add AI insights: {e}")
            # Return original data if AI insights fail
            return task_data
    
    def _parse_requirements(self, requirements: str) -> List[RequirementItem]:
        """Parse requirements string into structured RequirementItem objects"""
        import json
        
        requirement_items = []
        
        try:
            if requirements.startswith('[') or requirements.startswith('{'):
                # JSON format
                requirements_data = json.loads(requirements)
            else:
                # Comma-separated format
                requirements_data = [
                    {'description': req.strip(), 'priority': 'medium'}
                    for req in requirements.split(',') if req.strip()
                ]
            
            for i, req_data in enumerate(requirements_data):
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
                
        except json.JSONDecodeError:
            logger.warning("Invalid JSON requirements, treating as single requirement")
            requirement_items = [RequirementItem(
                id="req_1",
                description=requirements,
                priority='medium'
            )]
        
        return requirement_items
    
    async def _create_mcp_tasks_from_plan(self, task_plan: TaskPlan, git_branch_id: str,
                                         user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create MCP tasks from AI-generated task plan"""
        created_tasks = []
        
        # Get root tasks first (tasks without parent)
        root_tasks = [task for task in task_plan.tasks if not task.parent_task_id]
        
        for planned_task in root_tasks:
            try:
                # Create MCP task request
                create_request = CreateTaskRequest(
                    title=planned_task.title,
                    description=planned_task.description or "AI-generated task",
                    status='todo',
                    priority=planned_task.priority or 'medium',
                    git_branch_id=git_branch_id,
                    assignees=[planned_task.agent_assignment.agent_id] if planned_task.agent_assignment else [],
                    estimated_effort=f"{planned_task.estimated_hours} hours" if planned_task.estimated_hours else None,
                    details=f"AI-generated task from plan {task_plan.id}. Estimated complexity: {planned_task.estimated_complexity}",
                    user_id=user_id
                )
                
                # Create the task
                result = self.task_facade.create_task(create_request)
                
                if result.get('success'):
                    mcp_task_id = result['task']['id']
                    planned_task.mcp_task_id = mcp_task_id
                    
                    created_tasks.append({
                        'planned_task_id': planned_task.id,
                        'mcp_task_id': mcp_task_id,
                        'title': planned_task.title,
                        'agent_assignment': planned_task.agent_assignment.agent_id if planned_task.agent_assignment else None,
                        'estimated_hours': planned_task.estimated_hours
                    })
                    
                    logger.info(f"Created MCP task {mcp_task_id} from planned task {planned_task.id}")
                else:
                    logger.error(f"Failed to create MCP task for planned task {planned_task.id}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error creating MCP task from planned task {planned_task.id}: {e}")
        
        return created_tasks
    
    async def _generate_task_breakdown(self, description: str, parent_task_id: str,
                                     git_branch_id: str) -> Dict[str, Any]:
        """Generate AI-powered task breakdown"""
        # This would use the requirement analyzer to break down the task
        # For now, return a placeholder
        return {
            'analysis': 'AI breakdown not yet implemented',
            'suggested_subtasks': [],
            'estimated_effort': 'TBD',
            'recommended_approach': 'Standard implementation'
        }
    
    async def _suggest_optimal_agents(self, task_content: str) -> Dict[str, Any]:
        """Suggest optimal agents based on task content"""
        # This would use agent intelligence to suggest assignments
        # For now, return basic suggestions
        suggestions = []
        
        if any(keyword in task_content.lower() for keyword in ['ui', 'frontend', 'component', 'interface']):
            suggestions.append('ui-specialist-agent')
        elif any(keyword in task_content.lower() for keyword in ['test', 'testing', 'qa']):
            suggestions.append('test-orchestrator-agent')
        elif any(keyword in task_content.lower() for keyword in ['security', 'auth', 'authentication']):
            suggestions.append('security-auditor-agent')
        elif any(keyword in task_content.lower() for keyword in ['debug', 'fix', 'bug', 'error']):
            suggestions.append('debugger-agent')
        else:
            suggestions.append('coding-agent')
        
        return {
            'suggested_agents': suggestions,
            'reasoning': 'Based on keyword analysis',
            'confidence': 0.7
        }
    
    async def _generate_task_insights(self, title: str, description: str, action: str) -> Dict[str, Any]:
        """Generate AI insights for a task"""
        insights = {
            'complexity_analysis': self._analyze_complexity(title, description),
            'suggested_next_actions': self._suggest_next_actions(action),
            'potential_risks': self._identify_risks(title, description),
            'optimization_suggestions': self._suggest_optimizations(title, description)
        }
        
        return insights
    
    def _analyze_complexity(self, title: str, description: str) -> Dict[str, Any]:
        """Analyze task complexity"""
        content = f"{title} {description}".lower()
        
        # Simple complexity analysis based on keywords
        complex_keywords = ['integration', 'migration', 'refactor', 'architecture', 'system', 'complex']
        medium_keywords = ['implement', 'create', 'add', 'update', 'modify']
        
        complexity_score = 0
        for keyword in complex_keywords:
            if keyword in content:
                complexity_score += 2
        
        for keyword in medium_keywords:
            if keyword in content:
                complexity_score += 1
        
        if complexity_score >= 4:
            level = 'high'
        elif complexity_score >= 2:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'level': level,
            'score': complexity_score,
            'factors': 'Keyword-based analysis'
        }
    
    def _suggest_next_actions(self, action: str) -> List[str]:
        """Suggest next actions based on current action"""
        suggestions = {
            'create': [
                'Define detailed acceptance criteria',
                'Break down into smaller tasks if complex',
                'Assign to appropriate agent',
                'Set realistic timeline'
            ],
            'get': [
                'Review task progress',
                'Check for blockers',
                'Update status if needed',
                'Coordinate with team members'
            ],
            'update': [
                'Validate changes',
                'Notify stakeholders',
                'Update dependent tasks',
                'Track progress metrics'
            ],
            'complete': [
                'Conduct final review',
                'Update documentation',
                'Notify dependent tasks',
                'Archive artifacts'
            ]
        }
        
        return suggestions.get(action, ['Continue with standard workflow'])
    
    def _identify_risks(self, title: str, description: str) -> List[str]:
        """Identify potential risks"""
        content = f"{title} {description}".lower()
        risks = []
        
        if any(keyword in content for keyword in ['integration', 'migration', 'refactor']):
            risks.append('High complexity may lead to scope creep')
            
        if any(keyword in content for keyword in ['database', 'schema', 'data']):
            risks.append('Data integrity concerns')
            
        if any(keyword in content for keyword in ['security', 'auth', 'authentication']):
            risks.append('Security implications require careful review')
            
        if any(keyword in content for keyword in ['api', 'external', 'third-party']):
            risks.append('External dependencies may cause delays')
        
        return risks if risks else ['No significant risks identified']
    
    def _suggest_optimizations(self, title: str, description: str) -> List[str]:
        """Suggest optimization opportunities"""
        content = f"{title} {description}".lower()
        optimizations = []
        
        if 'performance' in content:
            optimizations.append('Consider caching strategies')
            
        if any(keyword in content for keyword in ['ui', 'frontend', 'component']):
            optimizations.append('Implement component reusability')
            
        if any(keyword in content for keyword in ['test', 'testing']):
            optimizations.append('Automate test execution')
            
        if any(keyword in content for keyword in ['database', 'query']):
            optimizations.append('Optimize database queries')
        
        return optimizations if optimizations else ['Standard implementation approach']
    
    def _generate_ai_insights(self, task_plan: TaskPlan) -> Dict[str, Any]:
        """Generate high-level AI insights for the task plan"""
        return {
            'plan_quality': {
                'confidence_score': task_plan.confidence_score,
                'risk_level': task_plan.risk_level,
                'completeness': 'High' if len(task_plan.tasks) > 3 else 'Medium'
            },
            'execution_recommendations': [
                f'Plan involves {len(task_plan.required_agents)} specialized agents',
                f'Estimated duration: {task_plan.estimated_duration_days} days',
                f'Total effort: {task_plan.total_estimated_hours} hours'
            ],
            'success_factors': [
                'AI-generated task breakdown ensures comprehensive coverage',
                'Intelligent agent assignments optimize skill utilization',
                'Dependency analysis prevents bottlenecks'
            ]
        }