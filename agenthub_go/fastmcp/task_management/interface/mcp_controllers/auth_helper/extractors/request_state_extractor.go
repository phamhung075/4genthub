// Package extractors ports
// task_management/interface/mcp_controllers/auth_helper/extractors/request_state_extractor.py.
package extractors

import (
	"context"

	"agenthub/fastmcp/auth/middleware"
)

// RequestStateExtractor extracts user ID from request state / context.
type RequestStateExtractor struct{}

// ExtractUserID extracts user ID from the request context.
func (RequestStateExtractor) ExtractUserID(ctx context.Context) *string {
	if ctx == nil {
		return nil
	}
	return middleware.GetCurrentUserID(ctx)
}
