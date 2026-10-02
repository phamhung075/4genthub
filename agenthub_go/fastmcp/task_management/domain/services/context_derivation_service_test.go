package services

import (
	"context"
	"testing"
)

func TestContextDerivationDefaults(t *testing.T) {
	s := NewContextDerivationService(nil, nil)
	c := s.DeriveContextFromTask(context.Background(), "x", "")
	if c["project_id"] != "default_project" || c["git_branch_name"] != "main" || c["user_id"] != "system" {
		t.Fatal(c)
	}
	h := s.DeriveContextHierarchy(context.Background(), "t", "b", "", "u")
	if h["global"].(map[string]any)["user_id"] != "u" || h["project"].(map[string]any)["project_id"] != "default_project" {
		t.Fatalf("%v", h)
	}
	if s.DetermineContextLevel("", "b", "p") != "branch" || s.DetermineContextLevel("", "", "") != "global" {
		t.Fatal("level")
	}
}
