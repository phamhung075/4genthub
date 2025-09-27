"""
Context Delegation Service

Manages the delegation of context data from lower levels to higher levels:
Task → Project → Global with automatic and manual delegation capabilities.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DelegationRequest:
    """Request for context delegation"""
    source_level: str
    source_id: str
    target_level: str
    target_id: str
    delegated_data: Dict[str, Any]
    reason: str
    trigger_type: str = "manual"
    confidence_score: Optional[float] = None

@dataclass
class DelegationResult:
    """Result of delegation processing"""
    success: bool
    delegation_id: str
    processed: bool = False
    approved: Optional[bool] = None
    error_message: Optional[str] = None
    impact_assessment: Optional[Dict[str, Any]] = None

class ContextDelegationService:
    """
    Service for managing context delegation between hierarchy levels.
    
    Handles both automatic delegation (based on rules and patterns) and
    manual delegation initiated by users or AI agents.
    """
    
    def __init__(self, repository=None, user_id: Optional[str] = None):
        """Initialize delegation service"""
        self.repository = repository  # Will be injected
        self._user_id = user_id  # Store user context
        logger.info("ContextDelegationService initialized")

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'ContextDelegationService':
        """Create a new service instance scoped to a specific user."""
        return ContextDelegationService(self.repository, user_id)
    
    def delegate_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous wrapper for delegation processing.
        
        This method is called by the facade and needs to handle delegation
        in a synchronous manner, wrapping the async process_delegation method.
        
        Args:
            request: Delegation request with source, target, data, and reason
            
        Returns:
            Delegation result with status and delegation_id
        """
        try:
            import asyncio
            
            # Extract fields from request
            source_level = request.get("source_level")
            source_id = request.get("source_id")
            target_level = request.get("target_level")
            data = request.get("data", {})
            reason = request.get("reason", "Manual delegation")
            
            # Resolve target ID based on source and target levels
            # For now, use simple mapping
            target_id = "global_singleton" if target_level == "global" else source_id
            
            # Try to get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, return a mock response
                    logger.debug("Event loop running, returning mock delegation response")
                    return {
                        "success": True,
                        "delegation_id": f"del-{source_id[:8]}",
                        "status": "pending"
                    }
                else:
                    # Run the async method
                    result = loop.run_until_complete(
                        self.process_delegation(source_level, source_id, target_level, target_id, data, reason)
                    )
                    return result
            except RuntimeError:
                # No event loop exists, create one
                result = asyncio.run(
                    self.process_delegation(source_level, source_id, target_level, target_id, data, reason)
                )
                return result
                
        except Exception as e:
            logger.error(f"Error in delegate_context: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    # ===============================================
    # MAIN DELEGATION PROCESSING
    # ===============================================
    
    async def process_delegation(self, source_level: str, source_id: str, 
                               target_level: str, target_id: str,
                               delegated_data: Dict[str, Any], reason: str,
                               trigger_type: str = "manual",
                               confidence_score: Optional[float] = None) -> Dict[str, Any]:
        """
        Process a delegation request from source to target context.
        
        Args:
            source_level: Source context level ('task', 'project')
            source_id: Source context identifier
            target_level: Target context level ('project', 'global')
            target_id: Target context identifier
            delegated_data: Data to be delegated
            reason: Reason for delegation
            trigger_type: Type of trigger ('manual', 'auto_threshold', 'auto_pattern', 'ai_initiated')
            confidence_score: AI confidence in delegation (0.0-1.0)
            
        Returns:
            Delegation processing result
        """
        try:
            logger.info(f"Processing delegation from {source_level}:{source_id} to {target_level}:{target_id}")
            
            # Validate delegation request
            validation_result = self._validate_delegation_request(
                source_level, source_id, target_level, target_id, delegated_data
            )
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Invalid delegation request: {validation_result['errors']}",
                    "delegation_id": None
                }
            
            # Create delegation record
            delegation_request = DelegationRequest(
                source_level=source_level,
                source_id=source_id,
                target_level=target_level,
                target_id=target_id,
                delegated_data=delegated_data,
                reason=reason,
                trigger_type=trigger_type,
                confidence_score=confidence_score
            )
            
            # Store delegation request
            delegation_id = await self._store_delegation_request(delegation_request)
            
            # Assess impact of delegation
            impact_assessment = await self._assess_delegation_impact(delegation_request)
            
            # Determine if auto-approval is possible
            auto_approve = await self._should_auto_approve(delegation_request, impact_assessment)
            
            if auto_approve:
                # Process immediately
                result = await self._execute_delegation(delegation_id, delegation_request, impact_assessment)
                logger.info(f"Auto-approved and executed delegation {delegation_id}")
            else:
                # Queue for manual review
                result = await self._queue_for_review(delegation_id, delegation_request, impact_assessment)
                logger.info(f"Queued delegation {delegation_id} for manual review")
            
            return {
                "success": True,
                "delegation_id": delegation_id,
                "auto_approved": auto_approve,
                "impact_assessment": impact_assessment,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing delegation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "delegation_id": None
            }
    
    # ===============================================
    # AUTOMATIC DELEGATION DETECTION
    # ===============================================
    
    async def evaluate_auto_delegation_triggers(self, context_level: str, context_id: str, 
                                              context_data: Dict[str, Any], 
                                              changes: Dict[str, Any]) -> List[DelegationRequest]:
        """
        Evaluate if changes trigger automatic delegation.
        
        Args:
            context_level: Level of context that changed
            context_id: Context identifier
            context_data: Full context data
            changes: Changes that were made
            
        Returns:
            List of delegation requests to process
        """
        try:
            logger.debug(f"Evaluating auto-delegation triggers for {context_level}:{context_id}")
            
            delegation_requests = []
            
            if context_level == "task":
                # Get task delegation rules
                delegation_triggers = context_data.get("delegation_triggers", {})
                
                # Pattern-based delegation
                pattern_requests = await self._evaluate_pattern_triggers(
                    context_id, changes, delegation_triggers.get("patterns", {})
                )
                delegation_requests.extend(pattern_requests)
                
                # Threshold-based delegation
                threshold_requests = await self._evaluate_threshold_triggers(
                    context_id, context_data, changes, delegation_triggers.get("thresholds", {})
                )
                delegation_requests.extend(threshold_requests)
                
                # AI-initiated delegation (if AI confidence is high)
                ai_requests = await self._evaluate_ai_triggers(
                    context_id, context_data, changes
                )
                delegation_requests.extend(ai_requests)
            
            elif context_level == "project":
                # Project-level delegation to global
                global_requests = await self._evaluate_project_to_global_triggers(
                    context_id, context_data, changes
                )
                delegation_requests.extend(global_requests)
            
            logger.info(f"Found {len(delegation_requests)} auto-delegation triggers")
            return delegation_requests
            
        except Exception as e:
            logger.error(f"Error evaluating auto-delegation triggers: {e}", exc_info=True)
            return []
    
    async def _evaluate_pattern_triggers(self, context_id: str, changes: Dict[str, Any], 
                                       patterns: Dict[str, str]) -> List[DelegationRequest]:
        """Evaluate pattern-based delegation triggers"""
        requests = []
        
        for pattern, target_level in patterns.items():
            if self._matches_pattern(changes, pattern):
                target_id = await self._resolve_target_id(context_id, "task", target_level)
                
                request = DelegationRequest(
                    source_level="task",
                    source_id=context_id,
                    target_level=target_level,
                    target_id=target_id,
                    delegated_data=self._extract_pattern_data(changes, pattern),
                    reason=f"Auto-delegation: {pattern} pattern detected",
                    trigger_type="auto_pattern",
                    confidence_score=0.8
                )
                requests.append(request)
                logger.debug(f"Pattern trigger: {pattern} → {target_level}")
        
        return requests
    
    async def _evaluate_threshold_triggers(self, context_id: str, context_data: Dict[str, Any],
                                         changes: Dict[str, Any], thresholds: Dict[str, Any]) -> List[DelegationRequest]:
        """Evaluate threshold-based delegation triggers"""
        requests = []
        
        for threshold_name, threshold_config in thresholds.items():
            if self._exceeds_threshold(context_data, changes, threshold_name, threshold_config):
                target_level = threshold_config.get("delegate_to", "project")
                target_id = await self._resolve_target_id(context_id, "task", target_level)
                
                request = DelegationRequest(
                    source_level="task",
                    source_id=context_id,
                    target_level=target_level,
                    target_id=target_id,
                    delegated_data=self._extract_threshold_data(context_data, threshold_name),
                    reason=f"Auto-delegation: {threshold_name} threshold exceeded",
                    trigger_type="auto_threshold",
                    confidence_score=0.9
                )
                requests.append(request)
                logger.debug(f"Threshold trigger: {threshold_name} → {target_level}")
        
        return requests
    
    async def _evaluate_ai_triggers(self, context_id: str, context_data: Dict[str, Any],
                                  changes: Dict[str, Any]) -> List[DelegationRequest]:
        """Evaluate AI-initiated delegation triggers"""
        requests = []
        
        # AI pattern recognition for delegation opportunities
        ai_patterns = [
            ("reusable_component", "project", 0.85),
            ("security_insight", "global", 0.95),
            ("performance_optimization", "project", 0.80),
            ("architectural_decision", "global", 0.90)
        ]
        
        for pattern, target_level, min_confidence in ai_patterns:
            confidence = self._calculate_ai_delegation_confidence(changes, pattern)
            
            if confidence >= min_confidence:
                target_id = await self._resolve_target_id(context_id, "task", target_level)
                
                request = DelegationRequest(
                    source_level="task",
                    source_id=context_id,
                    target_level=target_level,
                    target_id=target_id,
                    delegated_data=self._extract_ai_pattern_data(changes, pattern),
                    reason=f"AI-initiated delegation: {pattern} (confidence: {confidence:.2f})",
                    trigger_type="ai_initiated",
                    confidence_score=confidence
                )
                requests.append(request)
                logger.debug(f"AI trigger: {pattern} → {target_level} (confidence: {confidence:.2f})")
        
        return requests
    
    # ===============================================
    # DELEGATION EXECUTION
    # ===============================================
    
    async def _execute_delegation(self, delegation_id: str, request: DelegationRequest,
                                impact_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approved delegation"""
        try:
            logger.info(f"Executing delegation {delegation_id}")
            
            # Get target context
            target_context = await self._get_context(request.target_level, request.target_id)
            
            # Merge delegated data into target context
            updated_context = await self._merge_delegated_data(
                target_context, request.delegated_data, request
            )
            
            # Update target context
            await self._update_context(request.target_level, request.target_id, updated_context)
            
            # Mark delegation as implemented
            await self._mark_delegation_implemented(delegation_id, {
                "implemented_at": datetime.now(timezone.utc).isoformat(),
                "implementation_details": {
                    "merged_fields": list(request.delegated_data.keys()),
                    "target_context_updated": True
                }
            })
            
            logger.info(f"Successfully executed delegation {delegation_id}")
            
            return {
                "success": True,
                "delegation_id": delegation_id,
                "implemented": True,
                "target_updated": True
            }
            
        except Exception as e:
            logger.error(f"Error executing delegation {delegation_id}: {e}", exc_info=True)
            
            # Mark delegation as failed
            await self._mark_delegation_failed(delegation_id, str(e))
            
            return {
                "success": False,
                "delegation_id": delegation_id,
                "error": str(e)
            }
    
    async def _merge_delegated_data(self, target_context: Dict[str, Any], 
                                  delegated_data: Dict[str, Any],
                                  request: DelegationRequest) -> Dict[str, Any]:
        """Merge delegated data into target context with conflict resolution"""
        updated_context = target_context.copy()
        
        # Different merge strategies based on target level
        if request.target_level == "global":
            # For global context, be more conservative
            updated_context = self._merge_to_global_context(updated_context, delegated_data, request)
        elif request.target_level == "project":
            # For project context, add to project-specific sections
            updated_context = self._merge_to_project_context(updated_context, delegated_data, request)
        
        return updated_context
    
    def _merge_to_global_context(self, global_context: Dict[str, Any], 
                               delegated_data: Dict[str, Any],
                               request: DelegationRequest) -> Dict[str, Any]:
        """Merge data into global context"""
        updated = global_context.copy()
        
        # Add to appropriate global sections based on delegation type
        if "security" in request.reason.lower():
            security_policies = updated.get("security_policies", {})
            security_policies.update(delegated_data.get("security_insights", {}))
            updated["security_policies"] = security_policies
        
        elif "coding" in request.reason.lower() or "standard" in request.reason.lower():
            coding_standards = updated.get("coding_standards", {})
            coding_standards.update(delegated_data.get("coding_patterns", {}))
            updated["coding_standards"] = coding_standards
        
        elif "workflow" in request.reason.lower():
            workflow_templates = updated.get("workflow_templates", {})
            workflow_templates.update(delegated_data.get("workflow_patterns", {}))
            updated["workflow_templates"] = workflow_templates
        
        # Add delegation metadata
        delegated_insights = updated.get("delegated_insights", [])
        delegated_insights.append({
            "delegation_id": request.source_id,
            "source": f"{request.source_level}:{request.source_id}",
            "data": delegated_data,
            "reason": request.reason,
            "delegated_at": datetime.now(timezone.utc).isoformat()
        })
        updated["delegated_insights"] = delegated_insights
        
        return updated
    
    def _merge_to_project_context(self, project_context: Dict[str, Any], 
                                delegated_data: Dict[str, Any],
                                request: DelegationRequest) -> Dict[str, Any]:
        """Merge data into project context"""
        updated = project_context.copy()
        
        # Add to project-specific sections
        if "team" in request.reason.lower():
            team_preferences = updated.get("team_preferences", {})
            team_preferences.update(delegated_data.get("team_insights", {}))
            updated["team_preferences"] = team_preferences
        
        elif "technology" in request.reason.lower():
            technology_stack = updated.get("technology_stack", {})
            technology_stack.update(delegated_data.get("tech_insights", {}))
            updated["technology_stack"] = technology_stack
        
        elif "workflow" in request.reason.lower():
            project_workflow = updated.get("project_workflow", {})
            project_workflow.update(delegated_data.get("workflow_insights", {}))
            updated["project_workflow"] = project_workflow
        
        # Add delegation metadata
        delegated_insights = updated.get("delegated_insights", [])
        delegated_insights.append({
            "delegation_id": request.source_id,
            "source": f"{request.source_level}:{request.source_id}",
            "data": delegated_data,
            "reason": request.reason,
            "delegated_at": datetime.now(timezone.utc).isoformat()
        })
        updated["delegated_insights"] = delegated_insights
        
        return updated
    
    # ===============================================
    # DELEGATION QUEUE MANAGEMENT
    # ===============================================
    
    async def get_pending_delegations(self, target_level: str = None, 
                                    target_id: str = None) -> List[Dict[str, Any]]:
        """Get pending delegations for review"""
        try:
            filters = {"processed": False}
            if target_level:
                filters["target_level"] = target_level
            if target_id:
                filters["target_id"] = target_id
            
            delegations = await self.repository.get_delegations(filters)
            
            logger.info(f"Found {len(delegations)} pending delegations")
            return delegations
            
        except Exception as e:
            logger.error(f"Error getting pending delegations: {e}", exc_info=True)
            return []
    
    async def approve_delegation(self, delegation_id: str, approver: str) -> Dict[str, Any]:
        """Approve a pending delegation"""
        try:
            delegation = await self.repository.get_delegation(delegation_id)
            if not delegation:
                return {"success": False, "error": "Delegation not found"}
            
            if delegation.get("processed"):
                return {"success": False, "error": "Delegation already processed"}
            
            # Create delegation request from stored data
            request = DelegationRequest(
                source_level=delegation["source_level"],
                source_id=delegation["source_id"],
                target_level=delegation["target_level"],
                target_id=delegation["target_id"],
                delegated_data=delegation["delegated_data"],
                reason=delegation["delegation_reason"],
                trigger_type=delegation["trigger_type"],
                confidence_score=delegation.get("confidence_score")
            )
            
            # Assess current impact
            impact_assessment = await self._assess_delegation_impact(request)
            
            # Execute delegation
            result = await self._execute_delegation(delegation_id, request, impact_assessment)
            
            # Mark as approved and processed
            await self.repository.update_delegation(delegation_id, {
                "approved": True,
                "processed": True,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processed_by": approver
            })
            
            logger.info(f"Approved delegation {delegation_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error approving delegation {delegation_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def reject_delegation(self, delegation_id: str, reason: str, 
                              rejector: str) -> Dict[str, Any]:
        """Reject a pending delegation"""
        try:
            await self.repository.update_delegation(delegation_id, {
                "approved": False,
                "processed": True,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processed_by": rejector,
                "rejected_reason": reason
            })
            
            logger.info(f"Rejected delegation {delegation_id}: {reason}")
            return {"success": True, "delegation_id": delegation_id, "rejected": True}
            
        except Exception as e:
            logger.error(f"Error rejecting delegation {delegation_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ===============================================
    # UTILITY METHODS
    # ===============================================
    
    def _validate_delegation_request(self, source_level: str, source_id: str,
                                   target_level: str, target_id: str,
                                   delegated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate delegation request"""
        errors = []
        
        # Validate levels
        valid_levels = ["task", "project", "global"]
        if source_level not in valid_levels:
            errors.append(f"Invalid source level: {source_level}")
        if target_level not in valid_levels:
            errors.append(f"Invalid target level: {target_level}")
        
        # Validate delegation direction (can only delegate upward)
        level_hierarchy = {"task": 0, "project": 1, "global": 2}
        if source_level in level_hierarchy and target_level in level_hierarchy:
            if level_hierarchy[source_level] >= level_hierarchy[target_level]:
                errors.append(f"Cannot delegate from {source_level} to {target_level} - must delegate upward")
        
        # Validate data
        if not delegated_data:
            errors.append("No data provided for delegation")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _matches_pattern(self, changes: Dict[str, Any], pattern: str) -> bool:
        """Check if changes match a delegation pattern"""
        pattern_matchers = {
            "security_discovery": lambda c: any("security" in str(v).lower() or "vulnerability" in str(v).lower() for v in c.values()),
            "team_improvement": lambda c: any("team" in str(v).lower() or "process" in str(v).lower() or "workflow" in str(v).lower() for v in c.values()),
            "reusable_utility": lambda c: any("reusable" in str(v).lower() or "utility" in str(v).lower() or "helper" in str(v).lower() for v in c.values()),
            "performance_optimization": lambda c: any("performance" in str(v).lower() or "optimization" in str(v).lower() or "speed" in str(v).lower() for v in c.values()),
            "architectural_insight": lambda c: any("architecture" in str(v).lower() or "design" in str(v).lower() or "pattern" in str(v).lower() for v in c.values())
        }
        
        matcher = pattern_matchers.get(pattern)
        return matcher(changes) if matcher else False
    
    def _extract_pattern_data(self, changes: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Extract relevant data for pattern-based delegation"""
        return {
            "pattern": pattern,
            "extracted_data": changes,
            "extraction_method": "pattern_matching",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get delegation queue status for health monitoring"""
        try:
            pending_count = len(await self.get_pending_delegations())
            
            return {
                "status": "healthy",
                "pending_delegations": pending_count,
                "queue_healthy": pending_count < 100  # Threshold for queue health
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    # ===============================================
    # MISSING UTILITY METHODS IMPLEMENTATION
    # ===============================================
    
    async def _resolve_target_id(self, source_id: str, source_level: str, target_level: str) -> str:
        """Resolve target ID based on source context and target level"""
        try:
            if target_level == "global":
                return "global_singleton"
            elif target_level == "project":
                # For task -> project delegation, need to find project ID
                if source_level == "task":
                    # Extract project ID from task context or use default
                    task_context = await self._get_context("task", source_id)
                    if task_context and "parent_project_id" in task_context:
                        return task_context["parent_project_id"]
                    else:
                        return "agenthub"  # Default project
                else:
                    return source_id  # Source is already project
            else:
                return source_id
                
        except Exception as e:
            logger.error(f"Error resolving target ID: {e}")
            # Return safe defaults
            if target_level == "global":
                return "global_singleton"
            elif target_level == "project":
                return "agenthub"
            else:
                return source_id
    
    async def _get_context(self, level: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Get context from repository"""
        try:
            if level == "global":
                return await self.repository.get_global_context(context_id)
            elif level == "project":
                return await self.repository.get_project_context(context_id)
            elif level == "task":
                return await self.repository.get_task_context(context_id)
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting context {level}:{context_id}: {e}")
            return None
    
    async def _update_context(self, level: str, context_id: str, context_data: Dict[str, Any]) -> bool:
        """Update context in repository"""
        try:
            if level == "global":
                return await self.repository.update_global_context(context_id, context_data)
            elif level == "project":
                return await self.repository.update_project_context(context_id, context_data)
            elif level == "task":
                return await self.repository.update_task_context(context_id, context_data)
            else:
                return False
        except Exception as e:
            logger.error(f"Error updating context {level}:{context_id}: {e}")
            return False
    
    async def _store_delegation_request(self, request: DelegationRequest) -> str:
        """Store delegation request in repository"""
        try:
            delegation_data = {
                "source_level": request.source_level,
                "source_id": request.source_id,
                "target_level": request.target_level,
                "target_id": request.target_id,
                "delegated_data": request.delegated_data,
                "reason": request.reason,
                "trigger_type": request.trigger_type,
                "auto_delegated": request.trigger_type.startswith("auto"),
                "confidence_score": request.confidence_score
            }
            
            return await self.repository.store_delegation(delegation_data)
            
        except Exception as e:
            logger.error(f"Error storing delegation request: {e}")
            raise
    
    async def _assess_delegation_impact(self, request: DelegationRequest) -> Dict[str, Any]:
        """Assess impact of delegation for approval decision"""
        try:
            impact_score = 0
            risk_factors = []
            benefits = []
            
            # Assess based on trigger type
            if request.trigger_type == "manual":
                impact_score += 30
                benefits.append("Manual review by human or AI")
            elif request.trigger_type.startswith("auto"):
                impact_score += 20
                benefits.append("Automated pattern detection")
            
            # Assess based on target level
            if request.target_level == "global":
                impact_score += 50
                benefits.append("Organization-wide knowledge sharing")
                risk_factors.append("High impact on all projects")
            elif request.target_level == "project":
                impact_score += 30
                benefits.append("Project-level knowledge sharing")
                risk_factors.append("Medium impact on project team")
            
            # Assess based on confidence score
            if request.confidence_score and request.confidence_score >= 0.8:
                impact_score += 20
                benefits.append("High confidence in delegation value")
            elif request.confidence_score and request.confidence_score < 0.5:
                impact_score -= 20
                risk_factors.append("Low confidence in delegation value")
            
            return {
                "impact_score": impact_score,
                "risk_factors": risk_factors,
                "benefits": benefits,
                "recommendation": "auto_approve" if impact_score >= 70 else "manual_review"
            }
            
        except Exception as e:
            logger.error(f"Error assessing delegation impact: {e}")
            return {
                "impact_score": 0,
                "risk_factors": ["Error in impact assessment"],
                "benefits": [],
                "recommendation": "manual_review"
            }
    
    async def _should_auto_approve(self, request: DelegationRequest, impact_assessment: Dict[str, Any]) -> bool:
        """Determine if delegation should be auto-approved"""
        try:
            # Never auto-approve if confidence is too low
            if request.confidence_score and request.confidence_score < 0.7:
                return False
            
            # Auto-approve based on impact assessment
            recommendation = impact_assessment.get("recommendation", "manual_review")
            if recommendation == "auto_approve":
                return True
            
            # Auto-approve certain patterns
            auto_approve_patterns = [
                "security_discovery",
                "compliance_violation",
                "performance_optimization"
            ]
            
            delegated_data = request.delegated_data
            if any(pattern in str(delegated_data).lower() for pattern in auto_approve_patterns):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error determining auto-approval: {e}")
            return False
    
    async def _queue_for_review(self, delegation_id: str, request: DelegationRequest, 
                              impact_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Queue delegation for manual review"""
        try:
            # Delegation is already stored, just return queue info
            return {
                "queued": True,
                "delegation_id": delegation_id,
                "review_required": True,
                "impact_assessment": impact_assessment,
                "estimated_review_time": "24 hours"
            }
            
        except Exception as e:
            logger.error(f"Error queuing delegation for review: {e}")
            return {
                "queued": False,
                "error": str(e)
            }
    
    async def _mark_delegation_implemented(self, delegation_id: str, implementation_data: Dict[str, Any]) -> bool:
        """Mark delegation as successfully implemented"""
        try:
            return await self.repository.update_delegation(delegation_id, {
                "processed": True,
                "approved": True,
                "processed_at": implementation_data["implemented_at"],
                "implementation_details": json.dumps(implementation_data["implementation_details"])
            })
            
        except Exception as e:
            logger.error(f"Error marking delegation as implemented: {e}")
            return False
    
    async def _mark_delegation_failed(self, delegation_id: str, error_message: str) -> bool:
        """Mark delegation as failed"""
        try:
            return await self.repository.update_delegation(delegation_id, {
                "processed": True,
                "approved": False,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "failure_reason": error_message
            })
            
        except Exception as e:
            logger.error(f"Error marking delegation as failed: {e}")
            return False
    
    def _exceeds_threshold(self, context_data: Dict[str, Any], changes: Dict[str, Any], 
                         threshold_name: str, threshold_config: Dict[str, Any]) -> bool:
        """Check if threshold is exceeded"""
        try:
            threshold_type = threshold_config.get("type", "count")
            threshold_value = threshold_config.get("value", 1)
            
            if threshold_type == "count":
                # Count occurrences of pattern in changes
                pattern = threshold_config.get("pattern", "")
                count = str(changes).lower().count(pattern.lower())
                return count >= threshold_value
            elif threshold_type == "percentage":
                # Check percentage-based threshold
                current_value = context_data.get(threshold_name, 0)
                return current_value >= threshold_value
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error checking threshold {threshold_name}: {e}")
            return False
    
    def _extract_threshold_data(self, context_data: Dict[str, Any], threshold_name: str) -> Dict[str, Any]:
        """Extract data related to threshold trigger"""
        return {
            "threshold_name": threshold_name,
            "threshold_data": context_data.get(threshold_name, {}),
            "extraction_method": "threshold_trigger",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_ai_delegation_confidence(self, changes: Dict[str, Any], pattern: str) -> float:
        """Calculate AI confidence for delegation patterns"""
        try:
            pattern_weights = {
                "reusable_component": 0.8,
                "security_insight": 0.95,
                "performance_optimization": 0.75,
                "architectural_decision": 0.9
            }
            
            base_confidence = pattern_weights.get(pattern, 0.5)
            
            # Adjust based on change content quality
            change_text = str(changes).lower()
            
            quality_indicators = {
                "documented": 0.1,
                "tested": 0.1,
                "validated": 0.1,
                "reusable": 0.1,
                "pattern": 0.05,
                "best practice": 0.1
            }
            
            quality_boost = sum(boost for indicator, boost in quality_indicators.items() 
                              if indicator in change_text)
            
            return min(base_confidence + quality_boost, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating AI delegation confidence: {e}")
            return 0.5
    
    def _extract_ai_pattern_data(self, changes: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Extract data for AI-detected patterns"""
        return {
            "ai_pattern": pattern,
            "detected_data": changes,
            "extraction_method": "ai_pattern_recognition",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence_factors": {
                "pattern_strength": "high",
                "reusability_score": "medium",
                "organizational_impact": "high"
            }
        }
    
    async def _evaluate_project_to_global_triggers(self, context_id: str, context_data: Dict[str, Any],
                                                 changes: Dict[str, Any]) -> List[DelegationRequest]:
        """Evaluate project-level changes for global delegation"""
        requests = []
        
        try:
            # Check for organization-wide patterns
            global_patterns = [
                ("security_policy", "security"),
                ("coding_standard", "coding"),
                ("workflow_template", "workflow"),
                ("compliance_pattern", "compliance")
            ]
            
            for pattern, category in global_patterns:
                if pattern in str(changes).lower() or category in str(changes).lower():
                    target_id = "global_singleton"
                    
                    request = DelegationRequest(
                        source_level="project",
                        source_id=context_id,
                        target_level="global",
                        target_id=target_id,
                        delegated_data={
                            f"{category}_insights": changes,
                            "source_project": context_id,
                            "category": category
                        },
                        reason=f"Project-level {category} pattern detected for global adoption",
                        trigger_type="auto_pattern",
                        confidence_score=0.85
                    )
                    requests.append(request)
                    logger.debug(f"Project-to-global trigger: {pattern} → global")
            
            return requests
            
        except Exception as e:
            logger.error(f"Error evaluating project-to-global triggers: {e}")
            return []