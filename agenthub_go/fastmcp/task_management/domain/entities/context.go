package entities

import (
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

var nestedCategoryKeys = []string{CategoryOrganization, CategoryDevelopment, CategorySecurity, CategoryOperations, CategoryPreferences}

// truthy mirrors Python truthiness for JSON-like values.
func truthy(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case bool:
		return x
	case string:
		return x != ""
	case int:
		return x != 0
	case int64:
		return x != 0
	case float64:
		return x != 0
	case []any:
		return len(x) > 0
	case []string:
		return len(x) > 0
	case map[string]any:
		return len(x) > 0
	}
	return true
}

func hasAnyKey(m map[string]any, keys []string) bool {
	for _, k := range keys {
		if _, ok := m[k]; ok {
			return true
		}
	}
	return false
}

func sortedMapKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func copyMap(m map[string]any) map[string]any {
	c := make(map[string]any, len(m))
	for k, v := range m {
		c[k] = v
	}
	return c
}

// GlobalContext is the organization-wide settings entity with nested (v2.0) categorization.
type GlobalContext struct {
	ID               string
	OrganizationName string
	GlobalSettings   map[string]any
	Metadata         map[string]any
	nestedData       *GlobalContextNestedData
}

// NewGlobalContext is __post_init__: it creates the nested structure and, when
// global_settings contains category keys, populates it from them.
func NewGlobalContext(id, organizationName string, globalSettings, metadata map[string]any) *GlobalContext {
	g := &GlobalContext{ID: id, OrganizationName: organizationName, GlobalSettings: globalSettings, Metadata: metadata}
	if g.GlobalSettings == nil {
		g.GlobalSettings = map[string]any{}
	}
	if g.Metadata == nil {
		g.Metadata = map[string]any{}
	}
	g.ensureNestedStructure()
	if len(g.GlobalSettings) > 0 && hasAnyKey(g.GlobalSettings, nestedCategoryKeys) {
		g.nestedData = GlobalContextNestedDataFromDict(g.GlobalSettings)
	}
	return g
}

func (g *GlobalContext) ensureNestedStructure() {
	if g.nestedData == nil {
		g.nestedData = NewGlobalContextNestedData()
	}
}

func (g *GlobalContext) isOnlyNestedStructureData() bool {
	for k := range g.GlobalSettings {
		if indexOf(append(append([]string{}, nestedCategoryKeys...), "_schema_version", "_custom_categories"), k) < 0 {
			return false
		}
	}
	return true
}

func (g *GlobalContext) GetNestedData() *GlobalContextNestedData {
	g.ensureNestedStructure()
	return g.nestedData
}

func (g *GlobalContext) SetNestedValue(path string, value any) error {
	if err := g.GetNestedData().SetNestedValue(path, value); err != nil {
		return err
	}
	g.syncToFlatStructure()
	return nil
}

func (g *GlobalContext) GetNestedValue(path string, def any) any {
	return g.GetNestedData().GetNestedValue(path, def)
}

func (g *GlobalContext) syncToFlatStructure() {
	if g.nestedData != nil {
		g.GlobalSettings = g.nestedData.ToDict()
	}
}

// UpdateGlobalSettings updates nested (deep-merge) or flat settings.
func (g *GlobalContext) UpdateGlobalSettings(settings map[string]any, useNested bool) error {
	if !useNested {
		for k, v := range settings {
			g.GlobalSettings[k] = v
		}
		if hasAnyKey(g.GlobalSettings, nestedCategoryKeys) {
			g.nestedData = GlobalContextNestedDataFromDict(g.GlobalSettings)
		}
		return nil
	}
	nested := g.GetNestedData()
	if hasAnyKey(settings, nestedCategoryKeys) {
		for _, category := range nestedCategoryKeys {
			raw, ok := settings[category]
			if !ok {
				continue
			}
			subs, ok := raw.(map[string]any)
			if !ok {
				return value_objects.TypeErrorf("'%s' object has no attribute 'items'", pyTypeName(raw))
			}
			dst, _ := nested.category(category)
			for _, sub := range sortedMapKeys(subs) {
				values := subs[sub]
				existing, exists := dst[sub]
				if !exists {
					dst[sub] = values
					continue
				}
				em, ok := existing.(map[string]any)
				vm, ok2 := values.(map[string]any)
				if !ok || !ok2 {
					return value_objects.TypeErrorf("cannot update '%s' with '%s'", pyTypeName(existing), pyTypeName(values))
				}
				for k, v := range vm {
					em[k] = v
				}
			}
		}
	} else {
		g.nestedData = GlobalContextNestedDataFromDict(settings)
	}
	g.syncToFlatStructure()
	return nil
}

func (g *GlobalContext) GetOrganizationStandards() any {
	return g.GetNestedValue("organization.standards", map[string]any{})
}

func subOrEmpty(m map[string]any, key string) any {
	if v, ok := m[key]; ok {
		return v
	}
	return map[string]any{}
}

func (g *GlobalContext) GetSecurityPolicies() map[string]any {
	s := g.GetNestedData().Security
	return map[string]any{"authentication": subOrEmpty(s, "authentication"), "encryption": subOrEmpty(s, "encryption"),
		"access_control": subOrEmpty(s, "access_control")}
}

func (g *GlobalContext) GetDevelopmentPatterns() any {
	return g.GetNestedValue("development.patterns", map[string]any{})
}

func (g *GlobalContext) GetUserPreferences() map[string]any {
	p := g.GetNestedData().Preferences
	return map[string]any{"user_interface": subOrEmpty(p, "user_interface"), "agent_behavior": subOrEmpty(p, "agent_behavior"),
		"workflow": subOrEmpty(p, "workflow")}
}

// ToDict is Python's dict(): custom settings are merged at the root level.
func (g *GlobalContext) ToDict() map[string]any {
	g.ensureNestedStructure()
	hasCustom := len(g.GlobalSettings) > 0 && !g.isOnlyNestedStructureData()
	if !hasCustom {
		g.syncToFlatStructure()
	}
	metadata := copyMap(g.Metadata)
	result := map[string]any{"id": g.ID, "organization_name": g.OrganizationName, "metadata": metadata}
	for k, v := range g.GlobalSettings {
		if k != "id" && k != "organization_name" && k != "metadata" {
			result[k] = v
		}
	}
	result["global_settings"] = g.GlobalSettings
	if g.nestedData != nil {
		metadata["schema_version"] = g.nestedData.SchemaVersion
		metadata["nested_structure"] = g.nestedData.ToDict()
	}
	return result
}

// GlobalContextFromDict mirrors GlobalContext.from_dict.
func GlobalContextFromDict(data map[string]any) *GlobalContext {
	str := func(k string) string { s, _ := data[k].(string); return s }
	gs, _ := data["global_settings"].(map[string]any)
	md, _ := data["metadata"].(map[string]any)
	g := NewGlobalContext(str("id"), str("organization_name"), gs, md)
	if nested, ok := g.Metadata["nested_structure"]; ok {
		nm, _ := nested.(map[string]any)
		g.nestedData = GlobalContextNestedDataFromDict(nm)
	} else {
		g.ensureNestedStructure()
	}
	return g
}

// ProjectContext holds project-specific settings.
type ProjectContext struct {
	ID                      string
	ProjectName             string
	ProjectInfo             map[string]any
	TeamPreferences         map[string]any
	TechnologyStack         map[string]any
	ProjectWorkflow         map[string]any
	LocalStandards          map[string]any
	ProjectSettings         map[string]any
	TechnicalSpecifications map[string]any
	Metadata                map[string]any
}

func orEmpty(m map[string]any) map[string]any {
	if m == nil {
		return map[string]any{}
	}
	return m
}

func (p ProjectContext) ToDict() map[string]any {
	return map[string]any{
		"id": p.ID, "project_name": p.ProjectName, "project_info": orEmpty(p.ProjectInfo),
		"team_preferences": orEmpty(p.TeamPreferences), "technology_stack": orEmpty(p.TechnologyStack),
		"project_workflow": orEmpty(p.ProjectWorkflow), "local_standards": orEmpty(p.LocalStandards),
		"project_settings": orEmpty(p.ProjectSettings), "technical_specifications": orEmpty(p.TechnicalSpecifications),
		"metadata": orEmpty(p.Metadata),
	}
}

// BranchContext holds git-branch-specific settings.
type BranchContext struct {
	ID                 string
	ProjectID          string
	GitBranchName      string
	BranchInfo         map[string]any
	BranchWorkflow     map[string]any
	FeatureFlags       map[string]any
	DiscoveredPatterns map[string]any
	BranchDecisions    map[string]any
	BranchSettings     map[string]any
	Metadata           map[string]any
}

func (b BranchContext) ToDict() map[string]any {
	return map[string]any{
		"id": b.ID, "project_id": b.ProjectID, "git_branch_name": b.GitBranchName,
		"branch_info": orEmpty(b.BranchInfo), "branch_workflow": orEmpty(b.BranchWorkflow),
		"feature_flags": orEmpty(b.FeatureFlags), "discovered_patterns": orEmpty(b.DiscoveredPatterns),
		"branch_decisions": orEmpty(b.BranchDecisions), "branch_settings": orEmpty(b.BranchSettings),
		"metadata": orEmpty(b.Metadata),
	}
}

var insightCategories = []string{"insight", "challenge", "solution", "decision", "technical", "business"}
var insightImportances = []string{"low", "medium", "high", "critical"}

// TaskContextUnified is the task context entity of the unified context system.
type TaskContextUnified struct {
	ID                  string
	BranchID            string
	TaskData            map[string]any
	ExecutionContext    map[string]any
	DiscoveredPatterns  map[string]any
	ImplementationNotes map[string]any
	TestResults         map[string]any
	Blockers            map[string]any
	Progress            int
	Insights            []any
	NextSteps           []any
	Metadata            map[string]any
}

// NewTaskContextUnified fills the empty collections.
func NewTaskContextUnified(id, branchID string) *TaskContextUnified {
	return &TaskContextUnified{ID: id, BranchID: branchID, TaskData: map[string]any{}, ExecutionContext: map[string]any{},
		DiscoveredPatterns: map[string]any{}, ImplementationNotes: map[string]any{}, TestResults: map[string]any{},
		Blockers: map[string]any{}, Insights: []any{}, NextSteps: []any{}, Metadata: map[string]any{}}
}

// ValidateContextData checks the business rules and returns every violation.
func (c *TaskContextUnified) ValidateContextData() (bool, []string) {
	errs := []string{}
	if c.Progress < 0 || c.Progress > 100 {
		errs = append(errs, fmt.Sprintf("Progress must be between 0-100, got %d", c.Progress))
	}
	if !truthy(c.TaskData["title"]) {
		errs = append(errs, "task_data must contain a title")
	}
	for idx, raw := range c.Insights {
		insight, ok := raw.(map[string]any)
		if !ok {
			errs = append(errs, fmt.Sprintf("Insight %d must be a dictionary", idx))
			continue
		}
		for _, f := range []string{"timestamp", "category", "content"} {
			if _, ok := insight[f]; !ok {
				errs = append(errs, fmt.Sprintf("Insight %d missing required field: %s", idx, f))
			}
		}
		if cat := insight["category"]; truthy(cat) {
			if s, isStr := cat.(string); !isStr || indexOf(insightCategories, s) < 0 {
				errs = append(errs, fmt.Sprintf("Insight %d has invalid category: %s", idx, value_objects.PyStr(cat)))
			}
		}
	}
	for _, key := range sortedMapKeys(c.Blockers) { // Python iterates in insertion order
		if b, ok := c.Blockers[key].(map[string]any); ok && !truthy(b["description"]) {
			errs = append(errs, fmt.Sprintf("Blocker '%s' must have a description", key))
		}
	}
	return len(errs) == 0, errs
}

func toFloat(v any) (float64, bool) {
	switch n := v.(type) {
	case int:
		return float64(n), true
	case int64:
		return float64(n), true
	case float64:
		return n, true
	}
	return 0, false
}

// MergeContextUpdates merges updates with the business rules (progress never
// decreases unless "_allow_progress_decrease", insights are append-only, ...).
func (c *TaskContextUnified) MergeContextUpdates(updates map[string]any) error {
	for _, key := range sortedMapKeys(updates) { // Python iterates in insertion order
		value := updates[key]
		switch key {
		case "progress":
			p, ok := toFloat(value)
			if !ok {
				return value_objects.TypeErrorf("'<' not supported between instances of '%s' and 'int'", pyTypeName(value))
			}
			if p < float64(c.Progress) && !truthy(updates["_allow_progress_decrease"]) {
				continue
			}
			c.Progress = int(math.Max(0, math.Min(100, p)))
		case "insights":
			switch v := value.(type) {
			case []any:
				c.Insights = append(c.Insights, v...)
			case map[string]any:
				c.Insights = append(c.Insights, v)
			}
		case "blockers":
			if m, ok := value.(map[string]any); ok {
				for k, v := range m {
					c.Blockers[k] = v
				}
			}
		case "metadata":
			if m, ok := value.(map[string]any); ok {
				for k, v := range m {
					c.Metadata[k] = v
				}
			}
		case "task_data", "execution_context", "discovered_patterns", "implementation_notes", "test_results":
			m, ok := value.(map[string]any)
			if !ok {
				return value_objects.TypeErrorf("%s must be a dict", key)
			}
			dst := map[string]map[string]any{"task_data": c.TaskData, "execution_context": c.ExecutionContext,
				"discovered_patterns": c.DiscoveredPatterns, "implementation_notes": c.ImplementationNotes,
				"test_results": c.TestResults}[key]
			for k, v := range m {
				dst[k] = v
			}
		case "next_steps":
			if l, ok := value.([]any); ok {
				c.NextSteps = l
			} else {
				c.NextSteps = []any{value}
			}
		case "id", "branch_id":
			if s, ok := value.(string); ok {
				if key == "id" {
					c.ID = s
				} else {
					c.BranchID = s
				}
			}
		}
		// other "_"-prefixed keys are internal flags; unknown keys are ignored (hasattr is false)
	}
	return nil
}

// AddInsight appends a validated, timestamped insight.
func (c *TaskContextUnified) AddInsight(category, content, agent, importance string) error {
	if indexOf(insightCategories, category) < 0 {
		return value_objects.ValueErrorf("Invalid category: %s. Must be one of %s", category, value_objects.PyRepr(insightCategories))
	}
	if strings.TrimSpace(content) == "" {
		return value_objects.ValueErrorf("Insight content cannot be empty")
	}
	if indexOf(insightImportances, importance) < 0 {
		return value_objects.ValueErrorf("Invalid importance: %s. Must be one of %s", importance, value_objects.PyRepr(insightImportances))
	}
	c.Insights = append(c.Insights, map[string]any{
		"timestamp": value_objects.IsoFormat(utcNow()), "category": category, "content": strings.TrimSpace(content),
		"agent": agent, "importance": importance,
	})
	return nil
}

// UpdateProgress validates and records a progress change in the context's implementation notes.
//
// One home for one idea: the entry goes to `progress_updates`, which is the key the live path
// (`UnifiedContextService.AddProgress`) writes and reads. `progress_history` is the retired name -
// it collides with the task column that the ledger cutover removes - and nothing read the
// metadata key, so the second write is gone rather than kept in step. The entry carries the whole
// transition (old, new, notes) because the retired key was the only place the old value appeared.
func (c *TaskContextUnified) UpdateProgress(newProgress int, notes *string, allowDecrease bool) error {
	if newProgress < 0 || newProgress > 100 {
		return value_objects.ValueErrorf("Progress must be between 0-100, got %d", newProgress)
	}
	if newProgress < c.Progress && !allowDecrease {
		return value_objects.ValueErrorf("Progress cannot decrease from %d to %d. Set allow_decrease=True to override.", c.Progress, newProgress)
	}
	old := c.Progress
	c.Progress = newProgress
	updates, _ := c.ImplementationNotes["progress_updates"].([]any)
	c.ImplementationNotes["progress_updates"] = append(updates, map[string]any{
		"timestamp": value_objects.IsoFormat(utcNow()), "old_progress": old, "new_progress": newProgress, "notes": strOrNil(notes),
	})
	return nil
}

func (c *TaskContextUnified) ToDict() map[string]any {
	return map[string]any{
		"id": c.ID, "branch_id": c.BranchID, "task_data": c.TaskData, "execution_context": c.ExecutionContext,
		"discovered_patterns": c.DiscoveredPatterns, "implementation_notes": c.ImplementationNotes,
		"test_results": c.TestResults, "blockers": c.Blockers, "progress": c.Progress,
		"insights": c.Insights, "next_steps": c.NextSteps, "metadata": c.Metadata,
	}
}

// ContextMetadata is the context metadata structure (clean relationship chain).
type ContextMetadata struct {
	base.BaseTimestampEntity
	TaskID    string
	Status    *value_objects.TaskStatus // nil → todo
	Priority  *value_objects.Priority   // nil → medium
	Assignees []string
	Labels    []string
	Version   *int // nil → 1
}

func NewContextMetadata(m ContextMetadata) (*ContextMetadata, error) {
	s := m
	if s.Status == nil {
		todo := mustTaskStatus("todo")
		s.Status = &todo
	}
	if s.Priority == nil {
		p := value_objects.PriorityMedium()
		s.Priority = &p
	}
	if s.Assignees == nil {
		s.Assignees = []string{}
	}
	if s.Labels == nil {
		s.Labels = []string{}
	}
	if s.Version == nil {
		one := 1
		s.Version = &one
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

func (m *ContextMetadata) GetEntityID() string {
	if m.TaskID == "" {
		return "unknown"
	}
	return m.TaskID
}

func (m *ContextMetadata) ValidateEntity() error {
	if m.TaskID == "" {
		return value_objects.ValueErrorf("ContextMetadata must have a task_id")
	}
	return nil
}

// toConvertedDict mirrors convert_dataclass(metadata): the entity's whole
// __dict__, including the leaked "_domain_events" list.
func (m *ContextMetadata) toConvertedDict() map[string]any {
	domainEvents := []any{}
	for _, e := range m.GetDomainEvents() {
		switch ev := e.(type) {
		case base.TimestampCreatedEvent:
			domainEvents = append(domainEvents, ev.RawDict())
		case base.TimestampUpdatedEvent:
			domainEvents = append(domainEvents, ev.RawDict())
		}
	}
	return map[string]any{
		"created_at": value_objects.IsoFormat(*m.CreatedAt), "updated_at": value_objects.IsoFormat(*m.UpdatedAt),
		"_domain_events": domainEvents, "task_id": m.TaskID, "status": m.Status.String(),
		"priority": m.Priority.String(), "assignees": m.Assignees, "labels": m.Labels, "version": *m.Version,
	}
}

// ContextObjective is the task objective and description.
type ContextObjective struct {
	Title           string
	Description     string
	EstimatedEffort *string
	DueDate         *time.Time
}

// ContextRequirement is an individual requirement item.
type ContextRequirement struct {
	ID        string
	Title     string
	Completed bool
	Priority  *value_objects.Priority // nil → medium
	Notes     string
}

// ContextRequirements is the requirements section.
type ContextRequirements struct {
	Checklist          []ContextRequirement
	CustomRequirements []string
	CompletionCriteria []string
}

// ContextTechnical is the technical details section.
type ContextTechnical struct {
	Technologies      []string
	Frameworks        []string
	Database          string
	KeyFiles          []string
	KeyDirectories    []string
	ArchitectureNotes string
	PatternsUsed      []string
}

// ContextDependency is dependency information.
type ContextDependency struct {
	TaskID         string
	Title          string
	Status         *value_objects.TaskStatus // nil → todo
	BlockingReason string
}

// ContextDependencies is the dependencies section.
type ContextDependencies struct {
	TaskDependencies     []ContextDependency
	ExternalDependencies []string
	BlockedBy            []string
}

// ContextProgressAction is an individual progress action (Status "" → "completed").
type ContextProgressAction struct {
	Timestamp string
	Action    string
	Agent     string
	Details   string
	Status    string
}

// ContextProgress is the progress tracking section.
type ContextProgress struct {
	CompletedActions      []ContextProgressAction
	CurrentSessionSummary string
	NextSteps             []string
	CompletionPercentage  float64
	TimeSpentMinutes      int
	CompletionSummary     *string
	TestingNotes          *string
	NextRecommendations   *string
	VisionAlignmentScore  *float64
}

// ContextInsight is an agent insight or note (Importance "" → "medium").
type ContextInsight struct {
	Timestamp  string
	Agent      string
	Category   string
	Content    string
	Importance string
}

// ContextNotes is the context notes and insights section.
type ContextNotes struct {
	AgentInsights         []ContextInsight
	ChallengesEncountered []ContextInsight
	SolutionsApplied      []ContextInsight
	DecisionsMade         []ContextInsight
	GeneralNotes          string
}

// ContextSubtask is subtask information.
type ContextSubtask struct {
	ID            string
	Title         string
	Description   string
	Status        *value_objects.TaskStatus // nil → todo
	Assignees     []string
	Completed     bool
	ProgressNotes string
}

// ContextSubtasks is the subtasks section.
type ContextSubtasks struct {
	Items              []ContextSubtask
	TotalCount         int
	CompletedCount     int
	ProgressPercentage float64
}

// ContextCustomSection is a custom extensible section (SchemaVersion "" → "1.0").
type ContextCustomSection struct {
	Name          string
	Data          map[string]any
	SchemaVersion string
}

// NewContextProgressAction applies the default status "completed".
func NewContextProgressAction(timestamp, action, agent, details string) ContextProgressAction {
	return ContextProgressAction{Timestamp: timestamp, Action: action, Agent: agent, Details: details, Status: "completed"}
}

// NewContextInsight applies the default importance "medium".
func NewContextInsight(timestamp, agent, category, content string) ContextInsight {
	return ContextInsight{Timestamp: timestamp, Agent: agent, Category: category, Content: content, Importance: "medium"}
}

// NewContextCustomSection applies the default schema version "1.0".
func NewContextCustomSection(name string, data map[string]any) ContextCustomSection {
	return ContextCustomSection{Name: name, Data: orEmpty(data), SchemaVersion: "1.0"}
}

// TaskContext is the complete task context structure.
type TaskContext struct {
	Metadata       *ContextMetadata
	Objective      ContextObjective
	Requirements   ContextRequirements
	Technical      ContextTechnical
	Dependencies   ContextDependencies
	Progress       ContextProgress
	Subtasks       ContextSubtasks
	Notes          ContextNotes
	CustomSections []ContextCustomSection

	ProgressTimeline   []map[string]any   // nil = None
	ProgressMilestones map[string]float64 // nil = None
	ProgressByType     map[string]float64 // nil = None
}

// NewTaskContext builds a context with empty sections.
func NewTaskContext(metadata *ContextMetadata, objective ContextObjective) *TaskContext {
	return &TaskContext{Metadata: metadata, Objective: objective, CustomSections: []ContextCustomSection{}}
}

// UpdateCompletionSummary records completion information (Vision System requirement).
func (t *TaskContext) UpdateCompletionSummary(summary string, testingNotes, nextRecommendations *string) error {
	if strings.TrimSpace(summary) == "" {
		return value_objects.ValueErrorf("completion_summary cannot be empty")
	}
	t.Progress.CompletionSummary = &summary
	if testingNotes != nil && *testingNotes != "" {
		t.Progress.TestingNotes = testingNotes
	}
	if nextRecommendations != nil && *nextRecommendations != "" {
		t.Progress.NextRecommendations = nextRecommendations
	}
	return t.Metadata.Touch("completion_summary_updated")
}

func (t *TaskContext) HasCompletionSummary() bool {
	return t.Progress.CompletionSummary != nil && strings.TrimSpace(*t.Progress.CompletionSummary) != ""
}

func (t *TaskContext) ValidateForTaskCompletion() (bool, []string) {
	errs := []string{}
	if !t.HasCompletionSummary() {
		errs = append(errs, "completion_summary is required for task completion")
	}
	return len(errs) == 0, errs
}

func insightsDict(l []ContextInsight) []any {
	out := make([]any, 0, len(l))
	for _, i := range l {
		out = append(out, map[string]any{"timestamp": i.Timestamp, "agent": i.Agent, "category": i.Category,
			"content": i.Content, "importance": i.Importance})
	}
	return out
}

func orEmptyStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

// ToDict converts the context for JSON serialization. embedded drops fields
// duplicated by the parent task. The metadata section includes the leaked
// `_domain_events` list exactly like Python's dataclass __dict__ walk.
func (t *TaskContext) ToDict(embedded bool) map[string]any {
	md := t.Metadata.toConvertedDict()

	var due any
	if t.Objective.DueDate != nil {
		due = value_objects.IsoFormat(*t.Objective.DueDate)
	}
	checklist := []any{}
	for _, r := range t.Requirements.Checklist {
		p := value_objects.PriorityMedium()
		if r.Priority != nil {
			p = *r.Priority
		}
		checklist = append(checklist, map[string]any{"id": r.ID, "title": r.Title, "completed": r.Completed,
			"priority": p.String(), "notes": r.Notes})
	}
	taskDeps := []any{}
	for _, d := range t.Dependencies.TaskDependencies {
		st := mustTaskStatus("todo")
		if d.Status != nil {
			st = *d.Status
		}
		taskDeps = append(taskDeps, map[string]any{"task_id": d.TaskID, "title": d.Title, "status": st.String(),
			"blocking_reason": d.BlockingReason})
	}
	actions := []any{}
	for _, a := range t.Progress.CompletedActions {
		actions = append(actions, map[string]any{"timestamp": a.Timestamp, "action": a.Action, "agent": a.Agent,
			"details": a.Details, "status": a.Status})
	}
	var score any
	if t.Progress.VisionAlignmentScore != nil {
		score = *t.Progress.VisionAlignmentScore
	}
	items := []any{}
	for _, s := range t.Subtasks.Items {
		st := mustTaskStatus("todo")
		if s.Status != nil {
			st = *s.Status
		}
		items = append(items, map[string]any{"id": s.ID, "title": s.Title, "description": s.Description,
			"status": st.String(), "assignees": orEmptyStrings(s.Assignees), "completed": s.Completed,
			"progress_notes": s.ProgressNotes})
	}
	sections := []any{}
	for _, s := range t.CustomSections {
		sections = append(sections, map[string]any{"name": s.Name, "data": orEmpty(s.Data), "schema_version": s.SchemaVersion})
	}
	var timeline, milestones, byType any
	if t.ProgressTimeline != nil {
		timeline = t.ProgressTimeline
	}
	if t.ProgressMilestones != nil {
		milestones = t.ProgressMilestones
	}
	if t.ProgressByType != nil {
		byType = t.ProgressByType
	}

	result := map[string]any{
		"metadata": md,
		"objective": map[string]any{"title": t.Objective.Title, "description": t.Objective.Description,
			"estimated_effort": strOrNil(t.Objective.EstimatedEffort), "due_date": due},
		"requirements": map[string]any{"checklist": checklist, "custom_requirements": orEmptyStrings(t.Requirements.CustomRequirements),
			"completion_criteria": orEmptyStrings(t.Requirements.CompletionCriteria)},
		"technical": map[string]any{"technologies": orEmptyStrings(t.Technical.Technologies),
			"frameworks": orEmptyStrings(t.Technical.Frameworks), "database": t.Technical.Database,
			"key_files": orEmptyStrings(t.Technical.KeyFiles), "key_directories": orEmptyStrings(t.Technical.KeyDirectories),
			"architecture_notes": t.Technical.ArchitectureNotes, "patterns_used": orEmptyStrings(t.Technical.PatternsUsed)},
		"dependencies": map[string]any{"task_dependencies": taskDeps,
			"external_dependencies": orEmptyStrings(t.Dependencies.ExternalDependencies),
			"blocked_by":            orEmptyStrings(t.Dependencies.BlockedBy)},
		"progress": map[string]any{"completed_actions": actions, "current_session_summary": t.Progress.CurrentSessionSummary,
			"next_steps": orEmptyStrings(t.Progress.NextSteps), "completion_percentage": t.Progress.CompletionPercentage,
			"time_spent_minutes": t.Progress.TimeSpentMinutes, "completion_summary": strOrNil(t.Progress.CompletionSummary),
			"testing_notes": strOrNil(t.Progress.TestingNotes), "next_recommendations": strOrNil(t.Progress.NextRecommendations),
			"vision_alignment_score": score},
		"subtasks": map[string]any{"items": items, "total_count": t.Subtasks.TotalCount,
			"completed_count": t.Subtasks.CompletedCount, "progress_percentage": t.Subtasks.ProgressPercentage},
		"notes": map[string]any{"agent_insights": insightsDict(t.Notes.AgentInsights),
			"challenges_encountered": insightsDict(t.Notes.ChallengesEncountered),
			"solutions_applied":      insightsDict(t.Notes.SolutionsApplied),
			"decisions_made":         insightsDict(t.Notes.DecisionsMade), "general_notes": t.Notes.GeneralNotes},
		"custom_sections":     sections,
		"progress_timeline":   timeline,
		"progress_milestones": milestones,
		"progress_by_type":    byType,
	}

	if embedded {
		optimized := map[string]any{}
		for _, k := range []string{"version", "assignees", "labels"} {
			optimized[k] = md[k]
		}
		result["metadata"] = optimized
	} else {
		result["task_id"] = t.Metadata.TaskID
	}

	keep := []any{}
	for _, s := range sections {
		section := s.(map[string]any)
		if section["name"] == "root_level_custom_fields" {
			if data, ok := section["data"].(map[string]any); ok {
				for k, v := range data {
					result[k] = v
				}
			}
		} else {
			keep = append(keep, section)
		}
	}
	result["custom_sections"] = keep
	return result
}

// contextKnownFields is from_dict's `known_fields`. Python's set literal is missing
// a comma after "task_id", so the implicit string concatenation yields the single
// member "task_iduser_id": "task_id" and "user_id" are NOT known, and to_dict's
// root-level task_id lands in the root_level_custom_fields section on re-import.
var contextKnownFields = map[string]bool{
	"metadata": true, "objective": true, "requirements": true, "technical": true, "dependencies": true,
	"progress": true, "subtasks": true, "notes": true, "custom_sections": true, "task_iduser_id": true,
	"status": true, "priority": true, "assignees": true, "labels": true, "title": true, "description": true,
	"estimated_effort": true, "due_date": true,
}

func joinQuoted(names []string) string {
	q := make([]string, len(names))
	for i, n := range names {
		q[i] = "'" + n + "'"
	}
	switch len(q) {
	case 1:
		return q[0]
	case 2:
		return q[0] + " and " + q[1]
	}
	return strings.Join(q[:len(q)-1], ", ") + ", and " + q[len(q)-1]
}

// checkKwargs mirrors Python's errors for `Class(**item)`: unexpected keywords first
// (sorted here; Python reports the first in dict order), then missing required ones.
func checkKwargs(class string, item map[string]any, required, optional []string) error {
	for _, k := range sortedMapKeys(item) {
		if indexOf(required, k) < 0 && indexOf(optional, k) < 0 {
			return value_objects.TypeErrorf("%s.__init__() got an unexpected keyword argument '%s'", class, k)
		}
	}
	missing := []string{}
	for _, r := range required {
		if _, ok := item[r]; !ok {
			missing = append(missing, r)
		}
	}
	if len(missing) == 1 {
		return value_objects.TypeErrorf("%s.__init__() missing 1 required positional argument: %s", class, joinQuoted(missing))
	} else if len(missing) > 1 {
		return value_objects.TypeErrorf("%s.__init__() missing %d required positional arguments: %s", class, len(missing), joinQuoted(missing))
	}
	return nil
}

func getMap(v any, what string) (map[string]any, error) {
	m, ok := v.(map[string]any)
	if !ok {
		return nil, value_objects.TypeErrorf("%s must be a dict", what)
	}
	return m, nil
}

func getItems(d map[string]any, key string) ([]map[string]any, error) {
	raw, ok := d[key]
	if !ok {
		return nil, nil
	}
	var list []any
	switch l := raw.(type) {
	case []any:
		list = l
	case []map[string]any:
		for _, m := range l {
			list = append(list, m)
		}
	default:
		return nil, value_objects.TypeErrorf("%s must be a list", key)
	}
	out := make([]map[string]any, 0, len(list))
	for _, e := range list {
		m, err := getMap(e, key+" item")
		if err != nil {
			return nil, err
		}
		out = append(out, m)
	}
	return out, nil
}

func strOr(d map[string]any, key, def string) string {
	if s, ok := d[key].(string); ok {
		return s
	}
	return def
}

func strsOr(d map[string]any, key string) ([]string, error) {
	v, ok := d[key]
	if !ok {
		return []string{}, nil
	}
	return stringList(v)
}

func optString(d map[string]any, key string) *string {
	if s, ok := d[key].(string); ok {
		return &s
	}
	return nil
}

func statusFromDict(d map[string]any) (*value_objects.TaskStatus, error) {
	s, err := value_objects.TaskStatusFromString(strOr(d, "status", "todo"))
	return &s, err
}

func priorityFromDict(d map[string]any) (*value_objects.Priority, error) {
	p, err := value_objects.PriorityFromString(strOr(d, "priority", "medium"))
	return &p, err
}

func parseContextDate(s string) (*time.Time, error) {
	if s == "" {
		return nil, nil
	}
	t, err := value_objects.ParseISO(strings.ReplaceAll(s, "Z", "+00:00"))
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func parseInsights(d map[string]any, key string) ([]ContextInsight, error) {
	items, err := getItems(d, key)
	if err != nil {
		return nil, err
	}
	out := []ContextInsight{}
	for _, it := range items {
		if err := checkKwargs("ContextInsight", it, []string{"timestamp", "agent", "category", "content"}, []string{"importance"}); err != nil {
			return nil, err
		}
		out = append(out, ContextInsight{Timestamp: strOr(it, "timestamp", ""), Agent: strOr(it, "agent", ""),
			Category: strOr(it, "category", ""), Content: strOr(it, "content", ""), Importance: strOr(it, "importance", "medium")})
	}
	return out, nil
}

// TaskContextFromDict mirrors TaskContext.from_dict (nested or flat format).
func TaskContextFromDict(data map[string]any) (*TaskContext, error) {
	var md ContextMetadata
	var err error
	if raw, ok := data["metadata"]; ok {
		m, err := getMap(raw, "metadata")
		if err != nil {
			return nil, err
		}
		if _, ok := m["task_id"]; !ok {
			return nil, &KeyError{"task_id"}
		}
		md.TaskID = strOr(m, "task_id", "")
		if md.Status, err = statusFromDict(m); err != nil {
			return nil, err
		}
		if md.Priority, err = priorityFromDict(m); err != nil {
			return nil, err
		}
		if md.Assignees, err = strsOr(m, "assignees"); err != nil {
			return nil, err
		}
		if md.Labels, err = strsOr(m, "labels"); err != nil {
			return nil, err
		}
		if v, ok := m["version"]; ok {
			f, isNum := toFloat(v)
			if !isNum {
				return nil, value_objects.TypeErrorf("version must be an int")
			}
			n := int(f)
			md.Version = &n
		}
	} else {
		if _, ok := data["task_id"]; !ok {
			return nil, &KeyError{"task_id"}
		}
		md.TaskID = strOr(data, "task_id", "")
		if md.Status, err = statusFromDict(data); err != nil {
			return nil, err
		}
		if md.Priority, err = priorityFromDict(data); err != nil {
			return nil, err
		}
		if md.Assignees, err = strsOr(data, "assignees"); err != nil {
			return nil, err
		}
		if md.Labels, err = strsOr(data, "labels"); err != nil {
			return nil, err
		}
	}
	metadata, err := NewContextMetadata(md)
	if err != nil {
		return nil, err
	}

	var objective ContextObjective
	if raw, ok := data["objective"]; ok {
		o, err := getMap(raw, "objective")
		if err != nil {
			return nil, err
		}
		if _, ok := o["title"]; !ok {
			return nil, &KeyError{"title"}
		}
		objective = ContextObjective{Title: strOr(o, "title", ""), Description: strOr(o, "description", ""),
			EstimatedEffort: optString(o, "estimated_effort")}
		if objective.DueDate, err = parseContextDate(strOr(o, "due_date", "")); err != nil {
			return nil, err
		}
	} else {
		objective = ContextObjective{Title: strOr(data, "title", "Context for task "+metadata.TaskID),
			Description: strOr(data, "description", ""), EstimatedEffort: optString(data, "estimated_effort")}
		if objective.DueDate, err = parseContextDate(strOr(data, "due_date", "")); err != nil {
			return nil, err
		}
	}
	ctx := NewTaskContext(metadata, objective)

	if raw, ok := data["requirements"]; ok {
		r, err := getMap(raw, "requirements")
		if err != nil {
			return nil, err
		}
		items, err := getItems(r, "checklist")
		if err != nil {
			return nil, err
		}
		for _, it := range items {
			p, err := priorityFromDict(it)
			if err != nil {
				return nil, err
			}
			done, _ := it["completed"].(bool)
			ctx.Requirements.Checklist = append(ctx.Requirements.Checklist, ContextRequirement{
				ID: strOr(it, "id", ""), Title: strOr(it, "title", ""), Completed: done, Priority: p, Notes: strOr(it, "notes", "")})
		}
		if ctx.Requirements.CustomRequirements, err = strsOr(r, "custom_requirements"); err != nil {
			return nil, err
		}
		if ctx.Requirements.CompletionCriteria, err = strsOr(r, "completion_criteria"); err != nil {
			return nil, err
		}
	}

	if raw, ok := data["technical"]; ok {
		tm, err := getMap(raw, "technical")
		if err != nil {
			return nil, err
		}
		if err := checkKwargs("ContextTechnical", tm, nil, []string{"technologies", "frameworks", "database", "key_files",
			"key_directories", "architecture_notes", "patterns_used"}); err != nil {
			return nil, err
		}
		tech := ContextTechnical{Database: strOr(tm, "database", ""), ArchitectureNotes: strOr(tm, "architecture_notes", "")}
		for key, dst := range map[string]*[]string{"technologies": &tech.Technologies, "frameworks": &tech.Frameworks,
			"key_files": &tech.KeyFiles, "key_directories": &tech.KeyDirectories, "patterns_used": &tech.PatternsUsed} {
			if *dst, err = strsOr(tm, key); err != nil {
				return nil, err
			}
		}
		ctx.Technical = tech
	}

	if raw, ok := data["dependencies"]; ok {
		dm, err := getMap(raw, "dependencies")
		if err != nil {
			return nil, err
		}
		items, err := getItems(dm, "task_dependencies")
		if err != nil {
			return nil, err
		}
		for _, it := range items {
			st, err := statusFromDict(it)
			if err != nil {
				return nil, err
			}
			ctx.Dependencies.TaskDependencies = append(ctx.Dependencies.TaskDependencies, ContextDependency{
				TaskID: strOr(it, "task_id", ""), Title: strOr(it, "title", ""), Status: st, BlockingReason: strOr(it, "blocking_reason", "")})
		}
		if ctx.Dependencies.ExternalDependencies, err = strsOr(dm, "external_dependencies"); err != nil {
			return nil, err
		}
		if ctx.Dependencies.BlockedBy, err = strsOr(dm, "blocked_by"); err != nil {
			return nil, err
		}
	}

	if raw, ok := data["progress"]; ok {
		pm, err := getMap(raw, "progress")
		if err != nil {
			return nil, err
		}
		items, err := getItems(pm, "completed_actions")
		if err != nil {
			return nil, err
		}
		var p ContextProgress
		for _, it := range items {
			if err := checkKwargs("ContextProgressAction", it, []string{"timestamp", "action", "agent"}, []string{"details", "status"}); err != nil {
				return nil, err
			}
			p.CompletedActions = append(p.CompletedActions, ContextProgressAction{Timestamp: strOr(it, "timestamp", ""),
				Action: strOr(it, "action", ""), Agent: strOr(it, "agent", ""), Details: strOr(it, "details", ""),
				Status: strOr(it, "status", "completed")})
		}
		p.CurrentSessionSummary = strOr(pm, "current_session_summary", "")
		if p.NextSteps, err = strsOr(pm, "next_steps"); err != nil {
			return nil, err
		}
		if f, ok := toFloat(pm["completion_percentage"]); ok {
			p.CompletionPercentage = f
		}
		if f, ok := toFloat(pm["time_spent_minutes"]); ok {
			p.TimeSpentMinutes = int(f)
		}
		p.CompletionSummary, p.TestingNotes = optString(pm, "completion_summary"), optString(pm, "testing_notes")
		p.NextRecommendations = optString(pm, "next_recommendations")
		if f, ok := toFloat(pm["vision_alignment_score"]); ok {
			p.VisionAlignmentScore = &f
		}
		ctx.Progress = p
	}

	if raw, ok := data["subtasks"]; ok {
		sm, err := getMap(raw, "subtasks")
		if err != nil {
			return nil, err
		}
		items, err := getItems(sm, "items")
		if err != nil {
			return nil, err
		}
		var s ContextSubtasks
		for _, it := range items {
			st, err := statusFromDict(it)
			if err != nil {
				return nil, err
			}
			assignees, err := strsOr(it, "assignees")
			if err != nil {
				return nil, err
			}
			done, _ := it["completed"].(bool)
			s.Items = append(s.Items, ContextSubtask{ID: strOr(it, "id", ""), Title: strOr(it, "title", ""),
				Description: strOr(it, "description", ""), Status: st, Assignees: assignees, Completed: done,
				ProgressNotes: strOr(it, "progress_notes", "")})
		}
		if f, ok := toFloat(sm["total_count"]); ok {
			s.TotalCount = int(f)
		}
		if f, ok := toFloat(sm["completed_count"]); ok {
			s.CompletedCount = int(f)
		}
		if f, ok := toFloat(sm["progress_percentage"]); ok {
			s.ProgressPercentage = f
		}
		ctx.Subtasks = s
	}

	if raw, ok := data["notes"]; ok {
		nm, err := getMap(raw, "notes")
		if err != nil {
			return nil, err
		}
		var n ContextNotes
		if n.AgentInsights, err = parseInsights(nm, "agent_insights"); err != nil {
			return nil, err
		}
		if n.ChallengesEncountered, err = parseInsights(nm, "challenges_encountered"); err != nil {
			return nil, err
		}
		if n.SolutionsApplied, err = parseInsights(nm, "solutions_applied"); err != nil {
			return nil, err
		}
		if n.DecisionsMade, err = parseInsights(nm, "decisions_made"); err != nil {
			return nil, err
		}
		n.GeneralNotes = strOr(nm, "general_notes", "")
		ctx.Notes = n
	}

	if _, ok := data["custom_sections"]; ok {
		items, err := getItems(data, "custom_sections")
		if err != nil {
			return nil, err
		}
		ctx.CustomSections = []ContextCustomSection{}
		for _, it := range items {
			if err := checkKwargs("ContextCustomSection", it, []string{"name"}, []string{"data", "schema_version"}); err != nil {
				return nil, err
			}
			d, _ := it["data"].(map[string]any)
			ctx.CustomSections = append(ctx.CustomSections, ContextCustomSection{Name: strOr(it, "name", ""),
				Data: orEmpty(d), SchemaVersion: strOr(it, "schema_version", "1.0")})
		}
	}

	custom := map[string]any{}
	for k, v := range data {
		if !contextKnownFields[k] {
			custom[k] = v
		}
	}
	if len(custom) > 0 {
		ctx.CustomSections = append(ctx.CustomSections, NewContextCustomSection("root_level_custom_fields", custom))
	}
	return ctx, nil
}

// ContextSchemaVersion is ContextSchema.SCHEMA_VERSION.
const ContextSchemaVersion = "1.0"

// ContextSchema offers context schema management and validation.
type ContextSchema struct{}

// GetDefaultSchema returns a fresh copy of the default context JSON schema.
func (ContextSchema) GetDefaultSchema() map[string]any {
	var schema map[string]any
	if err := json.Unmarshal([]byte(defaultContextSchemaJSON), &schema); err != nil {
		panic(err) // the embedded document is constant
	}
	return schema
}

// ValidateContext does the basic required-field validation.
func (ContextSchema) ValidateContext(contextData any) (bool, []string) {
	errs := []string{}
	data, ok := contextData.(map[string]any)
	if !ok {
		return false, append(errs, "Context data must be a dictionary")
	}
	_, hasMeta := data["metadata"]
	_, hasObj := data["objective"]
	if !hasMeta {
		errs = append(errs, "Missing required field: metadata")
	}
	if !hasObj {
		errs = append(errs, "Missing required field: objective")
	}
	if hasMeta {
		if m, ok := data["metadata"].(map[string]any); ok {
			if _, ok := m["task_id"]; !ok {
				errs = append(errs, "Missing required field: metadata.task_id")
			}
		}
	}
	if hasObj {
		if o, ok := data["objective"].(map[string]any); ok {
			if _, ok := o["title"]; !ok {
				errs = append(errs, "Missing required field: objective.title")
			}
		}
	}
	return len(errs) == 0, errs
}

// EmptyContextOptions are create_empty_context's kwargs ("" → Python default).
type EmptyContextOptions struct {
	Status          string
	Priority        string
	Assignees       []string
	Labels          []string
	Description     string
	EstimatedEffort *string
	DueDate         *time.Time
}

// CreateEmptyContext creates a context with minimal required fields.
func (ContextSchema) CreateEmptyContext(taskID, title string, o EmptyContextOptions) (*TaskContext, error) {
	if o.Status == "" {
		o.Status = string(value_objects.TaskStatusTodo)
	}
	if o.Priority == "" {
		o.Priority = "medium"
	}
	status, err := value_objects.NewTaskStatus(o.Status)
	if err != nil {
		return nil, err
	}
	priority, err := value_objects.NewPriority(o.Priority)
	if err != nil {
		return nil, err
	}
	metadata, err := NewContextMetadata(ContextMetadata{TaskID: taskID, Status: &status, Priority: &priority,
		Assignees: o.Assignees, Labels: o.Labels})
	if err != nil {
		return nil, err
	}
	return NewTaskContext(metadata, ContextObjective{Title: title, Description: o.Description,
		EstimatedEffort: o.EstimatedEffort, DueDate: o.DueDate}), nil
}

const defaultContextSchemaJSON = `{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "type": "object",
 "title": "Task Context Schema",
 "description": "Schema for task context JSON files",
 "version": "1.0",
 "required": [
  "metadata",
  "objective"
 ],
 "properties": {
  "metadata": {
   "type": "object",
   "required": [
    "task_id"
   ],
   "properties": {
    "task_id": {
     "type": "string"
    },
    "status": {
     "type": "string",
     "enum": [
      "todo",
      "in_progress",
      "blocked",
      "review",
      "testing",
      "done",
      "cancelled"
     ]
    },
    "priority": {
     "type": "string",
     "enum": [
      "low",
      "medium",
      "high",
      "urgent",
      "critical"
     ]
    },
    "assignees": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "labels": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "created_at": {
     "type": "string",
     "format": "date-time"
    },
    "updated_at": {
     "type": "string",
     "format": "date-time"
    },
    "version": {
     "type": "integer",
     "minimum": 1
    }
   }
  },
  "objective": {
   "type": "object",
   "required": [
    "title"
   ],
   "properties": {
    "title": {
     "type": "string"
    },
    "description": {
     "type": "string"
    },
    "estimated_effort": {
     "type": "string",
     "enum": [
      "quick",
      "short",
      "small",
      "medium",
      "large",
      "xlarge",
      "epic",
      "massive"
     ]
    },
    "due_date": {
     "type": [
      "string",
      "null"
     ],
     "format": "date"
    }
   }
  },
  "requirements": {
   "type": "object",
   "properties": {
    "checklist": {
     "type": "array",
     "items": {
      "type": "object",
      "required": [
       "id",
       "title"
      ],
      "properties": {
       "id": {
        "type": "string"
       },
       "title": {
        "type": "string"
       },
       "completed": {
        "type": "boolean",
        "default": false
       },
       "priority": {
        "type": "string",
        "enum": [
         "low",
         "medium",
         "high"
        ]
       },
       "notes": {
        "type": "string"
       }
      }
     }
    },
    "custom_requirements": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "completion_criteria": {
     "type": "array",
     "items": {
      "type": "string"
     }
    }
   }
  },
  "technical": {
   "type": "object",
   "properties": {
    "technologies": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "frameworks": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "database": {
     "type": "string"
    },
    "key_files": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "key_directories": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "architecture_notes": {
     "type": "string"
    },
    "patterns_used": {
     "type": "array",
     "items": {
      "type": "string"
     }
    }
   }
  },
  "dependencies": {
   "type": "object",
   "properties": {
    "task_dependencies": {
     "type": "array",
     "items": {
      "type": "object",
      "required": [
       "task_id"
      ],
      "properties": {
       "task_id": {
        "type": "string"
       },
       "title": {
        "type": "string"
       },
       "status": {
        "type": "string"
       },
       "blocking_reason": {
        "type": "string"
       }
      }
     }
    },
    "external_dependencies": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "blocked_by": {
     "type": "array",
     "items": {
      "type": "string"
     }
    }
   }
  },
  "progress": {
   "type": "object",
   "properties": {
    "completed_actions": {
     "type": "array",
     "items": {
      "type": "object",
      "required": [
       "timestamp",
       "action",
       "agent"
      ],
      "properties": {
       "timestamp": {
        "type": "string",
        "format": "date-time"
       },
       "action": {
        "type": "string"
       },
       "agent": {
        "type": "string"
       },
       "details": {
        "type": "string"
       },
       "status": {
        "type": "string",
        "enum": [
         "completed",
         "in_progress",
         "failed"
        ]
       }
      }
     }
    },
    "current_session_summary": {
     "type": "string"
    },
    "next_steps": {
     "type": "array",
     "items": {
      "type": "string"
     }
    },
    "completion_percentage": {
     "type": "number",
     "minimum": 0,
     "maximum": 100
    },
    "time_spent_minutes": {
     "type": "integer",
     "minimum": 0
    }
   }
  },
  "subtasks": {
   "type": "object",
   "properties": {
    "items": {
     "type": "array",
     "items": {
      "type": "object",
      "required": [
       "id",
       "title"
      ],
      "properties": {
       "id": {
        "type": "string"
       },
       "title": {
        "type": "string"
       },
       "description": {
        "type": "string"
       },
       "status": {
        "type": "string",
        "enum": [
         "todo",
         "in_progress",
         "done",
         "cancelled"
        ]
       },
       "assignees": {
        "type": "array",
        "items": {
         "type": "string"
        }
       },
       "completed": {
        "type": "boolean"
       },
       "progress_notes": {
        "type": "string"
       }
      }
     }
    },
    "total_count": {
     "type": "integer",
     "minimum": 0
    },
    "completed_count": {
     "type": "integer",
     "minimum": 0
    },
    "progress_percentage": {
     "type": "number",
     "minimum": 0,
     "maximum": 100
    }
   }
  },
  "notes": {
   "type": "object",
   "properties": {
    "agent_insights": {
     "type": "array",
     "items": {
      "type": "object",
      "required": [
       "timestamp",
       "agent",
       "category",
       "content"
      ],
      "properties": {
       "timestamp": {
        "type": "string",
        "format": "date-time"
       },
       "agent": {
        "type": "string"
       },
       "category": {
        "type": "string",
        "enum": [
         "insight",
         "challenge",
         "solution",
         "decision"
        ]
       },
       "content": {
        "type": "string"
       },
       "importance": {
        "type": "string",
        "enum": [
         "low",
         "medium",
         "high",
         "critical"
        ]
       }
      }
     }
    },
    "challenges_encountered": {
     "type": "array",
     "items": {
      "$ref": "#/properties/notes/properties/agent_insights/items"
     }
    },
    "solutions_applied": {
     "type": "array",
     "items": {
      "$ref": "#/properties/notes/properties/agent_insights/items"
     }
    },
    "decisions_made": {
     "type": "array",
     "items": {
      "$ref": "#/properties/notes/properties/agent_insights/items"
     }
    },
    "general_notes": {
     "type": "string"
    }
   }
  },
  "custom_sections": {
   "type": "array",
   "items": {
    "type": "object",
    "required": [
     "name"
    ],
    "properties": {
     "name": {
      "type": "string"
     },
     "data": {
      "type": "object"
     },
     "schema_version": {
      "type": "string",
      "default": "1.0"
     }
    }
   }
  }
 }
}`
