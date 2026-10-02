package entities

import (
	"fmt"
	"sort"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GitBranch is a git branch with a hierarchical task structure.
type GitBranch struct {
	base.BaseTimestampEntity
	ID            *value_objects.GitBranchId
	Name          string
	Description   string
	ProjectID     string
	GitBranchName *string

	RootTasks *OrderedMap[*Task] // task_id -> Task
	AllTasks  *OrderedMap[*Task] // flattened view for quick lookup

	AssignedAgentID *string
	AssignedAgents  []string
	Priority        *value_objects.Priority   // nil → medium
	Status          *value_objects.TaskStatus // nil → todo
	Archived        bool
}

// NewGitBranch applies the defaults, initializes timestamps and validates.
func NewGitBranch(b GitBranch) (*GitBranch, error) {
	s := b
	if s.RootTasks == nil {
		s.RootTasks = NewOrderedMap[*Task]()
	}
	if s.AllTasks == nil {
		s.AllTasks = NewOrderedMap[*Task]()
	}
	if s.AssignedAgents == nil {
		s.AssignedAgents = []string{}
	}
	if s.Priority == nil {
		m := value_objects.PriorityMedium()
		s.Priority = &m
	}
	if s.Status == nil {
		todo := mustTaskStatus("todo")
		s.Status = &todo
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// CreateGitBranch is the factory (generated UUID).
func CreateGitBranch(name, description, projectID string) (*GitBranch, error) {
	id := value_objects.GenerateNewGitBranchId()
	return NewGitBranch(GitBranch{ID: &id, Name: name, Description: description, ProjectID: projectID})
}

func (b *GitBranch) GetEntityID() string {
	if b.ID == nil {
		return "unknown"
	}
	return b.ID.Value
}

func (b *GitBranch) ValidateEntity() error {
	if b.ID == nil {
		return value_objects.ValueErrorf("GitBranch id cannot be empty")
	}
	if strings.TrimSpace(b.Name) == "" {
		return value_objects.ValueErrorf("GitBranch name cannot be empty")
	}
	if strings.TrimSpace(b.ProjectID) == "" {
		return value_objects.ValueErrorf("GitBranch project_id cannot be empty")
	}
	return nil
}

func taskKey(t *Task) string {
	if t.ID == nil {
		return ""
	}
	return t.ID.Value
}

func (b *GitBranch) AddRootTask(task *Task) error {
	k := taskKey(task)
	b.RootTasks.Set(k, task)
	b.AllTasks.Set(k, task)
	return b.Touch("root_task_added")
}

func (b *GitBranch) AddChildTask(parentTaskID string, child *Task) error {
	parent, ok := b.AllTasks.Get(parentTaskID)
	if !ok {
		return value_objects.ValueErrorf("Parent task %s not found in branch", parentTaskID)
	}
	k := taskKey(child)
	if _, err := parent.AddSubtask(k); err != nil {
		return err
	}
	b.AllTasks.Set(k, child)
	return b.Touch("child_task_added")
}

// RemoveTask removes a task and, recursively, its children.
func (b *GitBranch) RemoveTask(taskID string) (bool, error) {
	task, ok := b.AllTasks.Get(taskID)
	if !ok {
		return false, nil
	}
	b.RootTasks.Delete(taskID)
	for _, p := range b.AllTasks.Values() {
		if i := indexOf(p.Subtasks, taskID); i >= 0 {
			p.Subtasks = append(p.Subtasks[:i], p.Subtasks[i+1:]...)
		}
	}
	for _, child := range append([]string{}, task.Subtasks...) {
		if _, err := b.RemoveTask(child); err != nil {
			return false, err
		}
	}
	b.AllTasks.Delete(taskID)
	return true, b.Touch("task_removed")
}

func (b *GitBranch) GetTask(id string) *Task { t, _ := b.AllTasks.Get(id); return t }
func (b *GitBranch) HasTask(id string) bool  { return b.AllTasks.Has(id) }

func (b *GitBranch) GetAllTasks() *OrderedMap[*Task]  { return b.AllTasks.Copy() }
func (b *GitBranch) GetRootTasks() *OrderedMap[*Task] { return b.RootTasks.Copy() }
func (b *GitBranch) GetTaskCount() int                { return b.AllTasks.Len() }

func (b *GitBranch) countStatus(status string) int {
	n := 0
	for _, t := range b.AllTasks.Values() {
		if t.Status.Value == status {
			n++
		}
	}
	return n
}

func (b *GitBranch) GetCompletedTaskCount() int { return b.countStatus("done") }
func (b *GitBranch) GetActiveTaskCount() int    { return b.countStatus("in_progress") }

func (b *GitBranch) GetProgressPercentage() float64 {
	total := b.GetTaskCount()
	if total == 0 {
		return 0.0
	}
	return float64(b.GetCompletedTaskCount()) / float64(total) * 100.0
}

func (b *GitBranch) GetTreeStatus() map[string]any {
	statusCounts, priorityCounts := map[string]int{}, map[string]int{}
	for _, t := range b.AllTasks.Values() {
		statusCounts[t.Status.Value]++
		priorityCounts[t.Priority.Value]++
	}
	return map[string]any{
		"tree_name": b.Name, "total_tasks": b.GetTaskCount(), "completed_tasks": b.GetCompletedTaskCount(),
		"progress_percentage": b.GetProgressPercentage(),
		"status_breakdown":    statusCounts, "priority_breakdown": priorityCounts,
	}
}

func (b *GitBranch) GetAvailableTasks() []*Task {
	out := []*Task{}
	for _, t := range b.AllTasks.Values() {
		if t.Status.Value != "done" {
			out = append(out, t)
		}
	}
	return out
}

var branchPriorityOrder = map[string]int{"critical": 5, "urgent": 4, "high": 3, "medium": 2, "low": 1}

// GetNextTask returns the highest-priority available task (first wins on ties).
func (b *GitBranch) GetNextTask() *Task {
	available := b.GetAvailableTasks()
	if len(available) == 0 {
		return nil
	}
	rank := func(t *Task) int {
		if v, ok := branchPriorityOrder[t.Priority.Value]; ok {
			return v
		}
		return 2
	}
	sort.SliceStable(available, func(i, j int) bool { return rank(available[i]) > rank(available[j]) })
	return available[0]
}

// UpdateStatusBasedOnTasks derives the branch status from its tasks' statuses.
func (b *GitBranch) UpdateStatusBasedOnTasks() error {
	if b.AllTasks.Len() == 0 {
		todo := mustTaskStatus("todo")
		b.Status = &todo
		return nil
	}
	tasks := b.AllTasks.Values()
	all := true
	for _, t := range tasks {
		if t.Status.Value != "done" {
			all = false
			break
		}
	}
	next := "todo"
	if all {
		next = "done"
	} else {
		for _, s := range []string{"in_progress", "blocked", "review", "testing"} {
			if b.countStatus(s) > 0 {
				next = s
				break
			}
		}
	}
	st := mustTaskStatus(next)
	b.Status = &st
	return b.Touch("status_updated")
}

func (b *GitBranch) AssignAgent(agentID string) error {
	b.AssignedAgentID = &agentID
	return b.Touch("agent_assigned")
}

func (b *GitBranch) UnassignAgent() error {
	b.AssignedAgentID = nil
	return b.Touch("agent_unassigned")
}

func (b *GitBranch) IsAssignedToAgent(agentID string) bool {
	return b.AssignedAgentID != nil && *b.AssignedAgentID == agentID
}

func (b *GitBranch) ToDict() map[string]any {
	id := ""
	if b.ID != nil {
		id = b.ID.Value
	}
	return map[string]any{
		"id": id, "name": b.Name, "git_branch_name": strOrNil(b.GitBranchName), "description": b.Description,
		"project_id": b.ProjectID, "created_at": value_objects.IsoFormat(*b.CreatedAt),
		"updated_at": value_objects.IsoFormat(*b.UpdatedAt), "assigned_agent_id": strOrNil(b.AssignedAgentID),
		"assigned_agents": append([]string{}, b.AssignedAgents...), "priority": b.Priority.Value,
		"status": b.Status.Value, "archived": b.Archived,
	}
}

// String mirrors __repr__.
func (b *GitBranch) String() string {
	id := "None"
	if b.ID != nil {
		id = b.ID.Value
	}
	return fmt.Sprintf("GitBranch(id='%s', name='%s', project_id='%s', tasks=%d)", id, b.Name, b.ProjectID, b.GetTaskCount())
}
