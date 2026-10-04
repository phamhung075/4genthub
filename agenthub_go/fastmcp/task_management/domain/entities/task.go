package entities

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentNameResolver is task.to_dict's lazy import of
// application.use_cases.agent_mappings.resolve_agent_name. The domain package
// cannot import the application layer in Go (import cycle), so the use_cases
// package registers the function in its init().
var AgentNameResolver func(name string) string

// NormalizeDatetime converts a naive or aware datetime to a UTC-aware one.
func NormalizeDatetime(s string) (time.Time, error) {
	t, err := value_objects.ParseISO(s)
	if err != nil {
		return time.Time{}, err
	}
	return t.UTC(), nil
}

// Task is the task domain entity with business logic. Nil pointers mirror
// Python None; zero values of ProgressState/Status/Priority take the Python defaults.
type Task struct {
	base.BaseTimestampEntity
	Title             string
	Description       string
	ID                *value_objects.TaskId
	Status            *value_objects.TaskStatus
	Priority          *value_objects.Priority
	GitBranchID       *string
	ProgressHistory   map[string]any
	ProgressCount     int
	EstimatedEffort   string
	Assignees         []string
	Labels            []string
	Dependencies      []value_objects.TaskId
	Subtasks          []string
	CompletedSubtasks int
	DueDate           *string
	ContextID         *string
	UserID            *string

	// OverallProgress is an int in Python until _recalculate_overall_progress
	// turns it into a float; OverallProgressIsFloat keeps that distinction for to_dict.
	OverallProgress        float64
	OverallProgressIsFloat bool
	ProgressState          value_objects.ProgressState
	ProgressTimeline       *value_objects.ProgressTimeline

	// Events is Python's `_events` (separate from the base entity's timestamp events).
	Events []events.Event

	// CompletionSummary is `_completion_summary`; TestingNotes is the dynamic `_testing_notes` attribute.
	CompletionSummary *string
	TestingNotes      *string
}

// NewTask applies the Python defaults, initializes timestamps and validates.
func NewTask(t Task) (*Task, error) {
	s := t
	if s.Status == nil {
		todo := mustTaskStatus("todo")
		s.Status = &todo
	}
	if s.Priority == nil {
		m := value_objects.PriorityMedium()
		s.Priority = &m
	}
	if s.ProgressState == "" {
		s.ProgressState = value_objects.ProgressStateInitial
	}
	if s.ProgressHistory == nil {
		s.ProgressHistory = map[string]any{}
	}
	if s.Assignees == nil {
		s.Assignees = []string{}
	}
	if s.Labels == nil {
		s.Labels = []string{}
	}
	if s.Dependencies == nil {
		s.Dependencies = []value_objects.TaskId{}
	}
	if s.Subtasks == nil {
		s.Subtasks = []string{}
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// CreateTask is the factory: NewTask plus a TaskCreated event.
func CreateTask(t Task) (*Task, error) {
	task, err := NewTask(t)
	if err != nil {
		return nil, err
	}
	ev := events.NewTaskCreatedEvent()
	ev.TaskID, ev.Title = task.idRef(), task.Title
	task.Events = append(task.Events, ev)
	return task, nil
}

func mustTaskStatus(v string) value_objects.TaskStatus {
	s, err := value_objects.NewTaskStatus(v)
	if err != nil {
		panic(err)
	}
	return s
}

// idRef is the task ID as Python passes it into TaskCreatedEvent/TaskUpdatedEvent:
// the TaskId object itself (nil for None), not its string.
func (t *Task) idRef() any {
	if t.ID == nil {
		return nil
	}
	return *t.ID
}

func (t *Task) idStr() string {
	if t.ID == nil {
		return "None"
	}
	return t.ID.String()
}

func (t *Task) GetEntityID() string {
	if t.ID == nil {
		return "unknown"
	}
	return t.ID.String()
}

func (t *Task) ValidateEntity() error {
	if strings.TrimSpace(t.Title) == "" {
		return value_objects.ValueErrorf("Task title cannot be empty")
	}
	if strings.TrimSpace(t.Description) == "" {
		return value_objects.ValueErrorf("Task description cannot be empty")
	}
	if utf8.RuneCountInString(t.Title) > 200 {
		return value_objects.ValueErrorf("Task title cannot exceed 200 characters")
	}
	if utf8.RuneCountInString(t.Description) > 2000 {
		return value_objects.ValueErrorf("Task description cannot exceed 2000 characters")
	}
	return nil
}

// Equals: tasks are equal if they have the same ID.
func (t *Task) Equals(o *Task) bool {
	if o == nil {
		return false
	}
	if t.ID == nil || o.ID == nil {
		return t.ID == nil && o.ID == nil
	}
	return *t.ID == *o.ID
}

func (t *Task) IsBlocked() bool   { return t.Status.Value == string(value_objects.TaskStatusBlocked) }
func (t *Task) IsCompleted() bool { return t.Status.IsCompleted() }
func (t *Task) CanBeAssigned() bool {
	return t.Status.Value != "done" && t.Status.Value != "cancelled"
}
func (t *Task) SubtaskCount() int { return len(t.Subtasks) }

// ContextData builds the context_data structure from the task fields.
func (t *Task) ContextData() map[string]any {
	var taskID any
	if t.ID != nil {
		taskID = t.ID.Value
	}
	assignees, labels := t.Assignees, t.Labels
	if len(assignees) == 0 {
		assignees = []string{}
	}
	if len(labels) == 0 {
		labels = []string{}
	}
	var subPct any = 0.0
	if t.SubtaskCount() > 0 {
		subPct = float64(t.CompletedSubtasks) / float64(t.SubtaskCount()) * 100
	}
	return map[string]any{
		"metadata": map[string]any{
			"task_id": taskID, "status": t.Status.Value, "priority": t.Priority.Value,
			"assignees": assignees, "labels": labels, "version": 1,
		},
		"objective": map[string]any{
			"title": t.Title, "description": t.Description, "estimated_effort": t.EstimatedEffort,
		},
		"progress":     map[string]any{"completion_percentage": t.progressValue(), "time_spent_minutes": 0},
		"dependencies": map[string]any{},
		"subtasks": map[string]any{
			"total_count": t.SubtaskCount(), "completed_count": t.CompletedSubtasks, "progress_percentage": subPct,
		},
	}
}

// progressValue returns overall_progress as int or float like Python's dynamic value.
func (t *Task) progressValue() any {
	if t.OverallProgressIsFloat {
		return t.OverallProgress
	}
	return int(t.OverallProgress)
}

func (t *Task) updatedAtISO() any {
	if t.UpdatedAt == nil {
		return nil
	}
	return value_objects.IsoFormat(*t.UpdatedAt)
}

// emit appends a TaskUpdated event whose single change is field → details (+ updated_at).
func (t *Task) emit(field string, details map[string]any) {
	details["updated_at"] = t.updatedAtISO()
	ev := events.NewTaskUpdatedEvent()
	ev.TaskID = t.idRef()
	ev.Changes = map[string]any{field: details}
	t.Events = append(t.Events, ev)
}

func (t *Task) UpdateStatus(newStatus value_objects.TaskStatus) error {
	if !t.Status.CanTransitionTo(newStatus.Value) {
		return value_objects.ValueErrorf("Cannot transition from %s to %s", t.Status, newStatus)
	}
	old := *t.Status
	t.Status = &newStatus
	if err := t.Touch("status_update"); err != nil {
		return err
	}
	t.emit("status", map[string]any{"old_value": old.String(), "new_value": newStatus.String()})
	return nil
}

func (t *Task) UpdatePriority(p value_objects.Priority) error {
	old := *t.Priority
	t.Priority = &p
	if err := t.Touch("priority_update"); err != nil {
		return err
	}
	t.emit("priority", map[string]any{"old_value": old.String(), "new_value": p.String()})
	return nil
}

func (t *Task) UpdateTitle(title string) error {
	if strings.TrimSpace(title) == "" {
		return value_objects.ValueErrorf("Task title cannot be empty")
	}
	old := t.Title
	t.Title = title
	if err := t.Touch("title_update"); err != nil {
		return err
	}
	t.emit("title", map[string]any{"old_value": old, "new_value": title})
	return nil
}

func (t *Task) UpdateDescription(description string) error {
	if strings.TrimSpace(description) == "" {
		return value_objects.ValueErrorf("Task description cannot be empty")
	}
	old := t.Description
	t.Description = description
	if err := t.Touch("description_update"); err != nil {
		return err
	}
	t.emit("description", map[string]any{"old_value": old, "new_value": description})
	return nil
}

// AppendProgress appends numbered progress to the history.
func (t *Task) AppendProgress(content string) error {
	t.ProgressCount++
	header := fmt.Sprintf("=== Progress %d ===", t.ProgressCount)
	if t.ProgressHistory == nil {
		t.ProgressHistory = map[string]any{}
	}
	if err := t.Touch("progress_update"); err != nil {
		return err
	}
	t.ProgressHistory[fmt.Sprintf("progress_%d", t.ProgressCount)] = map[string]any{
		"content":         header + "\n" + content,
		"timestamp":       value_objects.IsoFormat(*t.UpdatedAt),
		"progress_number": t.ProgressCount,
	}
	t.ContextID = nil
	t.emit("progress_history", map[string]any{
		"old_value": fmt.Sprintf("progress_added_%d", t.ProgressCount-1),
		"new_value": fmt.Sprintf("progress_added_%d", t.ProgressCount),
	})
	return nil
}

// UpdateEstimatedEffort falls back to the MEDIUM label for invalid values.
func (t *Task) UpdateEstimatedEffort(effort string) error {
	if _, err := value_objects.NewEstimatedEffort(effort); err != nil {
		effort = value_objects.EstimatedEffortMedium().Value
	}
	old := t.EstimatedEffort
	t.EstimatedEffort = effort
	if err := t.Touch("estimated_effort_update"); err != nil {
		return err
	}
	t.emit("estimated_effort", map[string]any{"old_value": old, "new_value": effort})
	return nil
}

// normalizeAssignee resolves legacy roles, valid roles and @-prefixed names;
// known is false when the assignee is none of those.
func normalizeAssignee(assignee string) (validated string, known bool) {
	if resolved, ok := value_objects.ResolveLegacyRole(assignee); ok {
		if !strings.HasPrefix(resolved, "@") {
			resolved = "@" + resolved
		}
		return resolved, true
	}
	if value_objects.IsValidRole(assignee) {
		if !strings.HasPrefix(assignee, "@") {
			assignee = "@" + assignee
		}
		return assignee, true
	}
	if strings.HasPrefix(assignee, "@") {
		return assignee, true
	}
	return assignee, false
}

func (t *Task) UpdateAssignees(assignees []string) error {
	validated, err := NormalizeAssignees(assignees)
	if err != nil {
		return err
	}
	old := append([]string{}, t.Assignees...)
	t.Assignees = validated
	if err := t.Touch("assignees_update"); err != nil {
		return err
	}
	t.emit("assignees", map[string]any{"old_value": old, "new_value": validated})
	return nil
}

// AddAssigneeRole adds an AgentRole assignee as "@<role>".
func (t *Task) AddAssigneeRole(role value_objects.AgentRole) error {
	return t.AddAssignee("@" + string(role))
}

func (t *Task) AddAssignee(assignee string) error {
	if strings.TrimSpace(assignee) == "" {
		return nil
	}
	normalized, err := NormalizeAssignees([]string{assignee})
	if err != nil {
		return err
	}
	validated := normalized[0]
	if indexOf(t.Assignees, validated) >= 0 {
		return nil
	}
	t.Assignees = append(t.Assignees, validated)
	if err := t.Touch("assignee_added"); err != nil {
		return err
	}
	t.emit("assignees", map[string]any{"action": "assignee_added", "new_value": validated})
	return nil
}

func (t *Task) RemoveAssigneeRole(role value_objects.AgentRole) error {
	return t.RemoveAssignee("@" + string(role))
}

func (t *Task) RemoveAssignee(assignee string) error {
	i := indexOf(t.Assignees, assignee)
	if i < 0 {
		return nil
	}
	t.Assignees = append(t.Assignees[:i], t.Assignees[i+1:]...)
	if err := t.Touch("assignee_removed"); err != nil {
		return err
	}
	t.emit("assignees", map[string]any{"action": "assignee_removed", "removed_value": assignee})
	return nil
}

func (t *Task) HasAssignee(a string) bool { return indexOf(t.Assignees, a) >= 0 }

func (t *Task) GetPrimaryAssignee() *string {
	if len(t.Assignees) == 0 {
		return nil
	}
	return &t.Assignees[0]
}

func (t *Task) GetAssigneesCount() int { return len(t.Assignees) }
func (t *Task) IsMultiAssignee() bool  { return len(t.Assignees) > 1 }

func titleName(s string) string {
	return value_objects.PyTitle(strings.ReplaceAll(strings.ReplaceAll(s, "-", " "), "_", " "))
}

func roleInfo(assignee string) map[string]any {
	if role, ok := value_objects.GetRoleBySlug(assignee); ok {
		var md any
		if m := value_objects.GetRoleMetadataFromYaml(role); m != nil {
			md = m
		}
		return map[string]any{
			"role": string(role), "display_name": role.DisplayName(), "folder_name": role.FolderName(), "metadata": md,
		}
	}
	return map[string]any{
		"role": assignee, "display_name": titleName(assignee),
		"folder_name": strings.ReplaceAll(assignee, "-", "_"), "metadata": nil,
	}
}

// GetAssigneesInfo returns role information for all assignees.
func (t *Task) GetAssigneesInfo() []map[string]any {
	info := []map[string]any{}
	for _, a := range t.Assignees {
		if a == "" {
			continue
		}
		info = append(info, roleInfo(a))
	}
	return info
}

func (t *Task) GetInheritedAssigneesForSubtasks() []string {
	return append([]string{}, t.Assignees...)
}

// NormalizeAssignees is the one assignee rule of every path that stores assignees (REST and
// MCP create, task and subtask updates, subtask creation): blank entries are dropped, the rest is stripped,
// '@<name>' (a seat key or a role) is kept as given, a bare known role or legacy name becomes
// '@<role>', and any other bare name is rejected.
func NormalizeAssignees(assignees []string) ([]string, error) {
	if len(assignees) == 0 {
		return []string{}, nil
	}
	validated, invalid := []string{}, []string{}
	for _, a := range assignees {
		if clean := value_objects.PyStrip(a); clean != "" {
			if v, known := normalizeAssignee(clean); known {
				validated = append(validated, v)
			} else {
				invalid = append(invalid, a)
			}
		}
	}
	if len(invalid) > 0 {
		return nil, value_objects.ValueErrorf(
			"Invalid assignees: %s. An assignee is '@<seat_key>' or a known agent role.", value_objects.PyRepr(invalid))
	}
	return validated, nil
}

// UpdateLabels keeps non-empty labels of at most 50 characters (trimmed).
func (t *Task) UpdateLabels(labels []string) error {
	validated := []string{}
	for _, l := range labels {
		if n := strings.TrimSpace(l); n != "" && utf8.RuneCountInString(n) <= 50 {
			validated = append(validated, n)
		}
	}
	old := append([]string{}, t.Labels...)
	t.Labels = validated
	if err := t.Touch("labels_update"); err != nil {
		return err
	}
	t.emit("labels", map[string]any{"old_value": old, "new_value": validated})
	return nil
}

// UpdateDueDate normalizes to a UTC ISO string; nil clears it.
func (t *Task) UpdateDueDate(dueDate *string) error {
	if dueDate != nil {
		n, err := NormalizeDatetime(*dueDate)
		if err != nil {
			return value_objects.ValueErrorf(
				"Invalid due date format: %s. Expected ISO 8601 format (e.g., '2025-10-29' or '2025-10-29T23:59:59+00:00'). Error: %s",
				*dueDate, err.Error())
		}
		iso := value_objects.IsoFormat(n)
		dueDate = &iso
	}
	old := t.DueDate
	t.DueDate = dueDate
	if err := t.Touch("due_date_update"); err != nil {
		return err
	}
	t.emit("due_date", map[string]any{"old_value": strOrNil(old), "new_value": strOrNil(dueDate)})
	return nil
}

func (t *Task) MarkAsDeleted() error {
	if err := t.Touch("task_deleted"); err != nil {
		return err
	}
	ev := events.NewTaskDeletedEvent()
	ev.TaskID = t.idStr()
	t.Events = append(t.Events, ev)
	return nil
}

func numberOf(v any) float64 {
	switch n := v.(type) {
	case int:
		return float64(n)
	case int64:
		return float64(n)
	case float64:
		return n
	}
	return 0
}

// GetProgressHistoryText joins the history entries ordered by progress number.
func (t *Task) GetProgressHistoryText() string {
	if len(t.ProgressHistory) == 0 {
		return ""
	}
	type entry struct {
		key     string
		number  float64
		content string
	}
	entries := []entry{}
	for k, v := range t.ProgressHistory {
		m, _ := v.(map[string]any)
		c, _ := m["content"].(string)
		entries = append(entries, entry{k, numberOf(m["progress_number"]), c})
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].number != entries[j].number {
			return entries[i].number < entries[j].number
		}
		return entries[i].key < entries[j].key
	})
	parts := make([]string, len(entries))
	for i, e := range entries {
		parts[i] = e.content
	}
	return strings.Join(parts, "\n\n")
}

func (t *Task) AddDependency(dep value_objects.TaskId) error {
	if t.ID != nil && dep == *t.ID {
		return value_objects.ValueErrorf("Task cannot depend on itself")
	}
	if !t.HasDependency(dep) {
		t.Dependencies = append(t.Dependencies, dep)
		return t.Touch("dependency_added")
	}
	return nil
}

func (t *Task) RemoveDependency(dep value_objects.TaskId) error {
	for i, d := range t.Dependencies {
		if d.Value == dep.Value {
			t.Dependencies = append(t.Dependencies[:i], t.Dependencies[i+1:]...)
			return t.Touch("dependency_removed")
		}
	}
	return nil
}

func (t *Task) HasDependency(dep value_objects.TaskId) bool {
	for _, d := range t.Dependencies {
		if d.Value == dep.Value {
			return true
		}
	}
	return false
}

func (t *Task) GetDependencyIDs() []string {
	ids := make([]string, len(t.Dependencies))
	for i, d := range t.Dependencies {
		ids[i] = d.Value
	}
	return ids
}

func (t *Task) ClearDependencies() error {
	if len(t.Dependencies) > 0 {
		t.Dependencies = []value_objects.TaskId{}
		return t.Touch("dependencies_cleared")
	}
	return nil
}

// HasCircularDependency is the simplified immediate-cycle check.
func (t *Task) HasCircularDependency(dep value_objects.TaskId) bool {
	if t.ID != nil && dep == *t.ID {
		return true
	}
	return t.HasDependency(dep)
}

// AddLabel replaces unknown labels by the first suggestion, if any.
func (t *Task) AddLabel(label string) error {
	if label == "" {
		return nil
	}
	valid := label
	if !(value_objects.LabelValidator{}).IsValidLabel(label) {
		if s := value_objects.SuggestLabels(label); len(s) > 0 {
			valid = s[0]
		}
	}
	if indexOf(t.Labels, valid) < 0 {
		t.Labels = append(t.Labels, valid)
		return t.Touch("label_added")
	}
	return nil
}

func (t *Task) RemoveLabel(label string) error {
	if i := indexOf(t.Labels, label); i >= 0 {
		t.Labels = append(t.Labels[:i], t.Labels[i+1:]...)
		return t.Touch("label_removed")
	}
	return nil
}

func (t *Task) AddSubtask(id string) (string, error) {
	if id == "" {
		return "", value_objects.ValueErrorf("Subtask ID must be a non-empty string")
	}
	if indexOf(t.Subtasks, id) < 0 {
		t.Subtasks = append(t.Subtasks, id)
		if err := t.Touch("subtask_added"); err != nil {
			return "", err
		}
		t.emit("subtasks", map[string]any{"action": "subtask_added", "new_value": id, "subtask_count": len(t.Subtasks)})
	}
	return id, nil
}

func (t *Task) RemoveSubtask(id string) (bool, error) {
	i := indexOf(t.Subtasks, id)
	if i < 0 {
		return false, nil
	}
	t.Subtasks = append(t.Subtasks[:i], t.Subtasks[i+1:]...)
	if err := t.Touch("subtask_removed"); err != nil {
		return false, err
	}
	t.emit("subtasks", map[string]any{"action": "subtask_removed", "removed_value": id, "subtask_count": len(t.Subtasks)})
	return true, nil
}

func (t *Task) IncrementCompletedSubtasks() error {
	t.CompletedSubtasks++
	if err := t.Touch("completed_subtasks_incremented"); err != nil {
		return err
	}
	t.emit("completed_subtasks", map[string]any{"action": "incremented", "new_value": t.CompletedSubtasks})
	return nil
}

func (t *Task) DecrementCompletedSubtasks() error {
	if t.CompletedSubtasks > 0 {
		t.CompletedSubtasks--
		if err := t.Touch("completed_subtasks_decremented"); err != nil {
			return err
		}
		t.emit("completed_subtasks", map[string]any{"action": "decremented", "new_value": t.CompletedSubtasks})
	}
	return nil
}

// UpdateSubtask is a no-op kept by the Python entity (subtasks live in the subtask repository).
func (t *Task) UpdateSubtask(string, map[string]any) bool { return false }

// CompleteSubtask is a no-op kept by the Python entity.
func (t *Task) CompleteSubtask(string) bool { return false }

// CompleteTask sets the status to done; a completion summary is required.
func (t *Task) CompleteTask(completionSummary string, contextUpdatedAt *time.Time) error {
	if strings.TrimSpace(completionSummary) == "" {
		return exceptions.NewMissingCompletionSummaryError(t.idStr())
	}
	if contextUpdatedAt != nil && t.ContextID != nil && !contextUpdatedAt.After(*t.UpdatedAt) {
		diff := value_objects.PyTotalSeconds(t.UpdatedAt.Sub(*contextUpdatedAt))
		if t.ID == nil {
			return errors.New("AttributeError: 'NoneType' object has no attribute 'value'")
		}
		return value_objects.ValueErrorf(
			"Context must be updated AFTER the task was last modified. "+
				"Task was updated %.0f seconds after context. "+
				"Please update the context with your progress before completing the task. "+
				"Use: manage_context(action='add_progress', level='task', "+
				"context_id='%s', content='Your progress summary') before trying to complete.", diff, t.ID.Value)
	}
	t.CompletionSummary = &completionSummary
	old := *t.Status
	done := mustTaskStatus("done")
	t.Status = &done
	t.ProgressState = value_objects.ProgressStateComplete
	t.OverallProgress, t.OverallProgressIsFloat = 100, false
	if err := t.Touch("task_completed"); err != nil {
		return err
	}
	t.emit("status", map[string]any{
		"old_value": old.String(), "new_value": t.Status.String(), "completion_summary": completionSummary,
	})
	if len(t.Subtasks) > 0 {
		t.emit("subtasks", map[string]any{"action": "all_subtasks_completed", "subtask_ids": t.Subtasks})
	}
	return nil
}

// UpdateProgressState derives progress_state from the status and progress.
func (t *Task) UpdateProgressState() {
	status := strings.ToLower(t.Status.Value)
	switch {
	case t.Status.IsCompleted():
		t.ProgressState = value_objects.ProgressStateComplete
	case t.OverallProgress == 0 && (status == "todo" || status == "pending"):
		t.ProgressState = value_objects.ProgressStateInitial
	case t.OverallProgress > 0 || status == "in_progress" || status == "in-progress" || status == "active":
		t.ProgressState = value_objects.ProgressStateInProgress
	default:
		t.ProgressState = value_objects.ProgressStateFromProgressPercentage(int(t.OverallProgress))
	}
}

func (t *Task) SetStatus(status value_objects.TaskStatus) error {
	old := *t.Status
	t.Status = &status
	t.UpdateProgressState()
	if err := t.Touch("status_set"); err != nil {
		return err
	}
	t.emit("status", map[string]any{"old_value": old.String(), "new_value": status.String()})
	return nil
}

func (t *Task) SetProgressPercentage(percentage int) error {
	if percentage < 0 || percentage > 100 {
		return value_objects.ValueErrorf("Progress percentage must be between 0 and 100, got %d", percentage)
	}
	old := t.progressValue()
	t.OverallProgress, t.OverallProgressIsFloat = float64(percentage), false
	t.UpdateProgressState()
	if err := t.Touch("progress_percentage_set"); err != nil {
		return err
	}
	t.emit("overall_progress", map[string]any{"old_value": old, "new_value": percentage})
	return nil
}

func (t *Task) GetSubtask(id string) *string {
	if indexOf(t.Subtasks, id) >= 0 {
		return &id
	}
	return nil
}

// GetSubtaskByID is the alias of GetSubtask.
func (t *Task) GetSubtaskByID(id string) *string { return t.GetSubtask(id) }

// GetSubtaskProgress: only IDs are known here, so completed/percentage are always 0.
func (t *Task) GetSubtaskProgress() map[string]any {
	return map[string]any{"total": len(t.Subtasks), "completed": 0, "percentage": 0}
}

// AllSubtasksCompleted is conservative: false whenever subtasks exist.
func (t *Task) AllSubtasksCompleted() bool { return len(t.Subtasks) == 0 }

func (t *Task) IsOverdue() bool {
	if t.DueDate == nil || *t.DueDate == "" {
		return false
	}
	due, err := value_objects.ParseISO(*t.DueDate)
	if err != nil {
		return false
	}
	if !strings.ContainsAny((*t.DueDate)[min(10, len(*t.DueDate)):], "+-Z") {
		due = time.Date(due.Year(), due.Month(), due.Day(), due.Hour(), due.Minute(), due.Second(), due.Nanosecond(), time.UTC)
	}
	return time.Now().UTC().After(due) && !t.Status.IsCompleted()
}

// GetSuggestedLabels returns up to five labels whose keywords occur in the task text.
func (t *Task) GetSuggestedLabels(context string) []string {
	content := strings.ToLower(t.Title + " " + t.Description + " " + context)
	suggestions := []string{}
	for _, l := range value_objects.CommonLabelValues {
		for _, k := range l.GetKeywords() {
			if strings.Contains(content, k) {
				suggestions = append(suggestions, string(l))
				break
			}
		}
	}
	if len(suggestions) > 5 {
		suggestions = suggestions[:5]
	}
	return suggestions
}

func (t *Task) GetEffortLevel() string {
	e, err := value_objects.NewEstimatedEffort(t.EstimatedEffort)
	if err != nil {
		return "medium"
	}
	return e.GetLevel()
}

// GetAssigneeRoleInfo returns role info for the primary assignee; empty metadata becomes nil.
func (t *Task) GetAssigneeRoleInfo() map[string]any {
	if len(t.Assignees) == 0 {
		return nil
	}
	info := roleInfo(t.Assignees[0])
	if md, ok := info["metadata"].(map[string]any); ok && len(md) == 0 {
		info["metadata"] = nil
	}
	return info
}

func (t *Task) CanBeStarted() bool { return t.Status.IsTodo() }

func (t *Task) SetContextID(id string) error {
	t.ContextID = &id
	return t.Touch("context_id_set")
}

func (t *Task) ClearContextID() error {
	t.ContextID = nil
	return t.Touch("context_id_cleared")
}

func (t *Task) HasUpdatedContext() bool { return t.ContextID != nil }

func (t *Task) GetCompletionSummary() *string { return t.CompletionSummary }

// CanBeCompleted: all subtasks done and, when given, context updated after the task.
func (t *Task) CanBeCompleted(contextUpdatedAt *time.Time) bool {
	if !t.AllSubtasksCompleted() {
		return false
	}
	if contextUpdatedAt != nil {
		return contextUpdatedAt.After(*t.UpdatedAt)
	}
	return true
}

// ProgressUpdate carries update_progress' optional arguments.
type ProgressUpdate struct {
	Type        value_objects.ProgressType
	Percentage  float64
	Description *string
	Metadata    map[string]any
	AgentID     *string
}

func progressMetadataFrom(m map[string]any) (value_objects.ProgressMetadata, error) {
	pm := value_objects.NewProgressMetadata()
	if v, ok := m["blockers"]; ok {
		s, err := stringList(v)
		if err != nil {
			return pm, err
		}
		pm.Blockers = s
	}
	if v, ok := m["dependencies"]; ok {
		s, err := stringList(v)
		if err != nil {
			return pm, err
		}
		pm.Dependencies = s
	}
	if v, ok := m["confidence_level"]; ok {
		pm.ConfidenceLevel = numberOf(v)
	}
	if v, ok := m["notes"].(string); ok {
		pm.Notes = &v
	}
	switch v := m["estimated_completion"].(type) {
	case time.Time:
		pm.EstimatedCompletion = &v
	case *time.Time:
		pm.EstimatedCompletion = v
	case string:
		ts, err := value_objects.ParseISO(v)
		if err != nil {
			return pm, err
		}
		pm.EstimatedCompletion = &ts
	}
	return pm, nil
}

func stringList(v any) ([]string, error) {
	switch l := v.(type) {
	case []string:
		return append([]string{}, l...), nil
	case []any:
		out := []string{}
		for _, e := range l {
			s, ok := e.(string)
			if !ok {
				return nil, value_objects.TypeErrorf("expected a list of strings")
			}
			out = append(out, s)
		}
		return out, nil
	}
	return nil, value_objects.TypeErrorf("expected a list of strings")
}

// UpdateProgress records a progress snapshot for a progress type.
func (t *Task) UpdateProgress(u ProgressUpdate) error {
	if !(u.Percentage >= 0 && u.Percentage <= 100) {
		return value_objects.ValueErrorf("Progress percentage must be between 0 and 100, got %s", value_objects.PyStr(u.Percentage))
	}
	if t.ProgressTimeline == nil {
		t.ProgressTimeline = value_objects.NewProgressTimeline(t.idStr())
	}
	old := 0.0
	if latest, ok := t.ProgressTimeline.GetLatestSnapshot(); ok && latest.ProgressType == u.Type {
		old = latest.Percentage
	}
	var status value_objects.ProgressStatus
	switch {
	case u.Percentage == 0:
		status = value_objects.ProgressStatusNotStarted
	case u.Percentage == 100:
		status = value_objects.ProgressStatusCompleted
	case u.Percentage < old:
		status = value_objects.ProgressStatusBlocked
	default:
		status = value_objects.ProgressStatusInProgress
	}
	pm := value_objects.NewProgressMetadata()
	if len(u.Metadata) > 0 {
		var err error
		if pm, err = progressMetadataFrom(u.Metadata); err != nil {
			return err
		}
	}
	snap, err := value_objects.NewProgressSnapshot(value_objects.ProgressSnapshot{
		TaskID: t.idStr(), ProgressType: u.Type, Percentage: u.Percentage, Status: status,
		Description: u.Description, Metadata: pm, AgentID: u.AgentID,
	})
	if err != nil {
		return err
	}
	if err := t.ProgressTimeline.AddSnapshot(snap); err != nil {
		return err
	}
	t.recalculateOverallProgress()

	ev := events.NewProgressUpdated()
	ev.TaskID, ev.ProgressType, ev.OldPercentage, ev.NewPercentage = t.idStr(), u.Type, old, u.Percentage
	ev.Status, ev.Description, ev.Metadata, ev.AgentID = status, u.Description, u.Metadata, u.AgentID
	t.Events = append(t.Events, ev)

	t.checkProgressMilestones()
	if u.Percentage == 100 && old < 100 {
		done := events.NewProgressTypeCompleted()
		done.TaskID, done.ProgressType, done.AgentID = t.idStr(), u.Type, u.AgentID
		t.Events = append(t.Events, done)
	}
	return t.Touch("progress_updated")
}

func (t *Task) recalculateOverallProgress() {
	if t.ProgressTimeline == nil {
		t.OverallProgress, t.OverallProgressIsFloat = 0, true
		return
	}
	timeline := t.ProgressTimeline.GetOverallProgress()
	switch {
	case len(t.Subtasks) > 0 && timeline > 0:
		// subtask percentage is always the int 0 here
		t.OverallProgress, t.OverallProgressIsFloat = (timeline+0)/2, true
	case len(t.Subtasks) > 0:
		t.OverallProgress, t.OverallProgressIsFloat = 0, false
	default:
		t.OverallProgress, t.OverallProgressIsFloat = timeline, true
	}
}

// CalculateProgressFromSubtasks: subtask states are unknown to the entity, so 0.
func (t *Task) CalculateProgressFromSubtasks(includeBlocked bool) float64 { return 0.0 }

func (t *Task) AddProgressMilestone(name string, percentage float64) error {
	if t.ProgressTimeline == nil {
		t.ProgressTimeline = value_objects.NewProgressTimeline(t.idStr())
	}
	if err := t.ProgressTimeline.AddMilestone(name, percentage); err != nil {
		return err
	}
	return t.Touch("milestone_added")
}

func (t *Task) checkProgressMilestones() {
	if t.ProgressTimeline == nil {
		return
	}
	for _, name := range t.ProgressTimeline.MilestoneOrder {
		pct := t.ProgressTimeline.Milestones[name]
		if t.OverallProgress >= pct && !t.milestoneAlreadyReached(name) {
			ev := events.NewProgressMilestoneReached()
			ev.TaskID, ev.MilestoneName, ev.MilestonePercentage, ev.CurrentProgress = t.idStr(), name, pct, t.OverallProgress
			t.Events = append(t.Events, ev)
		}
	}
}

func (t *Task) milestoneAlreadyReached(name string) bool {
	for _, e := range t.Events {
		if m, ok := e.(events.ProgressMilestoneReached); ok && m.MilestoneName == name {
			return true
		}
	}
	return false
}

func (t *Task) GetProgressByType(pt value_objects.ProgressType) float64 {
	if t.ProgressTimeline == nil {
		return 0.0
	}
	snaps := t.ProgressTimeline.GetSnapshotsByType(pt)
	if len(snaps) == 0 {
		return 0.0
	}
	return snaps[len(snaps)-1].Percentage
}

func (t *Task) GetProgressTimelineData(hours int) []map[string]any {
	if t.ProgressTimeline == nil {
		return []map[string]any{}
	}
	out := []map[string]any{}
	for _, s := range t.ProgressTimeline.GetProgressTrend(hours) {
		out = append(out, s.ToDict())
	}
	return out
}

func (t *Task) HasProgressType(pt value_objects.ProgressType) bool {
	return t.ProgressTimeline != nil && len(t.ProgressTimeline.GetSnapshotsByType(pt)) > 0
}

// GetEvents returns and clears the domain events.
func (t *Task) GetEvents() []events.Event {
	out := append([]events.Event{}, t.Events...)
	t.Events = t.Events[:0]
	return out
}

func (t *Task) MarkAsRetrieved() error {
	if err := t.Touch("task_retrieved"); err != nil {
		return err
	}
	ev := events.NewTaskRetrievedEvent()
	ev.TaskID = t.idStr()
	t.Events = append(t.Events, ev)
	return nil
}

// ToDict converts the task to its dictionary representation; it needs AgentNameResolver
// (registered by the application layer) to normalize assignee names.
func (t *Task) ToDict() (map[string]any, error) {
	if AgentNameResolver == nil {
		return nil, errors.New("entities.AgentNameResolver is not registered (application use_cases.agent_mappings)")
	}
	assignees := []string{}
	for _, a := range t.Assignees {
		assignees = append(assignees, AgentNameResolver(a))
	}
	deps := t.GetDependencyIDs()
	result := map[string]any{
		"id": t.idStr(), "title": t.Title, "description": t.Description, "git_branch_id": strOrNil(t.GitBranchID),
		"status": t.Status.Value, "priority": t.Priority.Value,
		"progress_history": t.ProgressHistory, "progress_count": t.ProgressCount,
		"estimatedEffort": t.EstimatedEffort, "assignees": assignees,
		"labels": append([]string{}, t.Labels...), "dependencies": deps, "dependency_count": len(t.Dependencies),
		"subtasks": append([]string{}, t.Subtasks...), "subtask_count": len(t.Subtasks),
		"completed_subtasks": t.CompletedSubtasks, "dueDate": nil,
		"created_at": nil, "updated_at": t.updatedAtISO(), "context_id": strOrNil(t.ContextID),
		"overall_progress": t.progressValue(), "progress_percentage": t.progressValue(),
		"completion_summary": "", "testing_notes": "",
	}
	if t.DueDate != nil && *t.DueDate != "" {
		result["dueDate"] = *t.DueDate
	}
	if t.CreatedAt != nil {
		result["created_at"] = value_objects.IsoFormat(*t.CreatedAt)
	}
	if t.CompletionSummary != nil {
		result["completion_summary"] = *t.CompletionSummary
	}
	if t.TestingNotes != nil {
		result["testing_notes"] = *t.TestingNotes
	}
	if t.ProgressTimeline != nil {
		result["progress_timeline"] = t.ProgressTimeline.ToDict()
	}
	return result, nil
}

// MigrateSubtaskIDs is a no-op kept by the Python entity.
func (t *Task) MigrateSubtaskIDs() {}

// CleanInvalidSubtasks: Subtasks is []string, so there is never anything to remove.
func (t *Task) CleanInvalidSubtasks() int { return 0 }

// CleanSubtaskAssignees is a no-op returning 0.
func (t *Task) CleanSubtaskAssignees() int { return 0 }
