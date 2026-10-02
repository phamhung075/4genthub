package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeBranches []*entities.GitBranch

func (f fakeBranches) FindAllByProject(context.Context, string) ([]*entities.GitBranch, error) {
	return f, nil
}

func TestBranchFormat(t *testing.T) {
	v := NewGitBranchNameValidator(nil)
	cases := map[string]string{
		"":           "Branch name cannot be empty",
		"a b":        "Branch name cannot contain spaces. Use hyphens or underscores instead.",
		"a@{b":       "Branch name cannot contain the character '@{'",
		"-x":         "Branch name cannot start with '/', '.', or '-'",
		"x.":         "Branch name cannot end with '/' or '.'",
		"a..b":       "Branch name cannot contain consecutive dots (..)",
		"\x1c":       "Branch name cannot be empty",
		"ok/1.0.0-r": "",
	}
	for in, want := range cases {
		err := v.ValidateNameFormat(in)
		if (want == "") != (err == nil) || (err != nil && err.Error() != want) {
			t.Errorf("%q: got %v want %q", in, err, want)
		}
	}
	if err := v.ValidateNameFormat(strings.Repeat("a", 101)); err == nil || err.Error() != "Branch name cannot exceed 100 characters" {
		t.Error(err)
	}
}

func TestBranchUnique(t *testing.T) {
	v := NewGitBranchNameValidator(fakeBranches{{Name: "main"}})
	if err := v.ValidateUniqueName(context.Background(), " main ", "p", nil); err == nil ||
		err.Error() != "A branch with the name 'main' already exists in this project. Please choose a different name." {
		t.Error(err)
	}
	if err := v.ValidateUniqueName(context.Background(), "dev", "p", nil); err != nil {
		t.Error(err)
	}
}

func TestProjectFormat(t *testing.T) {
	v := NewProjectNameValidator(nil)
	if err := v.ValidateNameFormat("a/b"); err == nil || err.Error() != "Project name cannot contain the character '/'" {
		t.Error(err)
	}
	if err := v.ValidateNameFormat("fine name"); err != nil {
		t.Error(err)
	}
}
