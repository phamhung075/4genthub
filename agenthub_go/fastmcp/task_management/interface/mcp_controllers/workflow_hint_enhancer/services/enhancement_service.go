package services

// Enhancement Service for Workflow Hint Enhancer
// (Python mcp_controllers/workflow_hint_enhancer/services/enhancement_service.py).

import (
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// EnhancementService enhances responses with workflow hints and guidance.
type EnhancementService struct{}

// NewEnhancementService creates an EnhancementService.
func NewEnhancementService() *EnhancementService { return &EnhancementService{} }

// EnhanceResponse mirrors enhance_response.
func (s *EnhancementService) EnhanceResponse(response *entities.OrderedMap[any], operationContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	enhancedResponse := response.Copy()

	if !enhancedResponse.Has("workflow_hints") {
		enhancedResponse.Set("workflow_hints", entities.NewOrderedMap[any]())
	}

	hints := orderedChild(enhancedResponse, "workflow_hints")

	if operationContext != nil {
		hints.Set("operation_context", operationContext)
	}

	hints.Set("enhanced_at", value_objects.IsoFormat(time.Now().UTC().Truncate(time.Microsecond)))
	hints.Set("enhancement_version", "2.0")
	hints.Set("features_applied", []any{
		"operation_context",
		"temporal_awareness",
		"metadata_enrichment",
	})

	return enhancedResponse
}

// EnhanceTaskResponse mirrors enhance_task_response.
func (s *EnhancementService) EnhanceTaskResponse(response *entities.OrderedMap[any], action string, requestParams *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if requestParams == nil {
		requestParams = entities.NewOrderedMap[any]()
	}

	if !responseBool(response, "success") {
		return s.enhanceErrorResponse(response, action, requestParams)
	}

	taskContext := s.extractTaskContext(response, requestParams)
	if taskContext.Len() == 0 {
		return s.addBasicWorkflowHints(response, action)
	}

	enhancedResponse := response.Copy()
	enhancedResponse.Set("workflow_guidance", s.generateWorkflowGuidance(taskContext, action, requestParams))
	return enhancedResponse
}

// AddTaskHints mirrors add_task_hints.
func (s *EnhancementService) AddTaskHints(response *entities.OrderedMap[any], taskData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	enhanced := s.EnhanceResponse(response, nil)

	if !enhanced.Has("workflow_hints") {
		enhanced.Set("workflow_hints", entities.NewOrderedMap[any]())
	}
	hints := orderedChild(enhanced, "workflow_hints")

	if taskData != nil {
		state := s.analyzeTaskState(taskData)
		hints.Set("task_guidance", s.generateTaskGuidance(state, taskData))
		hints.Set("next_actions", s.suggestNextActions(state, taskData))
	} else {
		guidance := entities.NewOrderedMap[any]()
		guidance.Set("next_steps", []any{
			"Review task requirements",
			"Update task progress",
			"Add context information",
		})
		guidance.Set("best_practices", []any{
			"Keep task descriptions clear",
			"Update status regularly",
			"Link related tasks",
		})
		hints.Set("task_guidance", guidance)
	}

	return enhanced
}

// AddContextHints mirrors add_context_hints.
func (s *EnhancementService) AddContextHints(response *entities.OrderedMap[any], contextLevel *string) *entities.OrderedMap[any] {
	enhanced := s.EnhanceResponse(response, nil)

	if !enhanced.Has("workflow_hints") {
		enhanced.Set("workflow_hints", entities.NewOrderedMap[any]())
	}
	hints := orderedChild(enhanced, "workflow_hints")

	contextGuidance := entities.NewOrderedMap[any]()
	contextGuidance.Set("context_management", []any{
		"Use appropriate context level for sharing information",
		"Update context after significant discoveries",
		"Share insights across project boundaries when relevant",
		"Maintain context hierarchy for better organization",
	})
	contextGuidance.Set("level_specific", s.getLevelSpecificGuidance(contextLevel))
	contextGuidance.Set("best_practices", []any{
		"Keep context updates concise and actionable",
		"Include relevant metadata for future reference",
		"Link related contexts when appropriate",
	})

	hints.Set("context_guidance", contextGuidance)
	return enhanced
}

// AddCollaborationHints mirrors add_collaboration_hints.
func (s *EnhancementService) AddCollaborationHints(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	enhanced := s.EnhanceResponse(response, nil)

	if !enhanced.Has("workflow_hints") {
		enhanced.Set("workflow_hints", entities.NewOrderedMap[any]())
	}
	hints := orderedChild(enhanced, "workflow_hints")

	collaborationGuidance := entities.NewOrderedMap[any]()
	collaborationGuidance.Set("multi_agent_coordination", []any{
		"Share context updates with relevant agents",
		"Coordinate task assignments to avoid conflicts",
		"Use standardized communication patterns",
	})
	collaborationGuidance.Set("cross_project_awareness", []any{
		"Consider impacts on related projects",
		"Share reusable patterns and solutions",
		"Maintain consistent approaches across projects",
	})
	collaborationGuidance.Set("knowledge_sharing", []any{
		"Document decisions and rationale",
		"Update shared context with discoveries",
		"Provide clear handoff information",
	})

	hints.Set("collaboration_guidance", collaborationGuidance)
	return enhanced
}

func (s *EnhancementService) enhanceErrorResponse(response *entities.OrderedMap[any], action string, requestParams *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	enhanced := response.Copy()

	errorGuidance := entities.NewOrderedMap[any]()
	errorGuidance.Set("error_analysis", s.analyzeErrorType(response))
	errorGuidance.Set("suggested_fixes", s.suggestErrorFixes(response, action))
	errorGuidance.Set("prevention_tips", s.getErrorPreventionTips(response, action))
	errorGuidance.Set("next_steps", s.getErrorRecoverySteps(response, action))

	enhanced.Set("error_guidance", errorGuidance)
	return enhanced
}

func (s *EnhancementService) extractTaskContext(response *entities.OrderedMap[any], requestParams *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	context := entities.NewOrderedMap[any]()

	if taskAny, ok := response.Get("task"); ok {
		if task, ok := taskAny.(*entities.OrderedMap[any]); ok {
			for _, k := range task.KeysAny() {
				context.Set(k, task.GetAny(k))
			}
		}
	}

	relevantParams := []string{"git_branch_id", "project_id", "priority", "status"}
	for _, param := range relevantParams {
		if v, ok := requestParams.Get(param); ok {
			context.Set(param, v)
		}
	}

	return context
}

func (s *EnhancementService) addBasicWorkflowHints(response *entities.OrderedMap[any], action string) *entities.OrderedMap[any] {
	enhanced := response.Copy()

	basicHints := entities.NewOrderedMap[any]()
	basicHints.Set("action_completed", "Successfully performed "+action+" operation")
	basicHints.Set("general_guidance", []any{
		"Review the operation results",
		"Update related contexts if needed",
		"Consider next steps in your workflow",
	})
	basicHints.Set("best_practices", []any{
		"Keep operations focused and atomic",
		"Document important decisions",
		"Maintain consistent naming conventions",
	})

	enhanced.Set("workflow_guidance", basicHints)
	return enhanced
}

func (s *EnhancementService) generateWorkflowGuidance(taskContext *entities.OrderedMap[any], action string, requestParams *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	guidance := entities.NewOrderedMap[any]()
	guidance.Set("operation_summary", "Completed "+action+" operation")
	guidance.Set("context_insights", s.analyzeContextInsights(taskContext))
	guidance.Set("suggested_actions", s.suggestContextActions(taskContext, action))
	guidance.Set("workflow_stage", s.determineWorkflowStage(taskContext))
	guidance.Set("coordination_hints", s.getCoordinationHints(taskContext, action))
	return guidance
}

func (s *EnhancementService) analyzeTaskState(task *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	status := strings.ToLower(orderedString(task, "status", "pending"))
	priority := strings.ToLower(orderedString(task, "priority", "medium"))

	state := entities.NewOrderedMap[any]()
	state.Set("status", status)
	state.Set("priority", priority)
	state.Set("has_description", pyTruthy(orderedGet(task, "description")))
	state.Set("has_assignees", pyTruthy(orderedGet(task, "assignees")))
	state.Set("has_due_date", pyTruthy(orderedGet(task, "due_date")))
	state.Set("has_dependencies", pyTruthy(orderedGet(task, "dependencies")))
	state.Set("complexity_level", s.assessTaskComplexity(task))
	return state
}

func (s *EnhancementService) generateTaskGuidance(state *entities.OrderedMap[any], task *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	guidance := entities.NewOrderedMap[any]()
	guidance.Set("status_guidance", s.getStatusGuidance(orderedString(state, "status", "")))
	guidance.Set("priority_guidance", s.getPriorityGuidance(orderedString(state, "priority", "")))
	guidance.Set("completion_hints", s.getCompletionHints(state))
	guidance.Set("improvement_suggestions", s.getImprovementSuggestions(state, task))
	return guidance
}

func (s *EnhancementService) suggestNextActions(state *entities.OrderedMap[any], task *entities.OrderedMap[any]) []any {
	actions := []any{}

	if orderedString(state, "status", "") == "pending" {
		actions = append(actions, actionItem("start_work", "Begin working on the task", "high"))
	}
	if orderedString(state, "status", "") == "in_progress" {
		actions = append(actions, actionItem("update_progress", "Update task progress and add notes", "medium"))
	}
	if !orderedBool(state, "has_description") {
		actions = append(actions, actionItem("add_description", "Add detailed task description", "high"))
	}
	return actions
}

func (s *EnhancementService) assessTaskComplexity(task *entities.OrderedMap[any]) string {
	complexityScore := 0

	description := orderedString(task, "description", "")
	if len(description) > 500 {
		complexityScore += 2
	} else if len(description) > 100 {
		complexityScore += 1
	}

	dependencies := orderedList(task, "dependencies")
	complexityScore += minIntHelper(len(dependencies), 3)

	assignees := orderedList(task, "assignees")
	if len(assignees) > 3 {
		complexityScore += 2
	} else if len(assignees) > 1 {
		complexityScore += 1
	}

	if complexityScore <= 2 {
		return "simple"
	} else if complexityScore <= 4 {
		return "moderate"
	}
	return "complex"
}

func (s *EnhancementService) getLevelSpecificGuidance(level *string) []any {
	if level == nil {
		return []any{"Consider the appropriate context level for this operation"}
	}
	levelGuidance := map[string][]any{
		"global": {
			"This affects all projects - ensure broad compatibility",
			"Document changes that affect multiple teams",
			"Consider impact on existing workflows",
		},
		"project": {
			"Update project-level documentation",
			"Consider impact on other project components",
			"Share insights with project team",
		},
		"branch": {
			"Focus on branch-specific concerns",
			"Coordinate with other work on this branch",
			"Update branch progress tracking",
		},
		"task": {
			"Focus on task-specific details",
			"Update task progress and notes",
			"Link to related tasks when relevant",
		},
	}
	if v, ok := levelGuidance[*level]; ok {
		return v
	}
	return []any{"Context level not recognized"}
}

func (s *EnhancementService) analyzeErrorType(response *entities.OrderedMap[any]) string {
	error := orderedString(response, "error", "")

	if strings.Contains(strings.ToLower(error), "validation") {
		return "validation_error"
	} else if strings.Contains(strings.ToLower(error), "authentication") {
		return "authentication_error"
	} else if strings.Contains(strings.ToLower(error), "not found") {
		return "resource_not_found"
	}
	return "general_error"
}

func (s *EnhancementService) suggestErrorFixes(response *entities.OrderedMap[any], action string) []any {
	errorType := s.analyzeErrorType(response)

	fixes := map[string][]any{
		"validation_error": {
			"Check required parameters",
			"Verify parameter formats",
			"Review validation rules",
		},
		"authentication_error": {
			"Verify user credentials",
			"Check authentication context",
			"Ensure proper authorization",
		},
		"resource_not_found": {
			"Verify resource ID exists",
			"Check resource permissions",
			"Confirm resource hasn't been deleted",
		},
	}
	if v, ok := fixes[errorType]; ok {
		return v
	}
	return []any{"Review error details and retry"}
}

func (s *EnhancementService) getErrorPreventionTips(response *entities.OrderedMap[any], action string) []any {
	return []any{
		"Validate input parameters before operations",
		"Use consistent error handling patterns",
		"Implement proper logging for debugging",
	}
}

func (s *EnhancementService) getErrorRecoverySteps(response *entities.OrderedMap[any], action string) []any {
	return []any{
		"Review the error details carefully",
		"Fix the identified issues",
		"Retry the operation with corrected parameters",
	}
}

// Helpers specific to this module (unique names to avoid package collisions).

func orderedChild(parent *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	if v, ok := parent.Get(key); ok {
		if om, ok := v.(*entities.OrderedMap[any]); ok {
			return om
		}
	}
	om := entities.NewOrderedMap[any]()
	parent.Set(key, om)
	return om
}

func orderedGet(om *entities.OrderedMap[any], key string) any {
	v, _ := om.Get(key)
	return v
}

func orderedString(om *entities.OrderedMap[any], key, def string) string {
	if v, ok := om.Get(key); ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return def
}

func orderedBool(om *entities.OrderedMap[any], key string) bool {
	v, _ := om.Get(key)
	return pyTruthy(v)
}

func orderedList(om *entities.OrderedMap[any], key string) []any {
	if v, ok := om.Get(key); ok {
		if list, ok := v.([]any); ok {
			return list
		}
	}
	return []any{}
}

func responseBool(om *entities.OrderedMap[any], key string) bool {
	v, _ := om.Get(key)
	return pyTruthy(v)
}

func pyTruthy(v any) bool { return value_objects.PyTruthy(v) }

func actionItem(action, description, priority string) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("action", action)
	d.Set("description", description)
	d.Set("priority", priority)
	return d
}

func minIntHelper(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// The Python module calls the following methods in _generate_workflow_guidance and
// _generate_task_guidance but never defines them, so every such call raises
// AttributeError. The Go port panics with the same message to preserve the quirk.

func attributeError(name string) {
	panic("'EnhancementService' object has no attribute '" + name + "'")
}

func (s *EnhancementService) analyzeContextInsights(taskContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	attributeError("_analyze_context_insights")
	return nil
}

func (s *EnhancementService) suggestContextActions(taskContext *entities.OrderedMap[any], action string) []any {
	attributeError("_suggest_context_actions")
	return nil
}

func (s *EnhancementService) determineWorkflowStage(taskContext *entities.OrderedMap[any]) string {
	attributeError("_determine_workflow_stage")
	return ""
}

func (s *EnhancementService) getCoordinationHints(taskContext *entities.OrderedMap[any], action string) []any {
	attributeError("_get_coordination_hints")
	return nil
}

func (s *EnhancementService) getStatusGuidance(status string) []any {
	attributeError("_get_status_guidance")
	return nil
}

func (s *EnhancementService) getPriorityGuidance(priority string) []any {
	attributeError("_get_priority_guidance")
	return nil
}

func (s *EnhancementService) getCompletionHints(state *entities.OrderedMap[any]) []any {
	attributeError("_get_completion_hints")
	return nil
}

func (s *EnhancementService) getImprovementSuggestions(state *entities.OrderedMap[any], task *entities.OrderedMap[any]) []any {
	attributeError("_get_improvement_suggestions")
	return nil
}
