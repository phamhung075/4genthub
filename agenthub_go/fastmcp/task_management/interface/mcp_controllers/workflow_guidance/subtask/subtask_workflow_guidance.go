package subtask

// Subtask workflow guidance implementation
// (Python workflow_guidance/subtask/subtask_workflow_guidance.py).

import (
	"sort"
	"strconv"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskWorkflowGuidance provides comprehensive workflow guidance for subtask management.
type SubtaskWorkflowGuidance struct{}

// EnhanceResponse ports enhance_response.
func (g *SubtaskWorkflowGuidance) EnhanceResponse(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if !value_objects.PyTruthy(swgGet(response, "success")) {
		return response
	}

	subtask := swgOM(swgGet(response, "subtask"))
	subtasks := swgList(swgGet(response, "subtasks"))

	var currentState *entities.OrderedMap[any]
	if action == "list" {
		currentState = g.analyzeSubtasksState(subtasks)
	} else if value_objects.PyTruthy(subtask) {
		if swgHas(subtask, "subtask") {
			currentState = g.analyzeSubtaskState(swgOM(swgGet(subtask, "subtask")))
		} else {
			currentState = g.analyzeSubtaskState(subtask)
		}
	} else {
		currentState = entities.NewOrderedMap[any]()
		currentState.Set("phase", "unknown")
	}

	workflowGuidance := entities.NewOrderedMap[any]()
	workflowGuidance.Set("current_state", currentState)
	workflowGuidance.Set("rules", g.GetRules(action, response))
	workflowGuidance.Set("next_actions", g.SuggestNextActions(action, response, context))
	workflowGuidance.Set("hints", g.GenerateHints(action, response, context))
	workflowGuidance.Set("warnings", g.CheckWarnings(action, response, context))
	workflowGuidance.Set("examples", g.GetExamples(action, context))
	workflowGuidance.Set("parameter_guidance", g.GetParameterGuidance(action))

	switch action {
	case "create":
		workflowGuidance.Set("tips", []any{
			"🚀 Start working: Update status to 'in_progress' when you begin",
			"📊 Track progress: Use progress_percentage to show completion (0-100)",
			"🚧 Report blockers: Document any issues that prevent progress",
		})
	case "update":
		workflowGuidance.Set("tips", []any{
			"📊 Use progress_percentage to track completion (0-100)",
			"🚧 Document blockers immediately when encountered",
			"💡 Share insights that might help with other subtasks",
		})
	case "complete":
		workflowGuidance.Set("completion_checklist", []any{
			"✅ Subtask fully implemented and tested",
			"📝 Completion summary provided",
			"💡 Key insights documented",
			"🔗 Impact on parent task explained",
		})
	case "list":
		workflowGuidance.Set("overview", g.generateSubtasksOverview(swgOrList(subtasks)))
	}

	response.Set("workflow_guidance", workflowGuidance)
	return response
}

// AnalyzeState ports analyze_state.
func (g *SubtaskWorkflowGuidance) AnalyzeState(response *entities.OrderedMap[any], context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	subtask := swgOM(swgGet(response, "subtask"))
	if subtask != nil && swgHas(subtask, "subtask") {
		return g.analyzeSubtaskState(swgOM(swgGet(subtask, "subtask")))
	}
	return g.analyzeSubtaskState(subtask)
}

func (g *SubtaskWorkflowGuidance) analyzeSubtaskState(subtask *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	status := swgStr(swgGetDef(subtask, "status", "todo"))

	var phase string
	switch status {
	case "todo":
		phase = "not_started"
	case "in_progress":
		phase = "in_progress"
	case "done":
		phase = "completed"
	default:
		phase = status
	}

	out := entities.NewOrderedMap[any]()
	out.Set("phase", phase)
	out.Set("status", status)
	out.Set("has_assignees", value_objects.PyTruthy(swgGet(subtask, "assignees")))
	return out
}

func (g *SubtaskWorkflowGuidance) analyzeSubtasksState(subtasks []any) *entities.OrderedMap[any] {
	total := len(subtasks)
	if total == 0 {
		out := entities.NewOrderedMap[any]()
		out.Set("phase", "no_subtasks")
		out.Set("total", 0)
		return out
	}

	completed := 0
	inProgress := 0
	todo := 0
	for _, s := range subtasks {
		switch swgStr(swgGet(swgOM(s), "status")) {
		case "done":
			completed++
		case "in_progress":
			inProgress++
		case "todo":
			todo++
		}
	}

	var phase string
	if completed == total {
		phase = "all_complete"
	} else if inProgress > 0 || completed > 0 {
		phase = "in_progress"
	} else {
		phase = "not_started"
	}

	out := entities.NewOrderedMap[any]()
	out.Set("phase", phase)
	out.Set("total", total)
	out.Set("completed", completed)
	out.Set("in_progress", inProgress)
	out.Set("todo", todo)
	completionPercentage := 0
	if total > 0 {
		completionPercentage = int((float64(completed) / float64(total)) * 100)
	}
	out.Set("completion_percentage", completionPercentage)
	return out
}

// GetRules ports get_rules.
func (g *SubtaskWorkflowGuidance) GetRules(action string, response *entities.OrderedMap[any]) []string {
	rules := []string{}
	rules = append(rules, "📝 Keep parent task updated with subtask progress")
	rules = append(rules, "🔄 Update subtask status when work begins/ends")

	switch action {
	case "create":
		rules = append(rules,
			"🎯 Make subtask titles clear and actionable",
			"📏 Size subtasks appropriately (2-4 hours)",
			"🔗 Consider dependencies between subtasks",
		)
	case "update":
		rules = append(rules,
			"📊 Update progress_percentage (0-100)",
			"🚧 Document blockers immediately",
			"💡 Share insights for team learning",
		)
	case "complete":
		rules = append(rules,
			"📝 Completion summary is highly recommended",
			"💡 Document any insights or learnings",
			"🔗 Explain impact on parent task",
		)
	}
	return rules
}

// SuggestNextActions ports suggest_next_actions.
func (g *SubtaskWorkflowGuidance) SuggestNextActions(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []any {
	actions := []any{}

	taskID := swgGet(context, "task_id")
	subtaskID := swgGet(context, "subtask_id")
	state := swgOM(swgGet(swgOM(swgGet(response, "workflow_guidance")), "current_state"))

	switch action {
	case "list":
		if swgNum(swgGetDef(state, "todo", 0)) > 0 {
			actions = append(actions, swgMap(
				"priority", "high",
				"action", "Start next subtask",
				"description", "Pick a todo subtask and begin work",
				"example", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='...', status='in_progress', progress_notes='Starting implementation')",
			))
		}
		if swgStr(swgGet(state, "phase")) == "all_complete" {
			actions = append(actions, swgMap(
				"priority", "high",
				"action", "Complete parent task",
				"description", "All subtasks done - consider completing the parent",
				"example", "manage_task(action='complete', task_id='"+value_objects.PyStr(taskID)+"', completion_summary='All subtasks completed successfully')",
			))
		}
	case "create":
		createdSubtaskID := swgGetDef(swgOM(swgGet(response, "subtask")), "id", "new-subtask-id")
		actions = append(actions, swgMap(
			"priority", "high",
			"action", "Start the subtask",
			"description", "Update status when you begin work",
			"example", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(createdSubtaskID)+"', progress_percentage=10, progress_notes='Initial setup complete')",
		))
	case "update":
		subtask := swgOM(swgGet(response, "subtask"))
		currentSubtaskID := subtaskID
		if !value_objects.PyTruthy(subtaskID) {
			currentSubtaskID = swgGetDef(subtask, "id", "subtask-id")
		}
		if subtask != nil && swgStr(swgGet(subtask, "status")) == "in_progress" {
			actions = append(actions, swgMap(
				"priority", "medium",
				"action", "Continue tracking progress",
				"description", "Update progress_percentage as you work",
				"example", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(currentSubtaskID)+"', progress_percentage=75, progress_notes='Almost done, finalizing tests')",
			))
		}
	}
	return actions
}

// GenerateHints ports generate_hints.
func (g *SubtaskWorkflowGuidance) GenerateHints(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []string {
	hints := []string{}
	state := swgOM(swgGet(swgOM(swgGet(response, "workflow_guidance")), "current_state"))

	switch swgStr(swgGet(state, "phase")) {
	case "not_started":
		hints = append(hints, "🚀 Ready to start? Update status to 'in_progress' first")
	case "in_progress":
		hints = append(hints,
			"📊 Remember to update progress regularly",
			"🚧 Report any blockers as soon as you encounter them",
		)
	case "all_complete":
		hints = append(hints, "🎉 All subtasks complete! Parent task may be ready for completion")
	}

	switch {
	case action == "create":
		hints = append(hints, "💡 Keep subtasks focused and measurable")
	case action == "update" && swgStr(swgGet(state, "status")) == "in_progress":
		hints = append(hints, "💭 Consider adding insights_found to share learnings")
	case action == "complete":
		hints = append(hints, "📝 Provide a clear completion_summary for context")
	case action == "list":
		if swgNum(swgGetDef(state, "todo", 0)) > 0 {
			hints = append(hints, "📋 "+value_objects.PyStr(swgGetDef(state, "todo", 0))+" subtask(s) waiting to be started")
		}
		if swgNum(swgGetDef(state, "in_progress", 0)) > 0 {
			hints = append(hints, "🔄 "+value_objects.PyStr(swgGetDef(state, "in_progress", 0))+" subtask(s) currently in progress")
		}
	}
	return hints
}

// CheckWarnings ports check_warnings.
func (g *SubtaskWorkflowGuidance) CheckWarnings(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []string {
	warnings := []string{}
	state := swgOM(swgGet(swgOM(swgGet(response, "workflow_guidance")), "current_state"))

	if action == "create" && !value_objects.PyTruthy(swgGet(state, "has_assignees")) {
		warnings = append(warnings, "⚠️ No assignee specified - who will work on this?")
	}

	if action == "complete" {
		subtask := swgOMDef(swgGet(response, "subtask"))
		if swgStr(swgGet(subtask, "status")) != "done" {
			warnings = append(warnings, "⚠️ Subtask hasn't been started - cannot complete directly")
		}
	}

	if action == "list" && swgNum(swgGetDef(state, "in_progress", 0)) > 3 {
		warnings = append(warnings, "⚠️ "+value_objects.PyStr(swgGet(state, "in_progress"))+" subtasks in progress - consider completing some first")
	}
	return warnings
}

// GetExamples ports get_examples.
func (g *SubtaskWorkflowGuidance) GetExamples(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	examples := entities.NewOrderedMap[any]()
	taskID := swgGetDef(context, "task_id", "task-id")
	subtaskID := swgGetDef(context, "subtask_id", "subtask-id")

	switch action {
	case "create":
		examples.Set("start_work", swgMap(
			"description", "Start working on the subtask",
			"command", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(subtaskID)+"', status='in_progress', progress_notes='Starting implementation')",
		))
		examples.Set("track_progress", swgMap(
			"description", "Update progress as you work",
			"command", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(subtaskID)+"', progress_percentage=25, progress_notes='Completed initial setup')",
		))
	case "update":
		examples.Set("update_progress", swgMap(
			"description", "Update progress percentage",
			"command", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(subtaskID)+"', progress_percentage=50, progress_notes='Halfway done, completed core logic')",
		))
		examples.Set("update_blocked", swgMap(
			"description", "Report a blocker",
			"command", "manage_subtask(action='update', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(subtaskID)+"', blockers='Waiting for API documentation', progress_notes='Cannot proceed without API specs')",
		))
	case "complete":
		examples.Set("complete_basic", swgMap(
			"description", "Complete with summary",
			"command", "manage_subtask(action='complete', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(subtaskID)+"', completion_summary='Successfully implemented authentication with JWT tokens')",
		))
		examples.Set("complete_detailed", swgMap(
			"description", "Complete with full details",
			"command", "manage_subtask(action='complete', task_id='"+value_objects.PyStr(taskID)+"', subtask_id='"+value_objects.PyStr(subtaskID)+"', completion_summary='API endpoints fully tested and documented', impact_on_parent='Core functionality now ready for integration', insights_found=['JWT refresh tokens improve UX', 'Rate limiting prevents abuse'])",
		))
	case "list":
		examples.Set("list_subtasks", swgMap(
			"description", "List all subtasks",
			"command", "manage_subtask(action='list', task_id='"+value_objects.PyStr(taskID)+"')",
		))
	}
	return examples
}

// GetParameterGuidance ports get_parameter_guidance.
func (g *SubtaskWorkflowGuidance) GetParameterGuidance(action string) *entities.OrderedMap[any] {
	guidance := entities.NewOrderedMap[any]()

	nextActionParams := map[string][]string{
		"create":   {"task_id", "subtask_id", "status", "progress_percentage", "progress_notes", "blockers"},
		"update":   {"task_id", "subtask_id", "progress_percentage", "progress_notes", "blockers", "insights_found", "completion_summary"},
		"complete": {"task_id"},
		"delete":   {"task_id"},
		"get":      {"task_id", "subtask_id", "progress_percentage", "progress_notes"},
		"list":     {"task_id", "subtask_id", "status", "progress_percentage", "progress_notes"},
	}

	params := nextActionParams[action]
	applicable := make([]any, len(params))
	for i, p := range params {
		applicable[i] = p
	}
	guidance.Set("applicable_parameters", applicable)

	tips := entities.NewOrderedMap[any]()
	for _, p := range params {
		if tip := swgParamTip(p); tip != nil {
			tips.Set(p, tip)
		}
	}
	guidance.Set("parameter_tips", tips)
	return guidance
}

func swgParamTip(param string) *entities.OrderedMap[any] {
	switch param {
	case "task_id":
		return swgMap(
			"requirement", "REQUIRED for all operations",
			"tip", "Parent task identifier from creation",
		)
	case "subtask_id":
		return swgMap(
			"requirement", "REQUIRED for update/complete/get/delete",
			"tip", "Use the subtask_id returned from creation",
		)
	case "status":
		return swgMap(
			"requirement", "Optional - auto-updated by progress_percentage",
			"tip", "Set to 'in_progress' when starting work",
			"examples", []any{"todo", "in_progress", "done"},
		)
	case "progress_percentage":
		return swgMap(
			"requirement", "RECOMMENDED for tracking progress",
			"tip", "Use 0-100 range; automatically updates status (0=todo, 1-99=in_progress, 100=done)",
			"when_to_use", "Update regularly as you work",
			"examples", []any{10, 25, 50, 75, 90, 100},
		)
	case "progress_notes":
		return swgMap(
			"requirement", "HIGHLY RECOMMENDED",
			"when_to_use", "Every time you update progress or hit blockers",
			"examples", []any{
				"Starting implementation",
				"Completed database schema",
				"Fixed authentication bug",
				"Researching third-party integrations",
			},
			"best_practice", "Be specific about current work and what's done",
		)
	case "blockers":
		return swgMap(
			"requirement", "Use when blocked",
			"when_to_use", "Immediately when something prevents progress",
			"examples", []any{
				"Missing API documentation",
				"Waiting for design approval",
				"Dependencies not available",
			},
			"tip", "Document blockers as soon as encountered",
		)
	case "insights_found":
		return swgMap(
			"requirement", "Optional but valuable",
			"when_to_use", "When discovering something that could help others",
			"examples", []any{
				"Performance bottleneck found in current approach",
				"Better library available for this use case",
				"Security vulnerability identified",
			},
			"best_practice", "Share learnings that impact other subtasks or parent",
		)
	case "completion_summary":
		return swgMap(
			"requirement", "HIGHLY RECOMMENDED for complete action",
			"tip", "Summarize what was accomplished when completing",
			"when_to_use", "When progress_percentage reaches 100",
			"examples", []any{
				"Implemented secure user authentication with JWT",
				"Completed all CRUD operations for user management",
			},
		)
	}
	return nil
}

func (g *SubtaskWorkflowGuidance) generateSubtasksOverview(subtasks []any) *entities.OrderedMap[any] {
	total := len(subtasks)

	byStatus := entities.NewOrderedMap[any]()
	byStatus.Set("todo", []any{})
	byStatus.Set("in_progress", []any{})
	byStatus.Set("done", []any{})

	for _, s := range subtasks {
		om := swgOM(s)
		status := swgStr(swgGetDef(om, "status", "todo"))
		if status == "todo" || status == "in_progress" || status == "done" {
			cur, _ := byStatus.Get(status)
			arr := cur.([]any)
			item := entities.NewOrderedMap[any]()
			item.Set("id", swgGet(om, "id"))
			item.Set("title", swgGet(om, "title"))
			item.Set("assignees", swgGetDef(om, "assignees", []any{}))
			byStatus.Set(status, append(arr, item))
		}
	}

	doneArr, _ := byStatus.Get("done")
	doneCount := len(doneArr.([]any))
	completionRate := "0/0"
	if total > 0 {
		completionRate = strconv.Itoa(doneCount) + "/" + strconv.Itoa(total)
	}

	recommendations := []any{}
	if doneCount == total && total > 0 {
		recommendations = append(recommendations, "All subtasks complete - parent task ready for completion")
	} else {
		inProgressArr, _ := byStatus.Get("in_progress")
		todoArr, _ := byStatus.Get("todo")
		if len(inProgressArr.([]any)) > 3 {
			recommendations = append(recommendations, "Many subtasks in progress - focus on completing some")
		} else if len(todoArr.([]any)) > 0 && len(inProgressArr.([]any)) == 0 {
			recommendations = append(recommendations, "Start work on pending subtasks")
		}
	}

	overview := entities.NewOrderedMap[any]()
	overview.Set("total_subtasks", total)
	overview.Set("by_status", byStatus)
	overview.Set("completion_rate", completionRate)
	overview.Set("recommendations", recommendations)
	return overview
}

// --- helpers ---

func swgMap(kv ...any) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		om.Set(kv[i].(string), kv[i+1])
	}
	return om
}

func swgGet(om *entities.OrderedMap[any], k string) any {
	if om == nil {
		return nil
	}
	v, _ := om.Get(k)
	return v
}

func swgGetDef(om *entities.OrderedMap[any], k string, def any) any {
	if om == nil {
		return def
	}
	if v, ok := om.Get(k); ok {
		return v
	}
	return def
}

func swgHas(om *entities.OrderedMap[any], k string) bool {
	if om == nil {
		return false
	}
	return om.Has(k)
}

func swgOM(v any) *entities.OrderedMap[any] {
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

func swgOMDef(v any) *entities.OrderedMap[any] {
	if om := swgOM(v); om != nil {
		return om
	}
	return entities.NewOrderedMap[any]()
}

func swgList(v any) []any {
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

func swgOrList(v []any) []any {
	if v == nil {
		return []any{}
	}
	return v
}

func swgNum(v any) float64 {
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

func swgStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return value_objects.PyStr(v)
}
