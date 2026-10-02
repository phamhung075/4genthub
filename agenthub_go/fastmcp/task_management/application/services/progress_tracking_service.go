package services

// ProgressTrackingService ports
// task_management/application/services/progress_tracking_service.py.
//
// Porting notes (Python behaviour that the Go domain types cannot reproduce
// literally):
//   - The Python service mutates `context.progress` as if it were a list of
//     dicts, but the TaskContext entity stores `progress` as a ContextProgress
//     dataclass (no `.append`), so in Python that branch always raises
//     AttributeError and is swallowed. Here the progress entry is appended to
//     TaskContext.ProgressTimeline, the only list-of-dicts progress field.
//   - `infer_progress_from_context` reads `context.insights` and
//     `context.progress` (neither exists on the Python TaskContext). Here the
//     closest fields are used: Notes.AgentInsights for insights and
//     Progress.CompletedActions.Details for progress entries.
//   - Task.Subtasks is []string (IDs) in Go rather than a list of dicts, so the
//     subtask aggregation fallback has no per-subtask dict to read from.

import (
	"context"
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure"
)

// ProgressTrackingService tracks and manages task progress.
type ProgressTrackingService struct {
	TaskRepository    repositories.TaskRepository
	ContextRepository repositories.ContextRepository
	EventBus          *infrastructure.EventBus
	UserID            *string

	StallThresholdHours   float64
	AutoCalculateInterval int
}

// NewProgressTrackingService mirrors
// __init__(task_repository, context_repository, event_bus=None, user_id=None).
func NewProgressTrackingService(
	taskRepository repositories.TaskRepository,
	contextRepository repositories.ContextRepository,
	eventBus *infrastructure.EventBus,
	userID *string,
) *ProgressTrackingService {
	if eventBus == nil {
		eventBus = infrastructure.GetEventBus()
	}
	return &ProgressTrackingService{
		TaskRepository:        taskRepository,
		ContextRepository:     contextRepository,
		EventBus:              eventBus,
		UserID:                userID,
		StallThresholdHours:   24,
		AutoCalculateInterval: 300,
	}
}

// WithUser creates a new service instance scoped to a specific user.
func (s *ProgressTrackingService) WithUser(userID string) *ProgressTrackingService {
	return NewProgressTrackingService(s.TaskRepository, s.ContextRepository, s.EventBus, &userID)
}

// zpPtsGetUserScopedRepository is _get_user_scoped_repository.
func (s *ProgressTrackingService) zpPtsGetUserScopedRepository(repository any) any {
	return serviceUserScopedRepository(repository, s.UserID)
}

func (s *ProgressTrackingService) zpPtsUserScopedTaskRepository() repositories.TaskRepository {
	if r, ok := s.zpPtsGetUserScopedRepository(s.TaskRepository).(repositories.TaskRepository); ok {
		return r
	}
	return s.TaskRepository
}

// UpdateProgress updates progress for a specific task and progress type.
func (s *ProgressTrackingService) UpdateProgress(
	ctx context.Context,
	taskID string,
	progressType value_objects.ProgressType,
	percentage float64,
	description *string,
	metadata map[string]any,
	agentID *string,
) (*entities.Task, error) {
	taskRepo := s.zpPtsUserScopedTaskRepository()
	task, err := zpPtsFetchTask(ctx, taskRepo, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}

	if err := task.UpdateProgress(entities.ProgressUpdate{
		Type: progressType, Percentage: percentage, Description: description, Metadata: metadata, AgentID: agentID,
	}); err != nil {
		return nil, err
	}

	s.zpPtsUpdateContextProgress(ctx, task, progressType, percentage, description)
	s.zpPtsCheckStalledProgress(ctx, task)

	if _, err := s.TaskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	for _, event := range task.GetEvents() {
		s.EventBus.Publish(event)
	}

	if len(task.Subtasks) > 0 {
		s.zpPtsAggregateSubtaskProgress(ctx, task)
	}

	return task, nil
}

// zpPtsUpdateArgs is one parsed batch-update mapping.
type zpPtsUpdateArgs struct {
	TaskID       string
	ProgressType value_objects.ProgressType
	Percentage   float64
	Description  *string
	Metadata     map[string]any
	AgentID      *string
}

// BatchUpdateProgress updates progress for multiple tasks in batch. Failures are
// skipped, exactly like the Python try/except inside the loop.
func (s *ProgressTrackingService) BatchUpdateProgress(ctx context.Context, updates []map[string]any) []*entities.Task {
	updatedTasks := []*entities.Task{}
	for _, update := range updates {
		args, ok := zpPtsParseUpdate(update)
		if !ok {
			continue
		}
		task, err := s.UpdateProgress(ctx, args.TaskID, args.ProgressType, args.Percentage, args.Description, args.Metadata, args.AgentID)
		if err != nil {
			continue
		}
		updatedTasks = append(updatedTasks, task)
	}
	return updatedTasks
}

// CalculateOverallProgress calculates overall progress for a task.
func (s *ProgressTrackingService) CalculateOverallProgress(
	ctx context.Context,
	taskID string,
	includeSubtasks bool,
	weights map[string]float64,
) (float64, error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return 0, err
	}
	if task == nil {
		return 0, value_objects.ValueErrorf("Task %s not found", taskID)
	}

	values := []value_objects.KeyedProgress{}

	if task.ProgressTimeline != nil {
		for _, progressType := range value_objects.ProgressTypeValues {
			typeProgress := task.GetProgressByType(progressType)
			if typeProgress > 0 {
				values = append(values, value_objects.KeyedProgress{Key: string(progressType), Value: typeProgress})
			}
		}
	}

	if includeSubtasks && len(task.Subtasks) > 0 {
		values = append(values, value_objects.KeyedProgress{Key: "subtasks", Value: task.CalculateProgressFromSubtasks(false)})
	}

	if len(values) == 0 {
		return 0.0, nil
	}

	return value_objects.ProgressCalculationStrategy{}.CalculateWeightedAverage(values, weights), nil
}

// GetProgressTimeline gets the progress timeline for a task.
func (s *ProgressTrackingService) GetProgressTimeline(
	ctx context.Context,
	taskID string,
	hours int,
	progressType *value_objects.ProgressType,
) ([]value_objects.ProgressSnapshot, error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}
	if task.ProgressTimeline == nil {
		return []value_objects.ProgressSnapshot{}, nil
	}

	if progressType != nil {
		snapshots := task.ProgressTimeline.GetSnapshotsByType(*progressType)
		cutoff := time.Now().UTC().Add(-time.Duration(hours) * time.Hour)
		out := []value_objects.ProgressSnapshot{}
		for _, snapshot := range snapshots {
			if snapshot.Timestamp.After(cutoff) {
				out = append(out, snapshot)
			}
		}
		return out, nil
	}
	return task.ProgressTimeline.GetProgressTrend(hours), nil
}

// SetProgressMilestone sets a progress milestone for a task.
func (s *ProgressTrackingService) SetProgressMilestone(ctx context.Context, taskID, milestoneName string, percentage float64) (*entities.Task, error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}

	if err := task.AddProgressMilestone(milestoneName, percentage); err != nil {
		return nil, err
	}

	if _, err := s.TaskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	return task, nil
}

// CheckMilestones checks which milestones have been reached for a task.
func (s *ProgressTrackingService) CheckMilestones(ctx context.Context, taskID string) ([]string, error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}
	if task.ProgressTimeline == nil {
		return []string{}, nil
	}

	reachedMilestones := []string{}
	for _, name := range zpPtsMilestoneOrder(task.ProgressTimeline) {
		if task.ProgressTimeline.IsMilestoneReached(name) {
			reachedMilestones = append(reachedMilestones, name)
		}
	}

	return reachedMilestones, nil
}

// GetProgressSummary returns the comprehensive progress summary for a task.
func (s *ProgressTrackingService) GetProgressSummary(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}

	summary := entities.NewOrderedMap[any]()
	summary.Set("task_id", taskID)
	summary.Set("overall_progress", zpPtsOverallProgressValue(task))
	progressByType := entities.NewOrderedMap[any]()
	summary.Set("progress_by_type", progressByType)
	var subtaskProgress any
	if len(task.Subtasks) > 0 {
		subtaskProgress = task.GetSubtaskProgress()
	}
	summary.Set("subtask_progress", subtaskProgress)
	milestones := entities.NewOrderedMap[any]()
	summary.Set("milestones", milestones)
	summary.Set("recent_updates", []any{})
	summary.Set("is_stalled", false)
	summary.Set("blockers", []any{})

	if task.ProgressTimeline != nil {
		for _, progressType := range value_objects.ProgressTypeValues {
			progress := task.GetProgressByType(progressType)
			if progress > 0 {
				progressByType.Set(string(progressType), progress)
			}
		}

		for _, name := range zpPtsMilestoneOrder(task.ProgressTimeline) {
			entry := entities.NewOrderedMap[any]()
			entry.Set("target", task.ProgressTimeline.Milestones[name])
			entry.Set("reached", task.ProgressTimeline.IsMilestoneReached(name))
			milestones.Set(name, entry)
		}

		recentSnapshots := task.ProgressTimeline.GetProgressTrend(24)
		start := 0
		if len(recentSnapshots) > 5 {
			start = len(recentSnapshots) - 5
		}
		recentUpdates := make([]any, 0, len(recentSnapshots)-start)
		for _, snapshot := range recentSnapshots[start:] {
			recentUpdates = append(recentUpdates, snapshot.ToDict())
		}
		summary.Set("recent_updates", recentUpdates)

		if len(recentSnapshots) > 0 {
			lastUpdate := recentSnapshots[len(recentSnapshots)-1].Timestamp
			hoursSinceUpdate := value_objects.PyTotalSeconds(time.Now().UTC().Sub(lastUpdate)) / 3600
			summary.Set("is_stalled", hoursSinceUpdate > s.StallThresholdHours)
		}

		if latest, ok := task.ProgressTimeline.GetLatestSnapshot(); ok {
			summary.Set("blockers", zpPtsNonNilStrings(latest.Metadata.Blockers))
		}
	}

	return summary, nil
}

// InferProgressFromContext infers progress based on context updates and insights.
func (s *ProgressTrackingService) InferProgressFromContext(ctx context.Context, taskID string) (*float64, error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil || task.ContextID == nil {
		return nil, nil
	}

	contextData, err := s.ContextRepository.GetContext(ctx, *task.ContextID)
	if err != nil {
		return nil, err
	}
	if contextData == nil {
		return nil, nil
	}

	recentText := ""
	if len(contextData.Notes.AgentInsights) > 0 {
		insights := contextData.Notes.AgentInsights
		start := 0
		if len(insights) > 5 {
			start = len(insights) - 5
		}
		parts := make([]string, 0, len(insights)-start)
		for _, insight := range insights[start:] {
			parts = append(parts, insight.Content)
		}
		recentText += strings.Join(parts, " ")
	}
	if len(contextData.Progress.CompletedActions) > 0 {
		actions := contextData.Progress.CompletedActions
		start := 0
		if len(actions) > 5 {
			start = len(actions) - 5
		}
		parts := make([]string, 0, len(actions)-start)
		for _, action := range actions[start:] {
			parts = append(parts, action.Details)
		}
		recentText += strings.Join(parts, " ")
	}

	recentText = value_objects.PyLower(recentText)

	if zpPtsContainsAny(recentText, []string{"completed", "finished", "done", "accomplished"}) {
		return zpPtsFloatPtr(100.0), nil
	} else if zpPtsContainsAny(recentText, []string{"almost done", "nearly finished", "finalizing"}) {
		return zpPtsFloatPtr(85.0), nil
	} else if zpPtsContainsAny(recentText, []string{"testing", "verifying", "validating", "checking"}) {
		return zpPtsFloatPtr(70.0), nil
	} else if zpPtsContainsAny(recentText, []string{"working on", "implementing", "developing", "coding"}) {
		return zpPtsFloatPtr(50.0), nil
	} else if zpPtsContainsAny(recentText, []string{"began", "started", "initiated", "commenced"}) {
		return zpPtsFloatPtr(25.0), nil
	}

	return nil, nil
}

// SuggestProgressUpdate suggests a progress update based on task analysis.
func (s *ProgressTrackingService) SuggestProgressUpdate(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	task, err := zpPtsFetchTask(ctx, s.TaskRepository, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}

	suggestion := entities.NewOrderedMap[any]()
	suggestion.Set("task_id", taskID)
	suggestedUpdates := []any{}
	suggestion.Set("suggested_updates", suggestedUpdates)

	taskContent := value_objects.PyLower(task.Title + " " + task.Description)

	if strings.Contains(taskContent, "design") || strings.Contains(taskContent, "architect") {
		suggestedUpdates = append(suggestedUpdates, zpPtsSuggestedUpdate(value_objects.ProgressTypeDesign, 0.0, "Start design phase"))
	}

	if strings.Contains(taskContent, "implement") || strings.Contains(taskContent, "develop") || strings.Contains(taskContent, "code") {
		suggestedUpdates = append(suggestedUpdates, zpPtsSuggestedUpdate(value_objects.ProgressTypeImplementation, 0.0, "Begin implementation"))
	}

	if strings.Contains(taskContent, "test") || strings.Contains(taskContent, "verify") {
		suggestedUpdates = append(suggestedUpdates, zpPtsSuggestedUpdate(value_objects.ProgressTypeTesting, 0.0, "Start testing phase"))
	}

	if strings.Contains(taskContent, "document") || strings.Contains(taskContent, "readme") {
		suggestedUpdates = append(suggestedUpdates, zpPtsSuggestedUpdate(value_objects.ProgressTypeDocumentation, 0.0, "Begin documentation"))
	}

	if len(suggestedUpdates) == 0 {
		suggestedUpdates = append(suggestedUpdates, zpPtsSuggestedUpdate(value_objects.ProgressTypeGeneral, 0.0, "Start task"))
	}

	suggestion.Set("suggested_updates", suggestedUpdates)

	inferredProgress, err := s.InferProgressFromContext(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if inferredProgress != nil {
		suggestion.Set("inferred_progress", *inferredProgress)
	}

	return suggestion, nil
}

// zpPtsUpdateContextProgress updates the context with progress information.
func (s *ProgressTrackingService) zpPtsUpdateContextProgress(
	ctx context.Context,
	task *entities.Task,
	progressType value_objects.ProgressType,
	percentage float64,
	description *string,
) {
	if task.ContextID == nil {
		return
	}

	contextData, err := s.ContextRepository.GetContext(ctx, *task.ContextID)
	if err != nil || contextData == nil {
		return
	}

	entryDescription := ""
	if description != nil && *description != "" {
		entryDescription = *description
	} else {
		entryDescription = fmt.Sprintf("Updated %s progress to %s%%", string(progressType), value_objects.PyStr(percentage))
	}

	progressEntry := map[string]any{
		"timestamp":   value_objects.IsoFormat(time.Now().UTC()),
		"type":        string(progressType),
		"percentage":  percentage,
		"description": entryDescription,
	}
	contextData.ProgressTimeline = append(contextData.ProgressTimeline, progressEntry)

	_, _ = s.ContextRepository.UpdateContext(ctx, contextData)
}

// zpPtsCheckStalledProgress checks if task progress has stalled.
func (s *ProgressTrackingService) zpPtsCheckStalledProgress(ctx context.Context, task *entities.Task) {
	if task.ProgressTimeline == nil {
		return
	}

	latest, ok := task.ProgressTimeline.GetLatestSnapshot()
	if !ok {
		return
	}

	hoursSinceUpdate := value_objects.PyTotalSeconds(time.Now().UTC().Sub(latest.Timestamp)) / 3600

	if hoursSinceUpdate > s.StallThresholdHours && latest.Percentage < 100 {
		stalledEvent := events.NewProgressStalled()
		stalledEvent.TaskID = zpPtsTaskID(task)
		stalledEvent.LastUpdateTimestamp = latest.Timestamp
		stalledEvent.StallDurationHours = hoursSinceUpdate
		stalledEvent.CurrentPercentage = latest.Percentage
		stalledEvent.Blockers = zpPtsNonNilStrings(latest.Metadata.Blockers)
		s.EventBus.Publish(stalledEvent)
	}
}

// zpPtsAggregateSubtaskProgress aggregates progress from subtasks to the parent.
func (s *ProgressTrackingService) zpPtsAggregateSubtaskProgress(ctx context.Context, parentTask *entities.Task) {
	if len(parentTask.Subtasks) == 0 {
		return
	}

	oldProgress := parentTask.OverallProgress

	subtaskDetails := []map[string]any{}
	for _, subtaskID := range parentTask.Subtasks {
		if subtaskID == "" {
			continue
		}
		subtaskEntity, err := zpPtsFetchTask(ctx, s.TaskRepository, subtaskID)
		if err != nil {
			// Fallback to the (ID-only) subtask data.
			subtaskDetails = append(subtaskDetails, map[string]any{
				"id": subtaskID, "title": "", "progress": 0.0, "status": "todo",
			})
		} else if subtaskEntity != nil {
			status := "todo"
			if subtaskEntity.Status != nil {
				status = subtaskEntity.Status.Value
			}
			subtaskDetails = append(subtaskDetails, map[string]any{
				"id": subtaskID, "title": subtaskEntity.Title, "progress": subtaskEntity.OverallProgress, "status": status,
			})
		}
	}

	newProgress := value_objects.ProgressCalculationStrategy{}.CalculateFromSubtasks(subtaskDetails, false)

	if math.Abs(newProgress-oldProgress) > 0.1 {
		event := events.NewSubtaskProgressAggregated()
		event.TaskID = zpPtsTaskID(parentTask)
		event.ParentTaskID = zpPtsTaskID(parentTask)
		event.SubtaskCount = len(subtaskDetails)
		event.OldParentProgress = oldProgress
		event.NewParentProgress = newProgress
		event.SubtaskProgressDetails = subtaskDetails
		s.EventBus.Publish(event)
	}
}

// zpPtsFetchTask converts the id and fetches the task.
func zpPtsFetchTask(ctx context.Context, repo repositories.TaskRepository, taskID string) (*entities.Task, error) {
	domainTaskID, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil, err
	}
	return repo.FindByID(ctx, domainTaskID)
}

// zpPtsParseUpdate mirrors Python's `update_progress(**update)`: unknown keys,
// missing required keys or untyped values are a TypeError and drop the update.
func zpPtsParseUpdate(update map[string]any) (zpPtsUpdateArgs, bool) {
	var args zpPtsUpdateArgs

	allowed := map[string]struct{}{
		"task_id": {}, "progress_type": {}, "percentage": {},
		"description": {}, "metadata": {}, "agent_id": {},
	}
	for key := range update {
		if _, ok := allowed[key]; !ok {
			return args, false
		}
	}

	taskID, ok := update["task_id"].(string)
	if !ok {
		return args, false
	}
	progressType, ok := zpPtsProgressTypeValue(update["progress_type"])
	if !ok {
		return args, false
	}
	percentage, ok := value_objects.PyFloat(update["percentage"])
	if !ok {
		return args, false
	}
	description, ok := zpPtsOptionalString(update, "description")
	if !ok {
		return args, false
	}
	agentID, ok := zpPtsOptionalString(update, "agent_id")
	if !ok {
		return args, false
	}
	var metadata map[string]any
	if value, present := update["metadata"]; present && value != nil {
		m, ok := value.(map[string]any)
		if !ok {
			return args, false
		}
		metadata = m
	}

	args = zpPtsUpdateArgs{
		TaskID: taskID, ProgressType: progressType, Percentage: percentage,
		Description: description, Metadata: metadata, AgentID: agentID,
	}
	return args, true
}

func zpPtsProgressTypeValue(value any) (value_objects.ProgressType, bool) {
	switch v := value.(type) {
	case value_objects.ProgressType:
		for _, candidate := range value_objects.ProgressTypeValues {
			if candidate == v {
				return v, true
			}
		}
	case string:
		for _, candidate := range value_objects.ProgressTypeValues {
			if string(candidate) == v {
				return candidate, true
			}
		}
	}
	return "", false
}

func zpPtsOptionalString(update map[string]any, key string) (*string, bool) {
	value, present := update[key]
	if !present || value == nil {
		return nil, true
	}
	s, ok := value.(string)
	if !ok {
		return nil, false
	}
	return &s, true
}

func zpPtsSuggestedUpdate(progressType value_objects.ProgressType, percentage float64, description string) *entities.OrderedMap[any] {
	update := entities.NewOrderedMap[any]()
	update.Set("progress_type", progressType)
	update.Set("percentage", percentage)
	update.Set("description", description)
	return update
}

// zpPtsOverallProgressValue mirrors Python's dynamic overall_progress (int until a
// timeline recalculation turns it into a float).
func zpPtsOverallProgressValue(task *entities.Task) any {
	if task.OverallProgressIsFloat {
		return task.OverallProgress
	}
	return int(task.OverallProgress)
}

// zpPtsTaskID is Python's `task.id` as the event string field.
func zpPtsTaskID(task *entities.Task) string {
	if task.ID == nil {
		return "None"
	}
	return task.ID.String()
}

func zpPtsNonNilStrings(values []string) []string {
	if values == nil {
		return []string{}
	}
	return values
}

// zpPtsMilestoneOrder returns milestone names in Python dict insertion order.
func zpPtsMilestoneOrder(timeline *value_objects.ProgressTimeline) []string {
	if len(timeline.MilestoneOrder) > 0 {
		return timeline.MilestoneOrder
	}
	names := make([]string, 0, len(timeline.Milestones))
	for name := range timeline.Milestones {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func zpPtsContainsAny(text string, words []string) bool {
	for _, word := range words {
		if strings.Contains(text, word) {
			return true
		}
	}
	return false
}

func zpPtsFloatPtr(value float64) *float64 { return &value }
