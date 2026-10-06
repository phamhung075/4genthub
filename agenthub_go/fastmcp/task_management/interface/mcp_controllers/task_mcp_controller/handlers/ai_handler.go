package handlers

// AI Handler for Task MCP Controller (Python ai_handler.py).

import (
	"context"
	"sort"
	"strings"

	aentities "agenthub/fastmcp/ai_task_planning/domain/entities"
	domainservices "agenthub/fastmcp/ai_task_planning/domain/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AITaskIntegrationService is the AITaskIntegrationService surface used by the
// handler. It embeds the use-case interface (so the same value can build
// AITaskCreationUseCase) and adds the requirement-analyzer methods reached
// through ai_service.ai_planning_service.requirement_analyzer. The concrete
// task_management/application/services/ai_integration_service.py has no Go port
// yet; the interface is declared here and reported as a dependency.
type AITaskIntegrationService interface {
	use_cases.AITaskIntegrationService
	ParseRequirements(requirements string) []*aentities.RequirementItem
	AnalyzeRequirementsBatch(requirements []*aentities.RequirementItem) []*domainservices.AnalyzedRequirement
	GeneratePlanningInsights(analyzed []*domainservices.AnalyzedRequirement) *entities.OrderedMap[any]
}

// NewAITaskIntegrationService is the constructor hook for the service.
var NewAITaskIntegrationService = func(facade TaskFacade) AITaskIntegrationService { return nil }

// AIHandler ports AIHandler.
type AIHandler struct {
	responseFormatter ResponseFormatter
}

// NewAIHandler ports __init__(response_formatter).
func NewAIHandler(responseFormatter ResponseFormatter) *AIHandler {
	return &AIHandler{responseFormatter: responseFormatter}
}

// AIPlan ports ai_plan(facade, **kwargs). Python calls create_error_response
// with an unsupported `details=` keyword, and create_success_response with an
// unsupported `message=` keyword; both raise TypeError and are caught by the
// except block. That quirk is preserved here.
func (h *AIHandler) AIPlan(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	requiredParams := []string{"requirements", "title", "git_branch_id"}
	for _, param := range requiredParams {
		if !pyTruthyKw(kwargs, param) {
			return h.typeErrorResponse("ai_plan", "AI planning failed",
				"create_error_response() got an unexpected keyword argument 'details'")
		}
	}

	aiService := NewAITaskIntegrationService(facade)
	result, err := aiService.CreateAIEnhancedTaskPlan(ctx,
		kwStringValue(kwargs, "requirements"),
		kwStringValue(kwargs, "title"),
		kwStringDefault(kwargs, "description", "AI-generated task plan"),
		kwStringValue(kwargs, "git_branch_id"),
		kwStringDefault(kwargs, "context", "new_feature"),
		kwBoolDefault(kwargs, "auto_create_tasks", true),
		kwString(kwargs, "user_id"),
	)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("ai_plan", "AI planning failed: "+err.Error(),
			ErrorCodeOperationFailed, nil)
	}
	if result != nil && pyResultSuccess(result) {
		return h.typeErrorResponse("ai_plan", "AI planning failed",
			"create_success_response() got an unexpected keyword argument 'message'")
	}
	return h.resultError("ai_plan", result, "AI planning failed")
}

// AICreate ports ai_create(facade, **kwargs).
func (h *AIHandler) AICreate(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	if !pyTruthyKw(kwargs, "title") {
		return h.responseFormatter.CreateErrorResponse("ai_create",
			"Missing required parameter: title", ErrorCodeValidationError, nil)
	}
	if !pyTruthyKw(kwargs, "git_branch_id") {
		return h.responseFormatter.CreateErrorResponse("ai_create",
			"Missing required parameter: git_branch_id", ErrorCodeValidationError, nil)
	}

	aiRequest := &use_cases.AITaskCreationRequest{
		Title:                 kwStringValue(kwargs, "title"),
		Description:           kwString(kwargs, "description"),
		GitBranchID:           kwStringValue(kwargs, "git_branch_id"),
		Priority:              kwString(kwargs, "priority"),
		Assignees:             kwStringsOrEmpty(kwargs, "assignees"),
		EstimatedEffort:       kwString(kwargs, "estimated_effort"),
		Labels:                kwStringsOrEmpty(kwargs, "labels"),
		Dependencies:          kwStringsOrEmpty(kwargs, "dependencies"),
		UserID:                kwString(kwargs, "user_id"),
		EnableAIBreakdown:     kwBoolDefault(kwargs, "enable_ai_breakdown", false),
		EnableSmartAssignment: kwBoolDefault(kwargs, "enable_smart_assignment", false),
		EnableAutoSubtasks:    kwBoolDefault(kwargs, "enable_auto_subtasks", false),
		PlanningContext:       kwStringDefault(kwargs, "planning_context", "new_feature"),
		AIRequirements:        kwString(kwargs, "ai_requirements"),
	}
	if aiRequest.Priority == nil {
		medium := "medium"
		aiRequest.Priority = &medium
	}

	aiUseCase := use_cases.NewAITaskCreationUseCase(facade.TaskRepository(), facade,
		NewAITaskIntegrationService(facade))
	result := aiUseCase.Execute(ctx, aiRequest)

	if result != nil && pyResultSuccess(result) {
		return h.typeErrorResponse("ai_create", "AI task creation failed",
			"create_success_response() got an unexpected keyword argument 'message'")
	}
	return h.resultError("ai_create", result, "AI task creation failed")
}

// AIEnhance ports ai_enhance(facade, **kwargs).
func (h *AIHandler) AIEnhance(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	taskID := kwString(kwargs, "task_id")
	if taskID == nil || *taskID == "" {
		return h.responseFormatter.CreateErrorResponse("ai_enhance",
			"Missing required parameter: task_id", ErrorCodeValidationError, nil)
	}

	aiUseCase := use_cases.NewAITaskCreationUseCase(facade.TaskRepository(), facade,
		NewAITaskIntegrationService(facade))
	enhancementOptions := map[string]any{
		"analyze_complexity":    kwBoolDefault(kwargs, "analyze_complexity", true),
		"suggest_optimizations": kwBoolDefault(kwargs, "suggest_optimizations", true),
		"identify_risks":        kwBoolDefault(kwargs, "identify_risks", true),
	}
	result := aiUseCase.EnhanceExistingTask(ctx, *taskID, enhancementOptions)

	if result != nil && pyResultSuccess(result) {
		return h.typeErrorResponse("ai_enhance", "AI enhancement failed",
			"create_success_response() got an unexpected keyword argument 'message'")
	}
	return h.resultError("ai_enhance", result, "AI enhancement failed")
}

// AIAnalyze ports ai_analyze(facade, **kwargs).
func (h *AIHandler) AIAnalyze(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	requirements := kwString(kwargs, "requirements")
	if requirements == nil || *requirements == "" {
		return h.responseFormatter.CreateErrorResponse("ai_analyze",
			"Missing required parameter: requirements", ErrorCodeValidationError, nil)
	}

	aiService := NewAITaskIntegrationService(facade)
	requirementItems := aiService.ParseRequirements(*requirements)
	analyzedRequirements := aiService.AnalyzeRequirementsBatch(requirementItems)
	insights := aiService.GeneratePlanningInsights(analyzedRequirements)

	detailed := make([]any, 0, len(analyzedRequirements))
	for _, analysis := range analyzedRequirements {
		item := entities.NewOrderedMap[any]()
		requirementID := ""
		requirementDescription := ""
		if analysis.OriginalRequirement != nil {
			requirementID = analysis.OriginalRequirement.ID
			requirementDescription = analysis.OriginalRequirement.Description
		}
		item.Set("requirement_id", requirementID)
		item.Set("description", requirementDescription)
		patterns := make([]any, 0, len(analysis.DetectedPatterns))
		for _, p := range analysis.DetectedPatterns {
			patterns = append(patterns, string(p))
		}
		item.Set("detected_patterns", patterns)
		item.Set("suggested_agents", analysis.SuggestedAgents)
		item.Set("estimated_hours", analysis.EstimatedEffortHours)
		item.Set("risk_factors", analysis.RiskFactors)
		item.Set("technical_considerations", analysis.TechnicalConsiderations)
		detailed = append(detailed, item)
	}

	analysisResult := entities.NewOrderedMap[any]()
	analysisResult.Set("total_requirements", len(analyzedRequirements))
	analysisResult.Set("analysis_summary", insights)
	analysisResult.Set("detailed_analysis", detailed)

	// Python passes analysis_result to create_success_response, which raises
	// TypeError on the unsupported `message=` keyword before returning.
	_ = analysisResult

	return h.typeErrorResponse("ai_analyze", "Requirements analysis failed",
		"create_success_response() got an unexpected keyword argument 'message'")
}

// AISuggestAgents ports ai_suggest_agents(facade, **kwargs).
func (h *AIHandler) AISuggestAgents(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	requirements := kwString(kwargs, "requirements")
	if requirements == nil || *requirements == "" {
		return h.responseFormatter.CreateErrorResponse("ai_suggest_agents",
			"Missing required parameter: requirements", ErrorCodeValidationError, nil)
	}

	aiService := NewAITaskIntegrationService(facade)
	requirementItems := aiService.ParseRequirements(*requirements)
	analyzedRequirements := aiService.AnalyzeRequirementsBatch(requirementItems)
	insights := aiService.GeneratePlanningInsights(analyzedRequirements)

	agentRecommendations := orderedMapValue(insights, "agent_recommendations")

	availableAgents := kwString(kwargs, "available_agents")
	if availableAgents != nil && *availableAgents != "" {
		availableList := []string{}
		for _, agent := range strings.Split(*availableAgents, ",") {
			availableList = append(availableList, value_objects.PyStrip(agent))
		}
		filtered := entities.NewOrderedMap[any]()
		for _, agent := range agentRecommendations.Keys() {
			if containsString(availableList, agent) {
				v, _ := agentRecommendations.Get(agent)
				filtered.Set(agent, v)
			}
		}
		agentRecommendations = filtered
	}

	primaryAgents := topAgentKeys(agentRecommendations, 3)

	suggestionResult := entities.NewOrderedMap[any]()
	suggestionResult.Set("recommended_agents", agentRecommendations)
	suggestionResult.Set("primary_agents", primaryAgents)
	suggestionResult.Set("team_size_recommendation", agentRecommendations.Len())
	suggestionResult.Set("specialization_needs",
		h.identifySpecializationNeeds(orderedMapValue(insights, "pattern_distribution")))

	// Python passes suggestion_result to create_success_response, which raises
	// TypeError on the unsupported `message=` keyword before returning.
	_ = suggestionResult

	return h.typeErrorResponse("ai_suggest_agents", "Agent suggestion failed",
		"create_success_response() got an unexpected keyword argument 'message'")
}

// identifySpecializationNeeds ports _identify_specialization_needs.
func (h *AIHandler) identifySpecializationNeeds(patternDistribution *entities.OrderedMap[any]) []string {
	specializationMap := map[string]string{
		"user_authentication":     "Security expertise",
		"api_integration":         "API and integration knowledge",
		"ui_component":            "Frontend and UI/UX skills",
		"database_schema":         "Database design expertise",
		"performance_requirement": "Performance optimization skills",
		"deployment":              "DevOps and deployment knowledge",
		"testing_requirement":     "Testing and QA expertise",
	}

	specializations := []string{}
	for _, pattern := range patternDistribution.Keys() {
		count, _ := patternDistribution.Get(pattern)
		if pyCountTruthy(count) {
			if spec, ok := specializationMap[pattern]; ok {
				specializations = append(specializations, spec)
			}
		}
	}
	return specializations
}

// typeErrorResponse mirrors the `except Exception` branch triggered by the
// unsupported kwargs in the Python success/validation calls.
func (h *AIHandler) typeErrorResponse(operation, prefix, typeErrorMessage string) *entities.OrderedMap[any] {
	return h.responseFormatter.CreateErrorResponse(operation,
		prefix+": StandardResponseFormatter."+typeErrorMessage, ErrorCodeOperationFailed, nil)
}

func (h *AIHandler) resultError(operation string, result *entities.OrderedMap[any],
	defaultMessage string) *entities.OrderedMap[any] {
	message := defaultMessage
	if result != nil {
		if v, ok := result.Get("error"); ok && v != nil {
			if s, isStr := v.(string); isStr {
				message = s
			}
		}
	}
	return h.responseFormatter.CreateErrorResponse(operation, message, ErrorCodeOperationFailed, nil)
}

func pyResultSuccess(result *entities.OrderedMap[any]) bool {
	v, _ := result.Get("success")
	return value_objects.PyTruthy(v)
}

func pyTruthyKw(m map[string]any, key string) bool {
	v, ok := m[key]
	if !ok {
		return false
	}
	return value_objects.PyTruthy(v)
}

func kwStringDefault(m map[string]any, key, def string) string {
	if v := kwString(m, key); v != nil {
		return *v
	}
	return def
}

func kwBoolDefault(m map[string]any, key string, def bool) bool {
	v, ok := m[key]
	if !ok || v == nil {
		return def
	}
	if b, isBool := v.(bool); isBool {
		return b
	}
	return value_objects.PyTruthy(v)
}

func kwStringsOrEmpty(m map[string]any, key string) []string {
	if v := kwStrings(m, key); v != nil {
		return v
	}
	return []string{}
}

// orderedMapValue mirrors dict.get(key, {}) for the insights maps.
func orderedMapValue(source *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	if source != nil {
		if v, ok := source.Get(key); ok {
			if m, isMap := v.(*entities.OrderedMap[any]); isMap {
				return m
			}
		}
	}
	return entities.NewOrderedMap[any]()
}

func containsString(items []string, target string) bool {
	for _, item := range items {
		if item == target {
			return true
		}
	}
	return false
}

// topAgentKeys mirrors list(dict(sorted(items, key=count, reverse=True)[:3]).keys()).
func topAgentKeys(recommendations *entities.OrderedMap[any], limit int) []string {
	type entry struct {
		key   string
		count int
	}
	entries := make([]entry, 0, recommendations.Len())
	for _, key := range recommendations.Keys() {
		v, _ := recommendations.Get(key)
		entries = append(entries, entry{key: key, count: pyCountInt(v)})
	}
	sort.SliceStable(entries, func(i, j int) bool { return entries[i].count > entries[j].count })
	if len(entries) > limit {
		entries = entries[:limit]
	}
	out := make([]string, 0, len(entries))
	for _, e := range entries {
		out = append(out, e.key)
	}
	return out
}

func pyCountInt(v any) int {
	switch t := v.(type) {
	case int:
		return t
	case int64:
		return int(t)
	case float64:
		return int(t)
	}
	return 0
}

func pyCountTruthy(v any) bool { return pyCountInt(v) > 0 }
