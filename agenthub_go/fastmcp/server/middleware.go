// Package server ports fastmcp/server/middleware.py.
package server

import (
	"context"
	"time"

	"agenthub/fastmcp/tools"
)

// CallToolResult holds the result of a tool execution.
type CallToolResult struct {
	Content []any `json:"content"`
	IsError bool  `json:"isError"`
}

// ListToolsResult holds the tools list result.
type ListToolsResult struct {
	Tools map[string]tools.Tool `json:"tools"`
}

// MiddlewareContext wraps message and invocation metadata.
type MiddlewareContext struct {
	Source    string
	Type      string
	Method    string
	Timestamp time.Time
}

// Middleware intercepts server operations.
type Middleware interface {
	Process(ctx context.Context, mctx *MiddlewareContext, next func(ctx context.Context) (any, error)) (any, error)
}
