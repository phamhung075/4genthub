package services

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PriorityTaskRepositoryProtocol is the task repository protocol used by the service.
// (Python declares it as TaskRepositoryProtocol; the name would clash with the
// task_progress/branch_statistics protocols in this Go package.)
type PriorityTaskRepositoryProtocol interface {
	FindAll(ctx context.Context) ([]*entities.Task, error)
	FindByGitBranchID(ctx context.Context, gitBranchID string) ([]*entities.Task, error)
}

// TaskPriorityService calculates task priority scores and orders tasks.
//
// Python defects preserved (Task.due_date is a str, but the service treats it as a
// datetime): the urgency score is always 30.0 because `due_date.tzinfo` raises inside a
// swallowed try; `_get_priority_factors` calls `due_date.isoformat()` and raises for any
// task that has a due date, so OrderTasksByPriority then returns its error fallback for
// ALL tasks, and GetNextTaskRecommendation returns nil whenever an eligible task has a
// due date.
type TaskPriorityService struct {
	taskRepository PriorityTaskRepositoryProtocol
}

// NewTaskPriorityService builds the service; taskRepository may be nil.
func NewTaskPriorityService(r PriorityTaskRepositoryProtocol) *TaskPriorityService {
	return &TaskPriorityService{r}
}

var errStrNoIsoformat = errors.New("'str' object has no attribute 'isoformat'")

func priorityStr(t *entities.Task) string {
	if t.Priority == nil {
		return "None"
	}
	return t.Priority.Value
}

func hasDueDate(t *entities.Task) bool { return t.DueDate != nil && *t.DueDate != "" }

// CalculatePriorityScore returns the weighted score in [0.0, 100.0] (0.0 on failure).
func (s *TaskPriorityService) CalculatePriorityScore(task *entities.Task, contextFactors map[string]any) float64 {
	base := calculateBasePriorityScore(task) * 0.30
	urgency := calculateUrgencyScore(task) * 0.25
	blocking, err := calculateBlockingScore(contextFactors)
	if err != nil {
		return 0.0
	}
	blocking *= 0.20
	age := calculateAgeScore(task) * 0.15
	progress := calculateProgressScoreForPriority(task) * 0.10
	total := float64(base) + float64(urgency) + float64(blocking) + float64(age) + float64(progress)
	return max(0.0, min(100.0, total))
}

// OrderTasksByPriority orders tasks by descending score (stable). On any failure Python
// returns [{"task", "priority_score": 0.0, "error": msg}] for every task.
func (s *TaskPriorityService) OrderTasksByPriority(tasks []*entities.Task, contextFactors map[string]any) []map[string]any {
	scores := make([]map[string]any, 0, len(tasks))
	for _, task := range tasks {
		score := s.CalculatePriorityScore(task, contextFactors)
		factors, err := getPriorityFactors(task, contextFactors)
		if err != nil {
			fallback := make([]map[string]any, 0, len(tasks))
			for _, t := range tasks {
				fallback = append(fallback, map[string]any{"task": t, "priority_score": 0.0, "error": err.Error()})
			}
			return fallback
		}
		scores = append(scores, map[string]any{
			"task": task, "task_id": taskIDStr(task), "title": task.Title, "priority_score": score,
			"base_priority": priorityStr(task), "status": statusStr(task), "priority_factors": factors,
		})
	}
	sort.SliceStable(scores, func(i, j int) bool {
		return scores[i]["priority_score"].(float64) > scores[j]["priority_score"].(float64)
	})
	return scores
}

// GetNextTaskRecommendation returns the best eligible task in a branch, or nil. excludeStatuses
// nil/empty defaults to done and cancelled.
func (s *TaskPriorityService) GetNextTaskRecommendation(ctx context.Context, gitBranchID string, excludeStatuses []string) map[string]any {
	if s.taskRepository == nil {
		return nil
	}
	all, err := s.taskRepository.FindByGitBranchID(ctx, gitBranchID)
	if err != nil || len(all) == 0 {
		return nil
	}
	if len(excludeStatuses) == 0 {
		excludeStatuses = []string{"done", "cancelled"}
	}
	excluded := map[string]bool{}
	for _, e := range excludeStatuses {
		excluded[strings.ToLower(e)] = true
	}
	var eligible []*entities.Task
	for _, t := range all {
		if !excluded[strings.ToLower(statusStr(t))] {
			eligible = append(eligible, t)
		}
	}
	if len(eligible) == 0 {
		return nil
	}
	ordered := s.OrderTasksByPriority(eligible, nil)
	if len(ordered) == 0 {
		return nil
	}
	rec := ordered[0]
	if _, ok := rec["task_id"]; !ok { // fallback entries carry no task_id (KeyError in Python)
		return nil
	}
	reason, err := generateRecommendationReason(rec)
	if err != nil {
		return nil
	}
	alternatives := []map[string]any{}
	for i := 1; i < len(ordered) && i < 3; i++ {
		alternatives = append(alternatives, map[string]any{"task_id": ordered[i]["task_id"], "title": ordered[i]["title"],
			"priority_score": ordered[i]["priority_score"]})
	}
	return map[string]any{
		"task": rec["task"], "task_id": rec["task_id"], "title": rec["title"], "priority_score": rec["priority_score"],
		"recommendation_reason": reason, "alternative_tasks": alternatives, "total_eligible_tasks": len(eligible),
	}
}

// AdjustPriorityForDependencies returns a multiplier in [0.5, 2.0].
func (s *TaskPriorityService) AdjustPriorityForDependencies(task *entities.Task, allTasks []*entities.Task) float64 {
	if len(task.Dependencies) > 0 && len(allTasks) > 0 {
		if n := countIncompleteDependencies(task, allTasks); n > 0 {
			reduction := min(0.4, float64(n)*0.1)
			return max(0.5, 1.0-reduction)
		}
	}
	if len(allTasks) > 0 {
		if n := countTasksDependingOn(task, allTasks); n > 0 {
			increase := min(1.0, float64(n)*0.2)
			return min(2.0, 1.0+increase)
		}
	}
	return 1.0
}

func calculateBasePriorityScore(task *entities.Task) float64 {
	switch strings.ToLower(priorityStr(task)) {
	case "critical":
		return 100.0
	case "urgent":
		return 90.0
	case "high":
		return 75.0
	case "medium":
		return 50.0
	case "low":
		return 25.0
	}
	return 50.0
}

// calculateUrgencyScore is always 30.0 in Python: a missing due date gives 30.0 directly and a
// due date (a str) raises AttributeError on `.tzinfo`, which the method swallows, returning 30.0.
func calculateUrgencyScore(task *entities.Task) float64 { return 30.0 }

// calculateBlockingScore buckets context_factors["dependent_task_count"] (default 0). A
// non-numeric value makes Python's comparisons raise TypeError.
func calculateBlockingScore(contextFactors map[string]any) (float64, error) {
	count := 0.0
	if v, ok := contextFactors["dependent_task_count"]; ok {
		f, isNum := value_objects.PyFloat(v)
		if !isNum {
			return 0, value_objects.TypeErrorf("'==' not supported between instances of %T and 'int'", v)
		}
		count = f
	}
	switch {
	case count == 0:
		return 20.0, nil
	case count == 1:
		return 40.0, nil
	case count <= 3:
		return 60.0, nil
	case count <= 5:
		return 80.0, nil
	}
	return 100.0, nil
}

// daysBetween is timedelta.days of (a - b): whole days, floored toward -infinity.
func daysBetween(a, b time.Time) int {
	d := a.Sub(b)
	q := d / (24 * time.Hour)
	if d%(24*time.Hour) < 0 {
		q--
	}
	return int(q)
}

func calculateAgeScore(task *entities.Task) float64 {
	if task.CreatedAt == nil {
		return 40.0
	}
	age := daysBetween(time.Now().UTC(), *task.CreatedAt)
	switch {
	case age <= 1:
		return 10.0
	case age <= 3:
		return 20.0
	case age <= 7:
		return 40.0
	case age <= 30:
		return 60.0
	case age <= 90:
		return 80.0
	}
	return 100.0
}

func calculateProgressScoreForPriority(task *entities.Task) float64 {
	switch strings.ToLower(statusStr(task)) {
	case "in_progress":
		return 100.0
	case "review":
		return 80.0
	case "testing":
		return 70.0
	case "blocked", "done", "cancelled":
		return 0.0
	}
	return 50.0 // "todo" and unknown statuses
}

func getPriorityFactors(task *entities.Task, contextFactors map[string]any) (map[string]any, error) {
	if hasDueDate(task) {
		return nil, errStrNoIsoformat
	}
	blocking, err := calculateBlockingScore(contextFactors)
	if err != nil {
		return nil, err
	}
	var dependent any = 0
	if v, ok := contextFactors["dependent_task_count"]; ok {
		dependent = v
	}
	var createdAt any
	if task.CreatedAt != nil {
		createdAt = value_objects.IsoFormat(*task.CreatedAt)
	} else {
		return nil, fmt.Errorf("'NoneType' object has no attribute 'isoformat'")
	}
	return map[string]any{
		"base_priority":   map[string]any{"value": priorityStr(task), "score": calculateBasePriorityScore(task)},
		"urgency":         map[string]any{"due_date": nil, "score": calculateUrgencyScore(task)},
		"blocking_factor": map[string]any{"dependent_tasks": dependent, "score": blocking},
		"age_factor":      map[string]any{"created_at": createdAt, "score": calculateAgeScore(task)},
		"progress_factor": map[string]any{"status": statusStr(task), "score": calculateProgressScoreForPriority(task)},
	}, nil
}

// generateRecommendationReason mirrors Python, including that a task with a due date
// raises TypeError (str - datetime), which cannot happen here because the ordering step has
// already failed for such tasks.
func generateRecommendationReason(rec map[string]any) (string, error) {
	task := rec["task"].(*entities.Task)
	score := rec["priority_score"].(float64)
	var reasons []string
	if score >= 80 {
		reasons = append(reasons, "high priority score")
	}
	if hasDueDate(task) {
		return "", value_objects.TypeErrorf("unsupported operand type(s) for -: 'str' and 'datetime.datetime'")
	}
	if strings.ToLower(statusStr(task)) == "in_progress" {
		reasons = append(reasons, "already in progress")
	}
	switch p := strings.ToLower(priorityStr(task)); p {
	case "high", "urgent", "critical":
		reasons = append(reasons, p+" priority")
	}
	if len(reasons) == 0 {
		reasons = append(reasons, "best available option")
	}
	return "Recommended because: " + strings.Join(reasons, ", "), nil
}

func countIncompleteDependencies(task *entities.Task, all []*entities.Task) int {
	count := 0
	for _, dep := range task.Dependencies {
		for _, other := range all {
			if taskIDStr(other) == dep.Value {
				if other.Status == nil || !other.Status.IsDone() {
					count++
				}
				break
			}
		}
	}
	return count
}

func countTasksDependingOn(task *entities.Task, all []*entities.Task) int {
	id := taskIDStr(task)
	count := 0
	for _, other := range all {
		for _, dep := range other.Dependencies {
			if dep.Value == id {
				count++
				break
			}
		}
	}
	return count
}
