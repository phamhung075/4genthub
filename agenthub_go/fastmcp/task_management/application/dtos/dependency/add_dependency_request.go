// Package dependency ports task_management/application/dtos/dependency.
package dependency

// AddDependencyRequest is the request DTO for adding a dependency between tasks.
type AddDependencyRequest struct {
	TaskID          any
	DependsOnTaskID any
	DependencyType  string
}

// NewAddDependencyRequest applies the Python default dependency_type="blocks".
func NewAddDependencyRequest(taskID, dependsOnTaskID any, dependencyType *string) *AddDependencyRequest {
	dt := "blocks"
	if dependencyType != nil {
		dt = *dependencyType
	}
	return &AddDependencyRequest{TaskID: taskID, DependsOnTaskID: dependsOnTaskID, DependencyType: dt}
}
