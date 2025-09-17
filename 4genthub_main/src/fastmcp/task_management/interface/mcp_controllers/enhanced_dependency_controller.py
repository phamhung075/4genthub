"""
Enhanced Dependency Controller - AI-powered dependency management MCP controller

This controller extends the existing dependency management capabilities with
AI-powered features including automated dependency detection, ML-based suggestions,
and intelligent graph optimization.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Annotated
from pydantic import Field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP
    from ...application.facades.task_application_facade import TaskApplicationFacade

from ...application.services.dependency_management_engine import (
    DependencyManagementEngine, EnhancedDependencyRelationships, DependencySuggestion
)
from ...application.services.dependency_resolver_service import DependencyResolverService
from ...infrastructure.ai_services.ml_dependency_predictor import MLDependencyPredictor
from ...domain.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class EnhancedDependencyController:
    """
    Enhanced MCP controller for AI-powered dependency operations
    
    This controller provides advanced dependency management capabilities including:
    - AI-powered dependency suggestions
    - Content-based dependency detection
    - Pattern recognition from historical data
    - Intelligent graph optimization
    - ML model training and management
    """
    
    def __init__(
        self, 
        task_facade: "TaskApplicationFacade",
        task_repository: TaskRepository,
        dependency_resolver: DependencyResolverService
    ):
        self.task_facade = task_facade
        self.task_repository = task_repository
        self.dependency_resolver = dependency_resolver
        
        # Initialize AI components
        self.dependency_engine = DependencyManagementEngine(
            dependency_resolver, 
            task_repository
        )
        self.ml_predictor = MLDependencyPredictor(task_repository)
        
        logger.info("EnhancedDependencyController initialized with AI capabilities")
    
    def register_tools(self, mcp: "FastMCP"):
        """Register enhanced dependency management tools with MCP server"""
        
        # Main AI-enhanced dependency analysis tool
        @mcp.tool(description=self._get_ai_dependency_analysis_description())
        def analyze_dependencies_ai(
            task_id: Annotated[str, Field(description="Task ID to analyze dependencies for")],
            user_id: Annotated[str, Field(description="User ID for authentication")] = None,
            include_suggestions: Annotated[bool, Field(description="Include AI dependency suggestions")] = True,
            confidence_threshold: Annotated[float, Field(description="Minimum confidence for suggestions (0.0-1.0)")] = 0.5
        ) -> Dict[str, Any]:
            """
            Analyze task dependencies with AI enhancements
            
            Provides comprehensive dependency analysis including:
            - Existing dependency relationships
            - AI-powered dependency suggestions
            - Content analysis insights
            - Pattern recognition predictions
            - Optimization recommendations
            """
            return self.handle_ai_dependency_analysis(
                task_id=task_id,
                user_id=user_id,
                include_suggestions=include_suggestions,
                confidence_threshold=confidence_threshold
            )
        
        # Dependency suggestion tool
        @mcp.tool(description=self._get_dependency_suggestions_description())
        def suggest_dependencies(
            task_id: Annotated[str, Field(description="Task ID to generate suggestions for")],
            user_id: Annotated[str, Field(description="User ID for authentication")] = None,
            suggestion_types: Annotated[str, Field(description="Comma-separated list of suggestion types: content,pattern,semantic,resource")] = "content,pattern,resource",
            max_suggestions: Annotated[int, Field(description="Maximum number of suggestions to return")] = 10
        ) -> Dict[str, Any]:
            """
            Generate AI-powered dependency suggestions for a task
            
            Uses multiple analysis methods:
            - Content analysis: Keywords, file references, technical entities
            - Pattern recognition: ML-based predictions from historical data
            - Semantic analysis: NLP-based relationship detection
            - Resource analysis: Agent assignment conflicts and dependencies
            """
            return self.handle_dependency_suggestions(
                task_id=task_id,
                user_id=user_id,
                suggestion_types=suggestion_types,
                max_suggestions=max_suggestions
            )
        
        # Model training and management tool
        @mcp.tool(description=self._get_model_management_description())
        def manage_dependency_model(
            action: Annotated[str, Field(description="Action: train, retrain, status, info")],
            user_id: Annotated[str, Field(description="User ID for authentication")] = None,
            project_limit: Annotated[int, Field(description="Limit projects for training (optional)")] = None
        ) -> Dict[str, Any]:
            """
            Manage the dependency prediction ML model
            
            Actions:
            - train: Train new model from historical data
            - retrain: Retrain existing model with latest data  
            - status: Get current model status and statistics
            - info: Get detailed model information and metadata
            """
            return self.handle_model_management(
                action=action,
                user_id=user_id,
                project_limit=project_limit
            )
        
        # Batch dependency optimization tool
        @mcp.tool(description=self._get_batch_optimization_description())
        def optimize_project_dependencies(
            project_id: Annotated[str, Field(description="Project ID to optimize")] = None,
            git_branch_id: Annotated[str, Field(description="Git branch ID to optimize")] = None,
            user_id: Annotated[str, Field(description="User ID for authentication")] = None,
            auto_apply: Annotated[bool, Field(description="Automatically apply high-confidence suggestions")] = False,
            confidence_threshold: Annotated[float, Field(description="Confidence threshold for auto-application")] = 0.8
        ) -> Dict[str, Any]:
            """
            Optimize dependencies for an entire project or branch
            
            Analyzes all tasks in scope and provides:
            - Dependency gap analysis
            - Optimization recommendations
            - Batch suggestion application (if auto_apply=True)
            - Performance impact analysis
            """
            return self.handle_batch_optimization(
                project_id=project_id,
                git_branch_id=git_branch_id,
                user_id=user_id,
                auto_apply=auto_apply,
                confidence_threshold=confidence_threshold
            )
    
    def handle_ai_dependency_analysis(
        self, 
        task_id: str, 
        user_id: Optional[str] = None,
        include_suggestions: bool = True,
        confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Handle AI-enhanced dependency analysis"""
        
        try:
            # Create user-scoped engine if needed
            engine = self.dependency_engine
            if user_id:
                engine = engine.with_user(user_id)
            
            # Get enhanced dependency analysis
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                enhanced_relationships = loop.run_until_complete(
                    engine.resolve_dependencies_with_ai(task_id)
                )
            except RuntimeError:
                # No event loop running, create one
                enhanced_relationships = asyncio.run(
                    engine.resolve_dependencies_with_ai(task_id)
                )
            
            # Format response
            response = {
                "success": True,
                "task_id": task_id,
                "analysis": {
                    # Basic dependency information
                    "existing_dependencies": {
                        "depends_on": [self._format_dependency_info(dep) for dep in enhanced_relationships.basic_relationships.depends_on],
                        "blocks": [self._format_dependency_info(dep) for dep in enhanced_relationships.basic_relationships.blocks],
                        "total_dependencies": enhanced_relationships.basic_relationships.total_dependencies,
                        "completed_dependencies": enhanced_relationships.basic_relationships.completed_dependencies,
                        "can_start": enhanced_relationships.basic_relationships.can_start,
                        "is_blocked": enhanced_relationships.basic_relationships.is_blocked,
                        "dependency_summary": enhanced_relationships.basic_relationships.dependency_summary
                    },
                    
                    # AI enhancement information
                    "ai_analysis": {
                        "suggestions_generated": len(enhanced_relationships.ai_suggestions),
                        "suggestion_summary": enhanced_relationships.suggestion_summary,
                        "optimization_score": enhanced_relationships.optimization_score,
                        "performance_metrics": enhanced_relationships.performance_metrics
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Add suggestions if requested
            if include_suggestions:
                filtered_suggestions = [
                    s for s in enhanced_relationships.ai_suggestions 
                    if s.hint.confidence_score >= confidence_threshold
                ]
                
                response["analysis"]["ai_suggestions"] = [
                    self._format_suggestion(suggestion) for suggestion in filtered_suggestions
                ]
                response["analysis"]["ai_analysis"]["high_confidence_suggestions"] = len(filtered_suggestions)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in AI dependency analysis for task {task_id}: {e}")
            return {
                "success": False,
                "error": f"AI dependency analysis failed: {str(e)}",
                "error_code": "AI_ANALYSIS_FAILED",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def handle_dependency_suggestions(
        self,
        task_id: str,
        user_id: Optional[str] = None,
        suggestion_types: str = "content,pattern,resource",
        max_suggestions: int = 10
    ) -> Dict[str, Any]:
        """Handle dependency suggestion generation"""
        
        try:
            # Parse suggestion types
            requested_types = [t.strip() for t in suggestion_types.split(',')]
            
            # Create user-scoped engine if needed
            engine = self.dependency_engine
            if user_id:
                engine = engine.with_user(user_id)
            
            # Generate suggestions
            all_suggestions = engine.suggest_dependencies(task_id)
            
            # Filter by requested types
            type_mapping = {
                'content': ['content'],
                'pattern': ['pattern'],
                'semantic': ['semantic'],
                'resource': ['resource'],
                'temporal': ['temporal']
            }
            
            allowed_types = []
            for req_type in requested_types:
                if req_type in type_mapping:
                    allowed_types.extend(type_mapping[req_type])
            
            if allowed_types:
                filtered_suggestions = [
                    s for s in all_suggestions 
                    if s.hint.suggestion_type.value in allowed_types
                ]
            else:
                filtered_suggestions = all_suggestions
            
            # Limit results
            limited_suggestions = filtered_suggestions[:max_suggestions]
            
            # Format response
            response = {
                "success": True,
                "task_id": task_id,
                "suggestions": {
                    "total_generated": len(all_suggestions),
                    "filtered_count": len(filtered_suggestions),
                    "returned_count": len(limited_suggestions),
                    "suggestion_types_requested": requested_types,
                    "items": [self._format_suggestion(s) for s in limited_suggestions]
                },
                "statistics": {
                    "avg_confidence": sum(s.hint.confidence_score for s in limited_suggestions) / len(limited_suggestions) if limited_suggestions else 0.0,
                    "high_confidence_count": len([s for s in limited_suggestions if s.hint.confidence_score > 0.7]),
                    "medium_confidence_count": len([s for s in limited_suggestions if 0.4 < s.hint.confidence_score <= 0.7]),
                    "type_breakdown": self._get_type_breakdown(limited_suggestions)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating dependency suggestions for task {task_id}: {e}")
            return {
                "success": False,
                "error": f"Dependency suggestion generation failed: {str(e)}",
                "error_code": "SUGGESTION_GENERATION_FAILED",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def handle_model_management(
        self,
        action: str,
        user_id: Optional[str] = None,
        project_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Handle ML model management operations"""
        
        try:
            if action == "train":
                # Train new model
                training_results = self.ml_predictor.train_model(
                    project_limit=project_limit,
                    save_model=True
                )
                
                return {
                    "success": True,
                    "action": "train",
                    "results": training_results,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            elif action == "retrain":
                # Retrain existing model
                training_results = self.ml_predictor.retrain_model()
                
                return {
                    "success": True,
                    "action": "retrain", 
                    "results": training_results,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            elif action == "status":
                # Get model status
                engine_stats = self.dependency_engine.get_performance_metrics()
                model_info = self.ml_predictor.get_model_info()
                
                return {
                    "success": True,
                    "action": "status",
                    "model_status": {
                        "trained": model_info.get("trained", False),
                        "available_versions": model_info.get("available_versions", []),
                        "engine_performance": engine_stats,
                        "current_stats": model_info.get("current_stats")
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            elif action == "info":
                # Get detailed model information
                model_info = self.ml_predictor.get_model_info()
                
                return {
                    "success": True,
                    "action": "info",
                    "model_info": model_info,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "error_code": "INVALID_ACTION",
                    "valid_actions": ["train", "retrain", "status", "info"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error in model management action '{action}': {e}")
            return {
                "success": False,
                "error": f"Model management failed: {str(e)}",
                "error_code": "MODEL_MANAGEMENT_FAILED",
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def handle_batch_optimization(
        self,
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auto_apply: bool = False,
        confidence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Handle batch dependency optimization for projects/branches"""
        
        try:
            if not project_id and not git_branch_id:
                return {
                    "success": False,
                    "error": "Either project_id or git_branch_id must be provided",
                    "error_code": "MISSING_SCOPE",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Get tasks in scope
            if git_branch_id:
                # TODO: Implement get_tasks_by_branch method
                tasks = self._get_tasks_by_branch(git_branch_id)
                scope = f"Branch {git_branch_id}"
            else:
                # TODO: Implement get_tasks_by_project method
                tasks = self._get_tasks_by_project(project_id)
                scope = f"Project {project_id}"
            
            if not tasks:
                return {
                    "success": True,
                    "message": f"No tasks found in {scope}",
                    "scope": scope,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Analyze each task
            engine = self.dependency_engine
            if user_id:
                engine = engine.with_user(user_id)
            
            optimization_results = []
            applied_suggestions = []
            
            for task in tasks:
                try:
                    # Generate suggestions for this task
                    suggestions = engine.suggest_dependencies(str(task.id))
                    
                    if not suggestions:
                        continue
                    
                    high_confidence_suggestions = [
                        s for s in suggestions 
                        if s.hint.confidence_score >= confidence_threshold
                    ]
                    
                    task_result = {
                        "task_id": str(task.id),
                        "task_title": task.title,
                        "suggestions_count": len(suggestions),
                        "high_confidence_count": len(high_confidence_suggestions),
                        "suggestions": [self._format_suggestion(s) for s in suggestions[:5]]  # Top 5
                    }
                    
                    # Auto-apply if requested
                    if auto_apply and high_confidence_suggestions:
                        for suggestion in high_confidence_suggestions:
                            # TODO: Implement auto-application via task facade
                            # This would involve calling the actual dependency addition API
                            applied_suggestions.append({
                                "task_id": str(task.id),
                                "dependency_id": suggestion.hint.suggested_dependency_id,
                                "confidence": suggestion.hint.confidence_score,
                                "reason": suggestion.hint.suggestion_reason
                            })
                        
                        task_result["auto_applied"] = len(high_confidence_suggestions)
                    
                    optimization_results.append(task_result)
                    
                except Exception as e:
                    logger.error(f"Error analyzing task {task.id} in batch optimization: {e}")
                    optimization_results.append({
                        "task_id": str(task.id),
                        "error": str(e)
                    })
            
            # Calculate summary statistics
            total_suggestions = sum(r.get("suggestions_count", 0) for r in optimization_results)
            total_high_confidence = sum(r.get("high_confidence_count", 0) for r in optimization_results)
            
            return {
                "success": True,
                "scope": scope,
                "optimization_results": {
                    "tasks_analyzed": len(tasks),
                    "tasks_with_suggestions": len([r for r in optimization_results if r.get("suggestions_count", 0) > 0]),
                    "total_suggestions_generated": total_suggestions,
                    "high_confidence_suggestions": total_high_confidence,
                    "auto_applied_count": len(applied_suggestions) if auto_apply else 0,
                    "tasks": optimization_results
                },
                "applied_suggestions": applied_suggestions if auto_apply else None,
                "parameters": {
                    "auto_apply": auto_apply,
                    "confidence_threshold": confidence_threshold
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in batch optimization: {e}")
            return {
                "success": False,
                "error": f"Batch optimization failed: {str(e)}",
                "error_code": "BATCH_OPTIMIZATION_FAILED",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_tasks_by_branch(self, git_branch_id: str) -> List:
        """Get all tasks for a specific branch"""
        # This is a placeholder - implement actual branch task retrieval
        try:
            # For now, return all tasks filtered by branch
            all_tasks = self.task_repository.find_all()
            return [task for task in all_tasks if getattr(task, 'git_branch_id', None) == git_branch_id]
        except Exception as e:
            logger.error(f"Error getting tasks by branch {git_branch_id}: {e}")
            return []
    
    def _get_tasks_by_project(self, project_id: str) -> List:
        """Get all tasks for a specific project"""
        # This is a placeholder - implement actual project task retrieval
        try:
            # For now, return all tasks - in real implementation would filter by project
            return self.task_repository.find_all()
        except Exception as e:
            logger.error(f"Error getting tasks by project {project_id}: {e}")
            return []
    
    def _format_dependency_info(self, dep_info) -> Dict[str, Any]:
        """Format dependency info for API response"""
        return {
            "task_id": dep_info.task_id,
            "title": dep_info.title,
            "status": dep_info.status,
            "priority": dep_info.priority,
            "completion_percentage": dep_info.completion_percentage,
            "is_blocking": dep_info.is_blocking,
            "is_blocked": dep_info.is_blocked,
            "estimated_effort": dep_info.estimated_effort,
            "assignees": dep_info.assignees,
            "updated_at": dep_info.updated_at.isoformat() if dep_info.updated_at else None
        }
    
    def _format_suggestion(self, suggestion: DependencySuggestion) -> Dict[str, Any]:
        """Format suggestion for API response"""
        return {
            "suggested_dependency_id": suggestion.hint.suggested_dependency_id,
            "confidence_score": suggestion.hint.confidence_score,
            "suggestion_reason": suggestion.hint.suggestion_reason,
            "suggestion_type": suggestion.hint.suggestion_type.value,
            "evidence": suggestion.hint.evidence,
            "target_task": self._format_dependency_info(suggestion.target_task_info) if suggestion.target_task_info else None,
            "status": suggestion.status.value,
            "created_at": suggestion.created_at.isoformat()
        }
    
    def _get_type_breakdown(self, suggestions: List[DependencySuggestion]) -> Dict[str, int]:
        """Get breakdown of suggestion types"""
        breakdown = {}
        for suggestion in suggestions:
            suggestion_type = suggestion.hint.suggestion_type.value
            breakdown[suggestion_type] = breakdown.get(suggestion_type, 0) + 1
        return breakdown
    
    # Tool description methods
    def _get_ai_dependency_analysis_description(self) -> str:
        return """
Analyze task dependencies with AI enhancements including automated detection, 
pattern recognition, and optimization recommendations. Provides comprehensive
dependency analysis with confidence scores and actionable insights.
        """.strip()
    
    def _get_dependency_suggestions_description(self) -> str:
        return """
Generate AI-powered dependency suggestions using multiple analysis methods:
content analysis, pattern recognition, semantic analysis, and resource analysis.
Returns ranked suggestions with confidence scores and evidence.
        """.strip()
    
    def _get_model_management_description(self) -> str:
        return """
Manage the dependency prediction ML model including training, status checks,
and detailed model information. Supports training from historical data and
performance monitoring.
        """.strip()
    
    def _get_batch_optimization_description(self) -> str:
        return """
Optimize dependencies for an entire project or branch with batch analysis,
automated suggestions, and optional auto-application of high-confidence
dependency relationships.
        """.strip()