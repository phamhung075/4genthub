package services

import (
	"context"
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// BranchLister is the consumer-side interface for the method the validator calls:
// Python's GitBranchNameValidator uses GitBranchRepository.find_all_by_project,
// which the ABC does not declare (duck-typed), so it is declared here.
type BranchLister interface {
	FindAllByProject(ctx context.Context, projectID string) ([]*entities.GitBranch, error)
}

// GitBranchNameValidator validates git branch names (format and uniqueness).
type GitBranchNameValidator struct {
	gitBranchRepository BranchLister
}

// NewGitBranchNameValidator builds the validator around a branch repository.
func NewGitBranchNameValidator(repo BranchLister) *GitBranchNameValidator {
	return &GitBranchNameValidator{gitBranchRepository: repo}
}

// ValidateUniqueName checks that name is unique within the project. As in
// ProjectNameValidator, `branch.id == exclude_branch_id` compares a GitBranchId to
// a str in Python and is never true, so excludeBranchID never skips a match.
func (v *GitBranchNameValidator) ValidateUniqueName(ctx context.Context, name, projectID string, excludeBranchID *string) error {
	if value_objects.PyStrip(name) == "" {
		return validation("Branch name cannot be empty")
	}
	if value_objects.PyStrip(projectID) == "" {
		return validation("Project ID is required for validation")
	}
	name = value_objects.PyStrip(name)
	if n := utf8.RuneCountInString(name); n < 1 {
		return validation("Branch name must be at least 1 character long")
	} else if n > 100 {
		return validation("Branch name cannot exceed 100 characters")
	}
	branches, err := v.gitBranchRepository.FindAllByProject(ctx, projectID)
	if err != nil {
		return err
	}
	for _, b := range branches {
		if b.Name == name {
			return validation("A branch with the name '" + name + "' already exists in this project. Please choose a different name.")
		}
	}
	return nil
}

var branchForbiddenChars = []string{" ", "~", "^", ":", "\\", "*", "?", "[", "@{"}

// ValidateNameFormat applies the simplified git ref-name rules.
func (v *GitBranchNameValidator) ValidateNameFormat(name string) error {
	if value_objects.PyStrip(name) == "" {
		return validation("Branch name cannot be empty")
	}
	name = value_objects.PyStrip(name)
	if n := utf8.RuneCountInString(name); n < 1 {
		return validation("Branch name must be at least 1 character long")
	} else if n > 100 {
		return validation("Branch name cannot exceed 100 characters")
	}
	for _, c := range branchForbiddenChars {
		if strings.Contains(name, c) {
			if c == " " {
				return validation("Branch name cannot contain spaces. Use hyphens or underscores instead.")
			}
			return validation("Branch name cannot contain the character '" + c + "'")
		}
	}
	if strings.HasPrefix(name, "/") || strings.HasPrefix(name, ".") || strings.HasPrefix(name, "-") {
		return validation("Branch name cannot start with '/', '.', or '-'")
	}
	if strings.HasSuffix(name, "/") || strings.HasSuffix(name, ".") {
		return validation("Branch name cannot end with '/' or '.'")
	}
	if strings.Contains(name, "..") {
		return validation("Branch name cannot contain consecutive dots (..)")
	}
	// Python's final "cannot start or end with '/'" check is unreachable: both cases
	// are rejected above.
	return nil
}

// ValidateBranchName runs format then uniqueness validation.
func (v *GitBranchNameValidator) ValidateBranchName(ctx context.Context, name, projectID string, excludeBranchID *string) error {
	if err := v.ValidateNameFormat(name); err != nil {
		return err
	}
	return v.ValidateUniqueName(ctx, name, projectID, excludeBranchID)
}
