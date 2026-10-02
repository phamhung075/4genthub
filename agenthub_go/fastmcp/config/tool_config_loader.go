package config

import (
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ToolConfigError is raised when there are issues with tool configuration.
type ToolConfigError struct{ Msg string }

func (e *ToolConfigError) Error() string { return e.Msg }

// ToolConfigLoader loads and manages tool configuration from YAML files.
type ToolConfigLoader struct {
	ConfigPath string
	// ConfigData is the loaded configuration; Python keeps whatever YAML produced (a dict
	// normally, but any value after a failed validation). It starts as an empty dict.
	ConfigData  any
	Environment string
	Getenv      func(string) (string, bool)
}

// NewToolConfigLoader builds a loader. An empty configPath uses the default path, and a nil
// getenv reads the process environment.
func NewToolConfigLoader(configPath string, getenv func(string) (string, bool)) *ToolConfigLoader {
	if getenv == nil {
		getenv = os.LookupEnv
	}
	l := &ToolConfigLoader{Getenv: getenv, ConfigData: entities.NewOrderedMap[any]()}
	if configPath != "" {
		l.ConfigPath = configPath
	} else {
		l.ConfigPath = defaultToolConfigPath()
	}
	l.Environment = l.detectEnvironment()
	return l
}

// defaultToolConfigPath mirrors `Path(__file__).parent.parent.parent / "config" /
// "tool_config.yaml"`: Python locates the file relative to the module, so the Go port uses
// the compiled source location (runtime.Caller).
func defaultToolConfigPath() string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return filepath.Join("config", "tool_config.yaml")
	}
	moduleDir := filepath.Dir(filepath.Dir(filepath.Dir(file)))
	return filepath.Join(moduleDir, "config", "tool_config.yaml")
}

func (l *ToolConfigLoader) detectEnvironment() string {
	env, ok := l.Getenv("ENVIRONMENT")
	if !ok {
		env = "development"
	}
	lower := tmvo.PyLower(env)
	for _, indicator := range []string{"prod", "production", "live"} {
		if strings.Contains(lower, indicator) {
			return "production"
		}
	}
	return "development"
}

// LoadConfig loads the tool configuration from the YAML file. A missing file returns the
// default configuration *without* storing it (Python never assigns it to self.config_data).
func (l *ToolConfigLoader) LoadConfig() (*entities.OrderedMap[any], error) {
	if _, err := os.Stat(l.ConfigPath); err != nil {
		return l.defaultConfig(), nil
	}
	raw, err := os.ReadFile(l.ConfigPath)
	if err != nil {
		return nil, &ToolConfigError{Msg: fmt.Sprintf("Failed to load config file: %s", err)}
	}
	parsed, err := entities.LoadYAML(raw)
	if err != nil {
		return nil, &ToolConfigError{Msg: fmt.Sprintf("Invalid YAML in config file: %s", err)}
	}
	l.ConfigData = parsed
	if err := l.validateConfig(); err != nil {
		return nil, &ToolConfigError{Msg: fmt.Sprintf("Failed to load config file: %s", err)}
	}
	if err := l.applyEnvironmentOverrides(); err != nil {
		return nil, &ToolConfigError{Msg: fmt.Sprintf("Failed to load config file: %s", err)}
	}
	root, ok := l.ConfigData.(*entities.OrderedMap[any])
	if !ok {
		return nil, &ToolConfigError{Msg: "Failed to load config file: Configuration must be a dictionary"}
	}
	return root, nil
}

func (l *ToolConfigLoader) defaultConfig() *entities.OrderedMap[any] {
	authTools := entities.NewOrderedMap[any]()
	for _, name := range []string{"validate_token", "get_rate_limit_status", "revoke_token", "get_auth_status"} {
		cfg := entities.NewOrderedMap[any]()
		cfg.Set("enabled", true)
		authTools.Set(name, cfg)
	}
	genToken := entities.NewOrderedMap[any]()
	genToken.Set("enabled", false)
	authTools.Set("generate_token", genToken)

	auth := entities.NewOrderedMap[any]()
	auth.Set("enabled", true)
	auth.Set("tools", authTools)

	connTools := entities.NewOrderedMap[any]()
	manageConn := entities.NewOrderedMap[any]()
	manageConn.Set("enabled", true)
	connTools.Set("manage_connection", manageConn)

	conn := entities.NewOrderedMap[any]()
	conn.Set("enabled", true)
	conn.Set("tools", connTools)

	tools := entities.NewOrderedMap[any]()
	tools.Set("authentication", auth)
	tools.Set("connection", conn)

	global := entities.NewOrderedMap[any]()
	global.Set("respect_auth_env", true)
	global.Set("auth_env_override", true)
	global.Set("log_tool_registration", true)

	cfg := entities.NewOrderedMap[any]()
	cfg.Set("version", "1.0.0")
	cfg.Set("tools", tools)
	cfg.Set("global", global)
	return cfg
}

func (l *ToolConfigLoader) validateConfig() error {
	if _, ok := l.ConfigData.(*entities.OrderedMap[any]); !ok {
		return fmt.Errorf("Configuration must be a dictionary")
	}
	version := any("1.0.0")
	if v, err := cfgDictGet(l.ConfigData, "version", "1.0.0"); err != nil {
		return err
	} else {
		version = v
	}
	if err := l.checkVersionCompatible(version); err != nil {
		return err
	}
	tools, err := cfgDictGet(l.ConfigData, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return err
	}
	tm, ok := tools.(*entities.OrderedMap[any])
	if !ok {
		return fmt.Errorf("'tools' section must be a dictionary")
	}
	for _, groupName := range tm.Keys() {
		groupConfig, _ := tm.Get(groupName)
		if err := validateToolGroup(groupName, groupConfig); err != nil {
			return err
		}
	}
	return nil
}

func (l *ToolConfigLoader) checkVersionCompatible(version any) error {
	s, ok := version.(string)
	if !ok {
		return fmt.Errorf("'%s' object has no attribute 'startswith'", tcTypeName(version))
	}
	if !strings.HasPrefix(s, "1.") {
		return &ToolConfigError{Msg: fmt.Sprintf("Unsupported configuration version: %s", s)}
	}
	return nil
}

func validateToolGroup(groupName string, groupConfig any) error {
	gc, ok := groupConfig.(*entities.OrderedMap[any])
	if !ok {
		return &ToolConfigError{Msg: fmt.Sprintf("Tool group '%s' must be a dictionary", groupName)}
	}
	if v, ok := gc.Get("tools"); ok {
		if _, isMap := v.(*entities.OrderedMap[any]); !isMap {
			return &ToolConfigError{Msg: fmt.Sprintf("Tools in group '%s' must be a dictionary", groupName)}
		}
	}
	return nil
}

func (l *ToolConfigLoader) applyEnvironmentOverrides() error {
	overrides, err := cfgDictGet(l.ConfigData, "environment_overrides", entities.NewOrderedMap[any]())
	if err != nil {
		return err
	}
	envOverrides, err := cfgDictGet(overrides, l.Environment, entities.NewOrderedMap[any]())
	if err != nil {
		return err
	}
	if !tmvo.PyTruthy(envOverrides) {
		return nil
	}
	base, ok := l.ConfigData.(*entities.OrderedMap[any])
	if !ok {
		return fmt.Errorf("'%s' object has no attribute 'items'", tcTypeName(l.ConfigData))
	}
	om, ok := envOverrides.(*entities.OrderedMap[any])
	if !ok {
		return fmt.Errorf("'%s' object has no attribute 'items'", tcTypeName(envOverrides))
	}
	mergeConfig(base, om)
	return nil
}

// mergeConfig recursively merges override into base, like the Python method.
func mergeConfig(base, override *entities.OrderedMap[any]) {
	for _, key := range override.Keys() {
		value, _ := override.Get(key)
		if baseValue, exists := base.Get(key); exists {
			baseMap, baseIsMap := baseValue.(*entities.OrderedMap[any])
			valueMap, valueIsMap := value.(*entities.OrderedMap[any])
			if baseIsMap && valueIsMap {
				mergeConfig(baseMap, valueMap)
				continue
			}
		}
		base.Set(key, value)
	}
}

// IsToolEnabledValue is is_tool_enabled as Python returns it: the stored value (default
// true), which is not always a bool.
func (l *ToolConfigLoader) IsToolEnabledValue(groupName, toolName string) (any, error) {
	if groupName == "authentication" {
		global, err := cfgDictGet(l.ConfigData, "global", entities.NewOrderedMap[any]())
		if err != nil {
			return nil, err
		}
		respect, err := cfgDictGet(global, "respect_auth_env", true)
		if err != nil {
			return nil, err
		}
		if tmvo.PyTruthy(respect) {
			raw, ok := l.Getenv("AUTH_ENABLED")
			if !ok {
				raw = "true"
			}
			if tmvo.PyLower(raw) != "true" {
				override, err := cfgDictGet(global, "auth_env_override", true)
				if err != nil {
					return nil, err
				}
				if tmvo.PyTruthy(override) {
					return false, nil
				}
			}
		}
	}
	tools, err := cfgDictGet(l.ConfigData, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	groupConfig, err := cfgDictGet(tools, groupName, entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	groupEnabled, err := cfgDictGet(groupConfig, "enabled", true)
	if err != nil {
		return nil, err
	}
	if !tmvo.PyTruthy(groupEnabled) {
		return false, nil
	}
	toolMap, err := cfgDictGet(groupConfig, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	toolConfig, err := cfgDictGet(toolMap, toolName, entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	return cfgDictGet(toolConfig, "enabled", true)
}

// IsToolEnabled reports whether a tool is enabled by Python truthiness.
func (l *ToolConfigLoader) IsToolEnabled(groupName, toolName string) (bool, error) {
	v, err := l.IsToolEnabledValue(groupName, toolName)
	if err != nil {
		return false, err
	}
	return tmvo.PyTruthy(v), nil
}

// GetToolConfig returns the configuration for a specific tool, as stored.
func (l *ToolConfigLoader) GetToolConfig(groupName, toolName string) (any, error) {
	tools, err := cfgDictGet(l.ConfigData, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	groupConfig, err := cfgDictGet(tools, groupName, entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	toolMap, err := cfgDictGet(groupConfig, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	return cfgDictGet(toolMap, toolName, entities.NewOrderedMap[any]())
}

// GetEnabledTools returns the enabled tool names of a group in insertion order.
func (l *ToolConfigLoader) GetEnabledTools(groupName string) ([]string, error) {
	tools, err := cfgDictGet(l.ConfigData, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	groupConfig, err := cfgDictGet(tools, groupName, entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	enabled, err := cfgDictGet(groupConfig, "enabled", true)
	if err != nil {
		return nil, err
	}
	if !tmvo.PyTruthy(enabled) {
		return []string{}, nil
	}
	toolMap, err := cfgDictGet(groupConfig, "tools", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	names, err := cfgDictItemsKeys(toolMap)
	if err != nil {
		return nil, err
	}
	out := []string{}
	for _, name := range names {
		on, err := l.IsToolEnabled(groupName, name)
		if err != nil {
			return nil, err
		}
		if on {
			out = append(out, name)
		}
	}
	return out, nil
}

// ValidateDependencies checks that every declared dependency is available.
func (l *ToolConfigLoader) ValidateDependencies(groupName, toolName string, availableDependencies *entities.StringSet) (bool, error) {
	toolConfig, err := l.GetToolConfig(groupName, toolName)
	if err != nil {
		return false, err
	}
	deps, err := cfgDictGet(toolConfig, "dependencies", []any{})
	if err != nil {
		return false, err
	}
	missing := []any{}
	err = iterateAny(deps, func(dep any) {
		if s, ok := dep.(string); ok && availableDependencies != nil && availableDependencies.Has(s) {
			return
		}
		missing = append(missing, dep)
	})
	if err != nil {
		return false, err
	}
	if len(missing) > 0 {
		global, err := cfgDictGet(l.ConfigData, "global", entities.NewOrderedMap[any]())
		if err != nil {
			return false, err
		}
		failSilently, err := cfgDictGet(global, "fail_silently_on_missing_deps", true)
		if err != nil {
			return false, err
		}
		if tmvo.PyTruthy(failSilently) {
			return false, nil
		}
		return false, &ToolConfigError{Msg: fmt.Sprintf("Tool '%s' has missing dependencies: %s", toolName, tmvo.PyRepr(missing))}
	}
	return true, nil
}

// ShouldLogRegistration reports the log_tool_registration global setting as stored.
func (l *ToolConfigLoader) ShouldLogRegistration() (any, error) {
	global, err := cfgDictGet(l.ConfigData, "global", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	return cfgDictGet(global, "log_tool_registration", true)
}

// ShouldLogSkippedTools reports the mounting.log_skipped_tools setting as stored.
func (l *ToolConfigLoader) ShouldLogSkippedTools() (any, error) {
	mounting, err := cfgDictGet(l.ConfigData, "mounting", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	return cfgDictGet(mounting, "log_skipped_tools", true)
}

// GetDisabledStrategy returns the mounting.disabled_strategy setting as stored.
func (l *ToolConfigLoader) GetDisabledStrategy() (any, error) {
	mounting, err := cfgDictGet(l.ConfigData, "mounting", entities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	return cfgDictGet(mounting, "disabled_strategy", "skip")
}

// cfgDictGet is Python's dict.get(key, default): a non-dict receiver is the AttributeError
// Python would raise for `.get`.
func cfgDictGet(v any, key string, def any) (any, error) {
	m, ok := v.(*entities.OrderedMap[any])
	if !ok {
		return nil, fmt.Errorf("'%s' object has no attribute 'get'", tcTypeName(v))
	}
	if x, ok := m.Get(key); ok {
		return x, nil
	}
	return def, nil
}

// cfgDictItemsKeys is the key sequence of dict.items(), with Python's AttributeError for a
// non-dict.
func cfgDictItemsKeys(v any) ([]string, error) {
	m, ok := v.(*entities.OrderedMap[any])
	if !ok {
		return nil, fmt.Errorf("'%s' object has no attribute 'items'", tcTypeName(v))
	}
	return m.Keys(), nil
}

// iterateAny iterates the values Python would iterate over a dependencies value.
func iterateAny(v any, fn func(any)) error {
	switch x := v.(type) {
	case []any:
		for _, e := range x {
			fn(e)
		}
		return nil
	case []string:
		for _, e := range x {
			fn(e)
		}
		return nil
	case string:
		for _, r := range x {
			fn(string(r))
		}
		return nil
	case *entities.OrderedMap[any]:
		for _, k := range x.Keys() {
			fn(k)
		}
		return nil
	}
	return fmt.Errorf("'%s' object is not iterable", tcTypeName(v))
}

// tcTypeName is the Python type name used in AttributeError / TypeError text.
func tcTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case string:
		return "str"
	case bool:
		return "bool"
	case []any, []string:
		return "list"
	case float64:
		return "float"
	case int, int64, *big.Int:
		return "int"
	case *entities.OrderedMap[any]:
		return "dict"
	}
	return "object"
}
