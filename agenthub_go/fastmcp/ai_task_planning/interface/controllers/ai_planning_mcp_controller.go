// Package controllers ports ai_task_planning/interface/controllers.
package controllers

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"

	appservices "agenthub/fastmcp/ai_task_planning/application/services"
	"agenthub/fastmcp/ai_task_planning/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AITaskPlanningMCPController mirrors ai_planning_mcp_controller.AITaskPlanningMCPController.
type AITaskPlanningMCPController struct {
	planningService *appservices.AITaskPlanningService
}

// NewAITaskPlanningMCPController mirrors AITaskPlanningMCPController.__init__.
func NewAITaskPlanningMCPController() *AITaskPlanningMCPController {
	return &AITaskPlanningMCPController{
		planningService: appservices.NewAITaskPlanningService(nil),
	}
}

// CreateAIPlan creates an AI-generated task plan from requirements.
func (c *AITaskPlanningMCPController) CreateAIPlan(kwargs *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	result, err := c.aiPlanningCreateAIPlan(kwargs)
	if err != nil {
		out := tmentities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "AI planning failed: "+aiPlanningErrorMessage(err))
		out.Set("error_type", aiPlanningExceptionName(err))
		return out
	}
	return result
}

func (c *AITaskPlanningMCPController) aiPlanningCreateAIPlan(kwargs *tmentities.OrderedMap[any]) (*tmentities.OrderedMap[any], error) {
	requiredParams := []string{"title", "description", "requirements", "git_branch_id"}
	for _, param := range requiredParams {
		value, ok := kwargs.Get(param)
		if !ok {
			return aiPlanningMissingParameter(param, requiredParams), nil
		}
		if param != "requirements" && !tmvo.PyTruthy(value) {
			return aiPlanningMissingParameter(param, requiredParams), nil
		}
	}

	requirementsData, _ := kwargs.Get("requirements")
	requirementsList, kind := aiPlanningParseRequirements(requirementsData)
	switch kind {
	case aiPlanningParseJSONError:
		return aiPlanningSimpleError("Invalid JSON format for requirements"), nil
	case aiPlanningParseUnsupported:
		return aiPlanningSimpleError("Requirements must be JSON string, comma-separated string, or list"), nil
	}

	requirementItems, err := aiPlanningRequirementItems(requirementsList, true)
	if err != nil {
		return nil, err
	}

	contextValue := any("new_feature")
	if value, ok := kwargs.Get("context"); ok {
		contextValue = value
	}
	var context entities.PlanningContext
	if contextText, isStr := contextValue.(string); isStr {
		context, err = entities.ParsePlanningContext(contextText)
		if err != nil {
			return nil, err
		}
	} else {
		return nil, &tmvo.ValueError{Msg: tmvo.PyRepr(contextValue) + " is not a valid PlanningContext"}
	}

	var deadline *time.Time
	if value, ok := kwargs.Get("deadline"); ok && tmvo.PyTruthy(value) {
		deadlineText, isStr := value.(string)
		if !isStr {
			return nil, &aiPlanningAttributeError{Msg: aiPlanningAttrError(value, "replace")}
		}
		parsed, parseErr := tmvo.ParseISO(strings.ReplaceAll(deadlineText, "Z", "+00:00"))
		if parseErr != nil {
			return aiPlanningSimpleError("Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"), nil
		}
		deadline = &parsed
	}

	gitBranchID := aiPlanningKwargString(kwargs, "git_branch_id")
	planningRequest := entities.NewPlanningRequest(
		tmvo.NewUUIDv4(),
		aiPlanningKwargString(kwargs, "title"),
		aiPlanningKwargString(kwargs, "description"),
	)
	planningRequest.Requirements = requirementItems
	planningRequest.Context = context
	planningRequest.ProjectID = aiPlanningKwargOptString(kwargs, "project_id")
	planningRequest.GitBranchID = aiPlanningKwargOptString(kwargs, "git_branch_id")
	planningRequest.UserID = aiPlanningKwargOptString(kwargs, "user_id")
	planningRequest.Deadline = deadline
	planningRequest.PreferredApproach = aiPlanningKwargOptString(kwargs, "preferred_approach")
	planningRequest.RiskTolerance = aiPlanningKwargStringDefault(kwargs, "risk_tolerance", "medium")

	taskPlan, err := c.planningService.CreateIntelligentPlan(planningRequest)
	if err != nil {
		return nil, err
	}

	executionResult := c.planningService.ExecutePlanWithMCP(taskPlan, gitBranchID)

	planningRequestDict := tmentities.NewOrderedMap[any]()
	planningRequestDict.Set("id", planningRequest.ID)
	planningRequestDict.Set("title", planningRequest.Title)
	planningRequestDict.Set("description", planningRequest.Description)
	planningRequestDict.Set("requirements_count", len(planningRequest.Requirements))
	planningRequestDict.Set("context", string(planningRequest.Context))
	planningRequestDict.Set("estimated_complexity", string(planningRequest.EstimateOverallComplexity()))

	executionPhases := make([]string, 0, len(taskPlan.ExecutionPhases))
	for _, phase := range taskPlan.ExecutionPhases {
		executionPhases = append(executionPhases, string(phase))
	}
	taskPlanDict := tmentities.NewOrderedMap[any]()
	taskPlanDict.Set("id", taskPlan.ID)
	taskPlanDict.Set("title", taskPlan.Title)
	taskPlanDict.Set("description", taskPlan.Description)
	taskPlanDict.Set("total_tasks", len(taskPlan.Tasks))
	taskPlanDict.Set("total_estimated_hours", taskPlan.TotalEstimatedHours)
	taskPlanDict.Set("estimated_duration_days", taskPlan.EstimatedDurationDays)
	taskPlanDict.Set("confidence_score", taskPlan.ConfidenceScore)
	taskPlanDict.Set("risk_level", taskPlan.RiskLevel)
	taskPlanDict.Set("required_agents", taskPlan.RequiredAgents.Items())
	taskPlanDict.Set("execution_phases", executionPhases)
	taskPlanDict.Set("parallel_execution_groups", taskPlan.ParallelExecutionGroups)
	taskPlanDict.Set("critical_path", taskPlan.CriticalPath)
	taskPlanDict.Set("agent_workload", taskPlan.AgentWorkload)

	out := tmentities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("planning_request", planningRequestDict)
	out.Set("task_plan", taskPlanDict)
	out.Set("execution_result", executionResult)
	out.Set("recommendations", c.aiPlanningGenerateRecommendations(taskPlan))
	out.Set("created_at", tmvo.IsoFormat(taskPlan.CreatedAt))
	return out, nil
}

// GetPlanStatus returns the placeholder plan-status response.
func (c *AITaskPlanningMCPController) GetPlanStatus(kwargs *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", "Plan status tracking not yet implemented")
	out.Set("available_operations", []string{
		"create_ai_plan",
		"analyze_requirements",
		"estimate_effort",
		"suggest_agents",
		"validate_plan",
	})
	return out
}

// AnalyzeRequirements analyzes requirements without creating a full plan.
func (c *AITaskPlanningMCPController) AnalyzeRequirements(kwargs *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	result, err := c.aiPlanningAnalyzeRequirements(kwargs)
	if err != nil {
		out := tmentities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Requirement analysis failed: "+aiPlanningErrorMessage(err))
		out.Set("error_type", aiPlanningExceptionName(err))
		return out
	}
	return result
}

func (c *AITaskPlanningMCPController) aiPlanningAnalyzeRequirements(kwargs *tmentities.OrderedMap[any]) (*tmentities.OrderedMap[any], error) {
	if !kwargs.Has("requirements") {
		return aiPlanningSimpleError("Missing required parameter: requirements"), nil
	}

	requirementsData, _ := kwargs.Get("requirements")
	requirementsList, kind := aiPlanningParseRequirements(requirementsData)
	if kind == aiPlanningParseJSONError {
		requirementsText, _ := requirementsData.(string)
		requirementsList = aiPlanningCommaSeparated(requirementsText)
	} else if kind == aiPlanningParseUnsupported {
		// Python assigns the raw value and iterates it; a dict iterates its keys.
		if dict, isDict := requirementsData.(*tmentities.OrderedMap[any]); isDict {
			keys := dict.Keys()
			requirementsList = make([]any, 0, len(keys))
			for _, key := range keys {
				requirementsList = append(requirementsList, key)
			}
		} else {
			return nil, &tmvo.TypeError{Msg: "'" + aiPlanningGoTypeName(requirementsData) + "' object is not iterable"}
		}
	}

	requirementItems, err := aiPlanningRequirementItems(requirementsList, false)
	if err != nil {
		return nil, err
	}

	analyzedRequirements := c.planningService.RequirementAnalyzer.AnalyzeRequirementsBatch(requirementItems)
	insights := c.planningService.RequirementAnalyzer.GeneratePlanningInsights(analyzedRequirements)

	analysis := tmentities.NewOrderedMap[any]()
	analysis.Set("total_requirements", len(analyzedRequirements))
	analysis.Set("total_estimated_hours", aiPlanningInsight(insights, "total_estimated_hours"))
	analysis.Set("pattern_distribution", aiPlanningInsight(insights, "pattern_distribution"))
	analysis.Set("agent_recommendations", aiPlanningInsight(insights, "agent_recommendations"))
	analysis.Set("complexity_distribution", aiPlanningInsight(insights, "complexity_distribution"))
	analysis.Set("risk_summary", aiPlanningInsight(insights, "risk_summary"))
	analysis.Set("suggested_phases", aiPlanningInsight(insights, "suggested_phases"))

	detailedAnalysis := []any{}
	for _, requirement := range analyzedRequirements {
		detectedPatterns := make([]string, 0, len(requirement.DetectedPatterns))
		for _, pattern := range requirement.DetectedPatterns {
			detectedPatterns = append(detectedPatterns, string(pattern))
		}
		detail := tmentities.NewOrderedMap[any]()
		detail.Set("requirement_id", requirement.OriginalRequirement.ID)
		detail.Set("description", requirement.OriginalRequirement.Description)
		detail.Set("detected_patterns", detectedPatterns)
		detail.Set("suggested_agents", requirement.SuggestedAgents)
		detail.Set("estimated_hours", requirement.EstimatedEffortHours)
		detail.Set("risk_factors", requirement.RiskFactors)
		detail.Set("technical_considerations", requirement.TechnicalConsiderations)
		detail.Set("complexity_indicators", requirement.ComplexityIndicators)
		detailedAnalysis = append(detailedAnalysis, detail)
	}

	out := tmentities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("analysis", analysis)
	out.Set("detailed_analysis", detailedAnalysis)
	return out, nil
}

// EstimateEffort estimates effort for a set of requirements.
func (c *AITaskPlanningMCPController) EstimateEffort(kwargs *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	result, err := c.aiPlanningEstimateEffort(kwargs)
	if err != nil {
		out := tmentities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Effort estimation failed: "+aiPlanningErrorMessage(err))
		return out
	}
	return result
}

func (c *AITaskPlanningMCPController) aiPlanningEstimateEffort(kwargs *tmentities.OrderedMap[any]) (*tmentities.OrderedMap[any], error) {
	analysisResult := c.AnalyzeRequirements(kwargs)
	success, _ := analysisResult.Get("success")
	if !tmvo.PyTruthy(success) {
		return analysisResult, nil
	}

	analysisAny, _ := analysisResult.Get("analysis")
	analysis, ok := analysisAny.(*tmentities.OrderedMap[any])
	if !ok {
		return nil, &tmvo.TypeError{Msg: "'NoneType' object is not subscriptable"}
	}

	includeBreakdown := false
	if value, ok := kwargs.Get("include_breakdown"); ok {
		includeBreakdown = tmvo.PyTruthy(value)
	}

	totalHoursAny, _ := analysis.Get("total_estimated_hours")
	totalHours, _ := tmvo.PyFloat(totalHoursAny)
	complexityBreakdown, _ := analysis.Get("complexity_distribution")

	effortEstimate := tmentities.NewOrderedMap[any]()
	effortEstimate.Set("total_hours", totalHoursAny)
	effortEstimate.Set("total_days", tmvo.PyRound(totalHours/8, 1))
	effortEstimate.Set("total_weeks", tmvo.PyRound(totalHours/40, 1))
	effortEstimate.Set("complexity_breakdown", complexityBreakdown)
	effortEstimate.Set("confidence_level", c.aiPlanningCalculateEstimationConfidence(analysis))

	out := tmentities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("effort_estimate", effortEstimate)
	if includeBreakdown {
		detailedBreakdown, _ := analysisResult.Get("detailed_analysis")
		out.Set("detailed_breakdown", detailedBreakdown)
	}
	return out, nil
}

// SuggestAgents suggests optimal agents for requirements.
func (c *AITaskPlanningMCPController) SuggestAgents(kwargs *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	result, err := c.aiPlanningSuggestAgents(kwargs)
	if err != nil {
		out := tmentities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Agent suggestion failed: "+aiPlanningErrorMessage(err))
		return out
	}
	return result
}

func (c *AITaskPlanningMCPController) aiPlanningSuggestAgents(kwargs *tmentities.OrderedMap[any]) (*tmentities.OrderedMap[any], error) {
	analysisResult := c.AnalyzeRequirements(kwargs)
	success, _ := analysisResult.Get("success")
	if !tmvo.PyTruthy(success) {
		return analysisResult, nil
	}

	analysisAny, _ := analysisResult.Get("analysis")
	analysis, ok := analysisAny.(*tmentities.OrderedMap[any])
	if !ok {
		return nil, &tmvo.TypeError{Msg: "'NoneType' object is not subscriptable"}
	}
	agentRecommendationsAny, _ := analysis.Get("agent_recommendations")
	agentRecommendations, ok := agentRecommendationsAny.(*tmentities.OrderedMap[any])
	if !ok {
		return nil, &tmvo.TypeError{Msg: "'NoneType' object is not subscriptable"}
	}

	if value, ok := kwargs.Get("available_agents"); ok && tmvo.PyTruthy(value) {
		availableText, isStr := value.(string)
		if !isStr {
			return nil, &aiPlanningAttributeError{Msg: aiPlanningAttrError(value, "split")}
		}
		availableAgents := []string{}
		for _, agent := range strings.Split(availableText, ",") {
			availableAgents = append(availableAgents, tmvo.PyStrip(agent))
		}
		if len(availableAgents) > 0 {
			filtered := tmentities.NewOrderedMap[any]()
			for _, agent := range agentRecommendations.Keys() {
				count, _ := agentRecommendations.Get(agent)
				if aiPlanningStringIn(availableAgents, agent) {
					filtered.Set(agent, count)
				}
			}
			agentRecommendations = filtered
		}
	}

	totalHoursAny, _ := analysis.Get("total_estimated_hours")
	patternDistribution, _ := analysis.Get("pattern_distribution")

	agentSuggestions := tmentities.NewOrderedMap[any]()
	agentSuggestions.Set("recommended_agents", agentRecommendations)
	agentSuggestions.Set("primary_agents", aiPlanningPrimaryAgents(agentRecommendations))
	agentSuggestions.Set("workload_distribution", aiPlanningEstimateAgentWorkload(agentRecommendations, totalHoursAny))
	agentSuggestions.Set("team_size_recommendation", agentRecommendations.Len())
	agentSuggestions.Set("specialization_needs", aiPlanningIdentifySpecializationNeeds(patternDistribution))

	out := tmentities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent_suggestions", agentSuggestions)
	return out, nil
}

// ValidatePlan returns the placeholder plan-validation response.
func (c *AITaskPlanningMCPController) ValidatePlan(kwargs *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", "Plan validation not yet implemented")
	out.Set("available_validations", []string{
		"dependency_cycles",
		"agent_availability",
		"resource_conflicts",
		"timeline_feasibility",
		"requirement_coverage",
	})
	return out
}

func (c *AITaskPlanningMCPController) aiPlanningGenerateRecommendations(taskPlan *entities.TaskPlan) []string {
	recommendations := []string{}

	if taskPlan.ConfidenceScore < 0.6 {
		recommendations = append(recommendations,
			"Consider adding more detailed requirements to improve plan accuracy")
	}
	if taskPlan.TotalEstimatedHours > 80 {
		recommendations = append(recommendations,
			"Large project - consider breaking into smaller phases")
	}
	if taskPlan.RequiredAgents.Len() > 5 {
		recommendations = append(recommendations,
			"Many agents required - ensure coordination mechanisms are in place")
	}
	if taskPlan.RiskLevel == "high" || taskPlan.RiskLevel == "critical" {
		recommendations = append(recommendations,
			"High risk project - implement additional monitoring and checkpoints")
	}

	overloadedAgents := []string{}
	for _, agent := range taskPlan.AgentWorkload.Keys() {
		hours, _ := taskPlan.AgentWorkload.Get(agent)
		if hours > 40 {
			overloadedAgents = append(overloadedAgents, agent)
		}
	}
	if len(overloadedAgents) > 0 {
		recommendations = append(recommendations,
			"Agents may be overloaded: "+strings.Join(overloadedAgents, ", "))
	}

	return recommendations
}

func (c *AITaskPlanningMCPController) aiPlanningCalculateEstimationConfidence(analysis *tmentities.OrderedMap[any]) string {
	patternDistribution, _ := analysis.Get("pattern_distribution")
	patternCount := aiPlanningDistributionLen(patternDistribution)
	totalHoursAny, _ := analysis.Get("total_estimated_hours")
	totalHours, _ := tmvo.PyFloat(totalHoursAny)

	if patternCount >= 3 && totalHours >= 10 && totalHours <= 100 {
		return "high"
	} else if patternCount >= 2 && totalHours >= 5 && totalHours <= 200 {
		return "medium"
	}
	return "low"
}

func aiPlanningEstimateAgentWorkload(agentRecommendations *tmentities.OrderedMap[any],
	totalHoursAny any) *tmentities.OrderedMap[float64] {

	totalWeight := 0.0
	for _, agent := range agentRecommendations.Keys() {
		value, _ := agentRecommendations.Get(agent)
		count, _ := tmvo.PyFloat(value)
		totalWeight += count
	}

	out := tmentities.NewOrderedMap[float64]()
	if totalWeight == 0 {
		return out
	}

	totalHours, _ := tmvo.PyFloat(totalHoursAny)
	for _, agent := range agentRecommendations.Keys() {
		value, _ := agentRecommendations.Get(agent)
		count, _ := tmvo.PyFloat(value)
		out.Set(agent, tmvo.PyRound((count/totalWeight)*totalHours, 1))
	}
	return out
}

func aiPlanningIdentifySpecializationNeeds(patternDistribution any) []string {
	specializationMap := []struct {
		pattern string
		need    string
	}{
		{"user_authentication", "Security expertise"},
		{"api_integration", "API and integration knowledge"},
		{"ui_component", "Frontend and UI/UX skills"},
		{"database_schema", "Database design expertise"},
		{"performance_requirement", "Performance optimization skills"},
		{"deployment", "DevOps and deployment knowledge"},
		{"testing_requirement", "Testing and QA expertise"},
	}

	specializations := []string{}
	distribution, ok := patternDistribution.(*tmentities.OrderedMap[any])
	if !ok {
		return specializations
	}
	for _, pattern := range distribution.Keys() {
		value, _ := distribution.Get(pattern)
		count, _ := tmvo.PyFloat(value)
		if count <= 0 {
			continue
		}
		for _, entry := range specializationMap {
			if entry.pattern == pattern {
				specializations = append(specializations, entry.need)
				break
			}
		}
	}
	return specializations
}

// --- requirement parsing helpers -----------------------------------------

const (
	aiPlanningParseOK = iota
	aiPlanningParseJSONError
	aiPlanningParseUnsupported
)

func aiPlanningParseRequirements(data any) ([]any, int) {
	if text, isStr := data.(string); isStr {
		if strings.HasPrefix(text, "[") || strings.HasPrefix(text, "{") {
			decoded, err := tmentities.DecodeJSON([]byte(text))
			if err != nil {
				return nil, aiPlanningParseJSONError
			}
			return aiPlanningJSONToList(decoded), aiPlanningParseOK
		}
		return aiPlanningCommaSeparated(text), aiPlanningParseOK
	}
	switch value := data.(type) {
	case []any:
		return value, aiPlanningParseOK
	case []string:
		out := make([]any, 0, len(value))
		for _, item := range value {
			out = append(out, item)
		}
		return out, aiPlanningParseOK
	case []*tmentities.OrderedMap[any]:
		out := make([]any, 0, len(value))
		for _, item := range value {
			out = append(out, item)
		}
		return out, aiPlanningParseOK
	}
	return nil, aiPlanningParseUnsupported
}

// aiPlanningAttributeError mirrors Python's AttributeError so error_type matches.
type aiPlanningAttributeError struct{ Msg string }

func (e *aiPlanningAttributeError) Error() string { return e.Msg }

func aiPlanningJSONToList(value any) []any {
	switch decoded := value.(type) {
	case []any:
		return decoded
	case *tmentities.OrderedMap[any]:
		keys := decoded.Keys()
		out := make([]any, 0, len(keys))
		for _, key := range keys {
			out = append(out, key)
		}
		return out
	}
	return []any{value}
}

func aiPlanningCommaSeparated(text string) []any {
	out := []any{}
	for _, part := range strings.Split(text, ",") {
		stripped := tmvo.PyStrip(part)
		if stripped == "" {
			continue
		}
		entry := tmentities.NewOrderedMap[any]()
		entry.Set("description", stripped)
		entry.Set("priority", "medium")
		out = append(out, entry)
	}
	return out
}

func aiPlanningRequirementItems(list []any, includeRelatedFiles bool) ([]*entities.RequirementItem, error) {
	items := make([]*entities.RequirementItem, 0, len(list))
	for index, raw := range list {
		var data any = raw
		if text, isStr := raw.(string); isStr {
			entry := tmentities.NewOrderedMap[any]()
			entry.Set("description", text)
			entry.Set("priority", "medium")
			data = entry
		}
		if !aiPlanningIsDict(data) {
			return nil, &aiPlanningAttributeError{Msg: aiPlanningAttrError(data, "get")}
		}

		description, _ := aiPlanningDictGet(data, "description")
		priority, _ := aiPlanningDictGet(data, "priority")
		item := entities.NewRequirementItem(
			fmt.Sprintf("req_%d", index+1),
			aiPlanningValueString(description, ""),
		)
		item.Priority = aiPlanningValueString(priority, "medium")

		if value, ok := aiPlanningDictGet(data, "acceptance_criteria"); ok {
			converted, err := aiPlanningValueStringList(value)
			if err != nil {
				return nil, err
			}
			item.AcceptanceCriteria = converted
		}
		if value, ok := aiPlanningDictGet(data, "constraints"); ok {
			converted, err := aiPlanningValueStringList(value)
			if err != nil {
				return nil, err
			}
			item.Constraints = converted
		}
		if includeRelatedFiles {
			if value, ok := aiPlanningDictGet(data, "related_files"); ok {
				converted, err := aiPlanningValueStringList(value)
				if err != nil {
					return nil, err
				}
				item.RelatedFiles = converted
			}
		}

		items = append(items, item)
	}
	return items, nil
}

// --- small helpers --------------------------------------------------------

func aiPlanningIsDict(value any) bool {
	switch value.(type) {
	case *tmentities.OrderedMap[any], map[string]any:
		return true
	}
	return false
}

func aiPlanningDictGet(value any, key string) (any, bool) {
	switch dict := value.(type) {
	case *tmentities.OrderedMap[any]:
		return dict.Get(key)
	case map[string]any:
		item, ok := dict[key]
		return item, ok
	}
	return nil, false
}

func aiPlanningValueString(value any, def string) string {
	if value == nil {
		return def
	}
	if text, isStr := value.(string); isStr {
		return text
	}
	return tmvo.PyStr(value)
}

func aiPlanningValueStringList(value any) ([]string, error) {
	if value == nil {
		return nil, nil
	}
	switch list := value.(type) {
	case []string:
		out := make([]string, len(list))
		copy(out, list)
		return out, nil
	case []any:
		out := make([]string, 0, len(list))
		for index, item := range list {
			text, isStr := item.(string)
			if !isStr {
				return nil, &tmvo.TypeError{Msg: fmt.Sprintf(
					"sequence item %d: expected str instance, %s found", index, aiPlanningGoTypeName(item))}
			}
			out = append(out, text)
		}
		return out, nil
	}
	return nil, &tmvo.TypeError{Msg: "'" + aiPlanningGoTypeName(value) + "' object is not iterable"}
}

func aiPlanningGoTypeName(value any) string {
	if value == nil {
		return "NoneType"
	}
	switch value.(type) {
	case string:
		return "str"
	case bool:
		return "bool"
	case int, int8, int16, int32, int64:
		return "int"
	case float32, float64:
		return "float"
	case []any, []string:
		return "list"
	case *tmentities.OrderedMap[any], map[string]any:
		return "dict"
	}
	return fmt.Sprintf("%T", value)
}

func aiPlanningAttrError(value any, attr string) string {
	return "'" + aiPlanningGoTypeName(value) + "' object has no attribute '" + attr + "'"
}

func aiPlanningMissingParameter(param string, requiredParams []string) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("error", "Missing required parameter: "+param)
	out.Set("required_parameters", requiredParams)
	return out
}

func aiPlanningSimpleError(message string) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("error", message)
	return out
}

func aiPlanningInsight(insights *tmentities.OrderedMap[any], key string) any {
	value, _ := insights.Get(key)
	return value
}

func aiPlanningStringIn(items []string, item string) bool {
	for _, x := range items {
		if x == item {
			return true
		}
	}
	return false
}

func aiPlanningPrimaryAgents(agentRecommendations *tmentities.OrderedMap[any]) []string {
	type aiPlanningAgentCount struct {
		agent string
		count float64
	}

	entries := []aiPlanningAgentCount{}
	for _, agent := range agentRecommendations.Keys() {
		value, _ := agentRecommendations.Get(agent)
		count, _ := tmvo.PyFloat(value)
		entries = append(entries, aiPlanningAgentCount{agent, count})
	}

	// Python's sorted(..., reverse=True) is stable: equal counts keep insertion order.
	sort.SliceStable(entries, func(i, j int) bool { return entries[i].count > entries[j].count })
	if len(entries) > 3 {
		entries = entries[:3]
	}

	out := []string{}
	for _, entry := range entries {
		out = append(out, entry.agent)
	}
	return out
}

func aiPlanningDistributionLen(value any) int {
	switch distribution := value.(type) {
	case *tmentities.OrderedMap[any]:
		return distribution.Len()
	case map[string]any:
		return len(distribution)
	}
	return 0
}

func aiPlanningKwargString(kwargs *tmentities.OrderedMap[any], key string) string {
	value, _ := kwargs.Get(key)
	return aiPlanningValueString(value, "")
}

func aiPlanningKwargStringDefault(kwargs *tmentities.OrderedMap[any], key, def string) string {
	value, ok := kwargs.Get(key)
	if !ok || value == nil {
		return def
	}
	return aiPlanningValueString(value, def)
}

func aiPlanningKwargOptString(kwargs *tmentities.OrderedMap[any], key string) *string {
	value, ok := kwargs.Get(key)
	if !ok || value == nil {
		return nil
	}
	text := aiPlanningValueString(value, "")
	return &text
}

func aiPlanningExceptionName(err error) string {
	var valueErr *tmvo.ValueError
	var typeErr *tmvo.TypeError
	var attributeErr *aiPlanningAttributeError
	switch {
	case errors.As(err, &valueErr):
		return "ValueError"
	case errors.As(err, &typeErr):
		return "TypeError"
	case errors.As(err, &attributeErr):
		return "AttributeError"
	}
	if strings.HasPrefix(err.Error(), "KeyError: ") {
		return "KeyError"
	}
	return "Exception"
}

// aiPlanningErrorMessage strips the Go entity KeyError prefix so the message matches
// Python's str(KeyError).
func aiPlanningErrorMessage(err error) string {
	message := err.Error()
	if strings.HasPrefix(message, "KeyError: ") {
		return strings.TrimPrefix(message, "KeyError: ")
	}
	return message
}
