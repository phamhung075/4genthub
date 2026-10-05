// Package intelligence ports
// task_management/application/use_cases/intelligence.
package intelligence

import (
	"context"
	"errors"
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	domainintel "agenthub/fastmcp/task_management/domain/services/intelligence"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// IntelligentSelectionRequest is the request for intelligent context selection.
type IntelligentSelectionRequest struct {
	Query               string
	MaxTokens           int
	UserID              *string
	CurrentTaskID       *string
	ProjectID           *string
	GitBranchID         *string
	UserPreferences     *entities.OrderedMap[any]
	AggressiveExpansion bool
	SessionID           *string
}

// NewIntelligentSelectionRequest applies the Python default max_tokens=2000.
func NewIntelligentSelectionRequest(query string) *IntelligentSelectionRequest {
	return &IntelligentSelectionRequest{Query: query, MaxTokens: 2000}
}

// IntelligentSelectionResponse is the response from intelligent context selection.
type IntelligentSelectionResponse struct {
	SelectedContexts   []map[string]any
	TotalTokensUsed    int
	SelectionTimeMs    float64
	PerformanceMetrics *entities.OrderedMap[any]
	Recommendations    []string
	Success            bool
	ErrorMessage       *string
}

// IntelligentSelectionTaskRepository is the task repository surface used by the
// use case. Python uses infrastructure repository methods that the Go domain
// interface does not declare.
type IntelligentSelectionTaskRepository interface {
	GetTasksByBranch(ctx context.Context, gitBranchID string) ([]*entities.Task, error)
	GetTaskByID(ctx context.Context, taskID string) (*entities.Task, error)
}

// IntelligentSelectionProjectRepository is the project repository surface.
type IntelligentSelectionProjectRepository interface {
	GetProjectByID(ctx context.Context, projectID string) (*entities.Project, error)
}

// IntelligentContextSelectionUseCase ports
// intelligent_context_selection.IntelligentContextSelectionUseCase.
type IntelligentContextSelectionUseCase struct {
	ContextRepository   any
	TaskRepository      IntelligentSelectionTaskRepository
	ProjectRepository   IntelligentSelectionProjectRepository
	IntelligentSelector *domainintel.IntelligentContextSelector

	contextsLoaded     bool
	lastContextRefresh *time.Time
}

// NewIntelligentContextSelectionUseCase builds the use case; a nil selector is
// replaced by a default IntelligentContextSelector.
func NewIntelligentContextSelectionUseCase(contextRepository any,
	taskRepository IntelligentSelectionTaskRepository,
	projectRepository IntelligentSelectionProjectRepository,
	selector *domainintel.IntelligentContextSelector) (*IntelligentContextSelectionUseCase, error) {
	if selector == nil {
		created, err := domainintel.NewIntelligentContextSelector(domainintel.DefaultSelectorConfig())
		if err != nil {
			return nil, err
		}
		selector = created
	}
	return &IntelligentContextSelectionUseCase{
		ContextRepository:   contextRepository,
		TaskRepository:      taskRepository,
		ProjectRepository:   projectRepository,
		IntelligentSelector: selector,
	}, nil
}

// Execute runs intelligent context selection, turning any error into the
// success=false response with the error message.
func (uc *IntelligentContextSelectionUseCase) Execute(ctx context.Context,
	request *IntelligentSelectionRequest) *IntelligentSelectionResponse {
	response, err := uc.execute(ctx, request)
	if err != nil {
		message := err.Error()
		return &IntelligentSelectionResponse{
			SelectedContexts:   []map[string]any{},
			TotalTokensUsed:    0,
			SelectionTimeMs:    0.0,
			PerformanceMetrics: entities.NewOrderedMap[any](),
			Recommendations:    []string{},
			Success:            false,
			ErrorMessage:       &message,
		}
	}
	return response
}

func (uc *IntelligentContextSelectionUseCase) execute(ctx context.Context,
	request *IntelligentSelectionRequest) (*IntelligentSelectionResponse, error) {

	if request.SessionID != nil {
		uc.IntelligentSelector.StartSession(*request.SessionID, request.UserID)
	}

	if err := uc.ensureContextsLoaded(ctx, request.ProjectID, request.GitBranchID); err != nil {
		return nil, err
	}

	var currentTask map[string]any
	if request.CurrentTaskID != nil {
		currentTask = uc.getCurrentTask(ctx, *request.CurrentTaskID)
	}

	var projectContext map[string]any
	if request.ProjectID != nil {
		projectContext = uc.getProjectContext(ctx, *request.ProjectID)
	}

	var userPreferences *domainintel.UserPreferences
	if request.UserPreferences != nil {
		preferences := domainintel.NewUserPreferences()
		preferences.PreferredContextTypes = stringListPreference(request.UserPreferences, "preferred_context_types")
		preferences.MaxContextSize = intPreference(request.UserPreferences, "max_context_size", 2000)
		preferences.PriorityBoostKeywords = stringListPreference(request.UserPreferences, "priority_boost_keywords")
		preferences.PenaltyKeywords = stringListPreference(request.UserPreferences, "penalty_keywords")
		preferences.AgentPreferences = floatMapPreference(request.UserPreferences, "agent_preferences")
		userPreferences = preferences
	}

	selectionResult := uc.IntelligentSelector.SelectContext(request.Query, request.MaxTokens,
		domainintel.SelectOptions{
			UserPreferences:     userPreferences,
			CurrentTask:         currentTask,
			ProjectContext:      projectContext,
			AggressiveExpansion: request.AggressiveExpansion,
		})

	recommendations := uc.generateRecommendations(selectionResult, request)
	uc.recordSelectionForLearning(request, selectionResult)

	metrics := entities.NewOrderedMap[any]()
	metrics.Set("hit_rate_estimate", selectionResult.HitRateEstimate)
	metrics.Set("size_reduction_percent", selectionResult.SizeReductionPct)
	metrics.Set("contexts_considered", metadataGet(selectionResult.Metadata, "contexts_considered", 0))
	metrics.Set("semantic_matches", metadataGet(selectionResult.Metadata, "semantic_matches", 0))
	metrics.Set("expansion_path", metadataGet(selectionResult.Metadata, "expansion_path", []any{}))

	return &IntelligentSelectionResponse{
		SelectedContexts:   selectionResult.SelectedContexts,
		TotalTokensUsed:    selectionResult.TotalTokensUsed,
		SelectionTimeMs:    selectionResult.SelectionTimeMs,
		PerformanceMetrics: metrics,
		Recommendations:    recommendations,
		Success:            true,
	}, nil
}

// ensureContextsLoaded mirrors _ensure_contexts_loaded, including the Python
// AttributeError from task.details (the Task entity has no details attribute).
func (uc *IntelligentContextSelectionUseCase) ensureContextsLoaded(ctx context.Context,
	projectID, gitBranchID *string) error {

	shouldRefresh := !uc.contextsLoaded ||
		(uc.lastContextRefresh != nil && time.Since(*uc.lastContextRefresh).Seconds() > 300)
	if !shouldRefresh {
		return nil
	}

	availableContexts := []map[string]any{}

	if gitBranchID != nil {
		tasks, err := uc.TaskRepository.GetTasksByBranch(ctx, *gitBranchID)
		if err != nil {
			return err
		}
		for _, task := range tasks {
			_ = task
			return errors.New("'Task' object has no attribute 'details'")
		}
	}

	if projectID != nil {
		project, err := uc.ProjectRepository.GetProjectByID(ctx, *projectID)
		if err != nil {
			return err
		}
		if project != nil {
			availableContexts = append(availableContexts, map[string]any{
				"id":           "project_" + *projectID,
				"context_id":   "project_" + *projectID,
				"context_type": "project",
				"name":         project.Name,
				"description":  project.Description,
				"project_id":   *projectID,
			})
		}
	}

	if gitBranchID != nil {
		availableContexts = append(availableContexts, map[string]any{
			"id":            "branch_" + *gitBranchID,
			"context_id":    "branch_" + *gitBranchID,
			"context_type":  "branch",
			"git_branch_id": *gitBranchID,
			"project_id":    projectIDValue(projectID),
		})
	}

	availableContexts = append(availableContexts, map[string]any{
		"id":                "global_context",
		"context_id":        "global_context",
		"context_type":      "global",
		"organization_name": "Default Organization",
	})

	uc.IntelligentSelector.LoadAvailableContexts(availableContexts)
	uc.contextsLoaded = true
	now := time.Now().UTC()
	uc.lastContextRefresh = &now
	return nil
}

// getCurrentTask mirrors _get_current_task; failures return nil.
func (uc *IntelligentContextSelectionUseCase) getCurrentTask(ctx context.Context,
	taskID string) map[string]any {
	task, err := uc.TaskRepository.GetTaskByID(ctx, taskID)
	if err != nil || task == nil {
		return nil
	}
	return map[string]any{
		"id":            selectionTaskIDString(task),
		"task_id":       selectionTaskIDString(task),
		"title":         task.Title,
		"description":   task.Description,
		"status":        selectionStatusString(task),
		"git_branch_id": selectionPtrString(task.GitBranchID),
		"dependencies":  selectionDependencyStrings(task),
	}
}

// getProjectContext mirrors _get_project_context; failures return nil.
func (uc *IntelligentContextSelectionUseCase) getProjectContext(ctx context.Context,
	projectID string) map[string]any {
	project, err := uc.ProjectRepository.GetProjectByID(ctx, projectID)
	if err != nil || project == nil {
		return nil
	}
	id := ""
	if project.ID != nil {
		id = project.ID.Value
	}
	return map[string]any{
		"id":          id,
		"project_id":  id,
		"name":        project.Name,
		"description": project.Description,
		"priorities":  map[string]any{},
	}
}

// generateRecommendations mirrors _generate_recommendations.
func (uc *IntelligentContextSelectionUseCase) generateRecommendations(
	selectionResult *domainintel.SelectionResult,
	request *IntelligentSelectionRequest) []string {

	recommendations := []string{}
	if selectionResult.SelectionTimeMs > 150 {
		recommendations = append(recommendations,
			"Selection time approaching limit. Consider reducing query complexity or token budget.")
	}
	if selectionResult.HitRateEstimate < 0.7 {
		recommendations = append(recommendations,
			"Low relevance estimate. Try refining your query with more specific terms.")
	}
	if selectionResult.SizeReductionPct < 0.3 {
		recommendations = append(recommendations,
			"Limited context reduction achieved. Consider using a smaller token budget for more focused results.")
	}
	if len(selectionResult.SelectedContexts) == 0 {
		recommendations = append(recommendations,
			"No contexts selected. Try broadening your query or checking available contexts.")
	} else if len(selectionResult.SelectedContexts) == 1 {
		recommendations = append(recommendations,
			"Only one context selected. Consider using aggressive expansion for more comprehensive results.")
	}

	if request.MaxTokens != 0 {
		tokenUtilization := float64(selectionResult.TotalTokensUsed) / float64(request.MaxTokens)
		if tokenUtilization < 0.5 {
			recommendations = append(recommendations, fmt.Sprintf(
				"Token budget underutilized (%.1f%%). Consider increasing expansion aggressiveness.",
				tokenUtilization*100))
		} else if tokenUtilization > 0.9 {
			recommendations = append(recommendations, fmt.Sprintf(
				"Token budget nearly exhausted (%.1f%%). Consider increasing budget or reducing query scope.",
				tokenUtilization*100))
		}
	}
	return recommendations
}

// recordSelectionForLearning mirrors _record_selection_for_learning.
func (uc *IntelligentContextSelectionUseCase) recordSelectionForLearning(
	request *IntelligentSelectionRequest, result *domainintel.SelectionResult) {
	if request.SessionID == nil {
		return
	}
	for _, contextItem := range result.SelectedContexts {
		contextID := ""
		if id, ok := contextItem["id"]; ok && value_objects.PyTruthy(id) {
			contextID = value_objects.PyStr(id)
		} else {
			contextID = value_objects.PyStr(contextItem["context_id"])
		}
		uc.IntelligentSelector.RecordToolUsage("context_selection", contextID)
	}
}

// GetPerformanceStats returns the selector's performance stats as a dict.
func (uc *IntelligentContextSelectionUseCase) GetPerformanceStats() (*entities.OrderedMap[any], error) {
	stats, err := uc.IntelligentSelector.GetPerformanceStats()
	if err != nil {
		return nil, err
	}
	return performanceStatsToOrdered(stats), nil
}

// OptimizePerformance returns the selector's optimization report as a dict.
func (uc *IntelligentContextSelectionUseCase) OptimizePerformance() *entities.OrderedMap[any] {
	return optimizationReportToOrdered(uc.IntelligentSelector.OptimizePerformance())
}

// RefreshContexts forces the contexts to reload on the next selection.
func (uc *IntelligentContextSelectionUseCase) RefreshContexts() {
	uc.contextsLoaded = false
	uc.lastContextRefresh = nil
}

func performanceStatsToOrdered(stats *domainintel.PerformanceStats) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("total_selections", stats.TotalSelections)
	out.Set("avg_selection_time_ms", stats.AvgSelectionTimeMs)
	out.Set("avg_hit_rate", stats.AvgHitRate)
	out.Set("avg_size_reduction", stats.AvgSizeReduction)
	out.Set("cache_hit_rate", stats.CacheHitRate)
	out.Set("time_target_achievement", stats.TimeTargetAchievement)
	out.Set("hit_rate_target_achievement", stats.HitRateTargetAchievement)
	out.Set("size_reduction_target_achievement", stats.SizeReductionTargetAchievement)
	out.Set("semantic_matching", stats.SemanticMatching)
	out.Set("progressive_expansion", expansionStatsToOrdered(stats.ProgressiveExpansion))
	out.Set("predictive_loading", predictionStatsToOrdered(stats.PredictiveLoading))
	out.Set("context_prioritization", scoringStatsToOrdered(stats.ContextPrioritization))
	out.Set("available_contexts", stats.AvailableContexts)
	out.Set("cached_results", stats.CachedResults)
	out.Set("current_session", stats.CurrentSession)
	return out
}

func expansionStatsToOrdered(stats *domainintel.ExpansionStats) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if stats == nil {
		return out
	}
	out.Set("total_expansions", stats.TotalExpansions)
	out.Set("avg_tokens_used", stats.AvgTokensUsed)
	out.Set("avg_contexts_expanded", stats.AvgContextsExpanded)
	out.Set("tracked_context_patterns", stats.TrackedContextPatterns)
	out.Set("expansion_factor", stats.ExpansionFactor)
	out.Set("token_budget", stats.TokenBudget)
	return out
}

func predictionStatsToOrdered(stats *domainintel.PredictionStats) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if stats == nil {
		return out
	}
	patterns := []any{}
	for _, pattern := range stats.Patterns {
		m := entities.NewOrderedMap[any]()
		m.Set("pattern_id", pattern.PatternID)
		m.Set("pattern_type", pattern.PatternType)
		m.Set("frequency", pattern.Frequency)
		m.Set("confidence", pattern.Confidence)
		m.Set("success_rate", pattern.SuccessRate)
		patterns = append(patterns, m)
	}
	out.Set("total_patterns", stats.TotalPatterns)
	out.Set("avg_success_rate", stats.AvgSuccessRate)
	out.Set("high_confidence_patterns", stats.HighConfidencePatterns)
	out.Set("session_history_count", stats.SessionHistoryCount)
	out.Set("pattern_confidence_threshold", stats.PatternConfidenceThreshold)
	out.Set("patterns", patterns)
	return out
}

func scoringStatsToOrdered(stats *domainintel.ScoringStats) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if stats == nil {
		return out
	}
	frequent := []any{}
	for _, count := range stats.MostFrequentContexts {
		m := entities.NewOrderedMap[any]()
		m.Set("context_id", count.ContextID)
		m.Set("access_count", count.AccessCount)
		frequent = append(frequent, m)
	}
	out.Set("total_contexts_tracked", stats.TotalContextsTracked)
	out.Set("total_accesses_recorded", stats.TotalAccessesRecorded)
	out.Set("avg_accesses_per_context", stats.AvgAccessesPerContext)
	out.Set("recency_decay_hours", stats.RecencyDecayHours)
	out.Set("frequency_window_days", stats.FrequencyWindowDays)
	out.Set("size_penalty_threshold", stats.SizePenaltyThreshold)
	out.Set("most_frequent_contexts", frequent)
	return out
}

func optimizationReportToOrdered(report *domainintel.OptimizationReport) *entities.OrderedMap[any] {
	current := entities.NewOrderedMap[any]()
	current.Set("avg_selection_time_ms", report.AvgSelectionTimeMs)
	current.Set("avg_hit_rate", report.AvgHitRate)
	current.Set("avg_size_reduction", report.AvgSizeReduction)

	targets := entities.NewOrderedMap[any]()
	targets.Set("max_selection_time_ms", report.MaxSelectionTimeMs)
	targets.Set("target_hit_rate", report.TargetHitRate)
	targets.Set("target_size_reduction", report.TargetSizeReduction)

	out := entities.NewOrderedMap[any]()
	out.Set("optimization_actions", report.Actions)
	out.Set("current_performance", current)
	out.Set("targets", targets)
	return out
}

func metadataGet(metadata *entities.OrderedMap[any], key string, def any) any {
	if metadata == nil {
		return def
	}
	if v, ok := metadata.Get(key); ok {
		return v
	}
	return def
}

func stringListPreference(preferences *entities.OrderedMap[any], key string) []string {
	v, ok := preferences.Get(key)
	if !ok || v == nil {
		return []string{}
	}
	switch xs := v.(type) {
	case []string:
		return append([]string{}, xs...)
	case []any:
		out := make([]string, 0, len(xs))
		for _, x := range xs {
			out = append(out, value_objects.PyStr(x))
		}
		return out
	}
	return []string{}
}

func intPreference(preferences *entities.OrderedMap[any], key string, def int) int {
	v, ok := preferences.Get(key)
	if !ok || v == nil {
		return def
	}
	if n, ok := v.(int); ok {
		return n
	}
	if f, ok := v.(float64); ok {
		return int(f)
	}
	return def
}

func floatMapPreference(preferences *entities.OrderedMap[any], key string) map[string]float64 {
	v, ok := preferences.Get(key)
	if !ok || v == nil {
		return map[string]float64{}
	}
	out := map[string]float64{}
	switch m := v.(type) {
	case map[string]float64:
		return m
	case map[string]any:
		for k, raw := range m {
			if f, ok := raw.(float64); ok {
				out[k] = f
			}
		}
	}
	return out
}

func selectionTaskIDString(task *entities.Task) string {
	if task.ID == nil {
		return "None"
	}
	return task.ID.Value
}

func selectionStatusString(task *entities.Task) string {
	if task.Status == nil {
		return "None"
	}
	return task.Status.Value
}

func selectionPtrString(s *string) string {
	if s == nil {
		return "None"
	}
	return *s
}

func selectionDependencyStrings(task *entities.Task) []string {
	if len(task.Dependencies) == 0 {
		return []string{}
	}
	out := make([]string, 0, len(task.Dependencies))
	for _, dep := range task.Dependencies {
		out = append(out, dep.Value)
	}
	return out
}

func projectIDValue(projectID *string) any {
	if projectID == nil {
		return nil
	}
	return *projectID
}
