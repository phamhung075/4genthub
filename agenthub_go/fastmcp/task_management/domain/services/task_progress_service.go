package services

import (
	"context"
	"fmt"
	"math/big"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskRepositoryProtocol is the subtask repository protocol used by the service.
type SubtaskRepositoryProtocol interface {
	FindByParentTaskID(ctx context.Context, taskID value_objects.TaskId) ([]*entities.Subtask, error)
}

// TaskProgressService centralizes task progress calculations. The repository is
// optional (nil = absent). Like Python, calculation failures are folded into
// error-shaped results rather than returned.
type TaskProgressService struct {
	subtaskRepository SubtaskRepositoryProtocol
}

// NewTaskProgressService builds the service; subtaskRepository may be nil.
func NewTaskProgressService(r SubtaskRepositoryProtocol) *TaskProgressService {
	return &TaskProgressService{r}
}

func taskIDStr(t *entities.Task) string {
	if t.ID == nil {
		return "None"
	}
	return t.ID.Value
}

func statusStr(t *entities.Task) string {
	if t.Status == nil {
		return "None"
	}
	return t.Status.Value
}

// subtasksOf loads subtasks; a nil task ID reproduces Python's AttributeError-free
// path (find_by_parent_task_id(None)) as a repository error.
func (s *TaskProgressService) subtasksOf(ctx context.Context, t *entities.Task) ([]*entities.Subtask, error) {
	if t.ID == nil {
		return nil, fmt.Errorf("parent task id is None")
	}
	return s.subtaskRepository.FindByParentTaskID(ctx, *t.ID)
}

// CalculateTaskProgress returns the comprehensive progress dictionary.
func (s *TaskProgressService) CalculateTaskProgress(ctx context.Context, task *entities.Task) map[string]any {
	base := s.calculateBaseTaskProgress(task)
	var subtask map[string]any
	if s.subtaskRepository != nil {
		subtask = s.GetSubtaskSummary(ctx, task)
	}
	overall := calculateOverallProgress(base, subtask)
	return map[string]any{
		"task_id":          taskIDStr(task),
		"base_progress":    base,
		"subtask_progress": nilIfEmpty(subtask),
		"overall_progress": overall,
		"can_complete":     canCompleteBasedOnProgress(overall, subtask),
		"blocking_factors": identifyBlockingFactors(task, subtask),
	}
}

// nilIfEmpty maps a nil map to an untyped nil so it serializes as null.
func nilIfEmpty(m map[string]any) any {
	if m == nil {
		return nil
	}
	return m
}

// percentOneDecimal is float(Decimal(n)/Decimal(d)*100 quantized to 0.1, ROUND_HALF_UP)
// for non-negative n and positive d, computed exactly.
func percentOneDecimal(n, d int) float64 {
	v := new(big.Rat).SetFrac64(int64(n)*1000, int64(d)) // value * 10, with *100 folded in
	v.Add(v, big.NewRat(1, 2))
	tenths := new(big.Int).Quo(v.Num(), v.Denom()) // floor for non-negative
	return float64(tenths.Int64()) / 10.0
}

// CalculateSubtaskCompletionPercentage is the percentage of completed subtasks
// (100.0 when there are none, 0.0 on repository failure).
func (s *TaskProgressService) CalculateSubtaskCompletionPercentage(ctx context.Context, task *entities.Task) float64 {
	if s.subtaskRepository == nil {
		return 100.0
	}
	subtasks, err := s.subtasksOf(ctx, task)
	if err != nil {
		return 0.0
	}
	if len(subtasks) == 0 {
		return 100.0
	}
	completed := 0
	for _, st := range subtasks {
		if st.IsCompleted() {
			completed++
		}
	}
	return percentOneDecimal(completed, len(subtasks))
}

func emptySubtaskSummary() map[string]any {
	return map[string]any{"total": 0, "completed": 0, "incomplete": 0, "completion_percentage": 100.0,
		"can_complete_parent": true, "details": []map[string]any{}}
}

// GetSubtaskSummary returns detailed subtask statistics.
func (s *TaskProgressService) GetSubtaskSummary(ctx context.Context, task *entities.Task) map[string]any {
	if s.subtaskRepository == nil {
		return emptySubtaskSummary()
	}
	subtasks, err := s.subtasksOf(ctx, task)
	if err != nil {
		return map[string]any{"total": 0, "completed": 0, "incomplete": 0, "completion_percentage": 0.0,
			"can_complete_parent": false, "details": []map[string]any{}, "error": err.Error()}
	}
	if len(subtasks) == 0 {
		return emptySubtaskSummary()
	}
	var done, todo []*entities.Subtask
	for _, st := range subtasks {
		if st.IsCompleted() {
			done = append(done, st)
		} else {
			todo = append(todo, st)
		}
	}
	details := make([]map[string]any, 0, len(subtasks))
	for _, st := range subtasks {
		id := "None"
		if st.ID != nil {
			id = st.ID.Value
		}
		status := "incomplete"
		if st.IsCompleted() {
			status = "completed"
		}
		details = append(details, map[string]any{"id": id, "title": st.Title, "status": status,
			"progress_percentage": st.ProgressPercentage})
	}
	return map[string]any{
		"total": len(subtasks), "completed": len(done), "incomplete": len(todo),
		"completion_percentage": s.CalculateSubtaskCompletionPercentage(ctx, task),
		"can_complete_parent":   len(todo) == 0,
		"details":               details,
		"incomplete_titles":     firstTitles(todo, 5),
		"completed_titles":      firstTitles(done, 5),
	}
}

func firstTitles(list []*entities.Subtask, n int) []string {
	out := []string{}
	for i, st := range list {
		if i == n {
			break
		}
		out = append(out, st.Title)
	}
	return out
}

// CalculateProgressScore is the weighted score in [0.0, 1.0]: 60% task status,
// 40% subtask completion.
func (s *TaskProgressService) CalculateProgressScore(ctx context.Context, task *entities.Task) float64 {
	statusScore := statusProgressValue(statusStr(task))
	subtaskScore := s.CalculateSubtaskCompletionPercentage(ctx, task) / 100.0
	overall := float64(statusScore*0.6) + float64(subtaskScore*0.4)
	return max(0.0, min(1.0, overall))
}

func (s *TaskProgressService) calculateBaseTaskProgress(task *entities.Task) map[string]any {
	st := statusStr(task)
	return map[string]any{
		"status":              st,
		"progress_percentage": statusProgressValue(st) * 100,
		"is_completed":        task.Status != nil && task.Status.IsDone(),
		"is_in_progress":      isStatusInProgress(st),
		"is_blocked":          isStatusBlocked(st),
	}
}

func calculateOverallProgress(base, subtask map[string]any) map[string]any {
	basePct := base["progress_percentage"].(float64)
	if subtask == nil || subtask["total"].(int) == 0 {
		return map[string]any{"percentage": basePct, "weighted_percentage": basePct, "calculation_method": "task_status_only"}
	}
	subPct := subtask["completion_percentage"].(float64)
	weighted := float64(basePct*0.6) + float64(subPct*0.4)
	return map[string]any{"percentage": weighted, "weighted_percentage": weighted, "base_contribution": basePct,
		"subtask_contribution": subPct, "calculation_method": "weighted_combination"}
}

func canCompleteBasedOnProgress(overall, subtask map[string]any) bool {
	if subtask != nil && subtask["total"].(int) > 0 {
		return subtask["incomplete"].(int) == 0
	}
	return overall["percentage"].(float64) >= 0.0
}

func identifyBlockingFactors(task *entities.Task, subtask map[string]any) []string {
	factors := []string{}
	if subtask != nil && subtask["incomplete"].(int) > 0 {
		factors = append(factors, fmt.Sprintf("%d of %d subtasks incomplete", subtask["incomplete"].(int), subtask["total"].(int)))
	}
	if isStatusBlocked(statusStr(task)) {
		factors = append(factors, "Task status is blocked")
	}
	if len(task.Dependencies) > 0 {
		factors = append(factors, "Dependencies may not be satisfied")
	}
	return factors
}

func statusProgressValue(status string) float64 {
	switch strings.ToLower(status) {
	case "in_progress":
		return 0.5
	case "review":
		return 0.8
	case "testing":
		return 0.9
	case "done":
		return 1.0
	}
	return 0.0
}

func isStatusInProgress(status string) bool {
	switch strings.ToLower(status) {
	case "in_progress", "review", "testing":
		return true
	}
	return false
}

func isStatusBlocked(status string) bool { return strings.ToLower(status) == "blocked" }

func createErrorProgressResponse(task *entities.Task, msg string) map[string]any {
	return map[string]any{
		"task_id": taskIDStr(task),
		"base_progress": map[string]any{"status": statusStr(task), "progress_percentage": 0, "is_completed": false,
			"is_in_progress": false, "is_blocked": true},
		"subtask_progress": nil,
		"overall_progress": map[string]any{"percentage": 0, "weighted_percentage": 0, "calculation_method": "error"},
		"can_complete":     false,
		"blocking_factors": []string{"Calculation error: " + msg},
		"error":            msg,
	}
}
