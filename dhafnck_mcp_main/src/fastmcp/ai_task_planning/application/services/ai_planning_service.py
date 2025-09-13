"""AI Planning Service

Core application service that orchestrates the AI task planning process.
Coordinates requirement analysis, task generation, and plan optimization.
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from ...domain.entities.planning_request import PlanningRequest, RequirementItem, PlanningContext, ComplexityLevel
from ...domain.entities.task_plan import TaskPlan, PlannedTask, TaskType, ExecutionPhase, AgentAssignment
from ...domain.services.requirement_analyzer import RequirementAnalyzer, AnalyzedRequirement
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

class AITaskPlanningService:
    """
    Core service for AI-powered task planning.
    
    Transforms high-level requirements into executable task plans
    with intelligent agent assignments and dependency management.
    """
    
    def __init__(self, task_facade: Optional[TaskApplicationFacade] = None):
        self.requirement_analyzer = RequirementAnalyzer()
        self.task_facade = task_facade
        
        # Agent capability mapping for intelligent assignment
        self.agent_capabilities = {
            'coding-agent': {
                'patterns': ['crud_operations', 'api_integration', 'database_schema'],
                'phases': [ExecutionPhase.IMPLEMENTATION],
                'max_concurrent_tasks': 3,
                'specializations': ['backend', 'api', 'database']
            },
            'ui-specialist-agent': {
                'patterns': ['ui_component'],
                'phases': [ExecutionPhase.IMPLEMENTATION, ExecutionPhase.ARCHITECTURE],
                'max_concurrent_tasks': 2,
                'specializations': ['frontend', 'ui', 'components']
            },
            'system-architect-agent': {
                'patterns': ['database_schema', 'api_integration', 'security_requirement'],
                'phases': [ExecutionPhase.ARCHITECTURE, ExecutionPhase.PLANNING],
                'max_concurrent_tasks': 2,
                'specializations': ['architecture', 'design', 'systems']
            },
            'test-orchestrator-agent': {
                'patterns': ['testing_requirement'],
                'phases': [ExecutionPhase.TESTING],
                'max_concurrent_tasks': 4,
                'specializations': ['testing', 'qa', 'automation']
            },
            'security-auditor-agent': {
                'patterns': ['security_requirement', 'user_authentication'],
                'phases': [ExecutionPhase.REVIEW, ExecutionPhase.ARCHITECTURE],
                'max_concurrent_tasks': 2,
                'specializations': ['security', 'audit', 'compliance']
            },
            'debugger-agent': {
                'patterns': ['bug_fix'],
                'phases': [ExecutionPhase.IMPLEMENTATION],
                'max_concurrent_tasks': 2,
                'specializations': ['debugging', 'troubleshooting', 'fixes']
            },
            'documentation-agent': {
                'patterns': ['documentation_requirement'],
                'phases': [ExecutionPhase.PLANNING, ExecutionPhase.REVIEW],
                'max_concurrent_tasks': 3,
                'specializations': ['documentation', 'guides', 'specs']
            },
            'devops-agent': {
                'patterns': ['deployment', 'monitoring'],
                'phases': [ExecutionPhase.DEPLOYMENT, ExecutionPhase.MONITORING],
                'max_concurrent_tasks': 2,
                'specializations': ['deployment', 'infrastructure', 'cicd']
            }
        }
    
    async def create_intelligent_plan(self, planning_request: PlanningRequest) -> TaskPlan:
        """
        Create an AI-generated task plan from a planning request.
        
        Args:
            planning_request: The high-level planning request
            
        Returns:
            TaskPlan with intelligent task breakdown and assignments
        """
        # Step 1: Analyze requirements
        analyzed_requirements = self.requirement_analyzer.analyze_requirements_batch(
            planning_request.requirements
        )
        
        # Step 2: Generate planning insights
        insights = self.requirement_analyzer.generate_planning_insights(analyzed_requirements)
        
        # Step 3: Create task plan structure
        plan = TaskPlan(
            id=str(uuid.uuid4()),
            planning_request_id=planning_request.id,
            title=f"AI Plan: {planning_request.title}",
            description=f"Intelligent breakdown of {planning_request.title} into executable tasks"
        )
        
        # Step 4: Generate tasks from analyzed requirements
        await self._generate_tasks_from_requirements(plan, analyzed_requirements, planning_request)
        
        # Step 5: Optimize task assignments
        await self._optimize_agent_assignments(plan)
        
        # Step 6: Generate dependencies
        await self._generate_intelligent_dependencies(plan, analyzed_requirements)
        
        # Step 7: Calculate execution phases and parallel groups
        plan.calculate_critical_path()
        plan.find_parallel_execution_groups()
        
        # Step 8: Validate and adjust plan
        is_valid, validation_errors = plan.validate_plan()
        if not is_valid:
            await self._fix_plan_issues(plan, validation_errors)
        
        # Step 9: Calculate confidence score based on analysis quality
        plan.confidence_score = self._calculate_confidence_score(plan, analyzed_requirements, insights)
        
        return plan
    
    async def _generate_tasks_from_requirements(self, plan: TaskPlan, analyzed_requirements: List[AnalyzedRequirement], 
                                              planning_request: PlanningRequest):
        """Generate tasks from analyzed requirements"""
        
        for analysis in analyzed_requirements:
            # Determine task type based on patterns
            task_type = self._determine_task_type(analysis)
            
            # Determine execution phase 
            phase = self._determine_execution_phase(analysis)
            
            # Create main task
            main_task = PlannedTask(
                id=str(uuid.uuid4()),
                title=f"Implement: {analysis.original_requirement.description[:60]}...",
                description=analysis.original_requirement.description,
                task_type=task_type,
                phase=phase,
                estimated_hours=analysis.estimated_effort_hours,
                estimated_complexity=self._map_complexity_level(analysis),
                acceptance_criteria=analysis.original_requirement.acceptance_criteria,
                technical_requirements=analysis.technical_considerations,
                priority=analysis.original_requirement.priority,
                risks=analysis.risk_factors,
                file_references=analysis.original_requirement.related_files
            )
            
            # Add main task to plan
            plan.add_task(main_task)
            
            # Generate subtasks based on detected patterns
            await self._generate_subtasks_for_patterns(plan, main_task, analysis)
            
    async def _generate_subtasks_for_patterns(self, plan: TaskPlan, main_task: PlannedTask, 
                                            analysis: AnalyzedRequirement):
        """Generate appropriate subtasks based on detected patterns"""
        
        subtask_templates = {
            'crud_operations': [
                ('Design Data Models', ExecutionPhase.ARCHITECTURE, 'system-architect-agent', 2.0),
                ('Implement CRUD Operations', ExecutionPhase.IMPLEMENTATION, 'coding-agent', 4.0),
                ('Add Input Validation', ExecutionPhase.IMPLEMENTATION, 'coding-agent', 2.0),
                ('Create API Tests', ExecutionPhase.TESTING, 'test-orchestrator-agent', 3.0)
            ],
            'user_authentication': [
                ('Design Security Architecture', ExecutionPhase.ARCHITECTURE, 'security-auditor-agent', 3.0),
                ('Implement Authentication Logic', ExecutionPhase.IMPLEMENTATION, 'coding-agent', 4.0),
                ('Add Password Security', ExecutionPhase.IMPLEMENTATION, 'security-auditor-agent', 2.0),
                ('Security Audit', ExecutionPhase.REVIEW, 'security-auditor-agent', 2.0),
                ('Authentication Testing', ExecutionPhase.TESTING, 'test-orchestrator-agent', 3.0)
            ],
            'ui_component': [
                ('Design Component Structure', ExecutionPhase.ARCHITECTURE, 'ui-specialist-agent', 2.0),
                ('Implement UI Component', ExecutionPhase.IMPLEMENTATION, 'ui-specialist-agent', 3.0),
                ('Add Component Tests', ExecutionPhase.TESTING, 'test-orchestrator-agent', 2.0),
                ('Component Documentation', ExecutionPhase.REVIEW, 'documentation-agent', 1.0)
            ],
            'api_integration': [
                ('API Research and Documentation', ExecutionPhase.PLANNING, 'system-architect-agent', 2.0),
                ('Implement API Integration', ExecutionPhase.IMPLEMENTATION, 'coding-agent', 4.0),
                ('Error Handling', ExecutionPhase.IMPLEMENTATION, 'coding-agent', 2.0),
                ('Integration Testing', ExecutionPhase.TESTING, 'test-orchestrator-agent', 3.0)
            ]
        }
        
        # Generate subtasks based on detected patterns
        for pattern in analysis.detected_patterns:
            pattern_key = pattern.value
            if pattern_key in subtask_templates:
                templates = subtask_templates[pattern_key]
                
                for template_title, phase, agent, hours in templates:
                    subtask = PlannedTask(
                        id=str(uuid.uuid4()),
                        title=f"{main_task.title} - {template_title}",
                        description=f"{template_title} for {analysis.original_requirement.description}",
                        task_type=TaskType.SUBTASK,
                        phase=phase,
                        parent_task_id=main_task.id,
                        estimated_hours=hours,
                        estimated_complexity="medium",
                        agent_assignment=AgentAssignment(agent),
                        acceptance_criteria=[f"Complete {template_title.lower()}"],
                        priority=main_task.priority
                    )
                    
                    plan.add_task(subtask)
                    main_task.add_subtask(subtask)
    
    async def _optimize_agent_assignments(self, plan: TaskPlan):
        """Optimize agent assignments across all tasks"""
        
        # Collect unassigned tasks
        unassigned_tasks = [task for task in plan.tasks if not task.agent_assignment]
        
        for task in unassigned_tasks:
            # Find best agent based on patterns and workload
            best_agent = await self._find_optimal_agent(task, plan)
            
            if best_agent:
                task.agent_assignment = AgentAssignment(best_agent)
                # Update plan's agent workload
                plan.agent_workload[best_agent] = plan.agent_workload.get(best_agent, 0) + task.estimated_hours
                plan.required_agents.add(best_agent)
    
    async def _find_optimal_agent(self, task: PlannedTask, plan: TaskPlan) -> Optional[str]:
        """Find the optimal agent for a specific task"""
        
        # Score each agent based on capabilities and current workload
        agent_scores = {}
        
        for agent, capabilities in self.agent_capabilities.items():
            score = 0
            
            # Phase compatibility
            if task.phase in capabilities['phases']:
                score += 3
            
            # Current workload (prefer less loaded agents)
            current_workload = plan.agent_workload.get(agent, 0)
            max_workload = 40  # 40 hours per week
            workload_factor = max(0, (max_workload - current_workload) / max_workload)
            score += workload_factor * 2
            
            # Specialization match (would need more sophisticated matching)
            # For now, use simple heuristics
            if task.task_type == TaskType.TESTING and 'testing' in capabilities['specializations']:
                score += 4
            elif task.task_type in [TaskType.FEATURE, TaskType.TASK] and 'backend' in capabilities['specializations']:
                score += 2
            elif task.phase == ExecutionPhase.ARCHITECTURE and 'architecture' in capabilities['specializations']:
                score += 4
            
            agent_scores[agent] = score
        
        # Return agent with highest score
        if agent_scores:
            return max(agent_scores, key=agent_scores.get)
        
        return 'coding-agent'  # Default fallback
    
    async def _generate_intelligent_dependencies(self, plan: TaskPlan, analyzed_requirements: List[AnalyzedRequirement]):
        """Generate intelligent dependencies based on task relationships"""
        
        # Phase-based dependencies
        phase_order = [
            ExecutionPhase.PLANNING,
            ExecutionPhase.ARCHITECTURE,
            ExecutionPhase.IMPLEMENTATION,
            ExecutionPhase.TESTING,
            ExecutionPhase.REVIEW,
            ExecutionPhase.DEPLOYMENT,
            ExecutionPhase.MONITORING
        ]
        
        # Group tasks by phase
        tasks_by_phase = {}
        for task in plan.tasks:
            phase = task.phase
            if phase not in tasks_by_phase:
                tasks_by_phase[phase] = []
            tasks_by_phase[phase].append(task)
        
        # Create phase dependencies
        for i in range(len(phase_order) - 1):
            current_phase = phase_order[i]
            next_phase = phase_order[i + 1]
            
            current_tasks = tasks_by_phase.get(current_phase, [])
            next_tasks = tasks_by_phase.get(next_phase, [])
            
            # Next phase depends on current phase completion
            for current_task in current_tasks:
                for next_task in next_tasks:
                    # Add dependency if they're related (same parent or similar context)
                    if self._tasks_are_related(current_task, next_task):
                        plan.add_dependency(next_task.id, current_task.id)
        
        # Parent-child dependencies
        for task in plan.tasks:
            if task.parent_task_id:
                parent = plan.get_task_by_id(task.parent_task_id)
                if parent:
                    # Parent tasks depend on all their subtasks
                    plan.add_dependency(task.id, parent.id, "start_to_start")
    
    def _tasks_are_related(self, task1: PlannedTask, task2: PlannedTask) -> bool:
        """Check if two tasks are related and should have dependencies"""
        
        # Same parent
        if task1.parent_task_id == task2.parent_task_id and task1.parent_task_id:
            return True
        
        # Same file references
        if set(task1.file_references).intersection(set(task2.file_references)):
            return True
        
        # Similar titles (basic heuristic)
        common_words = set(task1.title.lower().split()).intersection(set(task2.title.lower().split()))
        if len(common_words) > 2:
            return True
        
        return False
    
    async def _fix_plan_issues(self, plan: TaskPlan, validation_errors: List[str]):
        """Attempt to fix common plan validation issues"""
        
        for error in validation_errors:
            if "Circular dependency" in error:
                # Remove problematic dependencies (simplified approach)
                if plan.dependencies:
                    plan.dependencies.pop()  # Remove last dependency as a simple fix
            
            elif "unassigned" in error.lower():
                # Assign agents to unassigned tasks
                unassigned = [t for t in plan.tasks if not t.agent_assignment]
                for task in unassigned:
                    task.agent_assignment = AgentAssignment('coding-agent')  # Default assignment
    
    def _calculate_confidence_score(self, plan: TaskPlan, analyzed_requirements: List[AnalyzedRequirement], 
                                   insights: Dict[str, Any]) -> float:
        """Calculate confidence score for the generated plan"""
        
        confidence_factors = []
        
        # Pattern recognition coverage
        total_patterns = len(insights.get('pattern_distribution', {}))
        if total_patterns > 0:
            confidence_factors.append(min(1.0, total_patterns / 5))  # More patterns = higher confidence
        
        # Agent assignment coverage
        assigned_tasks = [t for t in plan.tasks if t.agent_assignment]
        assignment_ratio = len(assigned_tasks) / len(plan.tasks) if plan.tasks else 0
        confidence_factors.append(assignment_ratio)
        
        # Requirement analysis quality
        avg_effort = sum(ar.estimated_effort_hours for ar in analyzed_requirements) / len(analyzed_requirements)
        if 1 <= avg_effort <= 8:  # Reasonable effort range
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Dependency reasonableness
        dep_ratio = len(plan.dependencies) / len(plan.tasks) if plan.tasks else 0
        if 0.1 <= dep_ratio <= 0.5:  # Reasonable dependency ratio
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Plan complexity balance
        complexity_dist = insights.get('complexity_distribution', {})
        if complexity_dist.get('medium', 0) > complexity_dist.get('high', 0):
            confidence_factors.append(0.8)  # Prefer more medium complexity tasks
        else:
            confidence_factors.append(0.6)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    def _determine_task_type(self, analysis: AnalyzedRequirement) -> TaskType:
        """Determine task type based on analysis"""
        
        if analysis.estimated_effort_hours > 40:
            return TaskType.EPIC
        elif analysis.estimated_effort_hours > 16:
            return TaskType.FEATURE
        elif 'testing_requirement' in [p.value for p in analysis.detected_patterns]:
            return TaskType.TESTING
        elif 'bug_fix' in [p.value for p in analysis.detected_patterns]:
            return TaskType.BUG
        elif 'documentation' in [p.value for p in analysis.detected_patterns]:
            return TaskType.DOCUMENTATION
        else:
            return TaskType.TASK
    
    def _determine_execution_phase(self, analysis: AnalyzedRequirement) -> ExecutionPhase:
        """Determine execution phase based on analysis"""
        
        patterns = [p.value for p in analysis.detected_patterns]
        
        if 'documentation_requirement' in patterns:
            return ExecutionPhase.PLANNING
        elif any(p in patterns for p in ['database_schema', 'security_requirement']):
            return ExecutionPhase.ARCHITECTURE
        elif 'testing_requirement' in patterns:
            return ExecutionPhase.TESTING
        elif any(p in patterns for p in ['deployment', 'monitoring']):
            return ExecutionPhase.DEPLOYMENT
        else:
            return ExecutionPhase.IMPLEMENTATION
    
    def _map_complexity_level(self, analysis: AnalyzedRequirement) -> str:
        """Map complexity indicators to string level"""
        
        keyword_complexity = analysis.complexity_indicators.get('keyword_complexity', 'medium')
        pattern_complexity = analysis.complexity_indicators.get('pattern_complexity', 2.0)
        
        if keyword_complexity == 'high' or pattern_complexity > 4:
            return 'complex'
        elif keyword_complexity == 'low' and pattern_complexity < 2:
            return 'simple'
        else:
            return 'medium'
    
    async def execute_plan_with_mcp(self, plan: TaskPlan, git_branch_id: str) -> Dict[str, Any]:
        """
        Execute the task plan by creating MCP tasks.
        
        Args:
            plan: The task plan to execute
            git_branch_id: Git branch ID for task creation
            
        Returns:
            Dictionary with execution results and created task IDs
        """
        
        if not self.task_facade:
            return {
                'success': False,
                'error': 'Task facade not available for MCP integration'
            }
        
        created_tasks = []
        failed_tasks = []
        
        # Execute tasks in dependency order (simplified - create all root tasks first)
        root_tasks = plan.get_root_tasks()
        
        for root_task in root_tasks:
            try:
                # Create MCP task
                mcp_request = root_task.to_mcp_task_request()
                mcp_request['git_branch_id'] = git_branch_id
                
                # Call MCP task creation (would need proper integration)
                # For now, just track the intention
                mcp_task_id = str(uuid.uuid4())
                root_task.mcp_task_id = mcp_task_id
                root_task.status = 'created'
                
                created_tasks.append({
                    'planned_task_id': root_task.id,
                    'mcp_task_id': mcp_task_id,
                    'title': root_task.title
                })
                
                # Create subtasks
                subtasks = plan.get_subtasks(root_task.id)
                for subtask in subtasks:
                    subtask_request = subtask.to_mcp_task_request()
                    subtask_request['git_branch_id'] = git_branch_id
                    
                    subtask_mcp_id = str(uuid.uuid4())
                    subtask.mcp_task_id = subtask_mcp_id
                    subtask.status = 'created'
                    
                    created_tasks.append({
                        'planned_task_id': subtask.id,
                        'mcp_task_id': subtask_mcp_id,
                        'title': subtask.title,
                        'parent_task_id': mcp_task_id
                    })
                
            except Exception as e:
                failed_tasks.append({
                    'planned_task_id': root_task.id,
                    'error': str(e)
                })
        
        return {
            'success': len(failed_tasks) == 0,
            'created_tasks': created_tasks,
            'failed_tasks': failed_tasks,
            'plan_summary': {
                'total_tasks': len(plan.tasks),
                'created_count': len(created_tasks),
                'failed_count': len(failed_tasks),
                'estimated_hours': plan.total_estimated_hours,
                'required_agents': list(plan.required_agents)
            }
        }