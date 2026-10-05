// Package project ports task_management/application/dtos/project.
package project

// CreateProjectRequest is the request DTO for creating a project.
type CreateProjectRequest struct {
	Name        string
	Description *string
}
