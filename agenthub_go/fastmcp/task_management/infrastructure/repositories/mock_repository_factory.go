package repositories

// Mock Repository Factory (Python infrastructure/repositories/mock_repository_factory.py):
// in-memory mock repositories for testing and development. Python stores entities in
// insertion-ordered dicts, so the Go mocks use *entities.OrderedMap to keep that observable
// order. Logging calls are dropped. The Python mock git-branch repository declares methods
// that do not match the Go domain GitBranchRepository (save/find_by_id/find_by_project_id/
// ... vs find_by_id/create_git_branch/...), and the mock project repository's signatures for
// get_project_health_summary/unassign_agent_from_tree differ from the Go domain interface, so
// those two mocks are standalone (only the task/subtask mocks satisfy the domain interfaces).

import (
	"context"
	"reflect"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// MockProjectRepository is MockProjectRepository.
type MockProjectRepository struct {
	Projects *entities.OrderedMap[*entities.Project]
}

// NewMockProjectRepository builds an empty mock project repository.
func NewMockProjectRepository() *MockProjectRepository {
	return &MockProjectRepository{Projects: entities.NewOrderedMap[*entities.Project]()}
}

func mockProjectKey(p *entities.Project) string {
	if p == nil || p.ID == nil {
		return ""
	}
	return p.ID.Value
}

// Save is save.
func (m *MockProjectRepository) Save(_ context.Context, project *entities.Project) (*entities.Project, error) {
	m.Projects.Set(mockProjectKey(project), project)
	return project, nil
}

// FindByID is find_by_id.
func (m *MockProjectRepository) FindByID(_ context.Context, projectID string) (*entities.Project, error) {
	p, _ := m.Projects.Get(projectID)
	return p, nil
}

// FindByName is find_by_name.
func (m *MockProjectRepository) FindByName(_ context.Context, name string) (*entities.Project, error) {
	for _, p := range m.Projects.Values() {
		if p.Name == name {
			return p, nil
		}
	}
	return nil, nil
}

// FindAll is find_all.
func (m *MockProjectRepository) FindAll(_ context.Context) ([]*entities.Project, error) {
	return m.Projects.Values(), nil
}

// Delete is delete.
func (m *MockProjectRepository) Delete(_ context.Context, projectID string) (bool, error) {
	if m.Projects.Has(projectID) {
		m.Projects.Delete(projectID)
		return true, nil
	}
	return false, nil
}

// Count is count.
func (m *MockProjectRepository) Count(_ context.Context) (int, error) { return m.Projects.Len(), nil }

// Exists is exists.
func (m *MockProjectRepository) Exists(_ context.Context, projectID string) (bool, error) {
	return m.Projects.Has(projectID), nil
}

// FindProjectsWithAgent is find_projects_with_agent (always empty in Python).
func (m *MockProjectRepository) FindProjectsWithAgent(_ context.Context, _ string) ([]*entities.Project, error) {
	return nil, nil
}

// FindProjectsByStatus is find_projects_by_status. The Python project entity has no
// `status` attribute, so the hasattr guard makes this always empty.
func (m *MockProjectRepository) FindProjectsByStatus(_ context.Context, _ string) ([]*entities.Project, error) {
	return nil, nil
}

// GetProjectHealthSummary is get_project_health_summary.
func (m *MockProjectRepository) GetProjectHealthSummary(_ context.Context, projectID string) (map[string]any, error) {
	return map[string]any{"health": "good", "project_id": projectID}, nil
}

// UnassignAgentFromTree is unassign_agent_from_tree (always true in Python).
func (m *MockProjectRepository) UnassignAgentFromTree(_ context.Context, _ string) (bool, error) {
	return true, nil
}

// Update is update; missing id raises ValueError like Python.
func (m *MockProjectRepository) Update(_ context.Context, project *entities.Project) (*entities.Project, error) {
	if m.Projects.Has(mockProjectKey(project)) {
		m.Projects.Set(mockProjectKey(project), project)
		return project, nil
	}
	return nil, &tmvo.ValueError{Msg: "Project with id " + mockProjectKey(project) + " not found"}
}

// MockGitBranchRepository is MockGitBranchRepository.
type MockGitBranchRepository struct {
	Branches *entities.OrderedMap[*entities.GitBranch]
}

// NewMockGitBranchRepository builds an empty mock branch repository.
func NewMockGitBranchRepository() *MockGitBranchRepository {
	return &MockGitBranchRepository{Branches: entities.NewOrderedMap[*entities.GitBranch]()}
}

func mockBranchKey(b *entities.GitBranch) string {
	if b == nil || b.ID == nil {
		return ""
	}
	return b.ID.Value
}

// Save is save.
func (m *MockGitBranchRepository) Save(_ context.Context, branch *entities.GitBranch) (*entities.GitBranch, error) {
	m.Branches.Set(mockBranchKey(branch), branch)
	return branch, nil
}

// FindByID is find_by_id.
func (m *MockGitBranchRepository) FindByID(_ context.Context, branchID string) (*entities.GitBranch, error) {
	b, _ := m.Branches.Get(branchID)
	return b, nil
}

// FindAll is find_all.
func (m *MockGitBranchRepository) FindAll(_ context.Context) ([]*entities.GitBranch, error) {
	return m.Branches.Values(), nil
}

// Delete is delete.
func (m *MockGitBranchRepository) Delete(_ context.Context, branchID string) (bool, error) {
	if m.Branches.Has(branchID) {
		m.Branches.Delete(branchID)
		return true, nil
	}
	return false, nil
}

// FindByProjectID is find_by_project_id.
func (m *MockGitBranchRepository) FindByProjectID(_ context.Context, projectID string) ([]*entities.GitBranch, error) {
	out := []*entities.GitBranch{}
	for _, b := range m.Branches.Values() {
		if b.ProjectID == projectID {
			out = append(out, b)
		}
	}
	return out, nil
}

// FindByNameAndProject is find_by_name_and_project.
func (m *MockGitBranchRepository) FindByNameAndProject(_ context.Context, name, projectID string) (*entities.GitBranch, error) {
	for _, b := range m.Branches.Values() {
		if b.Name == name && b.ProjectID == projectID {
			return b, nil
		}
	}
	return nil, nil
}

// Count is count.
func (m *MockGitBranchRepository) Count(_ context.Context) (int, error) { return m.Branches.Len(), nil }

// Exists is exists.
func (m *MockGitBranchRepository) Exists(_ context.Context, branchID string) (bool, error) {
	return m.Branches.Has(branchID), nil
}

// Update is update; missing id raises ValueError like Python.
func (m *MockGitBranchRepository) Update(_ context.Context, branch *entities.GitBranch) (*entities.GitBranch, error) {
	if m.Branches.Has(mockBranchKey(branch)) {
		m.Branches.Set(mockBranchKey(branch), branch)
		return branch, nil
	}
	return nil, &tmvo.ValueError{Msg: "Branch with id " + mockBranchKey(branch) + " not found"}
}

// MockTaskRepository is MockTaskRepository.
type MockTaskRepository struct {
	Tasks *entities.OrderedMap[*entities.Task]
}

// NewMockTaskRepository builds an empty mock task repository.
func NewMockTaskRepository() *MockTaskRepository {
	return &MockTaskRepository{Tasks: entities.NewOrderedMap[*entities.Task]()}
}

var _ domainrepos.TaskRepository = (*MockTaskRepository)(nil)

func mockTaskKey(task *entities.Task) string {
	if task == nil || task.ID == nil {
		return ""
	}
	return task.ID.Value
}

// Save is save.
func (m *MockTaskRepository) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	m.Tasks.Set(mockTaskKey(task), task)
	return task, nil
}

// FindByID is find_by_id.
func (m *MockTaskRepository) FindByID(_ context.Context, taskID tmvo.TaskId) (*entities.Task, error) {
	t, _ := m.Tasks.Get(taskID.Value)
	return t, nil
}

// FindAll is find_all.
func (m *MockTaskRepository) FindAll(_ context.Context) ([]*entities.Task, error) {
	return m.Tasks.Values(), nil
}

// Delete is delete.
func (m *MockTaskRepository) Delete(_ context.Context, taskID tmvo.TaskId) (bool, error) {
	if m.Tasks.Has(taskID.Value) {
		m.Tasks.Delete(taskID.Value)
		return true, nil
	}
	return false, nil
}

// FindByStatus is find_by_status.
func (m *MockTaskRepository) FindByStatus(_ context.Context, status tmvo.TaskStatus) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, t := range m.Tasks.Values() {
		if t.Status != nil && t.Status.Value == status.Value {
			out = append(out, t)
		}
	}
	return out, nil
}

// FindByPriority is find_by_priority.
func (m *MockTaskRepository) FindByPriority(_ context.Context, priority tmvo.Priority) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, t := range m.Tasks.Values() {
		if t.Priority != nil && t.Priority.Value == priority.Value {
			out = append(out, t)
		}
	}
	return out, nil
}

// FindByGitBranchID is find_by_git_branch_id.
func (m *MockTaskRepository) FindByGitBranchID(_ context.Context, gitBranchID string) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, t := range m.Tasks.Values() {
		if t.GitBranchID != nil && *t.GitBranchID == gitBranchID {
			out = append(out, t)
		}
	}
	return out, nil
}

// Count is count.
func (m *MockTaskRepository) Count(_ context.Context) (int, error) { return m.Tasks.Len(), nil }

// Exists is exists.
func (m *MockTaskRepository) Exists(_ context.Context, taskID tmvo.TaskId) (bool, error) {
	return m.Tasks.Has(taskID.Value), nil
}

// Search is search. Python lower-cases query/title/description and ignores its limit.
func (m *MockTaskRepository) Search(_ context.Context, query string, _ map[string]any, _ int) ([]*entities.Task, error) {
	out := []*entities.Task{}
	q := strings.ToLower(query)
	for _, t := range m.Tasks.Values() {
		if strings.Contains(strings.ToLower(t.Title), q) || strings.Contains(strings.ToLower(t.Description), q) {
			out = append(out, t)
		}
	}
	return out, nil
}

// Update is update; missing id raises ValueError like Python.
func (m *MockTaskRepository) Update(_ context.Context, task *entities.Task) (*entities.Task, error) {
	if m.Tasks.Has(mockTaskKey(task)) {
		m.Tasks.Set(mockTaskKey(task), task)
		return task, nil
	}
	return nil, &tmvo.ValueError{Msg: "Task with id " + mockTaskKey(task) + " not found"}
}

// FindByAssignee is find_by_assignee. The Python Task entity has no `assignee`
// attribute (only assignees), so the hasattr guard makes this always empty.
func (m *MockTaskRepository) FindByAssignee(_ context.Context, _ string) ([]*entities.Task, error) {
	return nil, nil
}

// FindByLabels is find_by_labels: any label present in task.labels.
func (m *MockTaskRepository) FindByLabels(_ context.Context, labels []string) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, t := range m.Tasks.Values() {
		if t.Labels == nil {
			continue
		}
		for _, label := range labels {
			if containsString(t.Labels, label) {
				out = append(out, t)
				break
			}
		}
	}
	return out, nil
}

// GetNextID is get_next_id. Python uses len(tasks)+1 and a "task-N" id.
func (m *MockTaskRepository) GetNextID(_ context.Context) (tmvo.TaskId, error) {
	id, err := tmvo.NewTaskId("task-" + strconv.Itoa(m.Tasks.Len()+1))
	if err != nil {
		return tmvo.TaskId{}, err
	}
	return id, nil
}

// GetStatistics is get_statistics.
func (m *MockTaskRepository) GetStatistics(_ context.Context) (map[string]any, error) {
	pending, inProgress, completed := 0, 0, 0
	for _, t := range m.Tasks.Values() {
		if t.Status == nil {
			continue
		}
		switch t.Status.Value {
		case "pending":
			pending++
		case "in_progress":
			inProgress++
		case "completed":
			completed++
		}
	}
	return map[string]any{
		"total":       m.Tasks.Len(),
		"pending":     pending,
		"in_progress": inProgress,
		"completed":   completed,
	}, nil
}

// FindByCriteria is find_by_criteria. Python compares getattr(task, key) against each
// filter and only appends when every key matches; limit is applied after a match.
func (m *MockTaskRepository) FindByCriteria(_ context.Context, filters map[string]any, limit *int) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, t := range m.Tasks.Values() {
		match := true
		for key, value := range filters {
			field, ok := mockTaskField(t, key)
			if !ok || !reflect.DeepEqual(field, value) {
				match = false
				break
			}
		}
		if match {
			out = append(out, t)
			if limit != nil && len(out) >= *limit {
				break
			}
		}
	}
	return out, nil
}

// FindByIDAllStates is find_by_id_all_states (delegates to find_by_id).
func (m *MockTaskRepository) FindByIDAllStates(ctx context.Context, taskID tmvo.TaskId) (*entities.Task, error) {
	return m.FindByID(ctx, taskID)
}

// AtomicIncrementCompletedSubtasks is atomic_increment_completed_subtasks.
func (m *MockTaskRepository) AtomicIncrementCompletedSubtasks(_ context.Context, taskID tmvo.TaskId) (bool, error) {
	task, _ := m.Tasks.Get(taskID.Value)
	if task == nil {
		return false, nil
	}
	task.CompletedSubtasks = task.CompletedSubtasks + 1
	return true, nil
}

// MockSubtaskRepository is MockSubtaskRepository.
type MockSubtaskRepository struct {
	Subtasks *entities.OrderedMap[*entities.Subtask]
}

// NewMockSubtaskRepository builds an empty mock subtask repository.
func NewMockSubtaskRepository() *MockSubtaskRepository {
	return &MockSubtaskRepository{Subtasks: entities.NewOrderedMap[*entities.Subtask]()}
}

var _ domainrepos.SubtaskRepository = (*MockSubtaskRepository)(nil)

func mockSubtaskKey(s *entities.Subtask) string {
	if s == nil || s.ID == nil {
		return ""
	}
	return s.ID.Value
}

// Save is save.
func (m *MockSubtaskRepository) Save(_ context.Context, subtask *entities.Subtask) (bool, error) {
	m.Subtasks.Set(mockSubtaskKey(subtask), subtask)
	return true, nil
}

// FindByID is find_by_id.
func (m *MockSubtaskRepository) FindByID(_ context.Context, id string) (*entities.Subtask, error) {
	s, _ := m.Subtasks.Get(id)
	return s, nil
}

// FindByTaskID is find_by_task_id.
func (m *MockSubtaskRepository) FindByTaskID(_ context.Context, taskID string) ([]*entities.Subtask, error) {
	return m.byParent(taskID), nil
}

// FindByParentTaskID is find_by_parent_task_id.
func (m *MockSubtaskRepository) FindByParentTaskID(_ context.Context, parentTaskID tmvo.TaskId) ([]*entities.Subtask, error) {
	return m.byParent(parentTaskID.Value), nil
}

func (m *MockSubtaskRepository) byParent(taskID string) []*entities.Subtask {
	out := []*entities.Subtask{}
	for _, s := range m.Subtasks.Values() {
		if s.ParentTaskID != nil && s.ParentTaskID.Value == taskID {
			out = append(out, s)
		}
	}
	return out
}

// Delete is delete.
func (m *MockSubtaskRepository) Delete(_ context.Context, id string) (bool, error) {
	if m.Subtasks.Has(id) {
		m.Subtasks.Delete(id)
		return true, nil
	}
	return false, nil
}

// CountByTaskID is count_by_task_id.
func (m *MockSubtaskRepository) CountByTaskID(_ context.Context, taskID string) (int, error) {
	return len(m.byParent(taskID)), nil
}

// DeleteByTaskID is delete_by_task_id; returns the number removed.
func (m *MockSubtaskRepository) DeleteByTaskID(_ context.Context, taskID string) (int, error) {
	toDelete := []string{}
	for _, s := range m.Subtasks.Values() {
		if s.ParentTaskID != nil && s.ParentTaskID.Value == taskID {
			toDelete = append(toDelete, mockSubtaskKey(s))
		}
	}
	for _, id := range toDelete {
		m.Subtasks.Delete(id)
	}
	return len(toDelete), nil
}

// Update is update; missing id raises ValueError like Python.
func (m *MockSubtaskRepository) Update(_ context.Context, subtask *entities.Subtask) (*entities.Subtask, error) {
	if m.Subtasks.Has(mockSubtaskKey(subtask)) {
		m.Subtasks.Set(mockSubtaskKey(subtask), subtask)
		return subtask, nil
	}
	return nil, &tmvo.ValueError{Msg: "Subtask with id " + mockSubtaskKey(subtask) + " not found"}
}

// FindByAssignee is find_by_assignee. The Python Subtask entity has no `assignee`
// attribute, so the hasattr guard makes this always empty.
func (m *MockSubtaskRepository) FindByAssignee(_ context.Context, _ string) ([]*entities.Subtask, error) {
	return nil, nil
}

// FindByStatus is find_by_status.
func (m *MockSubtaskRepository) FindByStatus(_ context.Context, status string) ([]*entities.Subtask, error) {
	out := []*entities.Subtask{}
	for _, s := range m.Subtasks.Values() {
		if s.Status != nil && s.Status.Value == status {
			out = append(out, s)
		}
	}
	return out, nil
}

// FindCompleted is find_completed.
func (m *MockSubtaskRepository) FindCompleted(_ context.Context, parentTaskID tmvo.TaskId) ([]*entities.Subtask, error) {
	return m.byParentAndStatus(parentTaskID.Value, "completed"), nil
}

// FindPending is find_pending.
func (m *MockSubtaskRepository) FindPending(_ context.Context, parentTaskID tmvo.TaskId) ([]*entities.Subtask, error) {
	return m.byParentAndStatus(parentTaskID.Value, "pending"), nil
}

func (m *MockSubtaskRepository) byParentAndStatus(taskID, status string) []*entities.Subtask {
	out := []*entities.Subtask{}
	for _, s := range m.Subtasks.Values() {
		if s.ParentTaskID != nil && s.ParentTaskID.Value == taskID && s.Status != nil && s.Status.Value == status {
			out = append(out, s)
		}
	}
	return out
}

// Exists is exists.
func (m *MockSubtaskRepository) Exists(_ context.Context, id string) (bool, error) {
	return m.Subtasks.Has(id), nil
}

// CountByParentTaskID is count_by_parent_task_id.
func (m *MockSubtaskRepository) CountByParentTaskID(_ context.Context, parentTaskID tmvo.TaskId) (int, error) {
	return len(m.byParent(parentTaskID.Value)), nil
}

// CountCompletedByParentTaskID is count_completed_by_parent_task_id.
func (m *MockSubtaskRepository) CountCompletedByParentTaskID(_ context.Context, parentTaskID tmvo.TaskId) (int, error) {
	return len(m.byParentAndStatus(parentTaskID.Value, "completed")), nil
}

// GetNextID is get_next_id. Python ignores the parent and uses len(subtasks)+1.
func (m *MockSubtaskRepository) GetNextID(_ context.Context, _ tmvo.TaskId) (tmvo.TaskId, error) {
	id, err := tmvo.NewTaskId("subtask-" + strconv.Itoa(m.Subtasks.Len()+1))
	if err != nil {
		return tmvo.TaskId{}, err
	}
	return id, nil
}

// GetSubtaskProgress is get_subtask_progress.
func (m *MockSubtaskRepository) GetSubtaskProgress(_ context.Context, parentTaskID tmvo.TaskId) (map[string]any, error) {
	subtasks := m.byParent(parentTaskID.Value)
	completed := len(m.byParentAndStatus(parentTaskID.Value, "completed"))
	total := len(subtasks)
	progress := float64(0)
	if total > 0 {
		progress = float64(completed) / float64(total) * 100
	}
	return map[string]any{
		"total":               total,
		"completed":           completed,
		"pending":             total - completed,
		"progress_percentage": progress,
	}, nil
}

// BulkUpdateStatus is bulk_update_status.
func (m *MockSubtaskRepository) BulkUpdateStatus(_ context.Context, parentTaskID tmvo.TaskId, status string) (bool, error) {
	updated := false
	for _, s := range m.Subtasks.Values() {
		if s.ParentTaskID != nil && s.ParentTaskID.Value == parentTaskID.Value {
			// Python assigns the raw status string without validation.
			st := tmvo.TaskStatus{Value: status}
			s.Status = &st
			updated = true
		}
	}
	return updated, nil
}

// BulkComplete is bulk_complete.
func (m *MockSubtaskRepository) BulkComplete(ctx context.Context, parentTaskID tmvo.TaskId) (bool, error) {
	return m.BulkUpdateStatus(ctx, parentTaskID, "completed")
}

// RemoveSubtask is remove_subtask.
func (m *MockSubtaskRepository) RemoveSubtask(_ context.Context, parentTaskID, subtaskID string) (bool, error) {
	if m.Subtasks.Has(subtaskID) {
		s, _ := m.Subtasks.Get(subtaskID)
		if s.ParentTaskID != nil && s.ParentTaskID.Value == parentTaskID {
			m.Subtasks.Delete(subtaskID)
			return true, nil
		}
	}
	return false, nil
}

// DeleteByParentTaskID is delete_by_parent_task_id; returns whether anything was removed.
func (m *MockSubtaskRepository) DeleteByParentTaskID(_ context.Context, parentTaskID tmvo.TaskId) (bool, error) {
	toDelete := []string{}
	for _, s := range m.Subtasks.Values() {
		if s.ParentTaskID != nil && s.ParentTaskID.Value == parentTaskID.Value {
			toDelete = append(toDelete, mockSubtaskKey(s))
		}
	}
	for _, id := range toDelete {
		m.Subtasks.Delete(id)
	}
	return len(toDelete) > 0, nil
}

// MockTaskRepositoryFunc mirrors Python's `lambda p, b, u: MockTaskRepository()`.
type MockTaskRepositoryFunc func(projectID, gitBranchID, userID *string) *MockTaskRepository

// MockSubtaskRepositoryFunc mirrors Python's `lambda p, b, u: MockSubtaskRepository()`.
type MockSubtaskRepositoryFunc func(projectID, gitBranchID, userID *string) *MockSubtaskRepository

// MockRepositoryFactory is MockRepositoryFactory.
type MockRepositoryFactory struct {
	projectRepo   *MockProjectRepository
	gitBranchRepo *MockGitBranchRepository
	taskRepo      *MockTaskRepository
	subtaskRepo   *MockSubtaskRepository
}

// NewMockRepositoryFactory builds the factory with one instance of each mock.
func NewMockRepositoryFactory() *MockRepositoryFactory {
	return &MockRepositoryFactory{
		projectRepo:   NewMockProjectRepository(),
		gitBranchRepo: NewMockGitBranchRepository(),
		taskRepo:      NewMockTaskRepository(),
		subtaskRepo:   NewMockSubtaskRepository(),
	}
}

// GetProjectRepository is get_project_repository.
func (f *MockRepositoryFactory) GetProjectRepository() *MockProjectRepository { return f.projectRepo }

// GetGitBranchRepository is get_git_branch_repository.
func (f *MockRepositoryFactory) GetGitBranchRepository() *MockGitBranchRepository {
	return f.gitBranchRepo
}

// GetTaskRepository is get_task_repository; Python ignores the scope arguments.
func (f *MockRepositoryFactory) GetTaskRepository(_, _, _ *string) *MockTaskRepository {
	return f.taskRepo
}

// GetSubtaskRepository is get_subtask_repository; Python ignores the scope arguments.
func (f *MockRepositoryFactory) GetSubtaskRepository(_, _, _ *string) *MockSubtaskRepository {
	return f.subtaskRepo
}

// CreateMockRepositories is create_mock_repositories. Key order matches Python's dict.
func CreateMockRepositories() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("project", NewMockProjectRepository())
	m.Set("git_branch", NewMockGitBranchRepository())
	m.Set("task", MockTaskRepositoryFunc(func(_, _, _ *string) *MockTaskRepository { return NewMockTaskRepository() }))
	m.Set("subtask", MockSubtaskRepositoryFunc(func(_, _, _ *string) *MockSubtaskRepository { return NewMockSubtaskRepository() }))
	return m
}

// --- local helpers (unique names to avoid clashing with other files) ---

func containsString(haystack []string, needle string) bool {
	for _, v := range haystack {
		if v == needle {
			return true
		}
	}
	return false
}

func mockTaskField(t *entities.Task, key string) (any, bool) {
	switch key {
	case "id":
		if t.ID != nil {
			return t.ID.Value, true
		}
		return nil, true
	case "title":
		return t.Title, true
	case "description":
		return t.Description, true
	case "status":
		if t.Status != nil {
			return t.Status.Value, true
		}
		return nil, true
	case "priority":
		if t.Priority != nil {
			return t.Priority.Value, true
		}
		return nil, true
	case "git_branch_id":
		if t.GitBranchID != nil {
			return *t.GitBranchID, true
		}
		return nil, true
	case "context_id":
		if t.ContextID != nil {
			return *t.ContextID, true
		}
		return nil, true
	case "user_id":
		if t.UserID != nil {
			return *t.UserID, true
		}
		return nil, true
	case "completed_subtasks":
		return t.CompletedSubtasks, true
	case "assignees":
		return t.Assignees, true
	case "labels":
		return t.Labels, true
	default:
		return nil, false
	}
}
