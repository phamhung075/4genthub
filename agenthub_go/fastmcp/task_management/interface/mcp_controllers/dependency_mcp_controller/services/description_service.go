// Package services ports
// task_management/interface/mcp_controllers/dependency_mcp_controller/services.
package services

import "agenthub/fastmcp/task_management/domain/entities"

// AllDescriptionsLoader is the minimal surface of the Python
// interface/utils/description_loader.DescriptionLoader.get_all_descriptions(),
// ported in interface/utils/description_loader.go. Callers wire it; when nil the
// result is empty.
var AllDescriptionsLoader func() map[string]any

// DescriptionService manages dependency descriptions.
type DescriptionService struct{}

// NewDescriptionService mirrors DescriptionService().
func NewDescriptionService() *DescriptionService { return &DescriptionService{} }

// GetDependencyManagementDescriptions mirrors get_dependency_management_descriptions:
// it flattens the `manage_dependency` entry found in any sub-dict, preserving
// Python insertion order for the outer result.
func (s *DescriptionService) GetDependencyManagementDescriptions() *entities.OrderedMap[any] {
	flat := entities.NewOrderedMap[any]()
	if AllDescriptionsLoader == nil {
		return flat
	}
	for _, sub := range AllDescriptionsLoader() {
		subMap, ok := sub.(map[string]any)
		if !ok {
			continue
		}
		if value, ok := subMap["manage_dependency"]; ok {
			flat.Set("manage_dependency", value)
		}
	}
	return flat
}
