// Package configuration ports task_management/infrastructure/configuration.
package configuration

import (
	"fmt"
	"os"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

type obj = *entities.OrderedMap[any]

// ToolConfig manages MCP tool configuration and enablement settings.
type ToolConfig struct {
	Config obj
	getenv func(string) (string, bool)
}

var toolEnvDefaults = []struct{ tool, env string }{
	{"manage_project", "TOOL_MANAGE_PROJECT"}, {"manage_task", "TOOL_MANAGE_TASK"}, {"manage_subtask", "TOOL_MANAGE_SUBTASK"},
	{"manage_agent", "TOOL_MANAGE_AGENT"}, {"manage_seat", "TOOL_MANAGE_SEAT"}, {"manage_document", "TOOL_MANAGE_DOCUMENT"},
	{"update_auto_rule", "TOOL_UPDATE_AUTO_RULE"}, {"validate_rules", "TOOL_VALIDATE_RULES"},
	{"regenerate_auto_rule", "TOOL_REGENERATE_AUTO_RULE"}, {"validate_tasks_json", "TOOL_VALIDATE_TASKS_JSON"},
	{"create_context_file", "TOOL_CREATE_CONTEXT_FILE"}, {"manage_context", "TOOL_MANAGE_CONTEXT"},
}

// NewToolConfig loads the configuration from the process environment.
func NewToolConfig(overrides obj) (*ToolConfig, error) {
	return NewToolConfigWithEnv(os.LookupEnv, overrides)
}

// NewToolConfigWithEnv loads the configuration through getenv.
// Merging an enabled_tools override into a non-dict enabled_tools (set by a legacy file) is
// an error, like the AttributeError Python raises from the constructor.
func NewToolConfigWithEnv(getenv func(string) (string, bool), overrides obj) (*ToolConfig, error) {
	t := &ToolConfig{getenv: getenv}
	config, err := t.loadConfig(overrides)
	if err != nil {
		return nil, err
	}
	t.Config = config
	return t, nil
}

func (t *ToolConfig) boolEnv(key string, def bool) bool {
	v, ok := t.getenv(key)
	if !ok {
		return def
	}
	switch tmvo.PyLower(v) {
	case "true", "1", "yes", "on":
		return true
	}
	return false
}

func (t *ToolConfig) loadConfig(overrides obj) (obj, error) {
	enabled := entities.NewOrderedMap[any]()
	for _, d := range toolEnvDefaults {
		enabled.Set(d.tool, t.boolEnv(d.env, true))
	}
	config := entities.NewOrderedMap[any]()
	config.Set("enabled_tools", enabled)
	config.Set("debug_mode", t.boolEnv("TOOL_DEBUG_MODE", false))
	config.Set("tool_logging", t.boolEnv("TOOL_LOGGING", false))
	config.Set("enable_workflow_guidance", t.boolEnv("ENABLE_WORKFLOW_GUIDANCE", false))

	// Legacy MCP_TOOL_CONFIG JSON file. Any failure is swallowed (Python logs a warning)
	// and what was merged before the failure stays.
	if path, ok := t.getenv("MCP_TOOL_CONFIG"); ok && path != "" {
		if _, err := os.Stat(path); err == nil {
			t.mergeLegacyFile(path, config)
		}
	}

	for _, key := range keysOf(overrides) {
		value, _ := overrides.Get(key)
		if enabledOver, isMap := value.(obj); key == "enabled_tools" && isMap {
			cur, _ := config.Get("enabled_tools")
			m, ok := cur.(obj)
			if !ok {
				return nil, fmt.Errorf("'%s' object has no attribute 'update'", pyClass(cur))
			}
			for _, k := range enabledOver.Keys() {
				v, _ := enabledOver.Get(k)
				m.Set(k, v)
			}
		} else {
			config.Set(key, value)
		}
	}
	return config, nil
}

func keysOf(o obj) []string {
	if o == nil {
		return nil
	}
	return o.Keys()
}

func (t *ToolConfig) mergeLegacyFile(path string, config obj) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return
	}
	jsonConfig, ok := decoded.(obj)
	if !ok {
		return // .items() on a non-dict raises AttributeError, swallowed
	}
	for _, key := range jsonConfig.Keys() {
		value, _ := jsonConfig.Get(key)
		if tools, isMap := value.(obj); key == "enabled_tools" && isMap {
			cur, _ := config.Get("enabled_tools")
			curMap, ok := cur.(obj)
			for _, name := range tools.Keys() {
				if _, set := t.getenv("TOOL_" + strings.ToUpper(name)); set {
					continue
				}
				v, _ := tools.Get(name)
				if !ok {
					return // config["enabled_tools"] was replaced by a non-dict: item assignment fails
				}
				curMap.Set(name, v)
			}
		} else if (key != "debug_mode" && key != "tool_logging") || !t.envHas("TOOL_"+strings.ToUpper(key)) {
			config.Set(key, value)
		}
	}
}

func (t *ToolConfig) envHas(key string) bool { _, ok := t.getenv(key); return ok }

// enabledTools returns the enabled_tools dict; Python raises AttributeError when a
// legacy file or an override replaced it with another type.
func (t *ToolConfig) enabledTools() (obj, error) {
	v, ok := t.Config.Get("enabled_tools")
	if !ok {
		return entities.NewOrderedMap[any](), nil
	}
	m, isMap := v.(obj)
	if !isMap {
		return nil, fmt.Errorf("'%s' object has no attribute 'get'", pyClass(v))
	}
	return m, nil
}

func pyClass(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case string:
		return "str"
	case bool:
		return "bool"
	case []any:
		return "list"
	case float64:
		return "float"
	case int, int64:
		return "int"
	}
	return "object"
}

// IsEnabledValue is is_enabled as Python returns it: the stored value (default true),
// which is not always a bool when it came from a legacy file or an override.
func (t *ToolConfig) IsEnabledValue(toolName string) (any, error) {
	m, err := t.enabledTools()
	if err != nil {
		return nil, err
	}
	if v, ok := m.Get(toolName); ok {
		return v, nil
	}
	return true, nil
}

// IsEnabled reports whether a tool is enabled by Python truthiness of IsEnabledValue.
func (t *ToolConfig) IsEnabled(toolName string) (bool, error) {
	v, err := t.IsEnabledValue(toolName)
	return tmvo.PyTruthy(v), err
}

// GetEnabledTools returns the enabled_tools value as stored (a dictionary unless a legacy
// file or an override replaced it).
func (t *ToolConfig) GetEnabledTools() any {
	v, ok := t.Config.Get("enabled_tools")
	if !ok {
		return entities.NewOrderedMap[any]()
	}
	return v
}

// IsWorkflowGuidanceEnabled reports whether workflow guidance is included in responses.
func (t *ToolConfig) IsWorkflowGuidanceEnabled() bool {
	v, ok := t.Config.Get("enable_workflow_guidance")
	return ok && tmvo.PyTruthy(v)
}
