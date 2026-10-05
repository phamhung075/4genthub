package config

import (
	"errors"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ToolServer is the FastMCP server surface ToolRegistry mounts tools to. The Python
// decorator call `server.tool(description=description)(tool_func)` becomes
// Tool(description)(toolFunc).
type ToolServer interface {
	Tool(description string) func(toolFunc any) any
}

// ToolRegistry manages conditional tool mounting.
type ToolRegistry struct {
	ConfigLoader          *ToolConfigLoader
	RegisteredTools       *entities.OrderedMap[*entities.OrderedMap[any]]
	AvailableDependencies *entities.StringSet
}

// NewToolRegistry builds a registry; a nil configLoader creates a default one.
func NewToolRegistry(configLoader *ToolConfigLoader) *ToolRegistry {
	if configLoader == nil {
		configLoader = NewToolConfigLoader("", nil)
	}
	return &ToolRegistry{
		ConfigLoader:          configLoader,
		RegisteredTools:       entities.NewOrderedMap[*entities.OrderedMap[any]](),
		AvailableDependencies: &entities.StringSet{},
	}
}

// LoadConfiguration loads the tool configuration, swallowing ToolConfigError like Python
// (it is logged and the caller continues).
func (r *ToolRegistry) LoadConfiguration() error {
	_, err := r.ConfigLoader.LoadConfig()
	if err != nil {
		var tce *ToolConfigError
		if errors.As(err, &tce) {
			return nil
		}
		return err
	}
	return nil
}

// RegisterToolGroup registers a group of tools.
func (r *ToolRegistry) RegisterToolGroup(groupName string, tools *entities.OrderedMap[any]) {
	r.RegisteredTools.Set(groupName, tools)
}

// AddDependency records an available dependency.
func (r *ToolRegistry) AddDependency(dependencyName string) {
	r.AvailableDependencies.Add(dependencyName)
}

// MountToolsToServer mounts enabled tools and returns the mounting statistics.
func (r *ToolRegistry) MountToolsToServer(server ToolServer) (*entities.OrderedMap[any], error) {
	stats := entities.NewOrderedMap[any]()
	stats.Set("total_groups", 0)
	stats.Set("total_tools", 0)
	stats.Set("mounted_tools", 0)
	stats.Set("skipped_tools", 0)
	stats.Set("disabled_tools", 0)
	stats.Set("dependency_failures", 0)
	stats.Set("results", entities.NewOrderedMap[any]())

	shouldLogVal, err := r.ConfigLoader.ShouldLogRegistration()
	if err != nil {
		return nil, err
	}
	shouldLog := tmvo.PyTruthy(shouldLogVal)
	shouldLogSkippedVal, err := r.ConfigLoader.ShouldLogSkippedTools()
	if err != nil {
		return nil, err
	}
	shouldLogSkipped := tmvo.PyTruthy(shouldLogSkippedVal)

	resultsVal, _ := stats.Get("results")
	results := resultsVal.(*entities.OrderedMap[any])

	for _, groupName := range r.RegisteredTools.Keys() {
		tools, _ := r.RegisteredTools.Get(groupName)
		stats.Set("total_groups", statInt(stats, "total_groups")+1)

		groupResults := entities.NewOrderedMap[any]()
		groupResults.Set("enabled", []string{})
		groupResults.Set("disabled", []string{})
		groupResults.Set("skipped", []string{})
		groupResults.Set("dependency_failures", []string{})

		for _, toolName := range tools.Keys() {
			toolFunc, _ := tools.Get(toolName)
			stats.Set("total_tools", statInt(stats, "total_tools")+1)

			enabledVal, err := r.ConfigLoader.IsToolEnabledValue(groupName, toolName)
			if err != nil {
				appendResult(groupResults, "skipped", toolName)
				stats.Set("skipped_tools", statInt(stats, "skipped_tools")+1)
				continue
			}
			if !tmvo.PyTruthy(enabledVal) {
				appendResult(groupResults, "disabled", toolName)
				stats.Set("disabled_tools", statInt(stats, "disabled_tools")+1)
				continue
			}
			ok, err := r.ConfigLoader.ValidateDependencies(groupName, toolName, r.AvailableDependencies)
			if err != nil {
				appendResult(groupResults, "skipped", toolName)
				stats.Set("skipped_tools", statInt(stats, "skipped_tools")+1)
				continue
			}
			if !ok {
				appendResult(groupResults, "dependency_failures", toolName)
				stats.Set("dependency_failures", statInt(stats, "dependency_failures")+1)
				continue
			}
			if err := r.mountToolToServer(server, toolName, toolFunc); err != nil {
				appendResult(groupResults, "skipped", toolName)
				stats.Set("skipped_tools", statInt(stats, "skipped_tools")+1)
				continue
			}
			appendResult(groupResults, "enabled", toolName)
			stats.Set("mounted_tools", statInt(stats, "mounted_tools")+1)
		}
		// Logging of the group summary is dropped (Python only logs it).
		_ = shouldLog
		_ = shouldLogSkipped
		results.Set(groupName, groupResults)
	}
	return stats, nil
}

func (r *ToolRegistry) mountToolToServer(server ToolServer, toolName string, toolFunc any) error {
	// Python hardcodes the "authentication" group here even for other groups.
	toolConfig, err := r.ConfigLoader.GetToolConfig("authentication", toolName)
	if err != nil {
		return err
	}
	toolMap, ok := toolConfig.(*entities.OrderedMap[any])
	if !ok {
		return fmt.Errorf("'%s' object has no attribute 'get'", tcTypeName(toolConfig))
	}
	description := "MCP tool: " + toolName
	if v, ok := toolMap.Get("description"); ok {
		description = tmvo.PyStr(v)
	}
	server.Tool(description)(toolFunc)
	return nil
}

// GetEnabledToolsSummary summarizes enabled tools per registered group.
func (r *ToolRegistry) GetEnabledToolsSummary() (*entities.OrderedMap[any], error) {
	summary := entities.NewOrderedMap[any]()
	for _, groupName := range r.RegisteredTools.Keys() {
		enabledTools, err := r.ConfigLoader.GetEnabledTools(groupName)
		if err != nil {
			return nil, err
		}
		tools, _ := r.RegisteredTools.Get(groupName)
		entry := entities.NewOrderedMap[any]()
		entry.Set("enabled_tools", enabledTools)
		entry.Set("total_tools", tools.Len())
		entry.Set("enabled_count", len(enabledTools))
		summary.Set(groupName, entry)
	}
	return summary, nil
}

// IsGroupEnabled reports whether a group has at least one enabled tool.
func (r *ToolRegistry) IsGroupEnabled(groupName string) (bool, error) {
	enabledTools, err := r.ConfigLoader.GetEnabledTools(groupName)
	if err != nil {
		return false, err
	}
	return len(enabledTools) > 0, nil
}

// GetToolInfo returns detailed information about a tool.
func (r *ToolRegistry) GetToolInfo(groupName, toolName string) (*entities.OrderedMap[any], error) {
	toolConfig, err := r.ConfigLoader.GetToolConfig(groupName, toolName)
	if err != nil {
		return nil, err
	}
	enabledVal, err := r.ConfigLoader.IsToolEnabledValue(groupName, toolName)
	if err != nil {
		return nil, err
	}
	dependencies, err := cfgDictGet(toolConfig, "dependencies", []any{})
	if err != nil {
		return nil, err
	}
	description, err := cfgDictGet(toolConfig, "description", "")
	if err != nil {
		return nil, err
	}
	deprecated, err := cfgDictGet(toolConfig, "deprecated", false)
	if err != nil {
		return nil, err
	}
	deprecationMessage, err := cfgDictGet(toolConfig, "deprecation_message", "")
	if err != nil {
		return nil, err
	}
	info := entities.NewOrderedMap[any]()
	info.Set("enabled", enabledVal)
	info.Set("config", toolConfig)
	info.Set("dependencies", dependencies)
	info.Set("description", description)
	info.Set("deprecated", deprecated)
	info.Set("deprecation_message", deprecationMessage)
	return info, nil
}

func statInt(m *entities.OrderedMap[any], key string) int {
	v, _ := m.Get(key)
	n, _ := v.(int)
	return n
}

func appendResult(m *entities.OrderedMap[any], key, toolName string) {
	v, _ := m.Get(key)
	list, _ := v.([]string)
	m.Set(key, append(list, toolName))
}
