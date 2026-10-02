// Package utils ports task_management/interface/utils/description_loader.py.
package utils

// DescriptionLoader is a utility for loading tool descriptions from separate files.
type DescriptionLoader struct {
	basePath string
}

// NewDescriptionLoader creates a new DescriptionLoader instance.
func NewDescriptionLoader(basePath ...string) *DescriptionLoader {
	bp := ""
	if len(basePath) > 0 {
		bp = basePath[0]
	}
	return &DescriptionLoader{basePath: bp}
}

// GetAllDescriptions returns tool descriptions. Python scans base_path (default:
// the utils directory itself) for *_description.py modules and executes them; the
// utils directory holds none, so the default loader returns {} and the controllers
// fall back to their own descriptions. Go cannot execute Python modules, so a
// custom base path also yields an empty result (the Go description constants live
// in the controller packages).
func (l *DescriptionLoader) GetAllDescriptions() map[string]any {
	return make(map[string]any)
}

// DescriptionLoaderInstance is the global instance for easy access.
var DescriptionLoaderInstance = NewDescriptionLoader()
