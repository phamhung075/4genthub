package services

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TransitionContext is the context of a state transition.
type TransitionContext string

const (
	TransitionUserInitiated       TransitionContext = "user_initiated"
	TransitionSystemInitiated     TransitionContext = "system_initiated"
	TransitionDependencyTriggered TransitionContext = "dependency_triggered"
	TransitionCompletionTriggered TransitionContext = "completion_triggered"
)

// TransitionSubtaskRepository is SubtaskRepositoryProtocol. taskID is nil for a task
// without an ID (Python passes None through).
type TransitionSubtaskRepository interface {
	FindByParentTaskID(ctx context.Context, taskID *value_objects.TaskId) ([]*entities.Subtask, error)
}

// TransitionTaskRepository is TaskRepositoryProtocol.
type TransitionTaskRepository interface {
	FindAll(ctx context.Context) ([]*entities.Task, error)
}

// TaskStateTransitionService manages task state transitions and enforces business rules.
// Both repositories are optional (nil).
type TaskStateTransitionService struct {
	subtaskRepository TransitionSubtaskRepository
	taskRepository    TransitionTaskRepository
	transitionRules   map[string][]string
}

func NewTaskStateTransitionService(s TransitionSubtaskRepository, t TransitionTaskRepository) *TaskStateTransitionService {
	return &TaskStateTransitionService{subtaskRepository: s, taskRepository: t, transitionRules: map[string][]string{
		"todo":        {"in_progress", "blocked", "cancelled"},
		"in_progress": {"review", "testing", "done", "blocked", "todo"},
		"review":      {"in_progress", "testing", "done", "blocked"},
		"testing":     {"review", "done", "in_progress", "blocked"},
		"blocked":     {"todo", "in_progress", "cancelled"},
		"done":        {"in_progress"},
		"cancelled":   {},
	}}
}

func lowerStatus(t *entities.Task) string { return value_objects.PyLower(statusStr(t)) }

// CanTransitionTo returns (allowed, reason); failures become a reason string.
func (s *TaskStateTransitionService) CanTransitionTo(ctx context.Context, task *entities.Task,
	target value_objects.TaskStatus, tctx TransitionContext) (bool, string) {
	current := lowerStatus(task)
	targetStr := value_objects.PyLower(target.String())
	allowed := false
	for _, a := range s.transitionRules[current] {
		if a == targetStr {
			allowed = true
		}
	}
	if !allowed {
		return false, fmt.Sprintf("Cannot transition from '%s' to '%s'", current, targetStr)
	}
	ok, reason, err := s.checkTransitionPrerequisites(ctx, task, target)
	if err != nil {
		return false, "Transition validation error: " + err.Error()
	}
	if !ok {
		return false, reason
	}
	return true, ""
}

// TransitionTo performs a state transition on a task.
func (s *TaskStateTransitionService) TransitionTo(ctx context.Context, task *entities.Task,
	target value_objects.TaskStatus, tctx TransitionContext) (bool, string) {
	if ok, reason := s.CanTransitionTo(ctx, task, target, tctx); !ok {
		return false, reason
	}
	old := statusStr(task)
	if err := task.UpdateStatus(target); err != nil {
		return false, "Transition failed: " + err.Error()
	}
	if value_objects.PyLower(target.String()) == "done" && s.taskRepository != nil {
		s.HandleDependencyCompletion(ctx, task)
	}
	return true, fmt.Sprintf("Status changed from '%s' to '%s'", old, target)
}

// TransitionInfo is one entry of get_allowed_transitions.
type TransitionInfo struct {
	Allowed       bool
	Reason        *string
	Description   string
	Prerequisites []string
}

// GetAllowedTransitions lists allowed transitions in rule order.
func (s *TaskStateTransitionService) GetAllowedTransitions(ctx context.Context, task *entities.Task) *entities.OrderedMap[TransitionInfo] {
	result := entities.NewOrderedMap[TransitionInfo]()
	current := lowerStatus(task)
	for _, target := range s.transitionRules[current] {
		obj, err := value_objects.NewTaskStatus(target)
		if err != nil {
			return entities.NewOrderedMap[TransitionInfo]()
		}
		ok, reason := s.CanTransitionTo(ctx, task, obj, TransitionUserInitiated)
		info := TransitionInfo{Allowed: ok, Description: transitionDescription(current, target),
			Prerequisites: transitionPrerequisites(current, target)}
		if reason != "" {
			r := reason
			info.Reason = &r
		}
		result.Set(target, info)
	}
	return result
}

var progressionPaths = map[string]string{
	"todo": "in_progress", "in_progress": "review", "review": "testing", "testing": "done", "blocked": "todo",
}

// SuggestNextStatus suggests the next logical status, or nil.
func (s *TaskStateTransitionService) SuggestNextStatus(ctx context.Context, task *entities.Task) map[string]any {
	current := lowerStatus(task)
	suggested, ok := progressionPaths[current]
	if !ok {
		return nil
	}
	obj, err := value_objects.NewTaskStatus(suggested)
	if err != nil {
		return nil
	}
	can, reason := s.CanTransitionTo(ctx, task, obj, TransitionUserInitiated)
	if can {
		return map[string]any{"suggested_status": suggested, "current_status": current,
			"reason":      fmt.Sprintf("Natural progression from '%s' to '%s'", current, suggested),
			"description": transitionDescription(current, suggested)}
	}
	return map[string]any{"suggested_status": suggested, "current_status": current, "blocked": true,
		"blocked_reason": reason, "alternative_suggestions": alternativeSuggestions(current)}
}

// HandleDependencyCompletion unblocks tasks whose dependencies are all done.
// Any repository error yields an empty list (Python catches and logs).
func (s *TaskStateTransitionService) HandleDependencyCompletion(ctx context.Context, completed *entities.Task) []map[string]any {
	updated := []map[string]any{}
	if s.taskRepository == nil {
		return updated
	}
	all, err := s.taskRepository.FindAll(ctx)
	if err != nil {
		return []map[string]any{}
	}
	completedID := taskIDStr(completed)
	for _, dep := range findDependentTasks(completedID, all) {
		if lowerStatus(dep) != "blocked" || !allDependenciesSatisfied(dep, all) {
			continue
		}
		todo, err := value_objects.NewTaskStatus("todo")
		if err != nil {
			return []map[string]any{}
		}
		if ok, _ := s.TransitionTo(ctx, dep, todo, TransitionDependencyTriggered); ok {
			updated = append(updated, map[string]any{"task_id": taskIDStr(dep), "title": dep.Title,
				"old_status": "blocked", "new_status": "todo",
				"reason": fmt.Sprintf("Unblocked by completion of task %s", completedID)})
		}
	}
	return updated
}

func (s *TaskStateTransitionService) checkTransitionPrerequisites(ctx context.Context, task *entities.Task,
	target value_objects.TaskStatus) (bool, string, error) {
	targetStr := value_objects.PyLower(target.String())
	if targetStr == "done" && s.subtaskRepository != nil {
		subtasks, err := s.subtaskRepository.FindByParentTaskID(ctx, task.ID)
		if err != nil {
			return false, "", err
		}
		incomplete := 0
		for _, st := range subtasks {
			if !st.IsCompleted() {
				incomplete++
			}
		}
		if incomplete > 0 {
			return false, fmt.Sprintf("Cannot complete task: %d subtasks are still incomplete", incomplete), nil
		}
	}
	if targetStr == "review" && lowerStatus(task) != "in_progress" {
		return false, "Task must be in progress before moving to review", nil
	}
	return true, "", nil
}

func findDependentTasks(completedID string, all []*entities.Task) []*entities.Task {
	var out []*entities.Task
	for _, t := range all {
		for _, d := range t.Dependencies {
			if d.Value == completedID {
				out = append(out, t)
				break
			}
		}
	}
	return out
}

func allDependenciesSatisfied(task *entities.Task, all []*entities.Task) bool {
	for _, d := range task.Dependencies {
		satisfied := false
		for _, other := range all {
			if taskIDStr(other) == d.Value {
				satisfied = other.Status != nil && other.Status.IsDone()
				break
			}
		}
		if !satisfied {
			return false
		}
	}
	return true
}

func transitionDescription(from, to string) string {
	switch from + ">" + to {
	case "todo>in_progress":
		return "Start working on this task"
	case "in_progress>review":
		return "Submit work for review"
	case "review>testing":
		return "Move to testing phase"
	case "testing>done":
		return "Mark as completed"
	case "blocked>todo":
		return "Unblock and return to todo"
	case "in_progress>blocked":
		return "Block due to impediment"
	}
	return fmt.Sprintf("Change status from %s to %s", from, to)
}

func transitionPrerequisites(from, to string) []string {
	switch from + ">" + to {
	case "todo>in_progress":
		return []string{"Task assignee available", "Dependencies satisfied"}
	case "in_progress>review":
		return []string{"Work completed", "Ready for review"}
	case "review>testing":
		return []string{"Review passed", "Code approved"}
	case "testing>done":
		return []string{"Tests passed", "All subtasks completed"}
	case "blocked>todo":
		return []string{"Blocking issues resolved"}
	}
	return []string{}
}

func alternativeSuggestions(current string) []string {
	switch current {
	case "todo":
		return []string{"blocked"}
	case "in_progress":
		return []string{"blocked", "todo"}
	case "review":
		return []string{"in_progress"}
	case "testing":
		return []string{"review", "in_progress"}
	case "blocked":
		return []string{"cancelled"}
	}
	return []string{}
}
