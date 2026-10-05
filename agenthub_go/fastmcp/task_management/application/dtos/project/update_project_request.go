package project

// UpdateProjectRequest is the request DTO for updating a project.
type UpdateProjectRequest struct {
	ProjectID   string
	Name        *string
	Description *string
}
