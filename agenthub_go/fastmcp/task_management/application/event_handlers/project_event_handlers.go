package event_handlers

import (
	"context"
	"strconv"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Deviation (MIGRATION.md, event_handlers decision 2026-10-02): the Python
// handlers read attributes the event classes do not define (created_by,
// project_name, changed_fields, new_values, previous_values, updated_by,
// deleted_by, active_tasks, health_indicators, health_score, identified_issues,
// previous_health_status, archive_reason) and raise AttributeError. The Go
// handlers work against the real event fields; wherever a Python-only attribute
// has no counterpart, the value is a documented placeholder (nil/empty).

// ProjectNotificationService is the minimal notification dependency.
type ProjectNotificationService interface {
	NotifyProjectCreated(ctx context.Context, projectID, projectName, createdBy string) error
	NotifyProjectUpdated(ctx context.Context, projectID string, changedFields []string, previousValues, newValues map[string]any, updatedBy string) error
	NotifyProjectDeleted(ctx context.Context, projectID, deletedBy string) error
	NotifyProjectHealthChanged(ctx context.Context, projectID, previousStatus, newStatus string, healthScore float64, issues []string) error
	NotifyProjectArchived(ctx context.Context, projectID, archivedBy, reason string) error
	SendHealthAlert(ctx context.Context, projectID, healthStatus string, healthScore float64, issues []string, urgency string) error
	SendHealthSuggestions(ctx context.Context, projectID string, suggestions []string) error
}

// ProjectAnalyticsService is the minimal analytics dependency.
type ProjectAnalyticsService interface {
	StartProjectTracking(ctx context.Context, projectID string, metadata map[string]any) error
	TrackProjectUpdate(ctx context.Context, projectID string, changes []string) error
	FinalizeProjectTracking(ctx context.Context, projectID string, deletedAt time.Time) error
	UpdateProjectMetrics(ctx context.Context, projectID string, metrics map[string]any) error
	ArchiveProjectData(ctx context.Context, projectID string, archivedAt time.Time) error
}

// ProjectStatsRepository is the synchronous statistics persistence dependency.
type ProjectStatsRepository interface {
	UpdateStatistics(projectID string, branchCount, taskCount, completedTasks, inProgressTasks, todoTasks int, progressPercentage float64)
}

// ProjectEventHandlers handles project-related domain events.
type ProjectEventHandlers struct {
	// mu guards the in-memory statistics maps/slices below.
	mu                  sync.Mutex
	EventStore          EventAppender
	ProjectRepository   ProjectStatsRepository
	NotificationService ProjectNotificationService
	AnalyticsService    ProjectAnalyticsService

	ProjectStats     map[string]map[string]any
	HealthHistory    map[string][]map[string]any
	ArchivedProjects map[string]map[string]any
}

// EventAppender is the minimal single-event append capability.
type EventAppender interface {
	Append(ctx context.Context, event events.Event) error
}

// NewProjectEventHandlers builds the handler with the Python default dicts.
func NewProjectEventHandlers(eventStore EventAppender, projectRepository ProjectStatsRepository, notificationService ProjectNotificationService, analyticsService ProjectAnalyticsService) *ProjectEventHandlers {
	return &ProjectEventHandlers{
		EventStore:          eventStore,
		ProjectRepository:   projectRepository,
		NotificationService: notificationService,
		AnalyticsService:    analyticsService,
		ProjectStats:        map[string]map[string]any{},
		HealthHistory:       map[string][]map[string]any{},
		ArchivedProjects:    map[string]map[string]any{},
	}
}

func (h *ProjectEventHandlers) stats(key string) map[string]any {
	s, ok := h.ProjectStats[key]
	if !ok {
		s = map[string]any{
			"created_at": nil, "total_tasks": 0, "completed_tasks": 0, "active_tasks": 0,
			"total_branches": 0, "total_agents": 0, "updates": 0, "health_changes": 0,
		}
		h.ProjectStats[key] = s
	}
	return s
}

func userIDOrEmpty(id *string) string {
	if id == nil {
		return ""
	}
	return *id
}

// HandleProjectCreated handles ProjectCreatedEvent.
func (h *ProjectEventHandlers) HandleProjectCreated(ctx context.Context, event events.ProjectCreatedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	key := event.ProjectID
	s := h.stats(key)
	s["created_at"] = event.OccurredAt
	s["name"] = event.Name
	s["created_by"] = userIDOrEmpty(event.UserID)
	if event.Description != nil {
		s["description"] = *event.Description
	} else {
		s["description"] = ""
	}

	h.HealthHistory[key] = append(h.HealthHistory[key], map[string]any{
		"status": "healthy", "score": 100.0,
		"timestamp": value_objects.IsoFormat(event.OccurredAt), "reason": "Project initialized",
	})

	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyProjectCreated(ctx, event.ProjectID, event.Name, userIDOrEmpty(event.UserID))
	}
	if h.AnalyticsService != nil {
		_ = h.AnalyticsService.StartProjectTracking(ctx, event.ProjectID, map[string]any{
			"name": event.Name, "created_at": value_objects.IsoFormat(event.OccurredAt), "created_by": userIDOrEmpty(event.UserID),
		})
	}
}

// HandleProjectUpdated handles ProjectUpdatedEvent.
func (h *ProjectEventHandlers) HandleProjectUpdated(ctx context.Context, event events.ProjectUpdatedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	key := event.ProjectID
	s := h.stats(key)
	s["updates"] = s["updates"].(int) + 1
	s["last_updated"] = event.OccurredAt

	changed, previous, current := projectChanges(event)
	significant := []string{}
	for _, f := range changed {
		if f == "name" || f == "status" || f == "description" {
			significant = append(significant, f)
		}
	}
	if len(significant) > 0 && h.NotificationService != nil {
		_ = h.NotificationService.NotifyProjectUpdated(ctx, event.ProjectID, significant, previous, current, userIDOrEmpty(event.UserID))
	}
	if h.AnalyticsService != nil {
		_ = h.AnalyticsService.TrackProjectUpdate(ctx, event.ProjectID, changed)
	}
}

func projectChanges(event events.ProjectUpdatedEvent) ([]string, map[string]any, map[string]any) {
	changed := []string{}
	previous := map[string]any{}
	current := map[string]any{}
	add := func(name string, oldV, newV *string) {
		if oldV != nil || newV != nil {
			changed = append(changed, name)
			if oldV != nil {
				previous[name] = *oldV
			} else {
				previous[name] = nil
			}
			if newV != nil {
				current[name] = *newV
			} else {
				current[name] = nil
			}
		}
	}
	add("name", event.OldName, event.NewName)
	add("status", event.OldStatus, event.NewStatus)
	add("description", event.OldDescription, event.NewDescription)
	return changed, previous, current
}

// HandleProjectDeleted handles ProjectDeletedEvent.
func (h *ProjectEventHandlers) HandleProjectDeleted(ctx context.Context, event events.ProjectDeletedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	key := event.ProjectID
	if s, ok := h.ProjectStats[key]; ok {
		archived := map[string]any{}
		for k, v := range s {
			archived[k] = v
		}
		archived["deleted_at"] = event.OccurredAt
		archived["deleted_by"] = userIDOrEmpty(event.UserID)
		if hh, ok := h.HealthHistory[key]; ok {
			archived["health_history"] = hh
		} else {
			archived["health_history"] = []map[string]any{}
		}
		h.ArchivedProjects[key] = archived
		delete(h.ProjectStats, key)
		delete(h.HealthHistory, key)
	}
	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyProjectDeleted(ctx, event.ProjectID, userIDOrEmpty(event.UserID))
	}
	if h.AnalyticsService != nil {
		_ = h.AnalyticsService.FinalizeProjectTracking(ctx, event.ProjectID, event.OccurredAt)
	}
}

// HandleProjectStatisticsUpdated handles ProjectStatisticsUpdatedEvent.
func (h *ProjectEventHandlers) HandleProjectStatisticsUpdated(ctx context.Context, event events.ProjectStatisticsUpdatedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	key := event.ProjectID
	s := h.stats(key)
	s["branch_count"] = event.BranchCount
	s["total_tasks"] = event.TotalTasks
	s["completed_tasks"] = event.CompletedTasks
	s["active_tasks"] = event.InProgressTasks
	s["completion_rate"] = event.OverallProgressPercentage / 100.0
	s["stats_updated_at"] = event.OccurredAt

	if h.ProjectRepository != nil {
		h.ProjectRepository.UpdateStatistics(event.ProjectID, event.BranchCount, event.TotalTasks, event.CompletedTasks, event.InProgressTasks, event.TodoTasks, event.OverallProgressPercentage)
	}

	h.assessProjectHealth(ctx, event.ProjectID, event)

	if h.AnalyticsService != nil {
		_ = h.AnalyticsService.UpdateProjectMetrics(ctx, event.ProjectID, map[string]any{
			"total_tasks": event.TotalTasks, "completed_tasks": event.CompletedTasks,
			"active_tasks": event.InProgressTasks, "completion_percentage": event.OverallProgressPercentage,
		})
	}
}

// HandleProjectHealthChanged handles ProjectHealthChanged.
func (h *ProjectEventHandlers) HandleProjectHealthChanged(ctx context.Context, event events.ProjectHealthChanged) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.handleProjectHealthChanged(ctx, event)
}

// handleProjectHealthChanged is HandleProjectHealthChanged without taking the lock (called from other locked handlers).
func (h *ProjectEventHandlers) handleProjectHealthChanged(ctx context.Context, event events.ProjectHealthChanged) {
	key := event.ProjectID
	s := h.stats(key)
	s["health_changes"] = s["health_changes"].(int) + 1

	score := numberOrZero(event.HealthMetrics["score"])
	indicators := stringsOrEmpty(event.HealthMetrics["indicators"])
	issues := stringsOrEmpty(event.HealthMetrics["issues"])

	record := map[string]any{
		"status": event.NewHealthStatus, "score": score, "previous_status": event.OldHealthStatus,
		"timestamp": value_objects.IsoFormat(event.OccurredAt), "indicators": indicators, "issues": issues,
	}
	hist := append(h.HealthHistory[key], record)
	if len(hist) > 50 {
		hist = hist[len(hist)-50:]
	}
	h.HealthHistory[key] = hist

	if event.NewHealthStatus == "at_risk" || event.NewHealthStatus == "critical" {
		h.triggerHealthIntervention(ctx, event, score, issues)
	}
	if event.OldHealthStatus != event.NewHealthStatus && h.NotificationService != nil {
		_ = h.NotificationService.NotifyProjectHealthChanged(ctx, event.ProjectID, event.OldHealthStatus, event.NewHealthStatus, score, issues)
	}
}

// HandleProjectArchived handles ProjectArchived.
func (h *ProjectEventHandlers) HandleProjectArchived(ctx context.Context, event events.ProjectArchived) {
	h.mu.Lock()
	defer h.mu.Unlock()
	key := event.ProjectID
	if s, ok := h.ProjectStats[key]; ok {
		archived := map[string]any{}
		for k, v := range s {
			archived[k] = v
		}
		archived["archived_at"] = event.OccurredAt
		archived["archived_by"] = event.ArchivedBy
		if event.Reason != nil {
			archived["archive_reason"] = *event.Reason
		} else {
			archived["archive_reason"] = nil
		}
		if hh, ok := h.HealthHistory[key]; ok {
			archived["final_health_history"] = hh
		} else {
			archived["final_health_history"] = []map[string]any{}
		}
		h.ArchivedProjects[key] = archived
		s["archived"] = true
		s["archived_at"] = event.OccurredAt
	}
	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyProjectArchived(ctx, event.ProjectID, event.ArchivedBy, derefOrEmpty(event.Reason))
	}
	if h.AnalyticsService != nil {
		_ = h.AnalyticsService.ArchiveProjectData(ctx, event.ProjectID, event.OccurredAt)
	}
}

func (h *ProjectEventHandlers) assessProjectHealth(ctx context.Context, projectID string, statsEvent events.ProjectStatisticsUpdatedEvent) {
	key := projectID
	var currentHealth map[string]any
	if hh, ok := h.HealthHistory[key]; ok && len(hh) > 0 {
		currentHealth = hh[len(hh)-1]
	}

	healthScore := 100.0
	indicators := []string{}
	issues := []string{}

	completionRate := statsEvent.OverallProgressPercentage / 100.0
	if completionRate < 0.2 {
		healthScore -= 20
		issues = append(issues, "Low completion rate")
	}
	indicators = append(indicators, "Completion: "+pyFloat1(statsEvent.OverallProgressPercentage)+"%")

	if statsEvent.TotalTasks > 0 {
		activeRatio := float64(statsEvent.InProgressTasks) / float64(statsEvent.TotalTasks)
		if activeRatio > 0.8 {
			healthScore -= 15
			issues = append(issues, "Too many active tasks")
		}
		indicators = append(indicators, "Active ratio: "+pyPercent1(activeRatio))
	}

	if currentHealth != nil {
		if prevScore, ok := currentHealth["score"].(float64); ok && healthScore < prevScore-10 {
			issues = append(issues, "Health declining")
		}
	}

	healthStatus := "critical"
	switch {
	case healthScore >= 80:
		healthStatus = "healthy"
	case healthScore >= 60:
		healthStatus = "stable"
	case healthScore >= 40:
		healthStatus = "at_risk"
	}

	previousStatus := "unknown"
	if currentHealth != nil {
		if st, ok := currentHealth["status"].(string); ok {
			previousStatus = st
		}
	}
	if currentHealth == nil || previousStatus != healthStatus {
		healthEvent := events.NewProjectHealthChanged()
		healthEvent.ProjectID = projectID
		healthEvent.OldHealthStatus = previousStatus
		healthEvent.NewHealthStatus = healthStatus
		healthEvent.HealthMetrics = map[string]any{"score": healthScore, "indicators": indicators, "issues": issues}
		uid := "system_health_check"
		healthEvent.UserID = &uid
		if h.EventStore != nil {
			_ = h.EventStore.Append(ctx, healthEvent)
		}
		h.handleProjectHealthChanged(ctx, healthEvent)
	}
}

func (h *ProjectEventHandlers) triggerHealthIntervention(ctx context.Context, event events.ProjectHealthChanged, score float64, issues []string) {
	if h.NotificationService != nil {
		urgency := "medium"
		if event.NewHealthStatus == "critical" {
			urgency = "high"
		}
		_ = h.NotificationService.SendHealthAlert(ctx, event.ProjectID, event.NewHealthStatus, score, issues, urgency)
	}
	suggestions := []string{}
	for _, issue := range issues {
		lower := strings.ToLower(issue)
		switch {
		case strings.Contains(lower, "completion rate"):
			suggestions = append(suggestions, "Consider reviewing task priorities and removing blockers")
		case strings.Contains(lower, "active tasks"):
			suggestions = append(suggestions, "Consider completing or postponing some active tasks")
		case strings.Contains(lower, "declining"):
			suggestions = append(suggestions, "Review recent changes and identify root causes")
		}
	}
	if len(suggestions) > 0 && h.NotificationService != nil {
		_ = h.NotificationService.SendHealthSuggestions(ctx, event.ProjectID, suggestions)
	}
}

// GetProjectStatistics returns statistics for one or all projects.
func (h *ProjectEventHandlers) GetProjectStatistics(ctx context.Context, projectID *string) map[string]any {
	h.mu.Lock()
	defer h.mu.Unlock()
	if projectID != nil {
		key := *projectID
		stats, _ := h.ProjectStats[key]
		health := h.HealthHistory[key]
		var current any
		if len(health) > 0 {
			current = health[len(health)-1]
		}
		if stats == nil {
			stats = map[string]any{}
		}
		tail := []map[string]any{}
		if len(health) > 0 {
			start := len(health) - 10
			if start < 0 {
				start = 0
			}
			tail = health[start:]
		}
		return map[string]any{
			"project_id": key, "statistics": stats, "current_health": current, "health_history": tail,
		}
	}

	active := map[string]map[string]any{}
	for k, v := range h.ProjectStats {
		archived, _ := v["archived"].(bool)
		if !archived {
			active[k] = v
		}
	}
	totalTasks, completedTasks := 0, 0
	rateSum := 0.0
	for _, p := range active {
		totalTasks += intOrZero(p["total_tasks"])
		completedTasks += intOrZero(p["completed_tasks"])
		if r, ok := p["completion_rate"].(float64); ok {
			rateSum += r
		}
	}
	avgRate := 0.0
	if len(active) > 0 {
		avgRate = rateSum / float64(len(active))
	}
	atRisk := 0
	for _, p := range h.HealthHistory {
		if len(p) > 0 {
			st, _ := p[len(p)-1]["status"].(string)
			if st == "at_risk" || st == "critical" {
				atRisk++
			}
		}
	}
	byProject := map[string]map[string]any{}
	for k, v := range active {
		byProject[k] = v
	}
	return map[string]any{
		"total_projects":    len(h.ProjectStats),
		"active_projects":   len(active),
		"archived_projects": len(h.ArchivedProjects),
		"summary": map[string]any{
			"total_tasks": totalTasks, "completed_tasks": completedTasks,
			"average_completion_rate": avgRate, "projects_at_risk": atRisk,
		},
		"by_project": byProject,
	}
}

// GetArchivedProjects returns all archived projects.
func (h *ProjectEventHandlers) GetArchivedProjects(ctx context.Context) map[string]any {
	h.mu.Lock()
	defer h.mu.Unlock()
	return map[string]any{"total_archived": len(h.ArchivedProjects), "projects": h.ArchivedProjects}
}

// ProcessEvent routes an event to the appropriate handler.
func (h *ProjectEventHandlers) ProcessEvent(ctx context.Context, event events.Event) {
	switch event.EventType() {
	case "ProjectCreatedEvent":
		h.HandleProjectCreated(ctx, event.(events.ProjectCreatedEvent))
	case "ProjectUpdatedEvent":
		h.HandleProjectUpdated(ctx, event.(events.ProjectUpdatedEvent))
	case "ProjectDeletedEvent":
		h.HandleProjectDeleted(ctx, event.(events.ProjectDeletedEvent))
	case "ProjectStatisticsUpdatedEvent":
		h.HandleProjectStatisticsUpdated(ctx, event.(events.ProjectStatisticsUpdatedEvent))
	case "ProjectHealthChanged":
		h.HandleProjectHealthChanged(ctx, event.(events.ProjectHealthChanged))
	case "ProjectArchived":
		h.HandleProjectArchived(ctx, event.(events.ProjectArchived))
	}
}

func derefOrEmpty(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func numberOrZero(v any) float64 {
	if f, ok := v.(float64); ok {
		return f
	}
	return 0
}

func intOrZero(v any) int {
	if i, ok := v.(int); ok {
		return i
	}
	return 0
}

func stringsOrEmpty(v any) []string {
	if s, ok := v.([]string); ok {
		return s
	}
	return []string{}
}

func pyFloat1(v float64) string { return strconv.FormatFloat(v, 'f', 1, 64) }

func pyPercent1(v float64) string { return strconv.FormatFloat(v*100, 'f', 1, 64) + "%" }

func pyInt(v float64) string { return strconv.Itoa(int(v)) }
