// Package entities ports agent_management/domain/entities.
package entities

import (
	"fmt"
	"math/big"
	"os"
	"time"

	"agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// FileNotFoundError is Python's FileNotFoundError (Unwrap gives os.ErrNotExist).
type FileNotFoundError struct{ Msg string }

func (e *FileNotFoundError) Error() string { return e.Msg }
func (e *FileNotFoundError) Unwrap() error { return os.ErrNotExist }

// AgentTemplate is the immutable template for agent instances loaded from the
// agent-library: the source-of-truth configuration for an agent type.
type AgentTemplate struct {
	base.BaseTimestampEntity

	ID                   *value_objects.AgentTemplateId
	Slug                 string // URL-friendly identifier, e.g. 'coding-agent'
	Name                 string
	Category             string
	Description          string
	Version              string
	DefaultConfiguration *value_objects.AgentConfiguration
	Metadata             *entities.OrderedMap[any] // nil is Python's None
}

// DefaultAgentTemplate has the dataclass defaults (version "1.0.0", empty metadata);
// set the fields and pass it to NewAgentTemplate.
func DefaultAgentTemplate() AgentTemplate {
	return AgentTemplate{Version: "1.0.0", Metadata: entities.NewOrderedMap[any]()}
}

// NewAgentTemplate requires a default configuration, initializes the timestamps and
// validates the business rules.
func NewAgentTemplate(t AgentTemplate) (*AgentTemplate, error) {
	if t.DefaultConfiguration == nil {
		return nil, tmvo.ValueErrorf("AgentTemplate must have a default_configuration")
	}
	s := t
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// GetEntityID is the template id or "unknown".
func (t *AgentTemplate) GetEntityID() string {
	if t.ID != nil {
		return t.ID.String()
	}
	return "unknown"
}

// ValidateEntity checks the template invariants.
func (t *AgentTemplate) ValidateEntity() error {
	switch {
	case tmvo.PyStrip(t.Slug) == "":
		return tmvo.ValueErrorf("AgentTemplate slug cannot be empty")
	case tmvo.PyStrip(t.Name) == "":
		return tmvo.ValueErrorf("AgentTemplate name cannot be empty")
	case tmvo.PyStrip(t.Category) == "":
		return tmvo.ValueErrorf("AgentTemplate category cannot be empty")
	case tmvo.PyStrip(t.Version) == "":
		return tmvo.ValueErrorf("AgentTemplate version cannot be empty")
	case t.DefaultConfiguration == nil:
		return tmvo.ValueErrorf("AgentTemplate must have default_configuration")
	}
	for _, c := range t.Slug {
		if !tmvo.PyIsAlnum(c) && c != '-' && c != '_' {
			return tmvo.ValueErrorf("AgentTemplate slug '%s' contains invalid characters. Only lowercase letters, numbers, hyphens, and underscores allowed.", t.Slug)
		}
	}
	return nil
}

// pyTypeName is the "<class 'x'>" text of a decoded YAML/JSON value's type.
func pyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "<class 'NoneType'>"
	case string:
		return "<class 'str'>"
	case bool:
		return "<class 'bool'>"
	case int64, *big.Int:
		return "<class 'int'>"
	case float64:
		return "<class 'float'>"
	case []any:
		return "<class 'list'>"
	case *entities.OrderedMap[any]:
		return "<class 'dict'>"
	}
	return fmt.Sprintf("%T", v)
}

// yamlString is a value used as a string field: strings only (Python would fail later on
// the first string operation).
func yamlString(v any, field string) (string, error) {
	s, ok := v.(string)
	if !ok {
		return "", tmvo.TypeErrorf("AgentTemplate %s must be a string, got %s", field, pyTypeName(v))
	}
	return s, nil
}

// FromYAML loads a template from a YAML file of the agent-library; a nil templateID
// generates a new id.
func FromYAML(yamlPath string, templateID *value_objects.AgentTemplateId) (*AgentTemplate, error) {
	raw, err := os.ReadFile(yamlPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, &FileNotFoundError{"Agent template YAML not found: " + yamlPath}
		}
		return nil, err
	}
	loaded, err := entities.LoadYAML(raw)
	if err != nil {
		return nil, tmvo.ValueErrorf("Invalid YAML in %s: %v", yamlPath, err)
	}
	data, ok := loaded.(*entities.OrderedMap[any])
	if !ok {
		return nil, tmvo.ValueErrorf("Expected dict in YAML, got %s", pyTypeName(loaded))
	}

	get := func(key string, def any) any {
		if v, ok := data.Get(key); ok {
			return v
		}
		return def
	}
	nameV := get("name", nil)
	slugV := get("slug", nil)
	var slug string
	if tmvo.PyTruthy(slugV) {
		if slug, err = yamlString(slugV, "slug"); err != nil {
			return nil, err
		}
	} else {
		nameStr, err := yamlString(get("name", ""), "name")
		if err != nil {
			return nil, err
		}
		slug = replaceSpaces(tmvo.PyLower(nameStr))
	}
	if !tmvo.PyTruthy(nameV) {
		return nil, tmvo.ValueErrorf("Agent template YAML missing 'name' field: %s", yamlPath)
	}
	name, err := yamlString(nameV, "name")
	if err != nil {
		return nil, err
	}

	configData := entities.NewOrderedMap[any]()
	configData.Set("system_prompt", get("system_prompt", ""))
	configData.Set("tools", get("tools", []any{}))
	configData.Set("capabilities", get("capabilities", entities.NewOrderedMap[any]()))
	configData.Set("rules", get("rules", []any{}))
	configData.Set("output_format", get("output_format", entities.NewOrderedMap[any]()))
	configData.Set("metadata", get("metadata", entities.NewOrderedMap[any]()))
	configuration, err := value_objects.AgentConfigurationFromDict(configData)
	if err != nil {
		return nil, err
	}

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("source_file", yamlPath)
	switch m := get("metadata", entities.NewOrderedMap[any]()).(type) {
	case *entities.OrderedMap[any]:
		for _, k := range m.Keys() {
			v, _ := m.Get(k)
			metadata.Set(k, v)
		}
	default:
		return nil, tmvo.TypeErrorf("'%s' object is not a mapping", pyTypeName(m))
	}

	t := DefaultAgentTemplate()
	if templateID != nil {
		t.ID = templateID
	} else {
		id := value_objects.GenerateNewAgentTemplateId()
		t.ID = &id
	}
	t.Slug, t.Name, t.DefaultConfiguration, t.Metadata = slug, name, &configuration, metadata
	for _, f := range []struct {
		key, def string
		dst      *string
	}{{"category", "general", &t.Category}, {"description", "", &t.Description}, {"version", "1.0.0", &t.Version}} {
		if *f.dst, err = yamlString(get(f.key, f.def), f.key); err != nil {
			return nil, err
		}
	}
	return NewAgentTemplate(t)
}

func replaceSpaces(s string) string {
	out := []rune(s)
	for i, r := range out {
		if r == ' ' {
			out[i] = '-'
		}
	}
	return string(out)
}

// optionalID is `T.from_string(str(v)) if data.get(key) else None`; an already typed
// id is used as is.
func optionalID[T any](data *entities.OrderedMap[any], key string, ctor func(string) (T, error)) (*T, error) {
	v, ok := data.Get(key)
	if !ok || !tmvo.PyTruthy(v) {
		return nil, nil
	}
	switch x := v.(type) {
	case T:
		return &x, nil
	case *T:
		return x, nil
	}
	id, err := ctor(tmvo.PyStr(v))
	if err != nil {
		return nil, err
	}
	return &id, nil
}

// optionalTime is a datetime field of from_dict: a time, or an ISO string, or absent.
func optionalTime(data *entities.OrderedMap[any], key string) (*time.Time, error) {
	v, ok := data.Get(key)
	if !ok || !tmvo.PyTruthy(v) {
		return nil, nil
	}
	switch x := v.(type) {
	case time.Time:
		return &x, nil
	case *time.Time:
		return x, nil
	case string:
		t, err := tmvo.ParseISO(x)
		if err != nil {
			return nil, err
		}
		return &t, nil
	}
	return nil, tmvo.TypeErrorf("%s must be a datetime, got %s", key, pyTypeName(v))
}

// configurationField is the `configuration` handling of from_dict: a dict is parsed, a
// configuration is used as is, anything else is a ValueError.
func configurationField(data *entities.OrderedMap[any], key, errMsg string) (*value_objects.AgentConfiguration, error) {
	v, _ := data.Get(key)
	switch c := v.(type) {
	case *entities.OrderedMap[any]:
		cfg, err := value_objects.AgentConfigurationFromDict(c)
		return &cfg, err
	case value_objects.AgentConfiguration:
		return &c, nil
	case *value_objects.AgentConfiguration:
		if c != nil {
			return c, nil
		}
	}
	return nil, tmvo.ValueErrorf("%s", errMsg)
}

func stringField(data *entities.OrderedMap[any], key, def string) (string, error) {
	v, ok := data.Get(key)
	if !ok {
		return def, nil
	}
	return yamlString(v, key)
}

// metadataField is data.get("metadata", {}): a dict or None.
func metadataField(data *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	v, ok := data.Get("metadata")
	if !ok {
		return entities.NewOrderedMap[any](), nil
	}
	switch m := v.(type) {
	case nil:
		return nil, nil
	case *entities.OrderedMap[any]:
		return m, nil
	}
	return nil, tmvo.TypeErrorf("metadata must be a dict, got %s", pyTypeName(v))
}

// AgentTemplateFromDict creates a template from a dict (e.g. a database row).
func AgentTemplateFromDict(data *entities.OrderedMap[any]) (*AgentTemplate, error) {
	t := AgentTemplate{}
	var err error
	if t.ID, err = optionalID(data, "id", value_objects.NewAgentTemplateId); err != nil {
		return nil, err
	}
	if t.DefaultConfiguration, err = configurationField(data, "default_configuration", "Invalid default_configuration format"); err != nil {
		return nil, err
	}
	for _, f := range []struct {
		key, def string
		dst      *string
	}{{"slug", "", &t.Slug}, {"name", "", &t.Name}, {"category", "", &t.Category}, {"description", "", &t.Description}, {"version", "1.0.0", &t.Version}} {
		if *f.dst, err = stringField(data, f.key, f.def); err != nil {
			return nil, err
		}
	}
	if t.Metadata, err = metadataField(data); err != nil {
		return nil, err
	}
	if t.CreatedAt, err = optionalTime(data, "created_at"); err != nil {
		return nil, err
	}
	if t.UpdatedAt, err = optionalTime(data, "updated_at"); err != nil {
		return nil, err
	}
	return NewAgentTemplate(t)
}

func isoOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return tmvo.IsoFormat(*t)
}

func idOrNil[T fmt.Stringer](id *T) any {
	if id == nil {
		return nil
	}
	return (*id).String()
}

func metaOrNone(m *entities.OrderedMap[any]) any {
	if m == nil {
		return nil
	}
	return m
}

// ToDict converts the template for storage / serialization.
func (t *AgentTemplate) ToDict() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("id", idOrNil(t.ID))
	d.Set("slug", t.Slug)
	d.Set("name", t.Name)
	d.Set("category", t.Category)
	d.Set("description", t.Description)
	d.Set("version", t.Version)
	if t.DefaultConfiguration != nil {
		d.Set("default_configuration", t.DefaultConfiguration.ToDict())
	} else {
		d.Set("default_configuration", entities.NewOrderedMap[any]())
	}
	d.Set("metadata", metaOrNone(t.Metadata))
	d.Set("created_at", isoOrNil(t.CreatedAt))
	d.Set("updated_at", isoOrNil(t.UpdatedAt))
	return d
}

// MatchesSlug compares slugs case-insensitively.
func (t *AgentTemplate) MatchesSlug(slug string) bool {
	return tmvo.PyLower(t.Slug) == tmvo.PyLower(slug)
}

// GetConfigurationCopy returns a copy of the default configuration (re-validated; the
// maps are shared, like Python's from_dict(to_dict())).
func (t *AgentTemplate) GetConfigurationCopy() (value_objects.AgentConfiguration, error) {
	if t.DefaultConfiguration == nil {
		return value_objects.AgentConfiguration{}, tmvo.ValueErrorf("Template has no default configuration")
	}
	return value_objects.AgentConfigurationFromDict(t.DefaultConfiguration.ToDict())
}

func (t *AgentTemplate) String() string {
	id := "None"
	if t.ID != nil {
		id = t.ID.String()
	}
	return fmt.Sprintf("AgentTemplate(id=%s, slug='%s', name='%s', category='%s', version='%s')", id, t.Slug, t.Name, t.Category, t.Version)
}
