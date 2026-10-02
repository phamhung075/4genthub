package services

import (
	"context"
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProjectNameValidator validates project names (format and uniqueness).
type ProjectNameValidator struct {
	projectRepository repositories.ProjectRepository
}

// NewProjectNameValidator builds the validator around a project repository.
func NewProjectNameValidator(repo repositories.ProjectRepository) *ProjectNameValidator {
	return &ProjectNameValidator{projectRepository: repo}
}

func validation(msg string) error { return exceptions.NewValidationException(msg, "", nil) }

// ValidateUniqueName checks that name is unique in the user's scope. excludeProjectID
// mirrors Python's `existing_project.id == exclude_project_id`: a ProjectId value
// object never equals a str in Python (EntityId.__eq__ returns NotImplemented for
// other types), so the exclusion can never match and is intentionally not applied.
func (v *ProjectNameValidator) ValidateUniqueName(ctx context.Context, name, userID string, excludeProjectID *string) error {
	if value_objects.PyStrip(name) == "" {
		return validation("Project name cannot be empty")
	}
	if value_objects.PyStrip(userID) == "" {
		return validation("User ID is required for validation")
	}
	name = value_objects.PyStrip(name)
	if n := utf8.RuneCountInString(name); n < 1 {
		return validation("Project name must be at least 1 character long")
	} else if n > 255 {
		return validation("Project name cannot exceed 255 characters")
	}
	existing, err := v.projectRepository.FindByName(ctx, name)
	if err != nil {
		return err
	}
	if existing != nil {
		return validation("A project with the name '" + name + "' already exists. Please choose a different name.")
	}
	return nil
}

var projectForbiddenChars = []string{"<", ">", "\"", "|", "\\", "/", ":", "*", "?"}

// ValidateNameFormat checks length and forbidden characters.
func (v *ProjectNameValidator) ValidateNameFormat(name string) error {
	if value_objects.PyStrip(name) == "" {
		return validation("Project name cannot be empty")
	}
	name = value_objects.PyStrip(name)
	if n := utf8.RuneCountInString(name); n < 1 {
		return validation("Project name must be at least 1 character long")
	} else if n > 255 {
		return validation("Project name cannot exceed 255 characters")
	}
	for _, c := range projectForbiddenChars {
		if strings.Contains(name, c) {
			return validation("Project name cannot contain the character '" + c + "'")
		}
	}
	return nil
}

// ValidateProjectName runs format then uniqueness validation.
func (v *ProjectNameValidator) ValidateProjectName(ctx context.Context, name, userID string, excludeProjectID *string) error {
	if err := v.ValidateNameFormat(name); err != nil {
		return err
	}
	return v.ValidateUniqueName(ctx, name, userID, excludeProjectID)
}
