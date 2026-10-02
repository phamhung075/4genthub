// Package tools ports fastmcp/tools/tool.py.
package tools

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// BaseTool implements the Tool interface with standard MCP metadata.
type BaseTool struct {
	Name        string
	Description string
	Parameters  map[string]any
	Tags        []string
	Enabled     bool
	Annotations map[string]any
	Handler     func(ctx context.Context, args *entities.OrderedMap[any]) ([]any, error)
}

// Key returns the tool's name/key.
func (t *BaseTool) Key() string {
	return t.Name
}

// WithKey returns a copy of the tool with a new key/name.
func (t *BaseTool) WithKey(key string) Tool {
	cpy := *t
	cpy.Name = key
	return &cpy
}

// Run executes the tool's handler.
func (t *BaseTool) Run(ctx context.Context, arguments *entities.OrderedMap[any]) ([]any, error) {
	if t.Handler != nil {
		return t.Handler(ctx, arguments)
	}
	return []any{}, nil
}

// ToMCPTool returns the tool's MCP representation dict.
func (t *BaseTool) ToMCPTool(overrides ...map[string]any) map[string]any {
	params := t.Parameters
	if params == nil {
		params = map[string]any{
			"type":       "object",
			"properties": map[string]any{},
		}
	}
	m := map[string]any{
		"name":        t.Name,
		"description": t.Description,
		"inputSchema": params,
	}
	if t.Annotations != nil {
		m["annotations"] = t.Annotations
	}
	for _, override := range overrides {
		for k, v := range override {
			m[k] = v
		}
	}
	return m
}

// FunctionTool wraps a callable as an MCP tool.
type FunctionTool struct {
	BaseTool
}

// NewTool creates a new BaseTool with default settings.
func NewTool(name, description string, handler func(ctx context.Context, args *entities.OrderedMap[any]) ([]any, error)) *BaseTool {
	return &BaseTool{
		Name:        name,
		Description: description,
		Parameters: map[string]any{
			"type":       "object",
			"properties": map[string]any{},
		},
		Enabled: true,
		Handler: handler,
	}
}

// FromFunction creates a FunctionTool from a name, description and handler function.
func FromFunction(name, description string, fn func(ctx context.Context, args *entities.OrderedMap[any]) ([]any, error)) *FunctionTool {
	return &FunctionTool{
		BaseTool: *NewTool(name, description, fn),
	}
}
