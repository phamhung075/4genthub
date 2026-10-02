package mcp_controllers

// Enhanced Dependency Controller - AI-powered dependency management MCP controller
// (Python enhanced_dependency_controller.py).
//
// FastMCP tool registration (`register_tools`) and the event-loop juggling around
// the async engine calls have no Go meaning and are not ported; the management
// logic is.

import (
	"context"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/ai_services"
)

// edcNow mirrors datetime.now(UTC).isoformat().
func edcNow() string { return value_objects.IsoFormat(time.Now().UTC()) }

// EnhancedDependencyController ports EnhancedDependencyController.
type EnhancedDependencyController struct {
	taskFacade         *facades.TaskApplicationFacade
	taskRepository     repositories.TaskRepository
	dependencyResolver *services.DependencyResolverService
	dependencyEngine   *services.DependencyManagementEngine
	mlPredictor        *ai_services.MLDependencyPredictor
}

// NewEnhancedDependencyController ports __init__(task_facade, task_repository,
// dependency_resolver). Python builds MLDependencyPredictor(task_repository); the
// Go predictor also needs a model directory, which is injected here.
func NewEnhancedDependencyController(taskFacade *facades.TaskApplicationFacade, taskRepository repositories.TaskRepository, dependencyResolver *services.DependencyResolverService, modelDir string) (*EnhancedDependencyController, error) {
	predictor, err := ai_services.NewMLDependencyPredictor(taskRepository, modelDir)
	if err != nil {
		return nil, err
	}
	return &EnhancedDependencyController{
		taskFacade:         taskFacade,
		taskRepository:     taskRepository,
		dependencyResolver: dependencyResolver,
		dependencyEngine:   services.NewDependencyManagementEngine(dependencyResolver, taskRepository, nil),
		mlPredictor:        predictor,
	}, nil
}

func edcMapWithUser(engine *services.DependencyManagementEngine, userID *string) *services.DependencyManagementEngine {
	if userID != nil && *userID != "" {
		return engine.WithUser(*userID)
	}
	return engine
}

func edcIsoOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return value_objects.IsoFormat(*t)
}

func edcNames(branches []any) []any {
	out := make([]any, 0, len(branches))
	for _, b := range branches {
		if m, ok := b.(*entities.OrderedMap[any]); ok {
			v, _ := m.Get("git_branch_name")
			out = append(out, v)
		}
	}
	return out
}

// HandleAIDependencyAnalysis ports
// handle_ai_dependency_analysis(task_id, user_id=None, include_suggestions=True,
// confidence_threshold=0.5).
func (c *EnhancedDependencyController) HandleAIDependencyAnalysis(ctx context.Context, taskID string, userID *string, includeSuggestions bool, confidenceThreshold float64) *entities.OrderedMap[any] {
	engine := edcMapWithUser(c.dependencyEngine, userID)

	relationships, err := engine.ResolveDependenciesWithAI(ctx, taskID)
	if err != nil {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "AI dependency analysis failed: "+err.Error())
		m.Set("error_code", "AI_ANALYSIS_FAILED")
		m.Set("task_id", taskID)
		m.Set("timestamp", edcNow())
		return m
	}

	basic := relationships.BasicRelationships

	dependsOn := make([]any, 0, len(basic.DependsOn))
	for i := range basic.DependsOn {
		dependsOn = append(dependsOn, c.formatDependencyInfo(&basic.DependsOn[i]))
	}
	blocks := make([]any, 0, len(basic.Blocks))
	for i := range basic.Blocks {
		blocks = append(blocks, c.formatDependencyInfo(&basic.Blocks[i]))
	}

	existingDeps := entities.NewOrderedMap[any]()
	existingDeps.Set("depends_on", dependsOn)
	existingDeps.Set("blocks", blocks)
	existingDeps.Set("total_dependencies", basic.TotalDependencies)
	existingDeps.Set("completed_dependencies", basic.CompletedDependencies)
	existingDeps.Set("can_start", basic.CanStart)
	existingDeps.Set("is_blocked", basic.IsBlocked)
	existingDeps.Set("dependency_summary", basic.DependencySummary)

	aiAnalysis := entities.NewOrderedMap[any]()
	aiAnalysis.Set("suggestions_generated", len(relationships.AISuggestions))
	aiAnalysis.Set("suggestion_summary", relationships.SuggestionSummary)
	aiAnalysis.Set("optimization_score", relationships.OptimizationScore)
	aiAnalysis.Set("performance_metrics", relationships.PerformanceMetrics)

	analysis := entities.NewOrderedMap[any]()
	analysis.Set("existing_dependencies", existingDeps)
	analysis.Set("ai_analysis", aiAnalysis)

	if includeSuggestions {
		filtered := make([]*services.DependencySuggestion, 0)
		for _, s := range relationships.AISuggestions {
			if s.Hint.ConfidenceScore >= confidenceThreshold {
				filtered = append(filtered, s)
			}
		}
		items := make([]any, 0, len(filtered))
		for _, s := range filtered {
			items = append(items, c.formatSuggestion(s))
		}
		analysis.Set("ai_suggestions", items)
		aiAnalysis.Set("high_confidence_suggestions", len(filtered))
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("task_id", taskID)
	m.Set("analysis", analysis)
	m.Set("timestamp", edcNow())
	return m
}

// HandleDependencySuggestions ports
// handle_dependency_suggestions(task_id, user_id=None,
// suggestion_types="content,pattern,resource", max_suggestions=10).
func (c *EnhancedDependencyController) HandleDependencySuggestions(ctx context.Context, taskID string, userID *string, suggestionTypes string, maxSuggestions int) *entities.OrderedMap[any] {
	requestedTypes := make([]string, 0)
	for _, t := range strings.Split(suggestionTypes, ",") {
		requestedTypes = append(requestedTypes, strings.TrimSpace(t))
	}

	engine := edcMapWithUser(c.dependencyEngine, userID)
	allSuggestions := engine.SuggestDependencies(ctx, taskID)

	allowedTypes := make([]string, 0)
	for _, reqType := range requestedTypes {
		switch reqType {
		case "content":
			allowedTypes = append(allowedTypes, "content")
		case "pattern":
			allowedTypes = append(allowedTypes, "pattern")
		case "semantic":
			allowedTypes = append(allowedTypes, "semantic")
		case "resource":
			allowedTypes = append(allowedTypes, "resource")
		case "temporal":
			allowedTypes = append(allowedTypes, "temporal")
		}
	}

	filtered := make([]*services.DependencySuggestion, 0)
	if len(allowedTypes) > 0 {
		for _, s := range allSuggestions {
			for _, allowed := range allowedTypes {
				if string(s.Hint.SuggestionType) == allowed {
					filtered = append(filtered, s)
					break
				}
			}
		}
	} else {
		filtered = allSuggestions
	}

	limited := filtered
	if maxSuggestions < len(limited) {
		limited = limited[:maxSuggestions]
	}

	items := make([]any, 0, len(limited))
	highConfidence := 0
	mediumConfidence := 0
	totalConfidence := 0.0
	for _, s := range limited {
		items = append(items, c.formatSuggestion(s))
		if s.Hint.ConfidenceScore > 0.7 {
			highConfidence++
		} else if s.Hint.ConfidenceScore > 0.4 && s.Hint.ConfidenceScore <= 0.7 {
			mediumConfidence++
		}
		totalConfidence += s.Hint.ConfidenceScore
	}
	avgConfidence := 0.0
	if len(limited) > 0 {
		avgConfidence = totalConfidence / float64(len(limited))
	}

	suggestions := entities.NewOrderedMap[any]()
	suggestions.Set("total_generated", len(allSuggestions))
	suggestions.Set("filtered_count", len(filtered))
	suggestions.Set("returned_count", len(limited))
	suggestions.Set("suggestion_types_requested", requestedTypes)
	suggestions.Set("items", items)

	statistics := entities.NewOrderedMap[any]()
	statistics.Set("avg_confidence", avgConfidence)
	statistics.Set("high_confidence_count", highConfidence)
	statistics.Set("medium_confidence_count", mediumConfidence)
	statistics.Set("type_breakdown", c.getTypeBreakdown(limited))

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("task_id", taskID)
	m.Set("suggestions", suggestions)
	m.Set("statistics", statistics)
	m.Set("timestamp", edcNow())
	return m
}

// HandleModelManagement ports handle_model_management(action, user_id=None, project_limit=None).
func (c *EnhancedDependencyController) HandleModelManagement(action string, userID *string, projectLimit *int) *entities.OrderedMap[any] {
	switch action {
	case "train":
		trainingResults := c.mlPredictor.TrainModel(projectLimit, true)
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "train")
		m.Set("results", trainingResults)
		m.Set("timestamp", edcNow())
		return m
	case "retrain":
		trainingResults := c.mlPredictor.RetrainModel()
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "retrain")
		m.Set("results", trainingResults)
		m.Set("timestamp", edcNow())
		return m
	case "status":
		engineStats := c.dependencyEngine.GetPerformanceMetrics()
		modelInfo := c.mlPredictor.GetModelInfo()

		trained, _ := modelInfo.Get("trained")
		availableVersions, ok := modelInfo.Get("available_versions")
		if !ok || availableVersions == nil {
			availableVersions = []any{}
		}
		currentStats, _ := modelInfo.Get("current_stats")

		modelStatus := entities.NewOrderedMap[any]()
		modelStatus.Set("trained", trained)
		modelStatus.Set("available_versions", availableVersions)
		modelStatus.Set("engine_performance", engineStats)
		modelStatus.Set("current_stats", currentStats)

		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "status")
		m.Set("model_status", modelStatus)
		m.Set("timestamp", edcNow())
		return m
	case "info":
		modelInfo := c.mlPredictor.GetModelInfo()
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "info")
		m.Set("model_info", modelInfo)
		m.Set("timestamp", edcNow())
		return m
	default:
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "Unknown action: "+action)
		m.Set("error_code", "INVALID_ACTION")
		m.Set("valid_actions", []any{"train", "retrain", "status", "info"})
		m.Set("timestamp", edcNow())
		return m
	}
}

// HandleBatchOptimization ports
// handle_batch_optimization(project_id=None, git_branch_id=None, user_id=None,
// auto_apply=False, confidence_threshold=0.8).
func (c *EnhancedDependencyController) HandleBatchOptimization(ctx context.Context, projectID, gitBranchID, userID *string, autoApply bool, confidenceThreshold float64) *entities.OrderedMap[any] {
	if (projectID == nil || *projectID == "") && (gitBranchID == nil || *gitBranchID == "") {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "Either project_id or git_branch_id must be provided")
		m.Set("error_code", "MISSING_SCOPE")
		m.Set("timestamp", edcNow())
		return m
	}

	var tasks []*entities.Task
	var scope string
	if gitBranchID != nil && *gitBranchID != "" {
		tasks = c.getTasksByBranch(ctx, *gitBranchID)
		scope = "Branch " + *gitBranchID
	} else {
		tasks = c.getTasksByProject(ctx, *projectID)
		scope = "Project " + *projectID
	}

	if len(tasks) == 0 {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("message", "No tasks found in "+scope)
		m.Set("scope", scope)
		m.Set("timestamp", edcNow())
		return m
	}

	engine := edcMapWithUser(c.dependencyEngine, userID)

	optimizationResults := make([]any, 0)
	appliedSuggestions := make([]any, 0)

	for _, t := range tasks {
		taskID := ""
		if t.ID != nil {
			taskID = t.ID.Value
		}

		suggestions := engine.SuggestDependencies(ctx, taskID)

		if len(suggestions) == 0 {
			continue
		}

		highConfidenceSuggestions := make([]*services.DependencySuggestion, 0)
		for _, s := range suggestions {
			if s.Hint.ConfidenceScore >= confidenceThreshold {
				highConfidenceSuggestions = append(highConfidenceSuggestions, s)
			}
		}

		top := suggestions
		if len(top) > 5 {
			top = top[:5]
		}
		itemSuggestions := make([]any, 0, len(top))
		for _, s := range top {
			itemSuggestions = append(itemSuggestions, c.formatSuggestion(s))
		}

		taskResult := entities.NewOrderedMap[any]()
		taskResult.Set("task_id", taskID)
		taskResult.Set("task_title", t.Title)
		taskResult.Set("suggestions_count", len(suggestions))
		taskResult.Set("high_confidence_count", len(highConfidenceSuggestions))
		taskResult.Set("suggestions", itemSuggestions)

		if autoApply && len(highConfidenceSuggestions) > 0 {
			for _, s := range highConfidenceSuggestions {
				applied := entities.NewOrderedMap[any]()
				applied.Set("task_id", taskID)
				applied.Set("dependency_id", s.Hint.SuggestedDependencyID)
				applied.Set("confidence", s.Hint.ConfidenceScore)
				applied.Set("reason", s.Hint.SuggestionReason)
				appliedSuggestions = append(appliedSuggestions, applied)
			}
			taskResult.Set("auto_applied", len(highConfidenceSuggestions))
		}

		optimizationResults = append(optimizationResults, taskResult)
	}

	totalSuggestions := 0
	totalHighConfidence := 0
	tasksWithSuggestions := 0
	for _, r := range optimizationResults {
		rm := r.(*entities.OrderedMap[any])
		sc, _ := rm.Get("suggestions_count")
		hc, _ := rm.Get("high_confidence_count")
		sci, _ := value_objects.PyFloat(sc)
		hci, _ := value_objects.PyFloat(hc)
		totalSuggestions += int(sci)
		totalHighConfidence += int(hci)
		if sci > 0 {
			tasksWithSuggestions++
		}
	}

	appliedCount := 0
	if autoApply {
		appliedCount = len(appliedSuggestions)
	}

	results := entities.NewOrderedMap[any]()
	results.Set("tasks_analyzed", len(tasks))
	results.Set("tasks_with_suggestions", tasksWithSuggestions)
	results.Set("total_suggestions_generated", totalSuggestions)
	results.Set("high_confidence_suggestions", totalHighConfidence)
	results.Set("auto_applied_count", appliedCount)
	results.Set("tasks", optimizationResults)

	parameters := entities.NewOrderedMap[any]()
	parameters.Set("auto_apply", autoApply)
	parameters.Set("confidence_threshold", confidenceThreshold)

	var applied any
	if autoApply {
		applied = appliedSuggestions
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("scope", scope)
	m.Set("optimization_results", results)
	m.Set("applied_suggestions", applied)
	m.Set("parameters", parameters)
	m.Set("timestamp", edcNow())
	return m
}

// getTasksByBranch ports _get_tasks_by_branch(git_branch_id).
func (c *EnhancedDependencyController) getTasksByBranch(ctx context.Context, gitBranchID string) []*entities.Task {
	allTasks, err := c.taskRepository.FindAll(ctx)
	if err != nil {
		return []*entities.Task{}
	}
	filtered := make([]*entities.Task, 0)
	for _, t := range allTasks {
		if t.GitBranchID != nil && *t.GitBranchID == gitBranchID {
			filtered = append(filtered, t)
		}
	}
	return filtered
}

// getTasksByProject ports _get_tasks_by_project(project_id).
func (c *EnhancedDependencyController) getTasksByProject(ctx context.Context, projectID string) []*entities.Task {
	allTasks, err := c.taskRepository.FindAll(ctx)
	if err != nil {
		return []*entities.Task{}
	}
	return allTasks
}

// formatDependencyInfo ports _format_dependency_info(dep_info).
func (c *EnhancedDependencyController) formatDependencyInfo(d *task.DependencyInfo) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", d.TaskID)
	m.Set("title", d.Title)
	m.Set("status", d.Status)
	m.Set("priority", d.Priority)
	m.Set("completion_percentage", d.CompletionPercentage)
	m.Set("is_blocking", d.IsBlocking)
	m.Set("is_blocked", d.IsBlocked)
	m.Set("estimated_effort", d.EstimatedEffort)
	m.Set("assignees", d.Assignees)
	m.Set("updated_at", edcIsoOrNil(d.UpdatedAt))
	return m
}

// formatSuggestion ports _format_suggestion(suggestion).
func (c *EnhancedDependencyController) formatSuggestion(s *services.DependencySuggestion) *entities.OrderedMap[any] {
	var target any
	if s.TargetTaskInfo != nil {
		target = c.formatDependencyInfo(s.TargetTaskInfo)
	}
	m := entities.NewOrderedMap[any]()
	m.Set("suggested_dependency_id", s.Hint.SuggestedDependencyID)
	m.Set("confidence_score", s.Hint.ConfidenceScore)
	m.Set("suggestion_reason", s.Hint.SuggestionReason)
	m.Set("suggestion_type", string(s.Hint.SuggestionType))
	m.Set("evidence", s.Hint.Evidence)
	m.Set("target_task", target)
	m.Set("status", string(s.Status))
	m.Set("created_at", value_objects.IsoFormat(s.CreatedAt))
	return m
}

// getTypeBreakdown ports _get_type_breakdown(suggestions).
func (c *EnhancedDependencyController) getTypeBreakdown(suggestions []*services.DependencySuggestion) *entities.OrderedMap[any] {
	breakdown := entities.NewOrderedMap[any]()
	for _, s := range suggestions {
		st := string(s.Hint.SuggestionType)
		if v, ok := breakdown.Get(st); ok {
			n, _ := value_objects.PyFloat(v)
			breakdown.Set(st, int(n)+1)
		} else {
			breakdown.Set(st, 1)
		}
	}
	return breakdown
}

// GetAIDependencyAnalysisDescription ports _get_ai_dependency_analysis_description().
func (c *EnhancedDependencyController) GetAIDependencyAnalysisDescription() string {
	return "Analyze task dependencies with AI enhancements including automated detection, \npattern recognition, and optimization recommendations. Provides comprehensive\ndependency analysis with confidence scores and actionable insights."
}

// GetDependencySuggestionsDescription ports _get_dependency_suggestions_description().
func (c *EnhancedDependencyController) GetDependencySuggestionsDescription() string {
	return "Generate AI-powered dependency suggestions using multiple analysis methods:\ncontent analysis, pattern recognition, semantic analysis, and resource analysis.\nReturns ranked suggestions with confidence scores and evidence."
}

// GetModelManagementDescription ports _get_model_management_description().
func (c *EnhancedDependencyController) GetModelManagementDescription() string {
	return "Manage the dependency prediction ML model including training, status checks,\nand detailed model information. Supports training from historical data and\nperformance monitoring."
}

// GetBatchOptimizationDescription ports _get_batch_optimization_description().
func (c *EnhancedDependencyController) GetBatchOptimizationDescription() string {
	return "Optimize dependencies for an entire project or branch with batch analysis,\nautomated suggestions, and optional auto-application of high-confidence\ndependency relationships."
}
