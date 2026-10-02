package services

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskContextRepositoryProtocol is the task context repository protocol. Get
// returns nil when the context does not exist.
type TaskContextRepositoryProtocol interface {
	Get(contextID string) (map[string]any, error)
}

// TaskCompletionService enforces task completion rules. Like Python, it remembers
// the detail of the last "incomplete subtasks" finding in instance state, and
// ValidateTaskCompletion reads that state even when a later failure has another
// cause (Python getattr/hasattr on private attributes).
type TaskCompletionService struct {
	subtaskRepository      repositories.SubtaskRepository
	taskContextRepository  TaskContextRepositoryProtocol
	incompleteSubtasks     []map[string]any
	hasIncompleteSubtasks  bool
	incompleteCount, total int
	hasTotal               bool
}

// NewTaskCompletionService builds the service; taskContextRepository may be nil.
func NewTaskCompletionService(s repositories.SubtaskRepository, c TaskContextRepositoryProtocol) *TaskCompletionService {
	return &TaskCompletionService{subtaskRepository: s, taskContextRepository: c}
}

const nilIDMessage = "'NoneType' object has no attribute 'value'"

func (s *TaskCompletionService) checkContext(task *entities.Task) error {
	if task.ContextID == nil && s.taskContextRepository != nil {
		if task.ID == nil {
			return fmt.Errorf("%s", nilIDMessage)
		}
		if _, err := s.taskContextRepository.Get(task.ID.Value); err != nil {
			return err
		}
	}
	return nil
}

func (s *TaskCompletionService) subtasksOf(ctx context.Context, task *entities.Task) ([]*entities.Subtask, error) {
	if task.ID == nil {
		return nil, fmt.Errorf("%s", nilIDMessage)
	}
	return s.subtaskRepository.FindByParentTaskID(ctx, *task.ID)
}

func incomplete(subtasks []*entities.Subtask) []*entities.Subtask {
	var out []*entities.Subtask
	for _, st := range subtasks {
		if !st.IsCompleted() {
			out = append(out, st)
		}
	}
	return out
}

// CanCompleteTask returns (ok, message); message is nil when ok.
func (s *TaskCompletionService) CanCompleteTask(ctx context.Context, task *entities.Task) (bool, *string) {
	fail := func(m string) (bool, *string) { return false, &m }
	if err := s.checkContext(task); err != nil {
		return fail("Internal error validating task completion: " + err.Error())
	}
	subtasks, err := s.subtasksOf(ctx, task)
	if err != nil {
		return fail("Internal error validating task completion: " + err.Error())
	}
	if len(subtasks) > 0 {
		inc := incomplete(subtasks)
		if len(inc) > 0 {
			details := make([]map[string]any, 0, len(inc))
			for _, st := range inc {
				id := ""
				if st.ID != nil {
					id = st.ID.Value
				}
				details = append(details, map[string]any{"id": id, "title": st.Title, "status": st.Status.Value})
			}
			s.incompleteSubtasks, s.hasIncompleteSubtasks = details, true
			s.incompleteCount, s.total, s.hasTotal = len(inc), len(subtasks), true
			return fail(fmt.Sprintf("Cannot complete task: %d of %d subtasks are not done", len(inc), len(subtasks)))
		}
	}
	return true, nil
}

// ValidateTaskCompletion returns a *exceptions.TaskCompletionError when the task
// cannot be completed.
func (s *TaskCompletionService) ValidateTaskCompletion(ctx context.Context, task *entities.Task) error {
	ok, msg := s.CanCompleteTask(ctx, task)
	if ok {
		return nil
	}
	m := "Task cannot be completed"
	if msg != nil && *msg != "" {
		m = *msg
	}
	var details []map[string]any
	if s.hasIncompleteSubtasks {
		details = s.incompleteSubtasks
	}
	e := exceptions.NewTaskCompletionError(m, details)
	if s.hasTotal {
		e.Context["total_count"] = s.total
	}
	return e
}

// GetCompletionBlockers lists the reasons a task cannot be completed.
func (s *TaskCompletionService) GetCompletionBlockers(ctx context.Context, task *entities.Task) []string {
	blockers := []string{}
	if err := s.checkContext(task); err != nil {
		return append(blockers, "Error checking completion status: "+err.Error())
	}
	subtasks, err := s.subtasksOf(ctx, task)
	if err != nil {
		return append(blockers, "Error checking completion status: "+err.Error())
	}
	if len(subtasks) > 0 {
		inc := incomplete(subtasks)
		if len(inc) > 0 {
			msg := fmt.Sprintf("%d of %d subtasks are incomplete", len(inc), len(subtasks))
			var titles []string
			for i, st := range inc {
				if i == 3 {
					break
				}
				titles = append(titles, st.Title)
			}
			msg += " (including: "
			if len(titles) < len(inc) {
				msg += fmt.Sprintf("%s, and %d more", strings.Join(titles, ", "), len(inc)-len(titles))
			} else {
				msg += strings.Join(titles, ", ")
			}
			msg += ")"
			msg += ". Complete all subtasks first."
			blockers = append(blockers, msg)
		}
	}
	return blockers
}

func (s *TaskCompletionService) createContextRequiredError(task *entities.Task) map[string]any {
	id := task.ID.Value
	return map[string]any{
		"error":       "Task completion requires context to be created first.",
		"explanation": "Context stores task progress with inheritance from branch, project and global contexts. This ensures work history is preserved with proper organizational structure.",
		"recovery_instructions": []string{
			"Create context for this task first",
			"Update the context with your progress",
			"Then try completing the task again",
		},
		"step_by_step_fix": []map[string]any{
			{"step": 1, "action": "Create context", "command": fmt.Sprintf("manage_context(action='create', level='task', context_id='%s', data={'title': '%s', 'description': 'Task context'})", id, task.Title)},
			{"step": 2, "action": "Update context status", "command": fmt.Sprintf("manage_context(action='update', level='task', context_id='%s', data={'status': 'done'})", id)},
			{"step": 3, "action": "Complete task", "command": fmt.Sprintf("manage_task(action='complete', task_id='%s', completion_summary='Your summary here')", id)},
		},
	}
}

func (s *TaskCompletionService) createIncompleteSubtasksError(ctx context.Context, task *entities.Task, inc []*entities.Subtask) (map[string]any, error) {
	all, err := s.subtasksOf(ctx, task)
	if err != nil {
		return nil, err
	}
	titles := []string{}
	for i, st := range inc {
		if i == 3 {
			break
		}
		titles = append(titles, st.Title)
	}
	id := task.ID.Value
	return map[string]any{
		"error":       "Cannot complete task while subtasks remain incomplete.",
		"explanation": "All subtasks must be completed before the parent task can be marked as done.",
		"details": map[string]any{
			"incomplete_count": len(inc), "total_subtasks": len(all), "incomplete_subtask_titles": titles,
		},
		"recovery_instructions": []string{
			"List all subtasks to see which are incomplete",
			"Complete each remaining subtask",
			"Then try completing the parent task again",
		},
		"step_by_step_fix": []map[string]any{
			{"step": 1, "action": "List subtasks", "command": fmt.Sprintf("manage_subtask(action='list', task_id='%s')", id)},
			{"step": 2, "action": "Complete each incomplete subtask", "command": fmt.Sprintf("manage_subtask(action='complete', task_id='%s', subtask_id='subtask-id', completion_summary='Subtask completed')", id)},
			{"step": 3, "action": "Complete parent task", "command": fmt.Sprintf("manage_task(action='complete', task_id='%s', completion_summary='All subtasks completed')", id)},
		},
	}, nil
}

// GetSubtaskCompletionSummary returns total/completed/incomplete counts. With no
// subtasks the percentage is the int 100; otherwise a float rounded to 1 digit.
func (s *TaskCompletionService) GetSubtaskCompletionSummary(ctx context.Context, task *entities.Task) map[string]any {
	subtasks, err := s.subtasksOf(ctx, task)
	if err != nil {
		return map[string]any{"total": 0, "completed": 0, "incomplete": 0, "completion_percentage": 0,
			"can_complete_parent": false, "error": err.Error()}
	}
	if len(subtasks) == 0 {
		return map[string]any{"total": 0, "completed": 0, "incomplete": 0, "completion_percentage": 100, "can_complete_parent": true}
	}
	total := len(subtasks)
	completed := 0
	for _, st := range subtasks {
		if st.IsCompleted() {
			completed++
		}
	}
	return map[string]any{
		"total": total, "completed": completed, "incomplete": total - completed,
		"completion_percentage": value_objects.PyRound(float64(completed)/float64(total)*100, 1),
		"can_complete_parent":   total-completed == 0,
	}
}
