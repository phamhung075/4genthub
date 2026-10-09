package tools

// Python tools/tool_manager.py.
//
// tool.py IS ported in tools/tool.go (BaseTool/FunctionTool, with FromFunction
// standing in for the pydantic from_function). The minimal Tool surface ToolManager
// needs is declared in this file; the
// MountedServer dataclass is likewise declared minimally because
// fastmcp/server/server.go explicitly does not port it.

import (
	"context"
	"errors"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Tool is the minimal surface of tools/tool.py used by ToolManager.
type Tool interface {
	Key() string
	WithKey(key string) Tool
	Run(ctx context.Context, arguments *entities.OrderedMap[any]) ([]any, error)
}

// MountedServer is the minimal surface of server.py's MountedServer used here.
type MountedServer interface {
	Prefix() string
	// ServerListTools is server._list_tools().
	ServerListTools(ctx context.Context) ([]Tool, error)
	// ServerToolManagerListTools is server._tool_manager.list_tools().
	ServerToolManagerListTools(ctx context.Context) ([]Tool, error)
	// ServerCallTool is server._call_tool(key, arguments).
	ServerCallTool(ctx context.Context, key string, arguments *entities.OrderedMap[any]) ([]any, error)
}

// ToolManager ports ToolManager.
type ToolManager struct {
	tools             *entities.OrderedMap[Tool]
	mountedServers    []MountedServer
	MaskErrorDetails  bool
	DuplicateBehavior fastmcp.DuplicateBehavior
}

// duplicateBehaviorArgs mirrors DuplicateBehavior.__args__.
var duplicateBehaviorArgs = []string{"warn", "error", "replace", "ignore"}

// NewToolManager ports __init__. A nil duplicateBehavior is Python's None.
func NewToolManager(duplicateBehavior *fastmcp.DuplicateBehavior, maskErrorDetails *bool) (*ToolManager, error) {
	m := &ToolManager{tools: entities.NewOrderedMap[Tool]()}

	masked := fastmcp.Settings.MaskErrorDetails
	if maskErrorDetails != nil && *maskErrorDetails {
		masked = true
	}
	m.MaskErrorDetails = masked

	if duplicateBehavior == nil {
		b := fastmcp.DuplicateBehaviorWarn
		duplicateBehavior = &b
	}
	valid := false
	for _, a := range duplicateBehaviorArgs {
		if string(*duplicateBehavior) == a {
			valid = true
			break
		}
	}
	if !valid {
		return nil, &value_objects.ValueError{Msg: "Invalid duplicate_behavior: " + string(*duplicateBehavior) +
			". Must be one of: warn, error, replace, ignore"}
	}
	m.DuplicateBehavior = *duplicateBehavior
	return m, nil
}

// Mount ports mount.
func (m *ToolManager) Mount(server MountedServer) {
	m.mountedServers = append(m.mountedServers, server)
}

// loadTools ports _load_tools.
func (m *ToolManager) loadTools(ctx context.Context, viaServer bool) *entities.OrderedMap[Tool] {
	allTools := entities.NewOrderedMap[Tool]()
	for _, mounted := range m.mountedServers {
		var childResults []Tool
		var err error
		if viaServer {
			childResults, err = mounted.ServerListTools(ctx)
		} else {
			childResults, err = mounted.ServerToolManagerListTools(ctx)
		}
		if err != nil {
			// Skip failed mounts silently, matches existing behavior.
			continue
		}
		childDict := entities.NewOrderedMap[Tool]()
		for _, t := range childResults {
			childDict.Set(t.Key(), t)
		}
		if mounted.Prefix() != "" {
			for _, key := range childDict.Keys() {
				t, _ := childDict.Get(key)
				prefixed := t.WithKey(mounted.Prefix() + "_" + t.Key())
				allTools.Set(prefixed.Key(), prefixed)
			}
		} else {
			for _, key := range childDict.Keys() {
				v, _ := childDict.Get(key)
				allTools.Set(key, v)
			}
		}
	}
	for _, key := range m.tools.Keys() {
		v, _ := m.tools.Get(key)
		allTools.Set(key, v)
	}
	return allTools
}

// HasTool ports has_tool.
func (m *ToolManager) HasTool(ctx context.Context, key string) bool {
	tools := m.GetTools(ctx)
	return tools.Has(key)
}

// GetTool ports get_tool.
func (m *ToolManager) GetTool(ctx context.Context, key string) (Tool, error) {
	tools := m.GetTools(ctx)
	if t, ok := tools.Get(key); ok {
		return t, nil
	}
	return nil, &fastmcp.NotFoundError{Msg: "Tool " + value_objects.PyRepr(key) + " not found"}
}

// GetTools ports get_tools.
func (m *ToolManager) GetTools(ctx context.Context) *entities.OrderedMap[Tool] {
	return m.loadTools(ctx, false)
}

// ListTools ports list_tools.
func (m *ToolManager) ListTools(ctx context.Context) []Tool {
	toolsDict := m.loadTools(ctx, true)
	out := make([]Tool, 0, toolsDict.Len())
	for _, key := range toolsDict.Keys() {
		v, _ := toolsDict.Get(key)
		out = append(out, v)
	}
	return out
}

// AddTool ports add_tool. The Python ValueError for duplicate_behavior="error"
// is returned instead of raised.
func (m *ToolManager) AddTool(tool Tool) (Tool, error) {
	existing, ok := m.tools.Get(tool.Key())
	if ok {
		switch m.DuplicateBehavior {
		case fastmcp.DuplicateBehaviorWarn:
			m.tools.Set(tool.Key(), tool)
		case fastmcp.DuplicateBehaviorReplace:
			m.tools.Set(tool.Key(), tool)
		case fastmcp.DuplicateBehaviorError:
			return nil, &value_objects.ValueError{Msg: "Tool already exists: " + tool.Key()}
		case fastmcp.DuplicateBehaviorIgnore:
			return existing, nil
		}
	} else {
		m.tools.Set(tool.Key(), tool)
	}
	return tool, nil
}

// RemoveTool ports remove_tool.
func (m *ToolManager) RemoveTool(key string) error {
	if m.tools.Has(key) {
		m.tools.Delete(key)
		return nil
	}
	return &fastmcp.NotFoundError{Msg: "Tool " + value_objects.PyRepr(key) + " not found"}
}

// CallTool ports call_tool.
func (m *ToolManager) CallTool(ctx context.Context, key string, arguments *entities.OrderedMap[any]) ([]any, error) {
	if m.tools.Has(key) {
		tool, err := m.GetTool(ctx, key)
		if err != nil {
			return nil, err
		}
		result, err := tool.Run(ctx, arguments)
		if err == nil {
			return result, nil
		}
		var toolErr *fastmcp.ToolError
		if errors.As(err, &toolErr) {
			return nil, err
		}
		if m.MaskErrorDetails {
			return nil, &fastmcp.ToolError{FastMCPError: fastmcp.FastMCPError{Msg: "Error calling tool " + value_objects.PyRepr(key)}}
		}
		return nil, &fastmcp.ToolError{FastMCPError: fastmcp.FastMCPError{Msg: "Error calling tool " + value_objects.PyRepr(key) + ": " + err.Error()}}
	}

	for i := len(m.mountedServers) - 1; i >= 0; i-- {
		mounted := m.mountedServers[i]
		toolKey := key
		if mounted.Prefix() != "" {
			prefix := mounted.Prefix() + "_"
			if len(key) >= len(prefix) && key[:len(prefix)] == prefix {
				toolKey = key[len(prefix):]
			} else {
				continue
			}
		}
		result, err := mounted.ServerCallTool(ctx, toolKey, arguments)
		if err == nil {
			return result, nil
		}
		var nf *fastmcp.NotFoundError
		if errors.As(err, &nf) {
			continue
		}
		return nil, err
	}
	return nil, &fastmcp.NotFoundError{Msg: "Tool " + value_objects.PyRepr(key) + " not found."}
}
