// Package extractors ports
// task_management/interface/mcp_controllers/auth_helper/extractors/mcp_context_extractor.py.
package extractors

import "context"

type mcpAuthContextKey struct{}

// WithMCPUserID sets the MCP user ID in the context.
func WithMCPUserID(ctx context.Context, userID string) context.Context {
	return context.WithValue(ctx, mcpAuthContextKey{}, userID)
}

// MCPContextExtractor extracts user ID from MCP authentication context.
type MCPContextExtractor struct{}

// ExtractUserID extracts user ID from MCP context if available.
func (MCPContextExtractor) ExtractUserID(ctx context.Context) *string {
	if ctx == nil {
		return nil
	}
	if v, ok := ctx.Value(mcpAuthContextKey{}).(string); ok && v != "" {
		return &v
	}
	return nil
}
