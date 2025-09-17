"""
Enhancement Service for Workflow Hint Enhancer

Handles response enhancement with workflow hints and guidance.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EnhancementService:
    """Service for enhancing responses with workflow hints and guidance."""
    
    def __init__(self):
        logger.info("EnhancementService initialized")
    
    def enhance_response(self, response: Dict[str, Any], 
                        operation_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced response with workflow hints and guidance."""
        
        if not isinstance(response, dict):
            return response
        
        enhanced_response = response.copy()
        
        # Add workflow hints section if not present
        if 'workflow_hints' not in enhanced_response:
            enhanced_response['workflow_hints'] = {}
        
        # Add operation context if provided
        if operation_context:
            enhanced_response['workflow_hints']['operation_context'] = operation_context
        
        # Add timestamp for enhancement
        enhanced_response['workflow_hints']['enhanced_at'] = datetime.now(timezone.utc).isoformat()
        
        # Add enhancement metadata
        enhanced_response['workflow_hints']['enhancement_version'] = '2.0'
        enhanced_response['workflow_hints']['features_applied'] = [
            'operation_context',
            'temporal_awareness',
            'metadata_enrichment'
        ]
        
        return enhanced_response
    
    def enhance_task_response(self, response: Dict[str, Any], action: str,
                             request_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced task response processing with validation and guidance."""
        
        if not isinstance(response, dict):
            return response
        
        request_params = request_params or {}
        
        # Handle error responses with enhanced analysis
        if not response.get("success"):
            return self._enhance_error_response(response, action, request_params)
        
        # Extract task context
        task_context = self._extract_task_context(response, request_params)
        if not task_context:
            return self._add_basic_workflow_hints(response, action)
        
        # Enhance with comprehensive workflow guidance
        enhanced_response = response.copy()
        enhanced_response["workflow_guidance"] = self._generate_workflow_guidance(
            task_context, action, request_params
        )
        
        return enhanced_response
    
    def add_task_hints(self, response: Dict[str, Any], 
                      task_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add task-specific workflow hints to response."""
        
        enhanced = self.enhance_response(response)
        
        if 'workflow_hints' not in enhanced:
            enhanced['workflow_hints'] = {}
        
        if task_data:
            # Analyze task state for better guidance
            state = self._analyze_task_state(task_data)
            enhanced['workflow_hints']['task_guidance'] = self._generate_task_guidance(state, task_data)
            enhanced['workflow_hints']['next_actions'] = self._suggest_next_actions(state, task_data)
        else:
            enhanced['workflow_hints']['task_guidance'] = {
                'next_steps': [
                    'Review task requirements',
                    'Update task progress',
                    'Add context information'
                ],
                'best_practices': [
                    'Keep task descriptions clear',
                    'Update status regularly',
                    'Link related tasks'
                ]
            }
        
        return enhanced
    
    def add_context_hints(self, response: Dict[str, Any], 
                         context_level: Optional[str] = None) -> Dict[str, Any]:
        """Add context-specific workflow hints to response."""
        
        enhanced = self.enhance_response(response)
        
        if 'workflow_hints' not in enhanced:
            enhanced['workflow_hints'] = {}
        
        context_guidance = {
            'context_management': [
                'Use appropriate context level for sharing information',
                'Update context after significant discoveries',
                'Share insights across project boundaries when relevant',
                'Maintain context hierarchy for better organization'
            ],
            'level_specific': self._get_level_specific_guidance(context_level),
            'best_practices': [
                'Keep context updates concise and actionable',
                'Include relevant metadata for future reference',
                'Link related contexts when appropriate'
            ]
        }
        
        enhanced['workflow_hints']['context_guidance'] = context_guidance
        
        return enhanced
    
    def add_collaboration_hints(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add collaboration-specific workflow hints to response."""
        
        enhanced = self.enhance_response(response)
        
        if 'workflow_hints' not in enhanced:
            enhanced['workflow_hints'] = {}
        
        collaboration_guidance = {
            'multi_agent_coordination': [
                'Share context updates with relevant agents',
                'Coordinate task assignments to avoid conflicts',
                'Use standardized communication patterns'
            ],
            'cross_project_awareness': [
                'Consider impacts on related projects',
                'Share reusable patterns and solutions',
                'Maintain consistent approaches across projects'
            ],
            'knowledge_sharing': [
                'Document decisions and rationale',
                'Update shared context with discoveries',
                'Provide clear handoff information'
            ]
        }
        
        enhanced['workflow_hints']['collaboration_guidance'] = collaboration_guidance
        
        return enhanced
    
    def _enhance_error_response(self, response: Dict[str, Any], action: str,
                               request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance error responses with helpful guidance."""
        
        enhanced = response.copy()
        
        error_guidance = {
            'error_analysis': self._analyze_error_type(response),
            'suggested_fixes': self._suggest_error_fixes(response, action),
            'prevention_tips': self._get_error_prevention_tips(response, action),
            'next_steps': self._get_error_recovery_steps(response, action)
        }
        
        enhanced['error_guidance'] = error_guidance
        
        return enhanced
    
    def _extract_task_context(self, response: Dict[str, Any], 
                             request_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract task context from response and request parameters."""
        
        context = {}
        
        # Extract from response
        if 'task' in response:
            context.update(response['task'])
        
        # Extract from request params
        relevant_params = ['git_branch_id', 'project_id', 'priority', 'status']
        for param in relevant_params:
            if param in request_params:
                context[param] = request_params[param]
        
        return context if context else None
    
    def _add_basic_workflow_hints(self, response: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Add basic workflow hints when no specific context is available."""
        
        enhanced = response.copy()
        
        basic_hints = {
            'action_completed': f"Successfully performed {action} operation",
            'general_guidance': [
                'Review the operation results',
                'Update related contexts if needed',
                'Consider next steps in your workflow'
            ],
            'best_practices': [
                'Keep operations focused and atomic',
                'Document important decisions',
                'Maintain consistent naming conventions'
            ]
        }
        
        enhanced['workflow_guidance'] = basic_hints
        
        return enhanced
    
    def _generate_workflow_guidance(self, task_context: Dict[str, Any], action: str,
                                  request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive workflow guidance based on context."""
        
        guidance = {
            'operation_summary': f"Completed {action} operation",
            'context_insights': self._analyze_context_insights(task_context),
            'suggested_actions': self._suggest_context_actions(task_context, action),
            'workflow_stage': self._determine_workflow_stage(task_context),
            'coordination_hints': self._get_coordination_hints(task_context, action)
        }
        
        return guidance
    
    def _analyze_task_state(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task state for guidance generation."""
        
        status = task.get('status', 'pending').lower()
        priority = task.get('priority', 'medium').lower()
        
        return {
            'status': status,
            'priority': priority,
            'has_description': bool(task.get('description')),
            'has_assignees': bool(task.get('assignees')),
            'has_due_date': bool(task.get('due_date')),
            'has_dependencies': bool(task.get('dependencies')),
            'complexity_level': self._assess_task_complexity(task)
        }
    
    def _generate_task_guidance(self, state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate task-specific guidance based on state analysis."""
        
        guidance = {
            'status_guidance': self._get_status_guidance(state['status']),
            'priority_guidance': self._get_priority_guidance(state['priority']),
            'completion_hints': self._get_completion_hints(state),
            'improvement_suggestions': self._get_improvement_suggestions(state, task)
        }
        
        return guidance
    
    def _suggest_next_actions(self, state: Dict[str, Any], task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest next actions based on task state."""
        
        actions = []
        
        if state['status'] == 'pending':
            actions.append({
                'action': 'start_work',
                'description': 'Begin working on the task',
                'priority': 'high'
            })
        
        if state['status'] == 'in_progress':
            actions.append({
                'action': 'update_progress',
                'description': 'Update task progress and add notes',
                'priority': 'medium'
            })
        
        if not state['has_description']:
            actions.append({
                'action': 'add_description',
                'description': 'Add detailed task description',
                'priority': 'high'
            })
        
        return actions
    
    def _assess_task_complexity(self, task: Dict[str, Any]) -> str:
        """Assess task complexity based on various factors."""
        
        complexity_score = 0
        
        # Description length
        description = task.get('description', '')
        if len(description) > 500:
            complexity_score += 2
        elif len(description) > 100:
            complexity_score += 1
        
        # Dependencies
        dependencies = task.get('dependencies', [])
        complexity_score += min(len(dependencies), 3)
        
        # Assignees
        assignees = task.get('assignees', [])
        if len(assignees) > 3:
            complexity_score += 2
        elif len(assignees) > 1:
            complexity_score += 1
        
        if complexity_score <= 2:
            return 'simple'
        elif complexity_score <= 4:
            return 'moderate'
        else:
            return 'complex'
    
    def _get_level_specific_guidance(self, level: Optional[str]) -> List[str]:
        """Get guidance specific to context level."""
        
        if not level:
            return ['Consider the appropriate context level for this operation']
        
        level_guidance = {
            'global': [
                'This affects all projects - ensure broad compatibility',
                'Document changes that affect multiple teams',
                'Consider impact on existing workflows'
            ],
            'project': [
                'Update project-level documentation',
                'Consider impact on other project components',
                'Share insights with project team'
            ],
            'branch': [
                'Focus on branch-specific concerns',
                'Coordinate with other work on this branch',
                'Update branch progress tracking'
            ],
            'task': [
                'Focus on task-specific details',
                'Update task progress and notes',
                'Link to related tasks when relevant'
            ]
        }
        
        return level_guidance.get(level, ['Context level not recognized'])
    
    # Helper methods for error handling and analysis
    def _analyze_error_type(self, response: Dict[str, Any]) -> str:
        """Analyze the type of error from response."""
        error = response.get('error', '')
        
        if 'validation' in error.lower():
            return 'validation_error'
        elif 'authentication' in error.lower():
            return 'authentication_error'
        elif 'not found' in error.lower():
            return 'resource_not_found'
        else:
            return 'general_error'
    
    def _suggest_error_fixes(self, response: Dict[str, Any], action: str) -> List[str]:
        """Suggest fixes based on error type."""
        error_type = self._analyze_error_type(response)
        
        fixes = {
            'validation_error': [
                'Check required parameters',
                'Verify parameter formats',
                'Review validation rules'
            ],
            'authentication_error': [
                'Verify user credentials',
                'Check authentication context',
                'Ensure proper authorization'
            ],
            'resource_not_found': [
                'Verify resource ID exists',
                'Check resource permissions',
                'Confirm resource hasn\'t been deleted'
            ]
        }
        
        return fixes.get(error_type, ['Review error details and retry'])
    
    def _get_error_prevention_tips(self, response: Dict[str, Any], action: str) -> List[str]:
        """Get tips to prevent similar errors."""
        return [
            'Validate input parameters before operations',
            'Use consistent error handling patterns',
            'Implement proper logging for debugging'
        ]
    
    def _get_error_recovery_steps(self, response: Dict[str, Any], action: str) -> List[str]:
        """Get steps to recover from the error."""
        return [
            'Review the error details carefully',
            'Fix the identified issues',
            'Retry the operation with corrected parameters'
        ]