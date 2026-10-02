package entities

import (
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

const noneValueError = "'NoneType' object has no attribute 'value'"

// KeyError mirrors Python's KeyError; its text is the repr of the missing key.
type KeyError struct{ Key string }

func (e *KeyError) Error() string { return value_objects.PyRepr(e.Key) }

// Template is a template in the system. Nil enum/ID pointers mirror Python None.
type Template struct {
	base.BaseTimestampEntity
	ID               *value_objects.TemplateId
	Name             string
	Description      string
	Content          string
	TemplateType     *value_objects.TemplateType
	Category         *value_objects.TemplateCategory
	Status           *value_objects.TemplateStatus
	Priority         *value_objects.TemplatePriority
	CompatibleAgents []string
	FilePatterns     []string
	Variables        []string
	Metadata         map[string]any
	Version          *int  // nil → 1
	IsActive         *bool // nil → true
}

// NewTemplate applies the Python dataclass defaults, initializes timestamps and validates.
func NewTemplate(t Template) (*Template, error) {
	s := t
	if s.CompatibleAgents == nil {
		s.CompatibleAgents = []string{}
	}
	if s.FilePatterns == nil {
		s.FilePatterns = []string{}
	}
	if s.Variables == nil {
		s.Variables = []string{}
	}
	if s.Metadata == nil {
		s.Metadata = map[string]any{}
	}
	if s.Version == nil {
		one := 1
		s.Version = &one
	}
	if s.IsActive == nil {
		yes := true
		s.IsActive = &yes
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

func (t *Template) GetEntityID() string {
	if t.ID == nil {
		return "None"
	}
	return t.ID.String()
}

func (t *Template) ValidateEntity() error {
	if strings.TrimSpace(t.Name) == "" {
		return value_objects.ValueErrorf("Template name cannot be empty")
	}
	if strings.TrimSpace(t.Content) == "" {
		return value_objects.ValueErrorf("Template content cannot be empty")
	}
	if strings.TrimSpace(t.Description) == "" {
		return value_objects.ValueErrorf("Template description cannot be empty")
	}
	return nil
}

func (t *Template) UpdateContent(content string) error {
	if strings.TrimSpace(content) == "" {
		return value_objects.ValueErrorf("Template content cannot be empty")
	}
	t.Content = content
	*t.Version++
	return t.Touch("content_updated")
}

func (t *Template) UpdateMetadata(metadata map[string]any) error {
	for k, v := range metadata {
		t.Metadata[k] = v
	}
	return t.Touch("metadata_updated")
}

func indexOf(l []string, v string) int {
	for i, e := range l {
		if e == v {
			return i
		}
	}
	return -1
}

func (t *Template) addTo(list *[]string, v, reason string) error {
	if indexOf(*list, v) < 0 {
		*list = append(*list, v)
		return t.Touch(reason)
	}
	return nil
}

func (t *Template) removeFrom(list *[]string, v, reason string) error {
	if i := indexOf(*list, v); i >= 0 {
		*list = append((*list)[:i], (*list)[i+1:]...)
		return t.Touch(reason)
	}
	return nil
}

func (t *Template) AddCompatibleAgent(n string) error {
	return t.addTo(&t.CompatibleAgents, n, "agent_added")
}
func (t *Template) RemoveCompatibleAgent(n string) error {
	return t.removeFrom(&t.CompatibleAgents, n, "agent_removed")
}
func (t *Template) AddFilePattern(p string) error {
	return t.addTo(&t.FilePatterns, p, "pattern_added")
}
func (t *Template) RemoveFilePattern(p string) error {
	return t.removeFrom(&t.FilePatterns, p, "pattern_removed")
}
func (t *Template) AddVariable(v string) error { return t.addTo(&t.Variables, v, "variable_added") }
func (t *Template) RemoveVariable(v string) error {
	return t.removeFrom(&t.Variables, v, "variable_removed")
}

func (t *Template) setStatus(active bool, s value_objects.TemplateStatus, reason string) error {
	*t.IsActive = active
	t.Status = &s
	return t.Touch(reason)
}

func (t *Template) Activate() error {
	return t.setStatus(true, value_objects.TemplateStatusActive, "template_activated")
}
func (t *Template) Deactivate() error {
	return t.setStatus(false, value_objects.TemplateStatusInactive, "template_deactivated")
}
func (t *Template) Archive() error {
	return t.setStatus(false, value_objects.TemplateStatusArchived, "template_archived")
}

func (t *Template) IsCompatibleWithAgent(agentName string) bool {
	return indexOf(t.CompatibleAgents, "*") >= 0 || indexOf(t.CompatibleAgents, agentName) >= 0
}

// MatchesFilePatterns reports whether any template pattern fnmatches any given file pattern.
func (t *Template) MatchesFilePatterns(filePatterns []string) bool {
	if len(t.FilePatterns) == 0 {
		return true
	}
	for _, tp := range t.FilePatterns {
		for _, fp := range filePatterns {
			if fnmatch(fp, tp) {
				return true
			}
		}
	}
	return false
}

// ToDict mirrors to_dict; Python raises AttributeError if id or an enum is None.
func (t *Template) ToDict() (map[string]any, error) {
	if t.ID == nil || t.TemplateType == nil || t.Category == nil || t.Status == nil || t.Priority == nil {
		return nil, fmt.Errorf("AttributeError: %s", noneValueError)
	}
	return map[string]any{
		"id": t.ID.Value, "name": t.Name, "description": t.Description, "content": t.Content,
		"template_type": string(*t.TemplateType), "category": string(*t.Category),
		"status": string(*t.Status), "priority": string(*t.Priority),
		"compatible_agents": t.CompatibleAgents, "file_patterns": t.FilePatterns,
		"variables": t.Variables, "metadata": t.Metadata,
		"created_at": value_objects.IsoFormat(*t.CreatedAt), "updated_at": value_objects.IsoFormat(*t.UpdatedAt),
		"version": *t.Version, "is_active": *t.IsActive,
	}, nil
}

func enumFrom[T ~string](name, v string, all []T) (T, error) {
	for _, e := range all {
		if string(e) == v {
			return e, nil
		}
	}
	var zero T
	return zero, value_objects.ValueErrorf("%s is not a valid %s", value_objects.PyRepr(v), name)
}

func reqString(d map[string]any, key string) (string, error) {
	v, ok := d[key]
	if !ok {
		return "", &KeyError{key}
	}
	s, ok := v.(string)
	if !ok {
		return "", value_objects.TypeErrorf("%s must be a string", key)
	}
	return s, nil
}

func reqStrings(d map[string]any, key string) ([]string, error) {
	v, ok := d[key]
	if !ok {
		return nil, &KeyError{key}
	}
	switch l := v.(type) {
	case []string:
		return append([]string{}, l...), nil
	case []any:
		out := []string{}
		for _, e := range l {
			s, ok := e.(string)
			if !ok {
				return nil, value_objects.TypeErrorf("%s must contain strings", key)
			}
			out = append(out, s)
		}
		return out, nil
	}
	return nil, value_objects.TypeErrorf("%s must be a list", key)
}

// TemplateFromDict mirrors Template.from_dict.
func TemplateFromDict(data map[string]any) (*Template, error) {
	idS, err := reqString(data, "id")
	if err != nil {
		return nil, err
	}
	id, err := value_objects.NewTemplateId(idS)
	if err != nil {
		return nil, err
	}
	t := Template{ID: &id}
	if t.Name, err = reqString(data, "name"); err != nil {
		return nil, err
	}
	if t.Description, err = reqString(data, "description"); err != nil {
		return nil, err
	}
	if t.Content, err = reqString(data, "content"); err != nil {
		return nil, err
	}
	ts, err := reqString(data, "template_type")
	if err != nil {
		return nil, err
	}
	tt, err := enumFrom("TemplateType", ts, value_objects.TemplateTypeValues)
	if err != nil {
		return nil, err
	}
	t.TemplateType = &tt
	cs, err := reqString(data, "category")
	if err != nil {
		return nil, err
	}
	cat, err := enumFrom("TemplateCategory", cs, value_objects.TemplateCategoryValues)
	if err != nil {
		return nil, err
	}
	t.Category = &cat
	ss, err := reqString(data, "status")
	if err != nil {
		return nil, err
	}
	st, err := enumFrom("TemplateStatus", ss, value_objects.TemplateStatusValues)
	if err != nil {
		return nil, err
	}
	t.Status = &st
	ps, err := reqString(data, "priority")
	if err != nil {
		return nil, err
	}
	pr, err := enumFrom("TemplatePriority", ps, value_objects.TemplatePriorityValues)
	if err != nil {
		return nil, err
	}
	t.Priority = &pr
	if t.CompatibleAgents, err = reqStrings(data, "compatible_agents"); err != nil {
		return nil, err
	}
	if t.FilePatterns, err = reqStrings(data, "file_patterns"); err != nil {
		return nil, err
	}
	if t.Variables, err = reqStrings(data, "variables"); err != nil {
		return nil, err
	}
	md, ok := data["metadata"]
	if !ok {
		return nil, &KeyError{"metadata"}
	}
	if t.Metadata, ok = md.(map[string]any); !ok {
		return nil, value_objects.TypeErrorf("metadata must be a dict")
	}
	if v, ok := data["version"]; ok {
		var n int
		switch x := v.(type) {
		case int:
			n = x
		case float64: // encoding/json decodes every number as float64
			if x != float64(int(x)) {
				return nil, value_objects.TypeErrorf("version must be an integer")
			}
			n = int(x)
		default:
			return nil, value_objects.TypeErrorf("version must be an int")
		}
		t.Version = &n
	}
	if v, ok := data["is_active"]; ok {
		b, ok := v.(bool)
		if !ok {
			return nil, value_objects.TypeErrorf("is_active must be a bool")
		}
		t.IsActive = &b
	}
	created, err := timestampFromDict(data, "created_at")
	if err != nil {
		return nil, err
	}
	t.CreatedAt = created
	updated, err := timestampFromDict(data, "updated_at")
	if err != nil {
		return nil, err
	}
	t.UpdatedAt = updated
	return NewTemplate(t)
}

// timestampFromDict parses an optional ISO timestamp and coerces it to UTC
// (naive values are taken as UTC, as _coerce_to_utc does).
func timestampFromDict(d map[string]any, key string) (*time.Time, error) {
	v, ok := d[key]
	if !ok {
		return nil, nil
	}
	s, ok := v.(string)
	if !ok {
		return nil, value_objects.TypeErrorf("fromisoformat: argument must be str")
	}
	ts, err := value_objects.ParseISO(s)
	if err != nil {
		return nil, err
	}
	ts = ts.UTC()
	return &ts, nil
}

// TemplateResult is the result of a template rendering operation.
type TemplateResult struct {
	Content          string
	TemplateID       value_objects.TemplateId
	VariablesUsed    map[string]any
	GeneratedAt      time.Time
	GenerationTimeMs int
	CacheHit         bool
	OutputPath       *string
}

func (r TemplateResult) ToDict() map[string]any {
	return map[string]any{
		"content": r.Content, "template_id": r.TemplateID.Value, "variables_used": r.VariablesUsed,
		"generated_at": value_objects.IsoFormat(r.GeneratedAt), "generation_time_ms": r.GenerationTimeMs,
		"cache_hit": r.CacheHit, "output_path": strOrNil(r.OutputPath),
	}
}

func strOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// TemplateRenderRequest is a request for template rendering.
type TemplateRenderRequest struct {
	TemplateID      value_objects.TemplateId
	Variables       map[string]any
	TaskContext     map[string]any
	OutputPath      *string
	CacheStrategy   string // "" → "default"
	ForceRegenerate bool
}

func (r TemplateRenderRequest) ToDict() map[string]any {
	cs := r.CacheStrategy
	if cs == "" {
		cs = "default"
	}
	var tc any
	if r.TaskContext != nil {
		tc = r.TaskContext
	}
	return map[string]any{
		"template_id": r.TemplateID.Value, "variables": r.Variables, "task_context": tc,
		"output_path": strOrNil(r.OutputPath), "cache_strategy": cs, "force_regenerate": r.ForceRegenerate,
	}
}

// TemplateUsage is the template usage tracking entity.
type TemplateUsage struct {
	TemplateID       value_objects.TemplateId
	TaskID           *string
	ProjectID        *string
	AgentName        *string
	VariablesUsed    map[string]any
	OutputPath       *string
	GenerationTimeMs int
	CacheHit         bool
	UsedAt           time.Time
}

func (u TemplateUsage) ToDict() map[string]any {
	return map[string]any{
		"template_id": u.TemplateID.Value, "task_id": strOrNil(u.TaskID), "project_id": strOrNil(u.ProjectID),
		"agent_name": strOrNil(u.AgentName), "variables_used": u.VariablesUsed, "output_path": strOrNil(u.OutputPath),
		"generation_time_ms": u.GenerationTimeMs, "cache_hit": u.CacheHit, "used_at": value_objects.IsoFormat(u.UsedAt),
	}
}
