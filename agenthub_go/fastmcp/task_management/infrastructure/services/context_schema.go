package services

import (
	"sort"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// contextSchemaNow is datetime.now() (naive local time, microsecond resolution).
var contextSchemaNow = func() time.Time { return time.Now().Truncate(time.Microsecond) }

func csNowISO() string { return value_objects.IsoFormatNaive(contextSchemaNow()) }

// csMap mirrors `.get(key, {})` and `dict` / OrderedMap inputs as a plain lookup map.
func csMap(v any) map[string]any {
	switch m := v.(type) {
	case map[string]any:
		return m
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		for _, k := range m.Keys() {
			x, _ := m.Get(k)
			out[k] = x
		}
		return out
	}
	return map[string]any{}
}

func csHas(d map[string]any, key string) bool {
	_, ok := d[key]
	return ok
}

// csStr mirrors `.get(key, default)` for values expected to be strings.
func csStr(v any, def string) string {
	if s, ok := v.(string); ok {
		return s
	}
	return def
}

func csStrings(v any) []string {
	out := []string{}
	switch l := v.(type) {
	case []string:
		return append([]string{}, l...)
	case []any:
		for _, e := range l {
			if s, ok := e.(string); ok {
				out = append(out, s)
			}
		}
	}
	return out
}

// csOrderedMap converts a dict-like value to an OrderedMap; map keys fall back to
// sorted order because Go maps do not retain insertion order.
func csOrderedMap(v any) *entities.OrderedMap[any] {
	if o, ok := v.(*entities.OrderedMap[any]); ok {
		if o == nil {
			return entities.NewOrderedMap[any]()
		}
		return o
	}
	o := entities.NewOrderedMap[any]()
	if m, ok := v.(map[string]any); ok {
		keys := make([]string, 0, len(m))
		for k := range m {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			o.Set(k, m[k])
		}
	}
	return o
}

// csOMap builds an insertion-ordered dict from alternating key/value arguments.
func csOMap(kv ...any) *entities.OrderedMap[any] {
	o := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		o.Set(kv[i].(string), kv[i+1])
	}
	return o
}

func csTasksStatuses() []string {
	out := make([]string, len(value_objects.TaskStatusValues))
	for i, s := range value_objects.TaskStatusValues {
		out[i] = string(s)
	}
	return out
}

func csPriorityLabels() []string {
	out := make([]string, len(value_objects.PriorityLevels))
	for i, p := range value_objects.PriorityLevels {
		out[i] = p.Label
	}
	return out
}

// ContextMetadata is context_schema.ContextMetadata.
type ContextMetadata struct {
	TaskID      string
	ProjectID   string
	GitBranchID string
	UserID      *string
	Status      value_objects.TaskStatus
	Priority    value_objects.Priority
	Assignees   []string
	Labels      []string
	CreatedAt   string
	UpdatedAt   string
	Version     string
}

// NewContextMetadata applies the dataclass defaults.
func NewContextMetadata(taskID, projectID string) *ContextMetadata {
	return &ContextMetadata{
		TaskID: taskID, ProjectID: projectID, GitBranchID: "main",
		Status: value_objects.TaskStatus{Value: "todo"}, Priority: value_objects.Priority{Value: "medium"},
		Assignees: []string{}, Labels: []string{}, CreatedAt: csNowISO(), UpdatedAt: csNowISO(), Version: "1.0",
	}
}

func (m *ContextMetadata) toOrdered() *entities.OrderedMap[any] {
	var userID any
	if m.UserID != nil {
		userID = *m.UserID
	}
	return csOMap(
		"task_id", m.TaskID,
		"project_id", m.ProjectID,
		"git_branch_id", m.GitBranchID,
		"user_id", userID,
		"status", m.Status.String(),
		"priority", m.Priority.String(),
		"assignees", m.Assignees,
		"labels", m.Labels,
		"created_at", m.CreatedAt,
		"updated_at", m.UpdatedAt,
		"version", m.Version,
	)
}

// ContextObjective is context_schema.ContextObjective.
type ContextObjective struct {
	Title           string
	Description     string
	EstimatedEffort string
	DueDate         *string
}

// NewContextObjective applies the dataclass defaults.
func NewContextObjective(title string) *ContextObjective {
	return &ContextObjective{Title: title, Description: "", EstimatedEffort: "medium"}
}

func (o *ContextObjective) toOrdered() *entities.OrderedMap[any] {
	var due any
	if o.DueDate != nil {
		due = *o.DueDate
	}
	return csOMap(
		"title", o.Title,
		"description", o.Description,
		"estimated_effort", o.EstimatedEffort,
		"due_date", due,
	)
}

// ContextRequirement is context_schema.ContextRequirement.
type ContextRequirement struct {
	ID        string
	Title     string
	Completed bool
	Priority  value_objects.Priority
	Notes     string
}

func (r *ContextRequirement) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"id", r.ID,
		"title", r.Title,
		"completed", r.Completed,
		"priority", r.Priority.String(),
		"notes", r.Notes,
	)
}

// ContextRequirements is context_schema.ContextRequirements.
type ContextRequirements struct {
	Checklist          []*ContextRequirement
	CustomRequirements []string
	CompletionCriteria []string
}

func newContextRequirements() *ContextRequirements {
	return &ContextRequirements{Checklist: []*ContextRequirement{}, CustomRequirements: []string{}, CompletionCriteria: []string{}}
}

func (r *ContextRequirements) toOrdered() *entities.OrderedMap[any] {
	checklist := make([]any, len(r.Checklist))
	for i, c := range r.Checklist {
		checklist[i] = c.toOrdered()
	}
	return csOMap(
		"checklist", checklist,
		"custom_requirements", r.CustomRequirements,
		"completion_criteria", r.CompletionCriteria,
	)
}

// ContextTechnical is context_schema.ContextTechnical.
type ContextTechnical struct {
	Technologies      []string
	Frameworks        []string
	KeyFiles          []string
	KeyDirectories    []string
	ArchitectureNotes string
	PatternsUsed      []string
}

func newContextTechnical() *ContextTechnical {
	return &ContextTechnical{Technologies: []string{}, Frameworks: []string{}, KeyFiles: []string{}, KeyDirectories: []string{}, PatternsUsed: []string{}}
}

func (t *ContextTechnical) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"technologies", t.Technologies,
		"frameworks", t.Frameworks,
		"key_files", t.KeyFiles,
		"key_directories", t.KeyDirectories,
		"architecture_notes", t.ArchitectureNotes,
		"patterns_used", t.PatternsUsed,
	)
}

// ContextDependency is context_schema.ContextDependency.
type ContextDependency struct {
	TaskID         string
	Title          string
	Status         value_objects.TaskStatus
	BlockingReason string
}

func (d *ContextDependency) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"task_id", d.TaskID,
		"title", d.Title,
		"status", d.Status.String(),
		"blocking_reason", d.BlockingReason,
	)
}

// ContextDependencies is context_schema.ContextDependencies.
type ContextDependencies struct {
	TaskDependencies     []*ContextDependency
	ExternalDependencies []string
	BlockedBy            []string
}

func newContextDependencies() *ContextDependencies {
	return &ContextDependencies{TaskDependencies: []*ContextDependency{}, ExternalDependencies: []string{}, BlockedBy: []string{}}
}

func (d *ContextDependencies) toOrdered() *entities.OrderedMap[any] {
	deps := make([]any, len(d.TaskDependencies))
	for i, dep := range d.TaskDependencies {
		deps[i] = dep.toOrdered()
	}
	return csOMap(
		"task_dependencies", deps,
		"external_dependencies", d.ExternalDependencies,
		"blocked_by", d.BlockedBy,
	)
}

// ContextProgressAction is context_schema.ContextProgressAction.
type ContextProgressAction struct {
	Timestamp string
	Action    string
	Agent     string
	Details   string
	Status    string
}

func (a *ContextProgressAction) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"timestamp", a.Timestamp,
		"action", a.Action,
		"agent", a.Agent,
		"details", a.Details,
		"status", a.Status,
	)
}

// ContextProgress is context_schema.ContextProgress.
type ContextProgress struct {
	CompletedActions      []*ContextProgressAction
	CurrentSessionSummary string
	NextSteps             []string
	CompletionPercentage  float64
	TimeSpentMinutes      int
}

func newContextProgress() *ContextProgress {
	return &ContextProgress{CompletedActions: []*ContextProgressAction{}, NextSteps: []string{}}
}

func (p *ContextProgress) toOrdered() *entities.OrderedMap[any] {
	actions := make([]any, len(p.CompletedActions))
	for i, a := range p.CompletedActions {
		actions[i] = a.toOrdered()
	}
	return csOMap(
		"completed_actions", actions,
		"current_session_summary", p.CurrentSessionSummary,
		"next_steps", p.NextSteps,
		"completion_percentage", p.CompletionPercentage,
		"time_spent_minutes", p.TimeSpentMinutes,
	)
}

// ContextInsight is context_schema.ContextInsight.
type ContextInsight struct {
	Timestamp  string
	Agent      string
	Category   string
	Content    string
	Importance string
}

func (i *ContextInsight) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"timestamp", i.Timestamp,
		"agent", i.Agent,
		"category", i.Category,
		"content", i.Content,
		"importance", i.Importance,
	)
}

// ContextNotes is context_schema.ContextNotes.
type ContextNotes struct {
	AgentInsights         []*ContextInsight
	ChallengesEncountered []*ContextInsight
	SolutionsApplied      []*ContextInsight
	DecisionsMade         []*ContextInsight
	GeneralNotes          string
}

func newContextNotes() *ContextNotes {
	return &ContextNotes{AgentInsights: []*ContextInsight{}, ChallengesEncountered: []*ContextInsight{}, SolutionsApplied: []*ContextInsight{}, DecisionsMade: []*ContextInsight{}}
}

func csInsights(items []*ContextInsight) []any {
	out := make([]any, len(items))
	for i, item := range items {
		out[i] = item.toOrdered()
	}
	return out
}

func (n *ContextNotes) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"agent_insights", csInsights(n.AgentInsights),
		"challenges_encountered", csInsights(n.ChallengesEncountered),
		"solutions_applied", csInsights(n.SolutionsApplied),
		"decisions_made", csInsights(n.DecisionsMade),
		"general_notes", n.GeneralNotes,
	)
}

// ContextSubtask is context_schema.ContextSubtask.
type ContextSubtask struct {
	ID            string
	Title         string
	Description   string
	Status        value_objects.TaskStatus
	Assignees     []string
	Completed     bool
	ProgressNotes string
}

func (s *ContextSubtask) toOrdered() *entities.OrderedMap[any] {
	return csOMap(
		"id", s.ID,
		"title", s.Title,
		"description", s.Description,
		"status", s.Status.String(),
		"assignees", s.Assignees,
		"completed", s.Completed,
		"progress_notes", s.ProgressNotes,
	)
}

// ContextSubtasks is context_schema.ContextSubtasks.
type ContextSubtasks struct {
	Items              []*ContextSubtask
	TotalCount         int
	CompletedCount     int
	ProgressPercentage float64
}

func newContextSubtasks() *ContextSubtasks {
	return &ContextSubtasks{Items: []*ContextSubtask{}}
}

func (s *ContextSubtasks) toOrdered() *entities.OrderedMap[any] {
	items := make([]any, len(s.Items))
	for i, item := range s.Items {
		items[i] = item.toOrdered()
	}
	return csOMap(
		"items", items,
		"total_count", s.TotalCount,
		"completed_count", s.CompletedCount,
		"progress_percentage", s.ProgressPercentage,
	)
}

// ContextCustomSection is context_schema.ContextCustomSection.
type ContextCustomSection struct {
	Name          string
	Data          *entities.OrderedMap[any]
	SchemaVersion string
}

func (s *ContextCustomSection) toOrdered() *entities.OrderedMap[any] {
	data := s.Data
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	return csOMap(
		"name", s.Name,
		"data", data,
		"schema_version", s.SchemaVersion,
	)
}

// TaskContext is context_schema.TaskContext.
type TaskContext struct {
	Metadata       *ContextMetadata
	Objective      *ContextObjective
	Requirements   *ContextRequirements
	Technical      *ContextTechnical
	Dependencies   *ContextDependencies
	Progress       *ContextProgress
	Subtasks       *ContextSubtasks
	Notes          *ContextNotes
	CustomSections []*ContextCustomSection
}

// NewTaskContext builds a context with the dataclass defaults for the optional sections.
func NewTaskContext(metadata *ContextMetadata, objective *ContextObjective) *TaskContext {
	return &TaskContext{
		Metadata: metadata, Objective: objective,
		Requirements: newContextRequirements(), Technical: newContextTechnical(),
		Dependencies: newContextDependencies(), Progress: newContextProgress(),
		Subtasks: newContextSubtasks(), Notes: newContextNotes(),
		CustomSections: []*ContextCustomSection{},
	}
}

// ToDict mirrors TaskContext.to_dict: every dataclass becomes a dict in field order.
func (c *TaskContext) ToDict() *entities.OrderedMap[any] {
	sections := make([]any, len(c.CustomSections))
	for i, s := range c.CustomSections {
		sections[i] = s.toOrdered()
	}
	return csOMap(
		"metadata", c.Metadata.toOrdered(),
		"objective", c.Objective.toOrdered(),
		"requirements", c.Requirements.toOrdered(),
		"technical", c.Technical.toOrdered(),
		"dependencies", c.Dependencies.toOrdered(),
		"progress", c.Progress.toOrdered(),
		"subtasks", c.Subtasks.toOrdered(),
		"notes", c.Notes.toOrdered(),
		"custom_sections", sections,
	)
}

// TaskContextFromDict mirrors TaskContext.from_dict. data may be a map or an
// OrderedMap; missing optional sections keep the dataclass defaults.
func TaskContextFromDict(data any) (*TaskContext, error) {
	d := csMap(data)

	metadataData := csMap(d["metadata"])
	metadata := NewContextMetadata(csStr(metadataData["task_id"], ""), csStr(metadataData["project_id"], ""))
	metadata.GitBranchID = csStr(metadataData["git_branch_id"], "main")
	if v, ok := metadataData["user_id"]; ok {
		if v != nil {
			s := csStr(v, "")
			metadata.UserID = &s
		}
	} else {
		s := ""
		metadata.UserID = &s
	}
	status, err := value_objects.TaskStatusFromString(csStr(metadataData["status"], "todo"))
	if err != nil {
		return nil, err
	}
	metadata.Status = status
	priority, err := value_objects.PriorityFromString(csStr(metadataData["priority"], "medium"))
	if err != nil {
		return nil, err
	}
	metadata.Priority = priority
	if v, ok := metadataData["assignees"]; ok {
		metadata.Assignees = csStrings(v)
	}
	if v, ok := metadataData["labels"]; ok {
		metadata.Labels = csStrings(v)
	}
	if v, ok := metadataData["created_at"]; ok {
		metadata.CreatedAt = csStr(v, metadata.CreatedAt)
	}
	if v, ok := metadataData["updated_at"]; ok {
		metadata.UpdatedAt = csStr(v, metadata.UpdatedAt)
	}
	if v, ok := metadataData["version"]; ok {
		metadata.Version = csStr(v, metadata.Version)
	}

	objectiveData := csMap(d["objective"])
	objective := NewContextObjective(csStr(objectiveData["title"], ""))
	objective.Description = csStr(objectiveData["description"], "")
	objective.EstimatedEffort = csStr(objectiveData["estimated_effort"], "medium")
	if v, ok := objectiveData["due_date"]; ok && v != nil {
		s := csStr(v, "")
		objective.DueDate = &s
	}

	context := NewTaskContext(metadata, objective)

	if csHas(d, "requirements") {
		reqData := csMap(d["requirements"])
		checklist := []*ContextRequirement{}
		for _, item := range csListOfMaps(reqData["checklist"]) {
			req := &ContextRequirement{
				ID:        csStr(item["id"], ""),
				Title:     csStr(item["title"], ""),
				Completed: csBool(item["completed"], false),
				Notes:     csStr(item["notes"], ""),
			}
			p, err := value_objects.PriorityFromString(csStr(item["priority"], "medium"))
			if err != nil {
				return nil, err
			}
			req.Priority = p
			checklist = append(checklist, req)
		}
		context.Requirements = &ContextRequirements{
			Checklist:          checklist,
			CustomRequirements: csStrings(reqData["custom_requirements"]),
			CompletionCriteria: csStrings(reqData["completion_criteria"]),
		}
	}

	if csHas(d, "technical") {
		techData := csMap(d["technical"])
		context.Technical = &ContextTechnical{
			Technologies:      csStrings(techData["technologies"]),
			Frameworks:        csStrings(techData["frameworks"]),
			KeyFiles:          csStrings(techData["key_files"]),
			KeyDirectories:    csStrings(techData["key_directories"]),
			ArchitectureNotes: csStr(techData["architecture_notes"], ""),
			PatternsUsed:      csStrings(techData["patterns_used"]),
		}
	}

	if csHas(d, "dependencies") {
		depData := csMap(d["dependencies"])
		taskDeps := []*ContextDependency{}
		for _, item := range csListOfMaps(depData["task_dependencies"]) {
			st, err := value_objects.TaskStatusFromString(csStr(item["status"], "todo"))
			if err != nil {
				return nil, err
			}
			taskDeps = append(taskDeps, &ContextDependency{
				TaskID:         csStr(item["task_id"], ""),
				Title:          csStr(item["title"], ""),
				Status:         st,
				BlockingReason: csStr(item["blocking_reason"], ""),
			})
		}
		context.Dependencies = &ContextDependencies{
			TaskDependencies:     taskDeps,
			ExternalDependencies: csStrings(depData["external_dependencies"]),
			BlockedBy:            csStrings(depData["blocked_by"]),
		}
	}

	if csHas(d, "progress") {
		progData := csMap(d["progress"])
		actions := []*ContextProgressAction{}
		for _, item := range csListOfMaps(progData["completed_actions"]) {
			actions = append(actions, &ContextProgressAction{
				Timestamp: csStr(item["timestamp"], ""),
				Action:    csStr(item["action"], ""),
				Agent:     csStr(item["agent"], ""),
				Details:   csStr(item["details"], ""),
				Status:    csStr(item["status"], "completed"),
			})
		}
		context.Progress = &ContextProgress{
			CompletedActions:      actions,
			CurrentSessionSummary: csStr(progData["current_session_summary"], ""),
			NextSteps:             csStrings(progData["next_steps"]),
			CompletionPercentage:  csFloat(progData["completion_percentage"], 0),
			TimeSpentMinutes:      csInt(progData["time_spent_minutes"], 0),
		}
	}

	if csHas(d, "subtasks") {
		subData := csMap(d["subtasks"])
		items := []*ContextSubtask{}
		for _, item := range csListOfMaps(subData["items"]) {
			st, err := value_objects.TaskStatusFromString(csStr(item["status"], "todo"))
			if err != nil {
				return nil, err
			}
			items = append(items, &ContextSubtask{
				ID:            csStr(item["id"], ""),
				Title:         csStr(item["title"], ""),
				Description:   csStr(item["description"], ""),
				Status:        st,
				Assignees:     csStrings(item["assignees"]),
				Completed:     csBool(item["completed"], false),
				ProgressNotes: csStr(item["progress_notes"], ""),
			})
		}
		context.Subtasks = &ContextSubtasks{
			Items:              items,
			TotalCount:         csInt(subData["total_count"], 0),
			CompletedCount:     csInt(subData["completed_count"], 0),
			ProgressPercentage: csFloat(subData["progress_percentage"], 0),
		}
	}

	if csHas(d, "notes") {
		notesData := csMap(d["notes"])
		context.Notes = &ContextNotes{
			AgentInsights:         csListInsights(notesData["agent_insights"]),
			ChallengesEncountered: csListInsights(notesData["challenges_encountered"]),
			SolutionsApplied:      csListInsights(notesData["solutions_applied"]),
			DecisionsMade:         csListInsights(notesData["decisions_made"]),
			GeneralNotes:          csStr(notesData["general_notes"], ""),
		}
	}

	if csHas(d, "custom_sections") {
		sections := []*ContextCustomSection{}
		for _, section := range csListOfMaps(d["custom_sections"]) {
			sections = append(sections, &ContextCustomSection{
				Name:          csStr(section["name"], ""),
				Data:          csOrderedMap(section["data"]),
				SchemaVersion: csStr(section["schema_version"], "1.0"),
			})
		}
		context.CustomSections = sections
	}

	return context, nil
}

func csListOfMaps(v any) []map[string]any {
	out := []map[string]any{}
	switch l := v.(type) {
	case []any:
		for _, e := range l {
			out = append(out, csMap(e))
		}
	case []map[string]any:
		for _, e := range l {
			out = append(out, e)
		}
	}
	return out
}

func csListInsights(v any) []*ContextInsight {
	out := []*ContextInsight{}
	for _, item := range csListOfMaps(v) {
		out = append(out, &ContextInsight{
			Timestamp:  csStr(item["timestamp"], ""),
			Agent:      csStr(item["agent"], ""),
			Category:   csStr(item["category"], ""),
			Content:    csStr(item["content"], ""),
			Importance: csStr(item["importance"], "medium"),
		})
	}
	return out
}

func csBool(v any, def bool) bool {
	if b, ok := v.(bool); ok {
		return b
	}
	return def
}

func csInt(v any, def int) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return def
}

func csFloat(v any, def float64) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	case int64:
		return float64(n)
	}
	return def
}

// ContextSchema is context_schema.ContextSchema.
type ContextSchema struct{}

// SchemaVersion is ContextSchema.SCHEMA_VERSION.
const ContextSchemaVersion = "1.0"

// GetDefaultSchema returns the default context schema (ordered like the Python dict).
func (ContextSchema) GetDefaultSchema() *entities.OrderedMap[any] {
	properties := csOMap(
		"metadata", csOMap(
			"type", "object",
			"required", []string{"task_id", "project_id"},
			"properties", csOMap(
				"task_id", csOMap("type", "string"),
				"project_id", csOMap("type", "string"),
				"git_branch_id", csOMap("type", "string", "default", "main"),
				"user_id", csOMap("type", []any{"string", "null"}, "default", nil),
				"status", csOMap("type", "string", "enum", csTasksStatuses()),
				"priority", csOMap("type", "string", "enum", csPriorityLabels()),
				"assignees", csOMap("type", "array", "items", csOMap("type", "string")),
				"labels", csOMap("type", "array", "items", csOMap("type", "string")),
				"created_at", csOMap("type", "string", "format", "date-time"),
				"updated_at", csOMap("type", "string", "format", "date-time"),
				"version", csOMap("type", "string", "default", "1.0"),
			),
		),
		"objective", csOMap(
			"type", "object",
			"required", []string{"title"},
			"properties", csOMap(
				"title", csOMap("type", "string"),
				"description", csOMap("type", "string"),
				"estimated_effort", csOMap("type", "string"),
				"due_date", csOMap("type", []any{"string", "null"}, "format", "date-time"),
			),
		),
		"requirements", csOMap(
			"type", "object",
			"properties", csOMap(
				"checklist", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/requirement")),
				"custom_requirements", csOMap("type", "array", "items", csOMap("type", "string")),
				"completion_criteria", csOMap("type", "array", "items", csOMap("type", "string")),
			),
		),
		"technical", csOMap(
			"type", "object",
			"properties", csOMap(
				"technologies", csOMap("type", "array", "items", csOMap("type", "string")),
				"frameworks", csOMap("type", "array", "items", csOMap("type", "string")),
				"key_files", csOMap("type", "array", "items", csOMap("type", "string")),
				"key_directories", csOMap("type", "array", "items", csOMap("type", "string")),
				"architecture_notes", csOMap("type", "string"),
				"patterns_used", csOMap("type", "array", "items", csOMap("type", "string")),
			),
		),
		"dependencies", csOMap(
			"type", "object",
			"properties", csOMap(
				"task_dependencies", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/dependency")),
				"external_dependencies", csOMap("type", "array", "items", csOMap("type", "string")),
				"blocked_by", csOMap("type", "array", "items", csOMap("type", "string")),
			),
		),
		"progress", csOMap(
			"type", "object",
			"properties", csOMap(
				"completed_actions", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/action")),
				"current_session_summary", csOMap("type", "string"),
				"next_steps", csOMap("type", "array", "items", csOMap("type", "string")),
				"completion_percentage", csOMap("type", "number", "minimum", 0, "maximum", 100),
				"time_spent_minutes", csOMap("type", "integer", "minimum", 0),
			),
		),
		"subtasks", csOMap(
			"type", "object",
			"properties", csOMap(
				"items", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/subtask")),
				"total_count", csOMap("type", "integer", "minimum", 0),
				"completed_count", csOMap("type", "integer", "minimum", 0),
				"progress_percentage", csOMap("type", "number", "minimum", 0, "maximum", 100),
			),
		),
		"notes", csOMap(
			"type", "object",
			"properties", csOMap(
				"agent_insights", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/insight")),
				"challenges_encountered", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/insight")),
				"solutions_applied", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/insight")),
				"decisions_made", csOMap("type", "array", "items", csOMap("$ref", "#/definitions/insight")),
				"general_notes", csOMap("type", "string"),
			),
		),
		"custom_sections", csOMap(
			"type", "array",
			"items", csOMap(
				"type", "object",
				"required", []string{"name", "data"},
				"properties", csOMap(
					"name", csOMap("type", "string"),
					"data", csOMap("type", "object"),
					"schema_version", csOMap("type", "string"),
				),
			),
		),
	)

	definitions := csOMap(
		"requirement", csOMap(
			"type", "object",
			"required", []string{"id", "title"},
			"properties", csOMap(
				"id", csOMap("type", "string"),
				"title", csOMap("type", "string"),
				"completed", csOMap("type", "boolean"),
				"priority", csOMap("type", "string", "enum", csPriorityLabels()),
				"notes", csOMap("type", "string"),
			),
		),
		"dependency", csOMap(
			"type", "object",
			"required", []string{"task_id"},
			"properties", csOMap(
				"task_id", csOMap("type", "string"),
				"title", csOMap("type", "string"),
				"status", csOMap("type", "string", "enum", csTasksStatuses()),
				"blocking_reason", csOMap("type", "string"),
			),
		),
		"action", csOMap(
			"type", "object",
			"required", []string{"timestamp", "action", "agent"},
			"properties", csOMap(
				"timestamp", csOMap("type", "string", "format", "date-time"),
				"action", csOMap("type", "string"),
				"agent", csOMap("type", "string"),
				"details", csOMap("type", "string"),
				"status", csOMap("type", "string"),
			),
		),
		"subtask", csOMap(
			"type", "object",
			"required", []string{"id", "title"},
			"properties", csOMap(
				"id", csOMap("type", "string"),
				"title", csOMap("type", "string"),
				"description", csOMap("type", "string"),
				"status", csOMap("type", "string", "enum", csTasksStatuses()),
				"assignees", csOMap("type", "array", "items", csOMap("type", "string")),
				"completed", csOMap("type", "boolean"),
				"progress_notes", csOMap("type", "string"),
			),
		),
		"insight", csOMap(
			"type", "object",
			"required", []string{"timestamp", "agent", "category", "content"},
			"properties", csOMap(
				"timestamp", csOMap("type", "string", "format", "date-time"),
				"agent", csOMap("type", "string"),
				"category", csOMap("type", "string"),
				"content", csOMap("type", "string"),
				"importance", csOMap("type", "string", "enum", []string{"low", "medium", "high", "critical"}),
			),
		),
	)

	return csOMap(
		"version", ContextSchemaVersion,
		"type", "object",
		"required", []string{"metadata", "objective"},
		"properties", properties,
		"definitions", definitions,
	)
}

// ValidateContext mirrors ContextSchema.validate_context.
func (ContextSchema) ValidateContext(contextData any) (bool, []string) {
	errors := []string{}
	if _, ok := contextData.(map[string]any); !ok {
		if _, ok := contextData.(*entities.OrderedMap[any]); !ok {
			errors = append(errors, "Context data must be a dictionary")
			return false, errors
		}
	}
	d := csMap(contextData)
	for _, section := range []string{"metadata", "objective"} {
		if !csHas(d, section) {
			errors = append(errors, "Missing required section: "+section)
		}
	}
	return len(errors) == 0, errors
}

// CreateEmptyContext mirrors ContextSchema.create_empty_context.
func (ContextSchema) CreateEmptyContext(taskID, projectID, title string, kwargs map[string]any) (*TaskContext, error) {
	metadata := NewContextMetadata(taskID, projectID)
	metadata.GitBranchID = csStr(kwargs["git_branch_id"], "main")
	s := csStr(kwargs["user_id"], "")
	metadata.UserID = &s
	status, err := value_objects.TaskStatusFromString(csStr(kwargs["status"], "todo"))
	if err != nil {
		return nil, err
	}
	metadata.Status = status
	priority, err := value_objects.PriorityFromString(csStr(kwargs["priority"], "medium"))
	if err != nil {
		return nil, err
	}
	metadata.Priority = priority
	if v, ok := kwargs["assignees"]; ok {
		metadata.Assignees = csStrings(v)
	}
	if v, ok := kwargs["labels"]; ok {
		metadata.Labels = csStrings(v)
	}

	objective := NewContextObjective(title)
	objective.Description = csStr(kwargs["description"], "")
	objective.EstimatedEffort = csStr(kwargs["estimated_effort"], "medium")
	if v, ok := kwargs["due_date"]; ok && v != nil {
		due := csStr(v, "")
		objective.DueDate = &due
	}

	return NewTaskContext(metadata, objective), nil
}
