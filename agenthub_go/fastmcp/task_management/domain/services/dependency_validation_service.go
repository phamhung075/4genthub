package services

import (
	"context"
	"errors"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// DependencyTaskRepository is the task repository surface used by the service.
type DependencyTaskRepository interface {
	FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
	FindAll(ctx context.Context) ([]*entities.Task, error)
}

// AcrossContextsFinder is implemented by repositories that support
// find_by_id_across_contexts (Python probes it with hasattr).
type AcrossContextsFinder interface {
	FindByIDAcrossContexts(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
}

// DependencyValidationService validates dependency chains and detects issues. Like
// Python, unexpected failures are folded into error-shaped results.
type DependencyValidationService struct {
	taskRepository DependencyTaskRepository
	idValidator    *utilities.IDValidator
}

// NewDependencyValidationService builds the service; idValidator nil uses a strict default.
func NewDependencyValidationService(r DependencyTaskRepository, v *utilities.IDValidator) *DependencyValidationService {
	if v == nil {
		v = utilities.NewIDValidator(true)
	}
	return &DependencyValidationService{r, v}
}

func taskMapOf(tasks []*entities.Task) map[string]*entities.Task {
	m := make(map[string]*entities.Task, len(tasks))
	for _, t := range tasks {
		m[taskIDStr(t)] = t
	}
	return m
}

func depStatus(t *entities.Task) string { return statusStr(t) }

func isoNowUTC() string { return value_objects.IsoFormat(time.Now().UTC().Truncate(time.Microsecond)) }

// ValidateDependencyChain validates the whole dependency chain of a task.
func (s *DependencyValidationService) ValidateDependencyChain(ctx context.Context, taskID value_objects.TaskId) map[string]any {
	failure := func(msg string) map[string]any {
		return map[string]any{"valid": false, "errors": []string{msg}, "issues": []map[string]any{}}
	}
	taskIDStr := taskID.Value
	if r := s.idValidator.DetectIDType(taskIDStr, "task_id"); !r.IsValid {
		return failure("Invalid task ID format: " + errText(r))
	}
	task, err := s.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return failure("Validation failed: " + err.Error())
	}
	if task == nil {
		return failure("Task " + taskIDStr + " not found")
	}
	allTasks, err := s.taskRepository.FindAll(ctx)
	if err != nil {
		return failure("Validation failed: " + err.Error())
	}
	taskMap := taskMapOf(allTasks)
	issues := []map[string]any{}
	errs := []string{}
	deps := task.GetDependencyIDs()
	if len(deps) == 0 {
		return map[string]any{"valid": true, "message": "Task has no dependencies", "issues": issues, "errors": errs}
	}
	for _, depID := range deps {
		if r := s.idValidator.DetectIDType(depID, "task_id"); !r.IsValid {
			errs = append(errs, "Invalid dependency ID format '"+depID+"': "+errText(r))
			continue
		}
		if taskIDStr == depID {
			errs = append(errs, "Task cannot depend on itself (ID: "+depID+")")
			continue
		}
		issues = append(issues, s.validateSingleDependency(ctx, depID, taskMap)...)
	}
	if cycle := s.checkCircularDependencies(task, allTasks); len(cycle) > 0 {
		errs = append(errs, "Circular dependency detected: "+strings.Join(cycle, " -> "))
	}
	for _, orphan := range s.checkOrphanedDependencies(ctx, task, taskMap) {
		errs = append(errs, "Dependency "+orphan+" no longer exists")
	}
	return map[string]any{
		"valid": len(errs) == 0, "task_id": taskIDStr, "dependency_count": len(deps), "issues": issues, "errors": errs,
		"can_proceed": s.canTaskProceed(ctx, task, taskMap), "validation_timestamp": isoNowUTC(),
	}
}

func errText(r utilities.ValidationResult) string {
	if r.ErrorMessage == nil {
		return "None"
	}
	return *r.ErrorMessage
}

func (s *DependencyValidationService) validateSingleDependency(ctx context.Context, dependencyID string, taskMap map[string]*entities.Task) []map[string]any {
	dep := taskMap[dependencyID]
	if dep == nil {
		dep = s.findDependencyAcrossStates(ctx, dependencyID)
	}
	if dep == nil {
		return []map[string]any{{
			"type": "missing_dependency", "dependency_id": dependencyID, "severity": "error",
			"message":    "Dependency task " + dependencyID + " not found in any state",
			"suggestion": "Remove this dependency or check if the task ID is correct",
		}}
	}
	issue := func(typ, severity, msg, suggestion string) []map[string]any {
		return []map[string]any{{"type": typ, "dependency_id": dependencyID, "dependency_title": dep.Title,
			"severity": severity, "message": msg, "suggestion": suggestion}}
	}
	switch depStatus(dep) {
	case "cancelled":
		return issue("cancelled_dependency", "warning", "Dependency '"+dep.Title+"' was cancelled",
			"Consider removing this dependency or finding an alternative")
	case "blocked":
		return issue("blocked_dependency", "warning", "Dependency '"+dep.Title+"' is currently blocked",
			"Resolve blockers in the dependency task first")
	case "done":
		return issue("satisfied_dependency", "info", "Dependency '"+dep.Title+"' is completed",
			"Task can proceed with this dependency satisfied")
	}
	return []map[string]any{}
}

// findDependencyAcrossStates looks a dependency up across contexts when the repository
// supports it, then by plain ID; every failure (including a malformed ID) yields nil.
func (s *DependencyValidationService) findDependencyAcrossStates(ctx context.Context, dependencyID string) *entities.Task {
	id, err := value_objects.NewTaskId(dependencyID)
	if err != nil {
		return nil
	}
	if f, ok := s.taskRepository.(AcrossContextsFinder); ok {
		if t, err := f.FindByIDAcrossContexts(ctx, id); err == nil && t != nil {
			return t
		}
	}
	if t, err := s.taskRepository.FindByID(ctx, id); err == nil && t != nil {
		return t
	}
	return nil
}

var errNotOnPath = errors.New("x is not in list")

// checkCircularDependencies runs Python's DFS, including its defect: reaching an
// already-visited task that is not on the current path (a diamond, not a cycle) makes
// `path.index` raise ValueError, the outer except swallows it, and the whole check
// reports no cycle.
func (s *DependencyValidationService) checkCircularDependencies(task *entities.Task, allTasks []*entities.Task) []string {
	visited := map[string]bool{}
	var path []string
	taskMap := taskMapOf(allTasks)
	var dfs func(id string) ([]string, error)
	dfs = func(id string) ([]string, error) {
		if visited[id] {
			for i, p := range path {
				if p == id {
					return append(append([]string{}, path[i:]...), id), nil
				}
			}
			return nil, errNotOnPath
		}
		visited[id] = true
		path = append(path, id)
		if cur := taskMap[id]; cur != nil {
			for _, dep := range cur.GetDependencyIDs() {
				cycle, err := dfs(dep)
				if err != nil {
					return nil, err
				}
				if len(cycle) > 0 {
					return cycle, nil
				}
			}
		}
		path = path[:len(path)-1]
		return nil, nil
	}
	cycle, err := dfs(taskIDStr(task))
	if err != nil {
		return nil
	}
	return cycle
}

func (s *DependencyValidationService) checkOrphanedDependencies(ctx context.Context, task *entities.Task, taskMap map[string]*entities.Task) []string {
	orphaned := []string{}
	for _, dep := range task.GetDependencyIDs() {
		if _, ok := taskMap[dep]; !ok && s.findDependencyAcrossStates(ctx, dep) == nil {
			orphaned = append(orphaned, dep)
		}
	}
	return orphaned
}

func (s *DependencyValidationService) canTaskProceed(ctx context.Context, task *entities.Task, taskMap map[string]*entities.Task) bool {
	for _, depID := range task.GetDependencyIDs() {
		dep := taskMap[depID]
		if dep == nil {
			dep = s.findDependencyAcrossStates(ctx, depID)
		}
		if dep == nil {
			return false
		}
		if dep.Status == nil || !dep.Status.IsDone() {
			return false
		}
	}
	return true
}

// GetDependencyChainStatus returns the detailed status of a task's dependency chain.
func (s *DependencyValidationService) GetDependencyChainStatus(ctx context.Context, taskID value_objects.TaskId) map[string]any {
	task, err := s.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return map[string]any{"error": "Analysis failed: " + err.Error()}
	}
	if task == nil {
		return map[string]any{"error": "Task " + taskID.Value + " not found"}
	}
	allTasks, err := s.taskRepository.FindAll(ctx)
	if err != nil {
		return map[string]any{"error": "Analysis failed: " + err.Error()}
	}
	taskMap := taskMapOf(allTasks)
	chain := []map[string]any{}
	for _, dep := range task.GetDependencyIDs() {
		chain = append(chain, s.getDependencyInfo(ctx, dep, taskMap))
	}
	total, completed, blocked := len(chain), 0, 0
	for _, d := range chain {
		switch d["status"] {
		case "done":
			completed++
		case "blocked":
			blocked++
		}
	}
	var pct any = 100
	if total > 0 {
		pct = float64(completed) / float64(total) * 100
	}
	return map[string]any{
		"task_id": taskID.Value, "task_title": task.Title, "task_status": statusStr(task), "dependency_chain": chain,
		"chain_statistics": map[string]any{"total_dependencies": total, "completed_dependencies": completed,
			"blocked_dependencies": blocked, "completion_percentage": pct},
		"can_proceed": s.canTaskProceed(ctx, task, taskMap), "analysis_timestamp": isoNowUTC(),
	}
}

func (s *DependencyValidationService) getDependencyInfo(ctx context.Context, dependencyID string, taskMap map[string]*entities.Task) map[string]any {
	dep := taskMap[dependencyID]
	if dep == nil {
		dep = s.findDependencyAcrossStates(ctx, dependencyID)
	}
	if dep == nil {
		return map[string]any{"dependency_id": dependencyID, "status": "missing", "title": "Unknown", "found": false,
			"message": "Dependency task not found"}
	}
	priority := "None"
	if dep.Priority != nil {
		priority = dep.Priority.Value
	}
	return map[string]any{"dependency_id": dependencyID, "title": dep.Title, "status": depStatus(dep), "found": true,
		"is_completed": dep.Status != nil && dep.Status.IsDone(), "priority": priority}
}
