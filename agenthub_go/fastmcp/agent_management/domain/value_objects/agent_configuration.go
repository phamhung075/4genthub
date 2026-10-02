package value_objects

import (
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentConfiguration is the immutable configuration of an agent: system prompt, tools,
// capabilities, rules, output format and metadata. A nil map is Python's None; the
// With* methods return new values and share the maps, like the frozen dataclass.
type AgentConfiguration struct {
	SystemPrompt string
	Tools        []string
	Capabilities *entities.OrderedMap[any]
	Rules        []string
	OutputFormat *entities.OrderedMap[any]
	Metadata     *entities.OrderedMap[any]
}

// NewAgentConfiguration validates the system prompt (not empty or whitespace).
func NewAgentConfiguration(systemPrompt string, tools []string, capabilities *entities.OrderedMap[any], rules []string, outputFormat, metadata *entities.OrderedMap[any]) (AgentConfiguration, error) {
	if tmvo.PyStrip(systemPrompt) == "" {
		return AgentConfiguration{}, tmvo.ValueErrorf("Agent system_prompt cannot be empty")
	}
	return AgentConfiguration{
		SystemPrompt: systemPrompt, Tools: append([]string{}, tools...), Capabilities: capabilities,
		Rules: append([]string{}, rules...), OutputFormat: outputFormat, Metadata: metadata,
	}, nil
}

// NewAgentConfigurationDefaults is AgentConfiguration(system_prompt=...) with the
// default empty tools, capabilities, rules, output format and metadata.
func NewAgentConfigurationDefaults(systemPrompt string) (AgentConfiguration, error) {
	return NewAgentConfiguration(systemPrompt, nil, entities.NewOrderedMap[any](), nil, entities.NewOrderedMap[any](), entities.NewOrderedMap[any]())
}

// dictField is data.get(key, {}): a missing key is an empty dict, null stays None.
func dictField(data *entities.OrderedMap[any], key string) (*entities.OrderedMap[any], error) {
	v, ok := data.Get(key)
	if !ok {
		return entities.NewOrderedMap[any](), nil
	}
	switch m := v.(type) {
	case nil:
		return nil, nil
	case *entities.OrderedMap[any]:
		return m, nil
	}
	return nil, tmvo.TypeErrorf("AgentConfiguration %s must be a dict, got %s", key, tmvo.PyRepr(v))
}

// listField is tuple(data.get(key, [])): null is not iterable; items must be strings.
func listField(data *entities.OrderedMap[any], key string) ([]string, error) {
	v, ok := data.Get(key)
	if !ok {
		return []string{}, nil
	}
	if strs, isStrs := v.([]string); isStrs {
		return append([]string{}, strs...), nil
	}
	list, isList := v.([]any)
	if !isList {
		return nil, tmvo.TypeErrorf("AgentConfiguration %s must be a list of strings", key)
	}
	out := make([]string, 0, len(list))
	for _, e := range list {
		s, isStr := e.(string)
		if !isStr {
			return nil, tmvo.TypeErrorf("AgentConfiguration %s must be a list of strings", key)
		}
		out = append(out, s)
	}
	return out, nil
}

// AgentConfigurationFromDict creates a configuration from a dict (missing system_prompt
// is empty and therefore a ValueError).
func AgentConfigurationFromDict(data *entities.OrderedMap[any]) (AgentConfiguration, error) {
	prompt := ""
	if v, ok := data.Get("system_prompt"); ok {
		s, isStr := v.(string)
		if !isStr {
			if v == nil {
				return AgentConfiguration{}, tmvo.ValueErrorf("Agent system_prompt cannot be empty")
			}
			return AgentConfiguration{}, tmvo.TypeErrorf("AgentConfiguration system_prompt must be a string")
		}
		prompt = s
	}
	tools, err := listField(data, "tools")
	if err != nil {
		return AgentConfiguration{}, err
	}
	capabilities, err := dictField(data, "capabilities")
	if err != nil {
		return AgentConfiguration{}, err
	}
	rules, err := listField(data, "rules")
	if err != nil {
		return AgentConfiguration{}, err
	}
	outputFormat, err := dictField(data, "output_format")
	if err != nil {
		return AgentConfiguration{}, err
	}
	metadata, err := dictField(data, "metadata")
	if err != nil {
		return AgentConfiguration{}, err
	}
	return NewAgentConfiguration(prompt, tools, capabilities, rules, outputFormat, metadata)
}

func orNone(m *entities.OrderedMap[any]) any {
	if m == nil {
		return nil
	}
	return m
}

func strList(items []string) []any {
	out := make([]any, len(items))
	for i, s := range items {
		out[i] = s
	}
	return out
}

// ToDict converts the configuration to a dict for storage.
func (c AgentConfiguration) ToDict() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("system_prompt", c.SystemPrompt)
	d.Set("tools", strList(c.Tools))
	d.Set("capabilities", orNone(c.Capabilities))
	d.Set("rules", strList(c.Rules))
	d.Set("output_format", orNone(c.OutputFormat))
	d.Set("metadata", orNone(c.Metadata))
	return d
}

// ToJSON is json.dumps(to_dict(), indent=2).
func (c AgentConfiguration) ToJSON() (string, error) { return tmvo.PyJSONDumps(c.ToDict(), 2) }

// WithSystemPrompt returns a copy with a new system prompt (validated).
func (c AgentConfiguration) WithSystemPrompt(systemPrompt string) (AgentConfiguration, error) {
	return NewAgentConfiguration(systemPrompt, c.Tools, c.Capabilities, c.Rules, c.OutputFormat, c.Metadata)
}

// WithTools returns a copy with a new tools list.
func (c AgentConfiguration) WithTools(tools []string) (AgentConfiguration, error) {
	return NewAgentConfiguration(c.SystemPrompt, tools, c.Capabilities, c.Rules, c.OutputFormat, c.Metadata)
}

// MergeCapabilities returns a copy with newCapabilities merged over the current ones
// ({**old, **new}: existing keys keep their position).
func (c AgentConfiguration) MergeCapabilities(newCapabilities *entities.OrderedMap[any]) (AgentConfiguration, error) {
	merged := entities.NewOrderedMap[any]()
	for _, src := range []*entities.OrderedMap[any]{c.Capabilities, newCapabilities} {
		if src == nil {
			continue
		}
		for _, k := range src.Keys() {
			v, _ := src.Get(k)
			merged.Set(k, v)
		}
	}
	return NewAgentConfiguration(c.SystemPrompt, c.Tools, merged, c.Rules, c.OutputFormat, c.Metadata)
}
