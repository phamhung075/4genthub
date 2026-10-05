// Package context_id_detector ports
// task_management/interface/mcp_controllers/context_id_detector/context_id_detector.py.
package context_id_detector

import (
	"context"

	"agenthub/fastmcp/task_management/application/services"
)

// ContextIDDetector detects the type of a given ID via the application layer.
type ContextIDDetector struct {
	service *services.ContextDetectionService
}

// NewContextIDDetector mirrors ContextIDDetector(). Python builds
// ContextDetectionService() with no arguments; the Go service requires the three
// domain repositories, so they are injected here.
func NewContextIDDetector(service *services.ContextDetectionService) *ContextIDDetector {
	return &ContextIDDetector{service: service}
}

// DetectIDType mirrors detect_id_type, returning (id_type, project_id).
func (d *ContextIDDetector) DetectIDType(ctx context.Context, contextID string) (string, *string) {
	return d.service.DetectIDType(ctx, contextID)
}

// GetContextLevelForID mirrors get_context_level_for_id.
func (d *ContextIDDetector) GetContextLevelForID(ctx context.Context, contextID string) string {
	return d.service.GetContextLevelForID(ctx, contextID)
}
