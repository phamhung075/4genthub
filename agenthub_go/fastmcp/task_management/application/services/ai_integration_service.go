package services

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	aiservices "agenthub/fastmcp/ai_task_planning/application/services"
	aientities "agenthub/fastmcp/ai_task_planning/domain/entities"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AITaskFacade is the TaskApplicationFacade surface used by the integration service.
type AITaskFacade interface {
	CreateTask(ctx context.Context, request dtostask.CreateTaskRequest) *entities.OrderedMap[any]
}

// AITaskIntegrationService bridges the AI planning engine and MCP task management.
type AITaskIntegrationService struct {
	TaskFacade        AITaskFacade
	AIPlanningService *aiservices.AITaskPlanningService
}

// NewAITaskIntegrationService builds the service (and its AITaskPlanningService).
func NewAITaskIntegrationService(taskFacade AITaskFacade) *AITaskIntegrationService {
	return &AITaskIntegrationService{TaskFacade: taskFacade, AIPlanningService: aiservices.NewAITaskPlanningService(taskFacade)}
}

type aiAttributeError struct{ msg string }

func (e *aiAttributeError) Error() string { return "AttributeError: " + e.msg }

// aiErrorType is type(e).__name__ for the errors this service produces.
func aiErrorType(err error) string {
	switch err.(type) {
	case *value_objects.ValueError:
		return "ValueError"
	case *aiAttributeError:
		return "AttributeError"
	}
	return "Exception"
}

func aiErrorText(err error) string {
	if e, ok := err.(*aiAttributeError); ok {
		return e.msg
	}
	return err.Error()
}

func omap(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func strList(l []string) []any {
	out := make([]any, len(l))
	for i, s := range l {
		out[i] = s
	}
	return out
}

func orderedGet(v any, key string) (any, bool) {
	o, ok := v.(value_objects.OrderedAny)
	if !ok {
		if m, ok := v.(map[string]any); ok {
			x, ok := m[key]
			return x, ok
		}
		return nil, false
	}
	for _, k := range o.KeysAny() {
		if k == key {
			return o.GetAny(k), true
		}
	}
	return nil, false
}

func truthy(v any) bool {
	b, ok := v.(bool)
	return ok && b
}

// CreateAIEnhancedTaskPlan creates an AI task plan and optionally MCP tasks.
func (s *AITaskIntegrationService) CreateAIEnhancedTaskPlan(ctx context.Context, requirements, title, description, gitBranchID, planningContext string, autoCreateTasks bool, userID *string) *entities.OrderedMap[any] {
	fail := func(err error) *entities.OrderedMap[any] {
		return omap("success", false, "error", "AI task planning failed: "+aiErrorText(err), "error_type", aiErrorType(err))
	}
	items, err := parseAIRequirements(requirements)
	if err != nil {
		return fail(err)
	}
	pctx, err := aientities.ParsePlanningContext(planningContext)
	if err != nil {
		return fail(err)
	}
	req := aientities.NewPlanningRequest(value_objects.NewUUIDv4(), title, description)
	req.Requirements, req.Context, req.GitBranchID, req.UserID = items, pctx, &gitBranchID, userID

	plan, err := s.AIPlanningService.CreateIntelligentPlan(req)
	if err != nil {
		return fail(err)
	}
	created := []any{}
	if autoCreateTasks {
		created = s.createMCPTasksFromPlan(ctx, plan, gitBranchID, userID)
	}
	workload := entities.NewOrderedMap[any]()
	if plan.AgentWorkload != nil {
		for _, k := range plan.AgentWorkload.Keys() {
			v, _ := plan.AgentWorkload.Get(k)
			workload.Set(k, v)
		}
	}
	return omap(
		"success", true,
		"planning_request", omap("id", req.ID, "title", req.Title, "description", req.Description,
			"requirements_count", len(req.Requirements), "context", string(req.Context)),
		"task_plan", omap("id", plan.ID, "title", plan.Title, "total_tasks", len(plan.Tasks),
			"total_estimated_hours", plan.TotalEstimatedHours, "estimated_duration_days", plan.EstimatedDurationDays,
			"confidence_score", plan.ConfidenceScore, "required_agents", strList(plan.RequiredAgents.Items()),
			"agent_workload", workload),
		"created_tasks", created,
		"ai_insights", generateAIInsights(plan),
	)
}

// EnhanceTaskCreation enhances task creation with AI capabilities.
func (s *AITaskIntegrationService) EnhanceTaskCreation(ctx context.Context, request dtostask.CreateTaskRequest, enableAIBreakdown, enableSmartAssignment bool) *entities.OrderedMap[any] {
	result := s.TaskFacade.CreateTask(ctx, request)
	if v, _ := result.Get("success"); !truthy(v) {
		return result
	}
	taskVal, ok := result.Get("task")
	if !ok {
		return omap("success", false, "error", "AI enhancement failed: 'task'") // KeyError
	}
	if _, ok := orderedGet(taskVal, "id"); !ok {
		return omap("success", false, "error", "AI enhancement failed: 'id'")
	}
	enhancements := entities.NewOrderedMap[any]()
	if enableAIBreakdown && request.Description != nil && *request.Description != "" {
		enhancements.Set("breakdown", generateTaskBreakdown())
	}
	if enableSmartAssignment {
		desc := ""
		if request.Description != nil {
			desc = *request.Description
		}
		enhancements.Set("agent_suggestions", suggestOptimalAgents(request.Title+" "+desc))
	}
	result.Set("ai_enhancements", enhancements)
	result.Set("ai_enhanced", true)
	return result
}

// AddAIInsightsToTaskResponse adds AI insights to an existing task response.
func (s *AITaskIntegrationService) AddAIInsightsToTaskResponse(taskData *entities.OrderedMap[any], action string) *entities.OrderedMap[any] {
	if v, _ := taskData.Get("success"); !truthy(v) {
		return taskData
	}
	task, ok := taskData.Get("task")
	if !ok || task == nil {
		return taskData
	}
	title, description := "", ""
	if v, ok := orderedGet(task, "title"); ok {
		title = value_objects.PyStr(v)
	}
	if v, ok := orderedGet(task, "description"); ok {
		description = value_objects.PyStr(v)
	}
	taskData.Set("ai_insights", omap(
		"complexity_analysis", analyzeComplexity(title, description),
		"suggested_next_actions", suggestNextActions(action),
		"potential_risks", identifyRisks(title, description),
		"optimization_suggestions", suggestOptimizations(title, description),
	))
	taskData.Set("enhanced_by_ai", true)
	return taskData
}

func jsonTypeAttrError(v any) error {
	name := "NoneType"
	switch v.(type) {
	case bool:
		name = "bool"
	case json.Number:
		if strings.ContainsAny(string(v.(json.Number)), ".eE") {
			name = "float"
		} else {
			name = "int"
		}
	case []any:
		name = "list"
	case nil:
	}
	return &aiAttributeError{"'" + name + "' object has no attribute 'get'"}
}

// orderedTopLevel decodes a JSON object's keys in order (Python dict iteration).
func orderedKeys(raw string) ([]any, error) {
	dec := json.NewDecoder(strings.NewReader(raw))
	if _, err := dec.Token(); err != nil {
		return nil, err
	}
	var keys []any
	for dec.More() {
		t, err := dec.Token()
		if err != nil {
			return nil, err
		}
		keys = append(keys, t.(string))
		var skip json.RawMessage
		if err := dec.Decode(&skip); err != nil {
			return nil, err
		}
	}
	if _, err := dec.Token(); err != nil {
		return nil, err
	}
	return keys, nil
}

func jsonStr(v any, def string) string {
	if v == nil {
		return def
	}
	if s, ok := v.(string); ok {
		return s
	}
	return fmt.Sprint(v)
}

func jsonStrList(v any) []string {
	l, ok := v.([]any)
	if !ok {
		return []string{}
	}
	out := make([]string, len(l))
	for i, x := range l {
		out[i] = jsonStr(x, "")
	}
	return out
}

// parseAIRequirements parses a JSON or comma-separated requirements string.
func parseAIRequirements(requirements string) ([]*aientities.RequirementItem, error) {
	var data []any
	if strings.HasPrefix(requirements, "[") || strings.HasPrefix(requirements, "{") {
		dec := json.NewDecoder(bytes.NewReader([]byte(requirements)))
		dec.UseNumber()
		var parsed any
		if err := dec.Decode(&parsed); err != nil || dec.More() {
			return []*aientities.RequirementItem{singleRequirement(requirements)}, nil
		}
		switch p := parsed.(type) {
		case []any:
			data = p
		case map[string]any:
			keys, err := orderedKeys(requirements)
			if err != nil {
				return []*aientities.RequirementItem{singleRequirement(requirements)}, nil
			}
			data = keys // iterating a dict yields its keys
		}
	} else {
		for _, r := range strings.Split(requirements, ",") {
			if r = strings.TrimSpace(r); r != "" {
				data = append(data, map[string]any{"description": r, "priority": "medium"})
			}
		}
	}
	var items []*aientities.RequirementItem
	for i, d := range data {
		if str, ok := d.(string); ok {
			d = map[string]any{"description": str, "priority": "medium"}
		}
		m, ok := d.(map[string]any)
		if !ok {
			return nil, jsonTypeAttrError(d)
		}
		item := aientities.NewRequirementItem(fmt.Sprintf("req_%d", i+1), jsonStr(m["description"], ""))
		item.Priority = jsonStr(m["priority"], "medium")
		item.AcceptanceCriteria = jsonStrList(m["acceptance_criteria"])
		item.Constraints = jsonStrList(m["constraints"])
		item.RelatedFiles = jsonStrList(m["related_files"])
		items = append(items, item)
	}
	return items, nil
}

func singleRequirement(description string) *aientities.RequirementItem {
	return aientities.NewRequirementItem("req_1", description)
}

// createMCPTasksFromPlan creates MCP tasks from the root planned tasks. As in
// Python, a task with an agent_assignment fails (AgentAssignment has no
// `agent_id`, AttributeError caught per task) before anything is created.
func (s *AITaskIntegrationService) createMCPTasksFromPlan(ctx context.Context, plan *aientities.TaskPlan, gitBranchID string, userID *string) []any {
	created := []any{}
	for _, pt := range plan.Tasks {
		if pt.ParentTaskID != nil && *pt.ParentTaskID != "" {
			continue
		}
		if pt.AgentAssignment != nil {
			continue
		}
		desc := pt.Description
		if desc == "" {
			desc = "AI-generated task"
		}
		priority := pt.Priority
		if priority == "" {
			priority = "medium"
		}
		status := "todo"
		effort := ""
		if pt.EstimatedHours != 0 {
			effort = value_objects.PyRepr(pt.EstimatedHours) + " hours"
		}
		request, err := dtostask.NewCreateTaskRequest(dtostask.CreateTaskRequest{
			Title: pt.Title, Description: &desc, Status: &status, Priority: &priority, GitBranchID: gitBranchID,
			Assignees: []string{}, EstimatedEffort: effort, UserID: userID,
			Details: fmt.Sprintf("AI-generated task from plan %s. Estimated complexity: %s", plan.ID, pt.EstimatedComplexity),
		})
		if err != nil {
			continue
		}
		result := s.TaskFacade.CreateTask(ctx, *request)
		if v, _ := result.Get("success"); !truthy(v) {
			continue
		}
		task, _ := result.Get("task")
		id, ok := orderedGet(task, "id")
		if !ok {
			continue
		}
		idStr := value_objects.PyStr(id)
		pt.MCPTaskID = &idStr
		created = append(created, omap("planned_task_id", pt.ID, "mcp_task_id", idStr, "title", pt.Title,
			"agent_assignment", nil, "estimated_hours", pt.EstimatedHours))
	}
	return created
}

func generateTaskBreakdown() *entities.OrderedMap[any] {
	return omap("analysis", "AI breakdown not yet implemented", "suggested_subtasks", []any{},
		"estimated_effort", "TBD", "recommended_approach", "Standard implementation")
}

var (
	testAgentRe     = regexp.MustCompile(`\b(test|testing|qa|suite|spec|unit|integration)\b`)
	uiAgentRe       = regexp.MustCompile(`\b(ui|frontend|component|interface|dashboard|view|screen)\b`)
	securityAgentRe = regexp.MustCompile(`\b(security|auth|authentication|login|permission|access)\b`)
	debugAgentRe    = regexp.MustCompile(`\b(debug|fix|bug|error|issue|troubleshoot)\b`)
)

func suggestOptimalAgents(taskContent string) *entities.OrderedMap[any] {
	c := strings.ToLower(taskContent)
	agent := "coding-agent"
	switch {
	case testAgentRe.MatchString(c):
		agent = "test-orchestrator-agent"
	case uiAgentRe.MatchString(c):
		agent = "shadcn-ui-expert-agent"
	case securityAgentRe.MatchString(c):
		agent = "security-auditor-agent"
	case debugAgentRe.MatchString(c):
		agent = "debugger-agent"
	}
	return omap("suggested_agents", []any{agent}, "reasoning", "Based on keyword analysis", "confidence", 0.7)
}

func analyzeComplexity(title, description string) *entities.OrderedMap[any] {
	content := strings.ToLower(title + " " + description)
	score := 0
	for _, k := range []string{"integration", "migration", "refactor", "architecture", "system", "complex"} {
		if strings.Contains(content, k) {
			score += 2
		}
	}
	for _, k := range []string{"implement", "create", "add", "update", "modify"} {
		if strings.Contains(content, k) {
			score++
		}
	}
	level := "low"
	if score >= 4 {
		level = "high"
	} else if score >= 2 {
		level = "medium"
	}
	return omap("level", level, "score", score, "factors", "Keyword-based analysis")
}

func suggestNextActions(action string) []any {
	m := map[string][]string{
		"create":   {"Define detailed acceptance criteria", "Break down into smaller tasks if complex", "Assign to appropriate agent", "Set realistic timeline"},
		"get":      {"Review task progress", "Check for blockers", "Update status if needed", "Coordinate with team members"},
		"update":   {"Validate changes", "Notify stakeholders", "Update dependent tasks", "Track progress metrics"},
		"complete": {"Conduct final review", "Update documentation", "Notify dependent tasks", "Archive artifacts"},
	}
	if l, ok := m[action]; ok {
		return strList(l)
	}
	return []any{"Continue with standard workflow"}
}

func containsAny(content string, keywords ...string) bool {
	for _, k := range keywords {
		if strings.Contains(content, k) {
			return true
		}
	}
	return false
}

func identifyRisks(title, description string) []any {
	c := strings.ToLower(title + " " + description)
	var risks []string
	if containsAny(c, "integration", "migration", "refactor") {
		risks = append(risks, "High complexity may lead to scope creep")
	}
	if containsAny(c, "database", "schema", "data") {
		risks = append(risks, "Data integrity concerns")
	}
	if containsAny(c, "security", "auth", "authentication") {
		risks = append(risks, "Security implications require careful review")
	}
	if containsAny(c, "api", "external", "third-party") {
		risks = append(risks, "External dependencies may cause delays")
	}
	if len(risks) == 0 {
		return []any{"No significant risks identified"}
	}
	return strList(risks)
}

func suggestOptimizations(title, description string) []any {
	c := strings.ToLower(title + " " + description)
	var o []string
	if strings.Contains(c, "performance") {
		o = append(o, "Consider caching strategies")
	}
	if containsAny(c, "ui", "frontend", "component") {
		o = append(o, "Implement component reusability")
	}
	if containsAny(c, "test", "testing") {
		o = append(o, "Automate test execution")
	}
	if containsAny(c, "database", "query") {
		o = append(o, "Optimize database queries")
	}
	if len(o) == 0 {
		return []any{"Standard implementation approach"}
	}
	return strList(o)
}

func generateAIInsights(plan *aientities.TaskPlan) *entities.OrderedMap[any] {
	completeness := "Medium"
	if len(plan.Tasks) > 3 {
		completeness = "High"
	}
	return omap(
		"plan_quality", omap("confidence_score", plan.ConfidenceScore, "risk_level", plan.RiskLevel, "completeness", completeness),
		"execution_recommendations", []any{
			fmt.Sprintf("Plan involves %d specialized agents", plan.RequiredAgents.Len()),
			"Estimated duration: " + value_objects.PyRepr(plan.EstimatedDurationDays) + " days",
			"Total effort: " + value_objects.PyRepr(plan.TotalEstimatedHours) + " hours",
		},
		"success_factors", []any{
			"AI-generated task breakdown ensures comprehensive coverage",
			"Intelligent agent assignments optimize skill utilization",
			"Dependency analysis prevents bottlenecks",
		},
	)
}
