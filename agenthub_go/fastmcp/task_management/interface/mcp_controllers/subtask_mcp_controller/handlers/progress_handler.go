package handlers

// Progress Handler for Subtask MCP Controller (Python progress_handler.py).
//
// Handles progress tracking and parent task context updates for subtask
// operations. Logging calls are dropped.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProgressHandler ports ProgressHandler.
type ProgressHandler struct {
	contextFacade ContextFacade
	taskFacade    any
}

// NewProgressHandler ports __init__(context_facade=None, task_facade=None).
func NewProgressHandler(contextFacade ContextFacade, taskFacade any) *ProgressHandler {
	return &ProgressHandler{contextFacade: contextFacade, taskFacade: taskFacade}
}

// UpdateParentProgress ports update_parent_progress.
func (h *ProgressHandler) UpdateParentProgress(ctx context.Context, taskID, subtaskOperation string,
	subtaskData *entities.OrderedMap[any], progressNotes *string) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = metaMap("updated", false, "error", fmt.Sprintf("%v", r))
		}
	}()

	if h.contextFacade == nil {
		return metaMap("updated", false, "reason", "No context facade available")
	}

	progressContent := h.createProgressContent(subtaskOperation, subtaskData, progressNotes)
	_, _ = h.contextFacade.AddProgress(ctx, taskID, progressContent, "subtask_controller")

	overallProgress := h.calculateOverallProgress(taskID)

	out = entities.NewOrderedMap[any]()
	out.Set("updated", true)
	out.Set("progress_content", progressContent)
	out.Set("overall_progress", overallProgress)
	out.Set("timestamp", value_objects.IsoFormat(nowUTC()))
	return out
}

// CalculateTaskProgress ports calculate_task_progress.
func (h *ProgressHandler) CalculateTaskProgress(taskID string, subtasks []*entities.OrderedMap[any]) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = metaMap("error", fmt.Sprintf("Failed to calculate progress: %v", r))
		}
	}()

	totalSubtaskCount := len(subtasks)

	if totalSubtaskCount == 0 {
		out = entities.NewOrderedMap[any]()
		out.Set("total_subtasks", 0)
		out.Set("completed_subtasks", 0)
		out.Set("in_progress_subtasks", 0)
		out.Set("pending_subtasks", 0)
		out.Set("progress_percentage", 0)
		out.Set("progress_status", "no_subtasks")
		return out
	}

	statusCounts := map[string]int{
		"completed": 0, "in_progress": 0, "pending": 0, "blocked": 0, "cancelled": 0,
	}

	for _, subtask := range subtasks {
		status := "pending"
		if v, ok := omString(subtask, "status"); ok {
			status = value_objects.PyLower(v)
		}
		if _, ok := statusCounts[status]; ok {
			statusCounts[status]++
		} else {
			statusCounts["pending"]++
		}
	}

	completed := statusCounts["completed"]
	inProgress := statusCounts["in_progress"]

	weightedCompleted := float64(completed) + float64(inProgress)*0.5
	progressPercentage := int((weightedCompleted / float64(totalSubtaskCount)) * 100)

	var progressStatus string
	switch {
	case completed == totalSubtaskCount:
		progressStatus = "completed"
	case completed > 0 || inProgress > 0:
		progressStatus = "in_progress"
	case statusCounts["blocked"] > 0:
		progressStatus = "blocked"
	default:
		progressStatus = "pending"
	}

	out = entities.NewOrderedMap[any]()
	out.Set("total_subtasks", totalSubtaskCount)
	out.Set("completed_subtasks", completed)
	out.Set("in_progress_subtasks", inProgress)
	out.Set("pending_subtasks", statusCounts["pending"])
	out.Set("blocked_subtasks", statusCounts["blocked"])
	out.Set("cancelled_subtasks", statusCounts["cancelled"])
	out.Set("progress_percentage", progressPercentage)
	out.Set("progress_status", progressStatus)
	out.Set("last_calculated", value_objects.IsoFormat(nowUTC()))
	return out
}

// GetProgressSummary ports get_progress_summary.
func (h *ProgressHandler) GetProgressSummary(taskID string, subtasks []*entities.OrderedMap[any]) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = metaMap("error", fmt.Sprintf("Failed to get progress summary: %v", r))
		}
	}()

	progress := h.CalculateTaskProgress(taskID, subtasks)
	progress.Set("insights", h.generateProgressInsights(progress, subtasks))
	progress.Set("recommendations", h.generateProgressRecommendations(progress, subtasks))
	return progress
}

// createProgressContent ports _create_progress_content.
func (h *ProgressHandler) createProgressContent(operation string, subtaskData *entities.OrderedMap[any], notes *string) string {
	title := "Unknown subtask"
	if v, ok := omString(subtaskData, "title"); ok {
		title = v
	}

	var content string
	switch operation {
	case "create":
		content = fmt.Sprintf("Created subtask: %s", title)
	case "update":
		status, ok := omString(subtaskData, "status")
		if ok && status != "" {
			content = fmt.Sprintf("Updated subtask '%s' - Status: %s", title, status)
		} else {
			content = fmt.Sprintf("Updated subtask: %s", title)
		}
	case "complete":
		content = fmt.Sprintf("Completed subtask: %s", title)
	case "delete":
		content = fmt.Sprintf("Deleted subtask: %s", title)
	default:
		content = fmt.Sprintf("Modified subtask: %s", title)
	}

	if notes != nil && *notes != "" {
		content += fmt.Sprintf(" - %s", *notes)
	}
	return content
}

// calculateOverallProgress ports _calculate_overall_progress (placeholder).
func (h *ProgressHandler) calculateOverallProgress(taskID string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("calculation_needed", true)
	out.Set("task_id", taskID)
	out.Set("timestamp", value_objects.IsoFormat(nowUTC()))
	return out
}

// generateProgressInsights ports _generate_progress_insights.
func (h *ProgressHandler) generateProgressInsights(progress *entities.OrderedMap[any], subtasks []*entities.OrderedMap[any]) []string {
	insights := []string{}

	total := intOrZero(omGet(progress, "total_subtasks"))
	completed := intOrZero(omGet(progress, "completed_subtasks"))
	inProgress := intOrZero(omGet(progress, "in_progress_subtasks"))
	blocked := intOrZero(omGet(progress, "blocked_subtasks"))

	switch {
	case total == 0:
		insights = append(insights, "No subtasks defined - consider breaking down the work")
	case completed == total:
		insights = append(insights, "All subtasks completed! 🎉")
	case blocked > 0:
		insights = append(insights, fmt.Sprintf("%d subtask(s) blocked - may need attention", blocked))
	case float64(inProgress) > float64(total)*0.7:
		insights = append(insights, "Many subtasks in progress - consider focusing efforts")
	case float64(completed) > float64(total)*0.8:
		insights = append(insights, "Nearly complete! Only a few subtasks remaining")
	}

	return insights
}

// generateProgressRecommendations ports _generate_progress_recommendations.
func (h *ProgressHandler) generateProgressRecommendations(progress *entities.OrderedMap[any], subtasks []*entities.OrderedMap[any]) []string {
	recommendations := []string{}

	total := intOrZero(omGet(progress, "total_subtasks"))
	completed := intOrZero(omGet(progress, "completed_subtasks"))
	inProgress := intOrZero(omGet(progress, "in_progress_subtasks"))
	blocked := intOrZero(omGet(progress, "blocked_subtasks"))
	pending := intOrZero(omGet(progress, "pending_subtasks"))

	if blocked > 0 {
		recommendations = append(recommendations, "Address blocked subtasks to maintain momentum")
	}
	if inProgress == 0 && pending > 0 {
		recommendations = append(recommendations, "Start working on pending subtasks")
	}
	if inProgress > 3 {
		recommendations = append(recommendations, "Consider focusing on fewer subtasks simultaneously")
	}
	if completed > 0 && completed == total {
		recommendations = append(recommendations, "Consider marking the parent task as completed")
	}

	return recommendations
}

func intOrZero(v any) int {
	if n, ok := intFromAny(v); ok {
		return n
	}
	return 0
}
