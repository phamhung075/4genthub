package task

// Enhanced Task workflow guidance implementation with autonomous AI capabilities
// (Python workflow_guidance/task/task_workflow_guidance.py).

import (
	"sort"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// WorkflowHintEnhancer is the minimal view of the workflow_hint_enhancer module,
// which IS ported (workflow_hint_enhancer.go). The hook below is still nil because
// the concrete type does not yet satisfy this interface - it lacks
// EnhanceErrorResponseV2 - so wiring it needs an adapter.
type WorkflowHintEnhancer interface {
	EnhanceErrorResponseV2(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any]
	EnhanceTaskResponse(response *entities.OrderedMap[any], action string, requestParams *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// NewWorkflowHintEnhancerFunc constructs a WorkflowHintEnhancer, mirroring
// `WorkflowHintEnhancer()`. Nil until workflow_hint_enhancer.go exists.
var NewWorkflowHintEnhancerFunc = func() WorkflowHintEnhancer { return nil }

// TaskWorkflowGuidance provides enhanced workflow guidance for autonomous AI task management.
type TaskWorkflowGuidance struct {
	workflowEnhancer WorkflowHintEnhancer
}

// NewTaskWorkflowGuidance ports __init__ (creates the enhanced workflow hint enhancer).
func NewTaskWorkflowGuidance() *TaskWorkflowGuidance {
	return &TaskWorkflowGuidance{workflowEnhancer: NewWorkflowHintEnhancerFunc()}
}

// EnhanceResponse ports enhance_response.
func (g *TaskWorkflowGuidance) EnhanceResponse(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if !value_objects.PyTruthy(twgGet(response, "success")) {
		if g.workflowEnhancer == nil {
			return response
		}
		return g.workflowEnhancer.EnhanceErrorResponseV2(response, action, context)
	}

	requestParams := context
	if requestParams == nil {
		requestParams = entities.NewOrderedMap[any]()
	}
	enhancedResponse := response
	if g.workflowEnhancer != nil {
		enhancedResponse = g.workflowEnhancer.EnhanceTaskResponse(response, action, requestParams)
	}

	var workflowGuidance *entities.OrderedMap[any]
	wgVal := twgGet(enhancedResponse, "workflow_guidance")
	if enhancedResponse != nil && enhancedResponse.Has("workflow_guidance") && value_objects.PyTruthy(wgVal) {
		workflowGuidance = twgOM(wgVal)
	} else {
		workflowGuidance = entities.NewOrderedMap[any]()
		workflowGuidance.Set("current_state", g.AnalyzeState(response, context))
		workflowGuidance.Set("rules", g.GetRules(action, response))
		workflowGuidance.Set("next_actions", g.SuggestNextActions(action, response, context))
		workflowGuidance.Set("hints", g.GenerateHints(action, response, context))
		workflowGuidance.Set("warnings", g.CheckWarnings(action, response, context))
		workflowGuidance.Set("examples", g.GetExamples(action, context))
		workflowGuidance.Set("parameter_guidance", g.GetParameterGuidance(action))
		enhancedResponse.Set("workflow_guidance", workflowGuidance)
	}

	switch action {
	case "create":
		if !workflowGuidance.Has("tips") {
			workflowGuidance.Set("tips", []any{
				"Break down complex tasks into subtasks for better tracking",
				"Update progress regularly to maintain context",
				"Use descriptive completion summaries for knowledge retention",
			})
		}
	case "list":
		workflowGuidance.Set("overview", g.generateListOverview(response))
		workflowGuidance.Set("dependency_overview", g.generateDependencyOverview(response))
	case "complete":
		workflowGuidance.Set("completion_checklist", []any{
			"✅ All acceptance criteria met",
			"✅ Code reviewed and tested",
			"✅ Documentation updated if needed",
			"✅ Completion summary provided",
			"✅ Testing notes documented",
			"✅ Any follow-up tasks created",
		})
	case "get":
		task := twgOM(twgGet(response, "task"))
		if value_objects.PyTruthy(twgGet(task, "dependency_relationships")) {
			workflowGuidance.Set("dependency_guidance", g.generateDependencyGuidance(task))
		}
	}

	if action == "create" || action == "get" || action == "next" {
		enhancedResponse.Set("ai_reminders", g.generateAIReminders(action, enhancedResponse, context))
	}

	return enhancedResponse
}

// AnalyzeState ports analyze_state.
func (g *TaskWorkflowGuidance) AnalyzeState(response *entities.OrderedMap[any], context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	state := entities.NewOrderedMap[any]()
	state.Set("phase", "unknown")

	task := twgOM(twgGet(response, "task"))
	if value_objects.PyTruthy(task) {
		status := twgStr(twgGetDef(task, "status", "todo"))
		progress := twgNum(twgGetDef(task, "overall_progress", 0))
		subtaskCount := len(twgList(twgGet(task, "subtasks")))

		switch status {
		case "todo":
			state.Set("phase", "not_started")
		case "in_progress":
			if progress < 25 {
				state.Set("phase", "early_progress")
			} else if progress < 75 {
				state.Set("phase", "mid_progress")
			} else {
				state.Set("phase", "near_completion")
			}
		case "done":
			state.Set("phase", "completed")
		case "blocked":
			state.Set("phase", "blocked")
		}

		state.Set("status", status)
		state.Set("progress", progress)
		state.Set("has_subtasks", subtaskCount > 0)
		state.Set("subtask_count", subtaskCount)
	}
	return state
}

// GetRules ports get_rules.
func (g *TaskWorkflowGuidance) GetRules(action string, response *entities.OrderedMap[any]) []string {
	rules := []string{}
	rules = append(rules, "📝 Always provide context when updating tasks")
	rules = append(rules, "🔄 Update task status to reflect actual progress")

	switch action {
	case "create":
		rules = append(rules,
			"🎯 Make task titles specific and actionable",
			"📊 Include estimated effort for better planning",
			"🏷️ Use labels for categorization",
		)
	case "update":
		rules = append(rules,
			"💡 Document any blockers or challenges",
			"📈 Update progress percentage if applicable",
		)
	case "complete":
		rules = append(rules,
			"✅ Provide comprehensive completion summary",
			"🧪 Document testing performed",
			"📚 Share insights for future reference",
		)
	}
	return rules
}

// SuggestNextActions ports suggest_next_actions.
func (g *TaskWorkflowGuidance) SuggestNextActions(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []any {
	suggestions := []any{}

	task := twgOM(twgGet(response, "task"))
	taskID := twgOr(twgGet(task, "id"), twgGet(context, "task_id"))
	taskStatus := twgStr(twgGetDef(task, "status", "todo"))
	hasContext := value_objects.PyTruthy(twgGet(task, "context_id"))

	if action == "create" && value_objects.PyTruthy(taskID) {
		if !hasContext {
			suggestions = append(suggestions, twgMap(
				"priority", "critical",
				"action", "Create context",
				"description", "REQUIRED: Create context before working - task completion will fail without this",
				"example", twgMap(
					"tool", "manage_context",
					"params", twgMap(
						"action", "create",
						"level", "task",
						"context_id", taskID,
						"data", twgMap("title", "Task Title", "description", "Task context"),
					),
				),
			))
		}
		suggestions = append(suggestions, twgMap(
			"priority", "high",
			"action", "Start work",
			"description", "Update status to in_progress when you begin",
			"example", twgMap(
				"action", "update",
				"task_id", taskID,
				"status", "in_progress",
				"details", "Starting work on [describe what you're doing]",
			),
		))
		suggestions = append(suggestions, twgMap(
			"priority", "medium",
			"action", "Add subtasks",
			"description", "Break down complex work into subtasks",
			"example", twgMap(
				"tool", "manage_subtask",
				"params", twgMap(
					"action", "create",
					"task_id", taskID,
					"title", "Implement core functionality",
					"description", "Build the main feature component",
				),
			),
		))
	} else if taskStatus == "todo" {
		if !hasContext {
			suggestions = append(suggestions, twgMap(
				"priority", "critical",
				"action", "Create context first",
				"description", "Context is required for task completion - create it now",
				"example", twgMap(
					"tool", "manage_context",
					"params", twgMap(
						"action", "create",
						"level", "task",
						"context_id", taskID,
						"data", twgMap("title", "Task Title", "description", "Task context"),
					),
				),
			))
		}
		suggestions = append(suggestions, twgMap(
			"priority", "high",
			"action", "Begin task",
			"description", "Start work by updating status",
			"example", twgMap(
				"action", "update",
				"task_id", taskID,
				"status", "in_progress",
				"details", "Starting work on [specific component/feature]",
			),
		))
	} else if taskStatus == "in_progress" {
		if !hasContext {
			suggestions = append(suggestions, twgMap(
				"priority", "critical",
				"action", "Create context NOW",
				"description", "URGENT: Context required for completion - create immediately",
				"example", twgMap(
					"tool", "manage_context",
					"params", twgMap(
						"action", "create",
						"level", "task",
						"context_id", taskID,
						"data", twgMap("title", "Task Title", "description", "Task context"),
					),
				),
			))
		}
		suggestions = append(suggestions, twgMap(
			"priority", "high",
			"action", "Track progress",
			"description", "Add progress notes to maintain context",
			"example", twgMap(
				"tool", "manage_context",
				"params", twgMap(
					"action", "add_progress",
					"level", "task",
					"context_id", taskID,
					"content", "Completed X, working on Y",
					"agent", "ai_assistant",
				),
			),
		))
		if twgNum(twgGetDef(task, "overall_progress", 0)) > 80 {
			suggestions = append(suggestions, twgMap(
				"priority", "high",
				"action", "Complete task",
				"description", "Task is nearly done - complete with summary",
				"example", twgMap(
					"action", "complete",
					"task_id", taskID,
					"completion_summary", "Successfully implemented [describe achievements]",
					"testing_notes", "Tested [describe testing approach and results]",
				),
			))
		} else {
			suggestions = append(suggestions, twgMap(
				"priority", "medium",
				"action", "Update progress",
				"description", "Document blockers if stuck, or progress if advancing",
				"example", twgMap(
					"action", "update",
					"task_id", taskID,
					"status", "in_progress",
					"details", "Progress: [describe current work and next steps]",
				),
			))
		}
	} else if taskStatus == "review" || taskStatus == "testing" {
		if !hasContext {
			suggestions = append(suggestions, twgMap(
				"priority", "critical",
				"action", "Create context for completion",
				"description", "REQUIRED: Context must exist before completing",
				"example", twgMap(
					"tool", "manage_context",
					"params", twgMap(
						"action", "create",
						"level", "task",
						"context_id", taskID,
						"data", twgMap("title", "Task Title", "description", "Task context"),
					),
				),
			))
		}
		suggestions = append(suggestions, twgMap(
			"priority", "high",
			"action", "Complete task",
			"description", "Task is ready for completion",
			"example", twgMap(
				"action", "complete",
				"task_id", taskID,
				"completion_summary", "Successfully completed [describe what was accomplished]",
				"testing_notes", "Testing completed: [describe testing approach and results]",
			),
		))
	} else if taskStatus == "blocked" {
		suggestions = append(suggestions, twgMap(
			"priority", "high",
			"action", "Resolve blocker",
			"description", "Document the blocker and create resolution plan",
			"example", twgMap(
				"action", "update",
				"task_id", taskID,
				"details", "Blocked by: [specific issue]. Resolution plan: [steps to unblock]",
			),
		))
		suggestions = append(suggestions, twgMap(
			"priority", "medium",
			"action", "Create blocker task",
			"description", "Create separate task to resolve the blocking issue",
			"example", twgMap(
				"action", "create",
				"git_branch_id", "your_branch_id",
				"title", "Resolve blocker: [issue description]",
				"description", "Unblock task by addressing [specific blocking issue]",
			),
		))
	}
	return suggestions
}

// GenerateHints ports generate_hints.
func (g *TaskWorkflowGuidance) GenerateHints(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []string {
	hints := []string{}

	task := twgOM(twgGet(response, "task"))
	hasContext := value_objects.PyTruthy(twgGet(task, "context_id"))

	if !value_objects.PyTruthy(twgGet(response, "success")) {
		errorMsg := strings.ToLower(twgStr(twgGetDef(response, "error", "")))
		if strings.Contains(errorMsg, "validation error") {
			hints = append(hints,
				"🔧 VALIDATION ERROR RECOVERY: Use arrays like labels=['tag1','tag2'], not strings",
				"📝 For progress_percentage, use integers 0-100: progress_percentage=50",
			)
		} else if strings.Contains(errorMsg, "context must be updated") {
			hints = append(hints,
				"🔧 CONTEXT ERROR RECOVERY: Run manage_context(action='create', level='task', context_id='your_task_id', data={'title': 'Task Title'})",
				"📋 Then update context with manage_context(action='update', level='task', context_id='task_id', data={'status': 'done'})",
			)
		} else if strings.Contains(errorMsg, "missing required") {
			hints = append(hints,
				"🔧 MISSING FIELD RECOVERY: Check the error for required fields and add them",
				"📚 Use workflow guidance examples for correct parameter format",
			)
		}
	}

	switch action {
	case "create":
		hints = append(hints, "💡 Consider adding subtasks if this work has multiple components")
		hints = append(hints, "🎯 Set a realistic estimated_effort to help with planning")
		if !hasContext {
			hints = append(hints, "⚠️ CRITICAL: Create context immediately after task creation")
		}
		hints = append(hints, "🔧 If validation fails: Use arrays for labels=['tag1','tag2'], not strings")
	case "list":
		taskCount := twgNum(twgGetDef(response, "count", 0))
		if taskCount > 10 {
			hints = append(hints,
				"📋 Many tasks found - consider using filters to narrow results",
				"🔍 Try: status='in_progress' or priority='high' to filter",
			)
		}
		if taskCount == 0 {
			hints = append(hints,
				"🚀 No tasks found - create one to get started",
				"💡 Check if you're in the right git branch with git_branch_id parameter",
			)
		}
	case "update":
		taskStatus := twgGet(task, "status")
		if twgStr(taskStatus) == "blocked" {
			hints = append(hints,
				"🚧 Task is blocked - document the blocker in details field",
				"💭 Consider creating a separate task to resolve the blocker",
			)
		} else if twgStr(taskStatus) == "in_progress" && !hasContext {
			hints = append(hints, "🚨 URGENT: Create context now - completion will fail without it")
		} else if twgStr(taskStatus) == "in_progress" {
			hints = append(hints,
				"📈 Track progress with manage_context(action='add_progress', level='task', context_id='task_id', content='Progress update')",
				"🔄 Update parent task progress syncs automatically from subtasks",
			)
		}
	case "complete":
		if !hasContext {
			hints = append(hints, "🚨 COMPLETION WILL FAIL: Create context first with manage_context")
		}
		hints = append(hints,
			"📝 Detailed completion summaries help with knowledge retention",
			"🧪 Document testing approach for future reference",
			"🎯 Include specific achievements and next recommendations",
		)
	case "search":
		hints = append(hints,
			"🔍 Use specific keywords for better search results",
			"💡 Search in title, description, and labels fields",
		)
	}

	subtaskCount := len(twgList(twgGet(task, "subtasks")))
	if subtaskCount > 0 {
		hints = append(hints, "🔗 Subtask progress automatically updates parent task statistics")
	}
	return hints
}

// CheckWarnings ports check_warnings.
func (g *TaskWorkflowGuidance) CheckWarnings(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []string {
	warnings := []string{}

	task := twgOM(twgGet(response, "task"))

	status := twgStr(twgGet(task, "status"))
	if (status == "in_progress" || status == "review" || status == "testing") && !value_objects.PyTruthy(twgGet(task, "context_id")) {
		warnings = append(warnings, "🚨 CRITICAL: Create context before completing this task!")
		warnings = append(warnings, "💡 Use: manage_context(action='create', level='task', context_id='"+twgStr(twgGetDef(task, "id", "task-id"))+"', data={'title': 'Task Title'})")
	}

	if (action == "update" || action == "complete") && (status == "in_progress" || status == "review") {
		if !value_objects.PyTruthy(twgGet(task, "context_id")) {
			warnings = append(warnings, "⚠️ Task completion will FAIL without context. Create context first!")
		}
	}

	if action == "complete" && !value_objects.PyTruthy(twgGet(context, "completion_summary")) {
		warnings = append(warnings,
			"⚠️ No completion summary provided - context will be lost",
			"💡 Recovery: Add completion_summary parameter describing what was accomplished",
		)
	}

	if status == "in_progress" {
		updatedAt := twgGet(task, "updated_at")
		if value_objects.PyTruthy(updatedAt) {
			raw := strings.ReplaceAll(twgStr(updatedAt), "Z", "+00:00")
			if lastUpdate, err := value_objects.ParseISO(raw); err == nil {
				daysOld := int(time.Since(lastUpdate).Hours() / 24)
				if daysOld > 7 {
					warnings = append(warnings,
						"⚠️ Task hasn't been updated in "+strconv.Itoa(daysOld)+" days",
						"💡 Consider updating progress or changing status to 'blocked'",
					)
				}
			}
		}
	}

	if action == "create" && value_objects.PyTruthy(twgGet(response, "success")) {
		warnings = append(warnings, "💡 TIP: If you get validation errors, use arrays like labels=['tag1','tag2'] not strings")
	}

	if action == "update" && status == "in_progress" {
		subtaskCount := len(twgList(twgGet(task, "subtasks")))
		if subtaskCount > 0 {
			warnings = append(warnings, "💡 Remember: Subtask progress updates automatically sync to parent task")
		}
	}

	if action == "list" {
		inProgress := 0
		for _, t := range twgList(twgGet(response, "tasks")) {
			if twgStr(twgGet(twgOM(t), "status")) == "in_progress" {
				inProgress++
			}
		}
		if inProgress > 5 {
			warnings = append(warnings,
				"⚠️ "+strconv.Itoa(inProgress)+" tasks in progress - consider completing some first",
				"💡 Use manage_task(action='list', status='in_progress') to review active tasks",
			)
		}
	}

	return warnings
}

// GetExamples ports get_examples.
func (g *TaskWorkflowGuidance) GetExamples(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	examples := entities.NewOrderedMap[any]()

	taskID := twgGetDef(context, "task_id", "task-id")
	gitBranchID := twgGetDef(context, "git_branch_id", "branch-id")

	switch action {
	case "create":
		examples.Set("start_work", twgMap(
			"description", "Start working on the task",
			"command", "manage_task(action=\"update\", task_id=\""+twgStr(taskID)+"\", status=\"in_progress\", details=\"Starting implementation of authentication system\")",
		))
		examples.Set("create_context", twgMap(
			"description", "Create task context (REQUIRED before completion)",
			"command", "manage_context(action=\"create\", level=\"task\", context_id=\""+twgStr(taskID)+"\", data={\"title\": \"Task Title\", \"description\": \"Task context and requirements\"})",
		))
		examples.Set("add_subtasks", twgMap(
			"description", "Break down into subtasks",
			"command", "manage_subtask(action=\"create\", task_id=\""+twgStr(taskID)+"\", title=\"Implement login endpoint\", description=\"Create POST /auth/login endpoint\")",
		))
	case "update":
		examples.Set("update_status", twgMap(
			"description", "Update task status and add progress notes",
			"command", "manage_task(action=\"update\", task_id=\""+twgStr(taskID)+"\", status=\"in_progress\", details=\"Completed database schema, working on API endpoints\")",
		))
		examples.Set("update_blocked", twgMap(
			"description", "Mark task as blocked with reason",
			"command", "manage_task(action=\"update\", task_id=\""+twgStr(taskID)+"\", status=\"blocked\", details=\"Waiting for API credentials from third-party service\")",
		))
	case "complete":
		examples.Set("complete_basic", twgMap(
			"description", "Complete task with summary",
			"command", "manage_task(action=\"complete\", task_id=\""+twgStr(taskID)+"\", completion_summary=\"Implemented full authentication flow with JWT tokens\")",
		))
		examples.Set("complete_detailed", twgMap(
			"description", "Complete with testing notes",
			"command", "manage_task(action=\"complete\", task_id=\""+twgStr(taskID)+"\", completion_summary=\"Built complete user management API\", testing_notes=\"Added unit tests for all endpoints, integration tests for auth flow, 95% code coverage\")",
		))
	case "list":
		examples.Set("list_filtered", twgMap(
			"description", "List tasks with filters",
			"command", "manage_task(action=\"list\", git_branch_id=\""+twgStr(gitBranchID)+"\", status=\"in_progress\", priority=\"high\")",
		))
		examples.Set("list_all", twgMap(
			"description", "List all tasks in branch",
			"command", "manage_task(action=\"list\", git_branch_id=\""+twgStr(gitBranchID)+"\")",
		))
	}
	return examples
}

// GetParameterGuidance ports get_parameter_guidance.
func (g *TaskWorkflowGuidance) GetParameterGuidance(action string) *entities.OrderedMap[any] {
	guidance := entities.NewOrderedMap[any]()

	nextActionParams := map[string][]string{
		"create":            {"task_id", "status", "details", "context_id", "level", "data"},
		"update":            {"task_id", "status", "details", "completion_summary", "testing_notes"},
		"complete":          {"git_branch_id", "status"},
		"get":               {"task_id", "status", "details"},
		"list":              {"task_id", "status", "details"},
		"search":            {"task_id", "include_context"},
		"next":              {"task_id", "status", "details"},
		"add_dependency":    {"task_id"},
		"remove_dependency": {"task_id"},
	}

	params := nextActionParams[action]
	applicable := make([]any, len(params))
	for i, p := range params {
		applicable[i] = p
	}
	guidance.Set("applicable_parameters", applicable)

	tips := entities.NewOrderedMap[any]()
	for _, p := range params {
		if tip := twgParamTip(p); tip != nil {
			tips.Set(p, tip)
		}
	}
	guidance.Set("parameter_tips", tips)
	return guidance
}

func twgParamTip(param string) *entities.OrderedMap[any] {
	switch param {
	case "task_id":
		return twgMap(
			"requirement", "REQUIRED for most operations",
			"tip", "Use the task_id returned from creation",
			"when_to_use", "For update, complete, get operations",
		)
	case "status":
		return twgMap(
			"requirement", "RECOMMENDED for update",
			"tip", "Track task progress through workflow states",
			"values", []any{"todo", "in_progress", "blocked", "review", "testing", "done", "cancelled"},
			"next_action_tips", twgMap(
				"create", "Set to 'in_progress' when starting work",
				"update", "Update as work progresses through stages",
			),
		)
	case "details":
		return twgMap(
			"requirement", "HIGHLY RECOMMENDED for updates",
			"tip", "Document progress, blockers, and next steps",
			"when_to_use", "Every time you update task status or make progress",
			"examples", []any{
				"Started implementation - completed database schema",
				"50% complete - login endpoint working, adding tests",
				"Blocked by missing API documentation",
			},
		)
	case "context_id":
		return twgMap(
			"requirement", "REQUIRED for context operations",
			"tip", "Use task_id as context_id for task-level context",
			"when_to_use", "After creating task, before completing it",
		)
	case "level":
		return twgMap(
			"requirement", "REQUIRED for context operations",
			"tip", "Use 'task' for task-level context",
			"values", []any{"global", "project", "branch", "task"},
		)
	case "data":
		return twgMap(
			"requirement", "REQUIRED for context creation",
			"tip", "Provide task context including requirements and approach",
			"examples", []any{
				"{\"title\": \"Implement Auth\", \"description\": \"JWT authentication system\"}",
				"{\"requirements\": [\"Login\", \"Logout\", \"Token refresh\"]}",
			},
		)
	case "completion_summary":
		return twgMap(
			"requirement", "HIGHLY RECOMMENDED for complete",
			"tip", "Document what was accomplished for future reference",
			"when_to_use", "When task is fully complete and ready to close",
			"best_practice", "Include key decisions, implementation details, and outcomes",
			"examples", []any{
				"Implemented JWT auth with 2FA support, added password reset flow, integrated with existing user service",
			},
		)
	case "testing_notes":
		return twgMap(
			"requirement", "RECOMMENDED for complete",
			"tip", "Document testing approach and coverage",
			"when_to_use", "When completing task to document quality assurance",
			"examples", []any{
				"Added unit tests with 90% coverage",
				"Manual testing completed on staging",
				"Load tested with 1000 concurrent users",
			},
		)
	case "git_branch_id":
		return twgMap(
			"requirement", "REQUIRED for list operations",
			"tip", "Filter tasks by git branch",
			"when_to_use", "After completing task to see other pending work",
		)
	case "include_context":
		return twgMap(
			"requirement", "Optional (default: false)",
			"tip", "Set to true for detailed task context and AI insights",
			"when_to_use", "When you need vision system insights or planning guidance",
		)
	}
	return nil
}

func (g *TaskWorkflowGuidance) generateAIReminders(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	reminders := entities.NewOrderedMap[any]()

	task := twgOM(twgGet(response, "task"))
	taskID := twgOr(twgGet(task, "id"), twgGet(context, "task_id"))

	switch action {
	case "create":
		reminders.Set("important", "📝 Remember to update task status when you start working!")
		reminders.Set("next_step", "Update status to 'in_progress' when beginning work")
		reminders.Set("example", twgMap(
			"tool", "manage_task",
			"params", twgMap(
				"action", "update",
				"task_id", taskID,
				"status", "in_progress",
				"details", "Starting implementation",
			),
		))
	case "get":
		reminders.Set("important", "📝 Remember to update progress and context!")
		reminders.Set("update_example", twgMap(
			"tool", "manage_task",
			"params", twgMap(
				"action", "update",
				"task_id", taskID,
				"details", "Describe what you've done",
				"status", "in_progress",
			),
		))
		reminders.Set("completion_example", twgMap(
			"tool", "manage_task",
			"params", twgMap(
				"action", "complete",
				"task_id", taskID,
				"completion_summary", "Brief summary of what was accomplished",
				"testing_notes", "Description of tests performed",
			),
		))
		if twgStr(twgGet(task, "status")) == "todo" {
			reminders.Set("next_step", "Start by updating status to 'in_progress'")
		} else {
			reminders.Set("next_step", "Continue working and update progress")
		}
	}
	return reminders
}

func (g *TaskWorkflowGuidance) generateListOverview(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	tasks := twgList(twgGet(response, "tasks"))
	total := len(tasks)

	byStatus := entities.NewOrderedMap[any]()
	byPriority := entities.NewOrderedMap[any]()

	for _, t := range tasks {
		task := twgOM(t)
		status := twgStr(twgGetDef(task, "status", "unknown"))
		priority := twgStr(twgGetDef(task, "priority", "medium"))

		var list []any
		if cur, ok := byStatus.Get(status); ok {
			list = cur.([]any)
		} else {
			list = []any{}
		}
		byStatus.Set(status, append(list, twgMap(
			"id", twgGet(task, "id"),
			"title", twgGet(task, "title"),
			"priority", priority,
		)))

		count := 0
		if cur, ok := byPriority.Get(priority); ok {
			count = cur.(int)
		}
		byPriority.Set(priority, count+1)
	}

	overview := entities.NewOrderedMap[any]()
	overview.Set("total_tasks", total)
	overview.Set("by_status", byStatus)
	overview.Set("by_priority", byPriority)

	recommendations := []any{}
	if blocked, ok := byStatus.Get("blocked"); ok && len(blocked.([]any)) > 0 {
		recommendations = append(recommendations, "Address blocked tasks to unblock progress")
	}
	if inProgress, ok := byStatus.Get("in_progress"); ok && len(inProgress.([]any)) > 3 {
		recommendations = append(recommendations, "Focus on completing in-progress tasks before starting new ones")
	}
	inProgress, hasInProgress := byStatus.Get("in_progress")
	todo, hasTodo := byStatus.Get("todo")
	if (!hasInProgress || len(inProgress.([]any)) == 0) && hasTodo && len(todo.([]any)) > 0 {
		recommendations = append(recommendations, "Start working on pending tasks")
	}
	overview.Set("recommendations", recommendations)

	return overview
}

func (g *TaskWorkflowGuidance) generateDependencyOverview(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	tasks := twgList(twgGet(response, "tasks"))

	overview := entities.NewOrderedMap[any]()
	overview.Set("total_tasks", len(tasks))
	overview.Set("blocked_tasks", 0)
	overview.Set("blocking_tasks", 0)
	overview.Set("ready_tasks", 0)
	overview.Set("dependency_chains", 0)

	for _, t := range tasks {
		depSummary := twgOM(twgGetDef(twgOM(t), "dependency_summary", nil))
		if value_objects.PyTruthy(twgGet(depSummary, "is_blocked")) {
			cur, _ := overview.Get("blocked_tasks")
			overview.Set("blocked_tasks", cur.(int)+1)
		}
		if value_objects.PyTruthy(twgGet(depSummary, "is_blocking_others")) {
			cur, _ := overview.Get("blocking_tasks")
			overview.Set("blocking_tasks", cur.(int)+1)
		}
		if value_objects.PyTruthy(twgGet(depSummary, "can_start")) {
			cur, _ := overview.Get("ready_tasks")
			overview.Set("ready_tasks", cur.(int)+1)
		}
	}

	recommendations := []any{}
	blocked, _ := overview.Get("blocked_tasks")
	blocking, _ := overview.Get("blocking_tasks")
	ready, _ := overview.Get("ready_tasks")
	if blocked.(int) > 0 {
		recommendations = append(recommendations, "🚧 "+strconv.Itoa(blocked.(int))+" task(s) are blocked - work on dependencies first")
	}
	if blocking.(int) > 0 {
		recommendations = append(recommendations, "🔓 "+strconv.Itoa(blocking.(int))+" task(s) are blocking others - prioritize these")
	}
	if ready.(int) > 0 {
		recommendations = append(recommendations, "✅ "+strconv.Itoa(ready.(int))+" task(s) are ready to start")
	}
	overview.Set("recommendations", recommendations)

	return overview
}

func (g *TaskWorkflowGuidance) generateDependencyGuidance(task *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	depRel := twgOM(twgGet(task, "dependency_relationships"))

	guidance := entities.NewOrderedMap[any]()
	guidance.Set("dependency_status", "unknown")

	recommendations := []any{}
	dependencyChainInfo := []any{}
	workflowActions := []any{}

	summary := twgOM(twgGet(depRel, "summary"))
	workflow := twgOM(twgGet(depRel, "workflow"))

	if value_objects.PyTruthy(twgGet(summary, "can_start")) {
		guidance.Set("dependency_status", "ready")
		recommendations = append(recommendations, "✅ Task is ready to start - no blocking dependencies")
	} else if value_objects.PyTruthy(twgGet(summary, "is_blocked")) {
		guidance.Set("dependency_status", "blocked")
		recommendations = append(recommendations, "🚧 Task is blocked by dependencies")
	} else {
		guidance.Set("dependency_status", "waiting")
		recommendations = append(recommendations, "⏳ Task is waiting for dependencies to complete")
	}

	workflowActions = append(workflowActions, twgList(twgGet(workflow, "next_actions"))...)

	for _, c := range twgList(twgGet(depRel, "dependency_chains")) {
		chain := twgOM(c)
		chainInfo := entities.NewOrderedMap[any]()
		chainInfo.Set("chain_id", twgGet(chain, "chain_id"))
		chainInfo.Set("status", twgGet(chain, "chain_status"))
		chainInfo.Set("progress", twgStr(twgGet(chain, "completed_tasks"))+"/"+twgStr(twgGet(chain, "total_tasks"))+" tasks completed")
		chainInfo.Set("completion_percentage", twgGet(chain, "completion_percentage"))
		if nextTask := twgOM(twgGet(chain, "next_task")); value_objects.PyTruthy(nextTask) {
			chainInfo.Set("next_task", twgGet(nextTask, "title"))
		}
		dependencyChainInfo = append(dependencyChainInfo, chainInfo)
	}

	guidance.Set("recommendations", recommendations)
	guidance.Set("dependency_chain_info", dependencyChainInfo)
	guidance.Set("workflow_actions", workflowActions)

	blockingInfo := twgOM(twgGet(workflow, "blocking_info"))
	if value_objects.PyTruthy(twgGet(blockingInfo, "is_blocked")) {
		blockingDetails := entities.NewOrderedMap[any]()
		blockingDetails.Set("blocking_tasks", len(twgList(twgGet(blockingInfo, "blocking_tasks"))))
		blockingDetails.Set("blocking_chains", len(twgList(twgGet(blockingInfo, "blocking_chains"))))
		blockingDetails.Set("resolution_suggestions", twgGetDef(blockingInfo, "resolution_suggestions", []any{}))
		guidance.Set("blocking_details", blockingDetails)
	}

	return guidance
}

// --- helpers ---

func twgMap(kv ...any) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		om.Set(kv[i].(string), kv[i+1])
	}
	return om
}

func twgGet(om *entities.OrderedMap[any], k string) any {
	if om == nil {
		return nil
	}
	v, _ := om.Get(k)
	return v
}

func twgGetDef(om *entities.OrderedMap[any], k string, def any) any {
	if om == nil {
		return def
	}
	if v, ok := om.Get(k); ok {
		return v
	}
	return def
}

func twgOr(a, b any) any {
	if value_objects.PyTruthy(a) {
		return a
	}
	return b
}

func twgOM(v any) *entities.OrderedMap[any] {
	switch t := v.(type) {
	case *entities.OrderedMap[any]:
		return t
	case map[string]any:
		om := entities.NewOrderedMap[any]()
		keys := make([]string, 0, len(t))
		for k := range t {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			om.Set(k, t[k])
		}
		return om
	}
	return nil
}

func twgList(v any) []any {
	switch t := v.(type) {
	case []any:
		return t
	case []string:
		out := make([]any, len(t))
		for i, s := range t {
			out[i] = s
		}
		return out
	}
	return nil
}

func twgNum(v any) float64 {
	switch t := v.(type) {
	case float64:
		return t
	case float32:
		return float64(t)
	case int:
		return float64(t)
	case int64:
		return float64(t)
	case int32:
		return float64(t)
	}
	return 0
}

func twgStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return value_objects.PyStr(v)
}
