// Package services ports
// task_management/interface/mcp_controllers/auth_helper/services/context_import_service.py.
package services

import (
	"context"

	"agenthub/fastmcp/auth/middleware"
)

// ContextImportService handles context middleware functions and availability checks.
type ContextImportService struct {
	RequestContextAvailable bool
	UserContextAvailable    bool
	StarletteAvailable      bool
}

// NewContextImportService creates a new ContextImportService instance.
func NewContextImportService() *ContextImportService {
	return &ContextImportService{
		RequestContextAvailable: true,
		UserContextAvailable:    true,
		StarletteAvailable:      true,
	}
}

// GetUserFromRequestContext returns the user ID from the request context.
func (s *ContextImportService) GetUserFromRequestContext(ctx context.Context) *string {
	return middleware.GetCurrentUserID(ctx)
}

// GetCurrentUserEmail returns the email from the request context.
func (s *ContextImportService) GetCurrentUserEmail(ctx context.Context) *string {
	return middleware.GetCurrentUserEmail(ctx)
}

// GetCurrentAuthMethod returns the auth method from the request context.
func (s *ContextImportService) GetCurrentAuthMethod(ctx context.Context) *string {
	return middleware.GetCurrentAuthMethod(ctx)
}

// IsRequestAuthenticated returns whether the request context is authenticated.
func (s *ContextImportService) IsRequestAuthenticated(ctx context.Context) bool {
	return middleware.IsRequestAuthenticated(ctx)
}

// GetAuthenticationContext returns full auth context map.
func (s *ContextImportService) GetAuthenticationContext(ctx context.Context) map[string]any {
	return middleware.GetAuthenticationContext(ctx)
}

// GetCurrentUserID returns current user ID.
func (s *ContextImportService) GetCurrentUserID(ctx context.Context) *string {
	return middleware.GetCurrentUserID(ctx)
}
