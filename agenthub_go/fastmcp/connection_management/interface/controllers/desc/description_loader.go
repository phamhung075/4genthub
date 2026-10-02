// Package desc ports connection_management/interface/controllers/desc/description_loader.py.
package desc

import (
	"agenthub/fastmcp/connection_management/interface/controllers/desc/connection"
)

// ConnectionDescriptionLoader utility for loading connection management tool descriptions.
type ConnectionDescriptionLoader struct {
	basePath string
}

// NewConnectionDescriptionLoader creates a new loader.
func NewConnectionDescriptionLoader(basePath ...string) *ConnectionDescriptionLoader {
	bp := ""
	if len(basePath) > 0 {
		bp = basePath[0]
	}
	return &ConnectionDescriptionLoader{basePath: bp}
}

// GetConnectionManagementDescriptions returns connection management tool descriptions.
func (l *ConnectionDescriptionLoader) GetConnectionManagementDescriptions() map[string]any {
	return map[string]any{
		"manage_connection": map[string]any{
			"description": connection.ManageConnectionDescription,
			"parameters":  connection.ManageConnectionParameters,
		},
	}
}

// GetAllDescriptions recursively loads all descriptions from base path.
func (l *ConnectionDescriptionLoader) GetAllDescriptions() map[string]any {
	return map[string]any{
		"connection": l.GetConnectionManagementDescriptions(),
	}
}

// ConnectionDescriptionLoaderInstance is the global instance for easy access.
var ConnectionDescriptionLoaderInstance = NewConnectionDescriptionLoader()
