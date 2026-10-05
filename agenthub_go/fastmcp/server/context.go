// Package server ports fastmcp/server/context.py.
package server

import (
	"context"
	"log"
)

type mcpContextKey struct{}

// Context provides access to MCP request capabilities and metadata.
type Context struct {
	RequestID string
	ClientID  string
	SessionID string
}

// NewContext creates a new Context instance.
func NewContext(requestID, clientID string, sessionID ...string) *Context {
	sid := ""
	if len(sessionID) > 0 {
		sid = sessionID[0]
	}
	return &Context{
		RequestID: requestID,
		ClientID:  clientID,
		SessionID: sid,
	}
}

// WithContext attaches Context to a Go context.Context.
func WithContext(ctx context.Context, mcpCtx *Context) context.Context {
	return context.WithValue(ctx, mcpContextKey{}, mcpCtx)
}

// GetContext retrieves Context from context.Context if present.
func GetContext(ctx context.Context) *Context {
	if ctx == nil {
		return nil
	}
	c, _ := ctx.Value(mcpContextKey{}).(*Context)
	return c
}

// Info logs an informational message.
func (c *Context) Info(message string) {
	log.Printf("[MCP INFO] %s: %s", c.RequestID, message)
}

// Debug logs a debug message.
func (c *Context) Debug(message string) {
	log.Printf("[MCP DEBUG] %s: %s", c.RequestID, message)
}

// Warning logs a warning message.
func (c *Context) Warning(message string) {
	log.Printf("[MCP WARNING] %s: %s", c.RequestID, message)
}

// Error logs an error message.
func (c *Context) Error(message string) {
	log.Printf("[MCP ERROR] %s: %s", c.RequestID, message)
}

// ReportProgress reports progress for the operation.
func (c *Context) ReportProgress(progress, total float64, message string) {
	// Progress notification hook
}
