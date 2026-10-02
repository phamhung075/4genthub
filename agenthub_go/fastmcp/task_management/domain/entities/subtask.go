package entities

import (
	"errors"
	"fmt"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Subtask is the subtask domain entity with business logic.
type Subtask struct {
	base.BaseTimestampEntity
	Title              string
	Description        string
	ParentTaskID       *value_objects.TaskId
	ID                 *value_objects.TaskId
	Status             *value_objects.TaskStatus
	Priority           *value_objects.Priority
	Assignees          []string
	ProgressPercentage int // 0-100
	ProgressHistory    map[string]any
	ProgressCount      int

	// Events is Python's `_events`.
	Events []events.Event
}

// NewSubtask applies the defaults, normalizes assignees (@ prefix / legacy
// roles), initializes timestamps and validates.
func NewSubtask(st Subtask) (*Subtask, error) {
	s := st
	if s.Status == nil {
		todo := mustTaskStatus("todo")
		s.Status = &todo
	}
	if s.Priority == nil {
		m := value_objects.PriorityMedium()
		s.Priority = &m
	}
	if s.Assignees == nil {
		s.Assignees = []string{}
	}
	if s.ProgressHistory == nil {
		s.ProgressHistory = map[string]any{}
	}
	if len(s.Assignees) > 0 {
		normalized := []string{}
		for _, a := range s.Assignees {
			if a != "" && strings.TrimSpace(a) != "" {
				v, _ := normalizeAssignee(a)
				normalized = append(normalized, v)
			}
		}
		s.Assignees = normalized
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

func (s *Subtask) GetEntityID() string {
	if s.ID != nil {
		return s.ID.String()
	}
	return fmt.Sprintf("subtask_%p", s)
}

func (s *Subtask) ValidateEntity() error {
	if strings.TrimSpace(s.Title) == "" {
		return value_objects.ValueErrorf("Subtask title cannot be empty")
	}
	if utf8.RuneCountInString(s.Title) > 200 {
		return value_objects.ValueErrorf("Subtask title cannot exceed 200 characters")
	}
	if utf8.RuneCountInString(s.Description) > 2000 {
		return value_objects.ValueErrorf("Subtask description cannot exceed 2000 characters")
	}
	if s.ParentTaskID == nil {
		return value_objects.ValueErrorf("Subtask must have a parent task ID")
	}
	return nil
}

// Equals: subtasks are equal if both have the same non-nil ID.
func (s *Subtask) Equals(o *Subtask) bool {
	return o != nil && s.ID != nil && o.ID != nil && *s.ID == *o.ID
}

// IsCompleted: status done OR progress at 100.
func (s *Subtask) IsCompleted() bool { return s.Status.IsCompleted() || s.ProgressPercentage >= 100 }

func (s *Subtask) CanBeAssigned() bool {
	return !s.IsCompleted() && s.Status.Value != string(value_objects.TaskStatusCancelled)
}

func (s *Subtask) idRepr() string {
	if s.ID == nil {
		return "None"
	}
	return s.ID.String()
}

func (s *Subtask) parentStr() string {
	if s.ParentTaskID == nil {
		return "None"
	}
	return s.ParentTaskID.String()
}

// emit appends a TaskUpdated event for the parent task with "<id>:<old>" / "<id>:<new>"
// values; updated_at is the datetime object itself (not its isoformat), as in Python.
func (s *Subtask) emit(field, old, new string) {
	ev := events.NewTaskUpdatedEvent()
	ev.TaskID = s.parentStr()
	ev.Changes = map[string]any{field: map[string]any{
		"old": s.idRepr() + ":" + old, "new": s.idRepr() + ":" + new, "updated_at": *s.UpdatedAt,
	}}
	s.Events = append(s.Events, ev)
}

func (s *Subtask) UpdateStatus(newStatus value_objects.TaskStatus) error {
	if !s.Status.CanTransitionTo(newStatus.Value) {
		return value_objects.ValueErrorf("Cannot transition from %s to %s", s.Status, newStatus)
	}
	old := *s.Status
	s.Status = &newStatus
	if err := s.Touch("status_changed"); err != nil {
		return err
	}
	switch newStatus.Value {
	case string(value_objects.TaskStatusDone):
		s.ProgressPercentage = 100
	case string(value_objects.TaskStatusTodo):
		if s.ProgressPercentage == 100 {
			s.ProgressPercentage = 0
		}
	}
	s.emit("subtask_status", old.String(), newStatus.String())
	return nil
}

func (s *Subtask) UpdatePriority(p value_objects.Priority) error {
	old := *s.Priority
	s.Priority = &p
	if err := s.Touch("priority_updated"); err != nil {
		return err
	}
	s.emit("subtask_priority", old.String(), p.String())
	return nil
}

func (s *Subtask) UpdateTitle(title string) error {
	if strings.TrimSpace(title) == "" {
		return value_objects.ValueErrorf("Subtask title cannot be empty")
	}
	old := s.Title
	s.Title = title
	if err := s.Touch("title_updated"); err != nil {
		return err
	}
	s.emit("subtask_title", old, title)
	return nil
}

func (s *Subtask) UpdateDescription(description string) error {
	old := s.Description
	s.Description = description
	if err := s.Touch("description_updated"); err != nil {
		return err
	}
	s.emit("subtask_description", old, description)
	return nil
}

func (s *Subtask) UpdateAssignees(assignees []string) error {
	validated := []string{}
	for _, a := range assignees {
		if a != "" && strings.TrimSpace(a) != "" {
			v, _ := normalizeAssignee(a)
			validated = append(validated, v)
		}
	}
	old := append([]string{}, s.Assignees...)
	s.Assignees = validated
	if err := s.Touch("assignees_updated"); err != nil {
		return err
	}
	s.emit("subtask_assignees", value_objects.PyRepr(old), value_objects.PyRepr(validated))
	return nil
}

func (s *Subtask) UpdateProgressPercentage(p int) error {
	if p < 0 || p > 100 {
		return value_objects.ValueErrorf("Progress percentage must be integer between 0-100, got: %d", p)
	}
	old := s.ProgressPercentage
	s.ProgressPercentage = p
	if err := s.Touch("progress_updated"); err != nil {
		return err
	}
	switch {
	case p == 0:
		st := mustTaskStatus("todo")
		s.Status = &st
	case p == 100:
		st := mustTaskStatus("done")
		s.Status = &st
	default:
		st := mustTaskStatus("in_progress")
		s.Status = &st
	}
	s.emit("subtask_progress", fmt.Sprint(old), fmt.Sprint(p))
	return nil
}

// AppendProgress appends numbered progress to the history.
func (s *Subtask) AppendProgress(content string) error {
	s.ProgressCount++
	header := fmt.Sprintf("=== Progress %d ===", s.ProgressCount)
	if s.ProgressHistory == nil {
		s.ProgressHistory = map[string]any{}
	}
	if err := s.Touch("progress_update"); err != nil {
		return err
	}
	s.ProgressHistory[fmt.Sprintf("progress_%d", s.ProgressCount)] = map[string]any{
		"content":         header + "\n" + content,
		"timestamp":       value_objects.IsoFormat(*s.UpdatedAt),
		"progress_number": s.ProgressCount,
	}
	ev := events.NewTaskUpdatedEvent()
	ev.TaskID = s.parentStr()
	ev.Changes = map[string]any{"subtask_progress_history": map[string]any{
		"old_value":  fmt.Sprintf("progress_added_%d", s.ProgressCount-1),
		"new_value":  fmt.Sprintf("progress_added_%d", s.ProgressCount),
		"subtask_id": s.idRepr(),
		"updated_at": value_objects.IsoFormat(*s.UpdatedAt),
	}}
	s.Events = append(s.Events, ev)
	return nil
}

func (s *Subtask) AddAssigneeRole(role value_objects.AgentRole) error {
	return s.AddAssignee("@" + string(role))
}

func (s *Subtask) AddAssignee(assignee string) error {
	if strings.TrimSpace(assignee) == "" {
		return nil
	}
	validated, _ := normalizeAssignee(assignee)
	if indexOf(s.Assignees, validated) >= 0 {
		return nil
	}
	s.Assignees = append(s.Assignees, validated)
	if err := s.Touch("assignee_added"); err != nil {
		return err
	}
	s.emit("subtask_assignees", "assignee_added", validated)
	return nil
}

func (s *Subtask) RemoveAssigneeRole(role value_objects.AgentRole) error {
	return s.RemoveAssignee("@" + string(role))
}

func (s *Subtask) RemoveAssignee(assignee string) error {
	i := indexOf(s.Assignees, assignee)
	if i < 0 {
		return nil
	}
	s.Assignees = append(s.Assignees[:i], s.Assignees[i+1:]...)
	if err := s.Touch("assignee_removed"); err != nil {
		return err
	}
	s.emit("subtask_assignees", "assignee_removed", assignee)
	return nil
}

// InheritAssigneesFromParent copies the parent's assignees when this subtask has none.
func (s *Subtask) InheritAssigneesFromParent(parent []string) error {
	if len(s.Assignees) == 0 && len(parent) > 0 {
		s.Assignees = append([]string{}, parent...)
		if err := s.Touch("assignees_inherited"); err != nil {
			return err
		}
		s.emit("subtask_assignees", "inherited_from_parent", value_objects.PyRepr(s.Assignees))
	}
	return nil
}

func (s *Subtask) HasAssignees() bool           { return len(s.Assignees) > 0 }
func (s *Subtask) ShouldInheritAssignees() bool { return !s.HasAssignees() }

// Complete marks the subtask done (no-op when already completed).
func (s *Subtask) Complete() error {
	if s.IsCompleted() {
		return nil
	}
	old := *s.Status
	done := mustTaskStatus("done")
	s.Status = &done
	s.ProgressPercentage = 100
	if err := s.Touch("subtask_completed"); err != nil {
		return err
	}
	s.emit("subtask_status", old.String(), s.Status.String())
	return nil
}

// Reopen resets a completed subtask to todo (progress is left unchanged).
func (s *Subtask) Reopen() error {
	if !s.IsCompleted() {
		return nil
	}
	old := *s.Status
	todo := mustTaskStatus("todo")
	s.Status = &todo
	if err := s.Touch("subtask_reopened"); err != nil {
		return err
	}
	s.emit("subtask_status", old.String(), s.Status.String())
	return nil
}

// GetEvents returns and clears the domain events.
func (s *Subtask) GetEvents() []events.Event {
	out := append([]events.Event{}, s.Events...)
	s.Events = s.Events[:0]
	return out
}

// ToDict converts the subtask to a dictionary; parent_task_id only when requested.
// Needs AgentNameResolver (see Task.ToDict).
func (s *Subtask) ToDict(includeParentID bool) (map[string]any, error) {
	if AgentNameResolver == nil {
		return nil, errors.New("entities.AgentNameResolver is not registered (application use_cases.agent_mappings)")
	}
	assignees := []string{}
	for _, a := range s.Assignees {
		assignees = append(assignees, AgentNameResolver(a))
	}
	var id any
	if s.ID != nil {
		id = s.ID.Value
	}
	result := map[string]any{
		"id": id, "title": s.Title, "description": s.Description,
		"status": s.Status.String(), "priority": s.Priority.String(), "assignees": assignees,
		"progress_percentage": s.ProgressPercentage, "progress_history": s.ProgressHistory,
		"progress_count": s.ProgressCount, "created_at": nil, "updated_at": nil,
	}
	if s.CreatedAt != nil {
		result["created_at"] = value_objects.IsoFormat(*s.CreatedAt)
	}
	if s.UpdatedAt != nil {
		result["updated_at"] = value_objects.IsoFormat(*s.UpdatedAt)
	}
	if includeParentID {
		result["parent_task_id"] = s.parentStr()
	}
	return result, nil
}

// SubtaskOptions are the kwargs Subtask.create passes through.
type SubtaskOptions struct {
	Assignees          []string
	ProgressPercentage int
	CreatedAt          *time.Time
	UpdatedAt          *time.Time
}

// CreateSubtask is the factory method.
func CreateSubtask(id value_objects.TaskId, title, description string, parent value_objects.TaskId,
	status *value_objects.TaskStatus, priority *value_objects.Priority, opts SubtaskOptions) (*Subtask, error) {
	st := Subtask{
		ID: &id, Title: title, Description: description, ParentTaskID: &parent, Status: status, Priority: priority,
		Assignees: opts.Assignees, ProgressPercentage: opts.ProgressPercentage,
	}
	st.CreatedAt, st.UpdatedAt = opts.CreatedAt, opts.UpdatedAt
	return NewSubtask(st)
}

// SubtaskFromDict mirrors Subtask.from_dict (missing keys take the Python defaults).
func SubtaskFromDict(data map[string]any, parent value_objects.TaskId) (*Subtask, error) {
	st := Subtask{ParentTaskID: &parent}
	var err error
	if v, _ := data["created_at"].(string); v != "" {
		t, err := value_objects.ParseISO(v)
		if err != nil {
			return nil, err
		}
		st.CreatedAt = &t
	}
	if v, _ := data["updated_at"].(string); v != "" {
		t, err := value_objects.ParseISO(v)
		if err != nil {
			return nil, err
		}
		st.UpdatedAt = &t
	}
	status, ok := data["status"].(string)
	if !ok {
		status = "todo"
	}
	ts, err := value_objects.TaskStatusFromString(status)
	if err != nil {
		return nil, err
	}
	st.Status = &ts
	prio, ok := data["priority"].(string)
	if !ok {
		prio = "medium"
	}
	p, err := value_objects.PriorityFromString(prio)
	if err != nil {
		return nil, err
	}
	st.Priority = &p
	if idS, _ := data["id"].(string); idS != "" {
		id, err := value_objects.NewTaskId(idS)
		if err != nil {
			return nil, err
		}
		st.ID = &id
	}
	st.Title, _ = data["title"].(string)
	st.Description, _ = data["description"].(string)
	if v, ok := data["assignees"]; ok {
		if st.Assignees, err = stringList(v); err != nil {
			return nil, err
		}
	}
	if v, ok := data["progress_percentage"]; ok {
		f := numberOf(v) // JSON numbers arrive as float64
		if f != float64(int(f)) {
			return nil, value_objects.TypeErrorf("progress_percentage must be an integer")
		}
		st.ProgressPercentage = int(f)
	}
	return NewSubtask(st)
}
