package use_cases

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ValidateDependenciesUseCase ports validate_dependencies.ValidateDependenciesUseCase.
type ValidateDependenciesUseCase struct {
	taskRepository    repositories.TaskRepository
	validationService *services.DependencyValidationService
}

// NewValidateDependenciesUseCase builds the use case and its domain service.
func NewValidateDependenciesUseCase(taskRepository repositories.TaskRepository) *ValidateDependenciesUseCase {
	return &ValidateDependenciesUseCase{
		taskRepository:    taskRepository,
		validationService: services.NewDependencyValidationService(taskRepository, nil),
	}
}

// ValidateTaskDependencies ports validate_task_dependencies.
func (uc *ValidateDependenciesUseCase) ValidateTaskDependencies(ctx context.Context, taskID any) map[string]any {
	domainTaskID, err := value_objects.NewTaskId(value_objects.PyStr(taskID))
	if err != nil {
		return map[string]any{"valid": false, "error": "Validation failed: " + err.Error(), "task_id": value_objects.PyStr(taskID)}
	}
	validationResult := uc.validationService.ValidateDependencyChain(ctx, domainTaskID)
	validationResult["use_case"] = "validate_dependencies"
	validationResult["requested_task_id"] = value_objects.PyStr(taskID)
	if value_objects.PyTruthy(validationResult["issues"]) || value_objects.PyTruthy(validationResult["errors"]) {
		validationResult["recommendations"] = uc.generateRecommendations(validationResult)
	}
	return validationResult
}

// GetDependencyChainAnalysis ports get_dependency_chain_analysis.
func (uc *ValidateDependenciesUseCase) GetDependencyChainAnalysis(ctx context.Context, taskID any) map[string]any {
	domainTaskID, err := value_objects.NewTaskId(value_objects.PyStr(taskID))
	if err != nil {
		return map[string]any{"error": "Analysis failed: " + err.Error(), "task_id": value_objects.PyStr(taskID)}
	}
	chainStatus := uc.validationService.GetDependencyChainStatus(ctx, domainTaskID)
	if _, hasError := chainStatus["error"]; !hasError {
		chainStatus["insights"] = uc.generateChainInsights(chainStatus)
		chainStatus["next_actions"] = uc.suggestNextActions(chainStatus)
	}
	return chainStatus
}

// ValidateMultipleTasks ports validate_multiple_tasks.
func (uc *ValidateDependenciesUseCase) ValidateMultipleTasks(ctx context.Context, taskIDs []any) *entities.OrderedMap[any] {
	taskResults := entities.NewOrderedMap[any]()
	summary := entities.NewOrderedMap[any]()
	summary.Set("total_tasks", len(taskIDs))
	summary.Set("valid_tasks", 0)
	summary.Set("invalid_tasks", 0)
	summary.Set("tasks_with_issues", 0)

	overallValid := true
	for _, taskID := range taskIDs {
		taskResult := uc.ValidateTaskDependencies(ctx, taskID)
		taskResults.Set(value_objects.PyStr(taskID), taskResult)

		if valid, _ := taskResult["valid"].(bool); valid {
			summary.Set("valid_tasks", summaryMustInt(summary, "valid_tasks")+1)
		} else {
			summary.Set("invalid_tasks", summaryMustInt(summary, "invalid_tasks")+1)
			overallValid = false
		}
		if value_objects.PyTruthy(taskResult["issues"]) || value_objects.PyTruthy(taskResult["errors"]) {
			summary.Set("tasks_with_issues", summaryMustInt(summary, "tasks_with_issues")+1)
		}
	}

	results := entities.NewOrderedMap[any]()
	results.Set("overall_valid", overallValid)
	results.Set("task_results", taskResults)
	results.Set("summary", summary)
	if !overallValid {
		results.Set("overall_recommendations", uc.generateOverallRecommendations(summary))
	}
	return results
}

func summaryMustInt(m *entities.OrderedMap[any], key string) int {
	v, _ := m.Get(key)
	f, _ := value_objects.PyFloat(v)
	return int(f)
}

func (uc *ValidateDependenciesUseCase) generateRecommendations(validationResult map[string]any) []any {
	recommendations := []any{}

	for _, errText := range stringListOf(validationResult["errors"]) {
		if strings.Contains(errText, "Circular dependency") {
			recommendations = append(recommendations, recommendationEntry(
				"error_fix", "high", "Break circular dependency chain", errText,
				"Remove one of the dependencies to break the cycle"))
		} else if strings.Contains(errText, "no longer exists") {
			recommendations = append(recommendations, recommendationEntry(
				"error_fix", "high", "Remove orphaned dependency", errText,
				"Use remove_dependency to clean up missing dependencies"))
		}
	}

	for _, issue := range mapListOf(validationResult["issues"]) {
		issueType := "unknown"
		if t, ok := issue["type"].(string); ok {
			issueType = t
		}
		message, _ := issue["message"].(string)
		dependencyID, _ := issue["dependency_id"].(string)
		switch issueType {
		case "cancelled_dependency":
			recommendations = append(recommendations, recommendationEntry(
				"dependency_cleanup", "medium", "Review cancelled dependency", message,
				"Consider removing dependency "+dependencyID+" or finding alternative"))
		case "blocked_dependency":
			recommendations = append(recommendations, recommendationEntry(
				"dependency_unblock", "high", "Unblock dependency", message,
				"Work on unblocking task "+dependencyID+" first"))
		}
	}
	return recommendations
}

func recommendationEntry(typ, priority, action, details, suggestedCommand string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("type", typ)
	m.Set("priority", priority)
	m.Set("action", action)
	m.Set("details", details)
	m.Set("suggested_command", suggestedCommand)
	return m
}

func (uc *ValidateDependenciesUseCase) generateChainInsights(chainStatus map[string]any) []any {
	insights := []any{}

	stats := mapOf(chainStatus["chain_statistics"])
	totalDeps := int(floatOf(stats["total_dependencies"]))
	completedDeps := int(floatOf(stats["completed_dependencies"]))
	completionPct := floatOf(stats["completion_percentage"])

	switch {
	case totalDeps == 0:
		insights = append(insights, insightEntry("no_dependencies", "Task has no dependencies and can be started immediately"))
	case completionPct == 100:
		insights = append(insights, insightEntry("ready_to_start", "All dependencies are completed - task is ready to start"))
	case completionPct > 75:
		insights = append(insights, insightEntry("nearly_ready",
			fmt.Sprintf("Most dependencies are complete (%d/%d) - task should be ready soon", completedDeps, totalDeps)))
	case completionPct > 25:
		insights = append(insights, insightEntry("partial_progress",
			fmt.Sprintf("Some dependencies are complete (%d/%d) - moderate progress", completedDeps, totalDeps)))
	default:
		insights = append(insights, insightEntry("early_stage",
			fmt.Sprintf("Most dependencies are still pending (%d/%d) - task is in early stage", totalDeps-completedDeps, totalDeps)))
	}
	return insights
}

func insightEntry(typ, message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("type", typ)
	m.Set("message", message)
	return m
}

func (uc *ValidateDependenciesUseCase) suggestNextActions(chainStatus map[string]any) []any {
	actions := []any{}

	canProceed, _ := chainStatus["can_proceed"].(bool)
	if canProceed {
		taskID, _ := chainStatus["task_id"].(string)
		action := entities.NewOrderedMap[any]()
		action.Set("action", "start_task")
		action.Set("priority", "high")
		action.Set("description", "All dependencies are satisfied - task can be started")
		action.Set("command", "Start working on task "+taskID)
		actions = append(actions, action)
	} else {
		for _, dep := range mapListOf(chainStatus["dependency_chain"]) {
			isCompleted, _ := dep["is_completed"].(bool)
			status, _ := dep["status"].(string)
			if !isCompleted && status != "blocked" {
				title, _ := dep["title"].(string)
				if title == "" {
					title = "Unknown"
				}
				dependencyID, _ := dep["dependency_id"].(string)
				action := entities.NewOrderedMap[any]()
				action.Set("action", "work_on_dependency")
				action.Set("priority", "high")
				action.Set("description", "Work on dependency: "+title)
				action.Set("command", "Start working on task "+dependencyID)
				actions = append(actions, action)
				break
			}
		}
	}
	return actions
}

func (uc *ValidateDependenciesUseCase) generateOverallRecommendations(summary *entities.OrderedMap[any]) []any {
	recommendations := []any{}
	invalidCount := summaryMustInt(summary, "invalid_tasks")
	issuesCount := summaryMustInt(summary, "tasks_with_issues")

	if invalidCount > 0 {
		m := entities.NewOrderedMap[any]()
		m.Set("type", "dependency_cleanup")
		m.Set("priority", "high")
		m.Set("action", fmt.Sprintf("Fix %d tasks with invalid dependencies", invalidCount))
		m.Set("description", "Review and fix dependency issues before proceeding")
		recommendations = append(recommendations, m)
	}
	if issuesCount > 0 {
		m := entities.NewOrderedMap[any]()
		m.Set("type", "dependency_review")
		m.Set("priority", "medium")
		m.Set("action", fmt.Sprintf("Review %d tasks with dependency issues", issuesCount))
		m.Set("description", "Address warnings and optimize dependency chains")
		recommendations = append(recommendations, m)
	}
	return recommendations
}

// --- value-conversion helpers for the map-shaped service results ---

func floatOf(v any) float64 {
	f, _ := value_objects.PyFloat(v)
	return f
}

func mapOf(v any) map[string]any {
	switch m := v.(type) {
	case map[string]any:
		return m
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		for _, k := range m.Keys() {
			out[k], _ = m.Get(k)
		}
		return out
	}
	return map[string]any{}
}

func stringListOf(v any) []string {
	switch xs := v.(type) {
	case []string:
		return xs
	case []any:
		out := make([]string, 0, len(xs))
		for _, x := range xs {
			if s, ok := x.(string); ok {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}

func mapListOf(v any) []map[string]any {
	switch xs := v.(type) {
	case []map[string]any:
		return xs
	case []any:
		out := make([]map[string]any, 0, len(xs))
		for _, x := range xs {
			if m, ok := x.(map[string]any); ok {
				out = append(out, m)
			} else if om, ok := x.(*entities.OrderedMap[any]); ok {
				m := map[string]any{}
				for _, k := range om.Keys() {
					m[k], _ = om.Get(k)
				}
				out = append(out, m)
			}
		}
		return out
	}
	return nil
}
