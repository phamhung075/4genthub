package entities

import (
	"strings"
	"testing"
)

func TestNestedCategorySchema(t *testing.T) {
	s := NestedCategorySchema{}
	paths := s.GetAllPaths()
	if len(paths) != 20 || paths[0] != "organization" || paths[1] != "organization.standards" || paths[19] != "preferences.workflow" {
		t.Fatalf("paths %v", paths)
	}
	if !s.ValidateCategoryPath("security.encryption") || s.ValidateCategoryPath("security.x") || s.ValidateCategoryPath("a.b.c") {
		t.Fatal("validate")
	}
	if c, ok := s.GetFieldCategory("linters"); !ok || c != "development.tools" {
		t.Fatal("field category")
	}
	if s.GetCategoryPath("a", "") != "a" || s.GetCategoryPath("a", "b") != "a.b" {
		t.Fatal("path")
	}
}

func TestGlobalContextNestedData(t *testing.T) {
	g := NewGlobalContextNestedData()
	_ = g.SetNestedValue("development.tools.linters", "ruff")
	_ = g.SetNestedValue("development.extra.x", 1)
	if g.GetNestedValue("development.tools.linters", nil) != "ruff" || g.GetNestedValue("nope.a.b", "d") != "d" {
		t.Fatal("get/set")
	}
	_ = g.SetNestedValue("security.encryption", "str")
	if err := g.SetNestedValue("security.encryption.k", 1); err == nil || !strings.Contains(err.Error(), "'str' object") {
		t.Fatalf("type error: %v", err)
	}
	back := GlobalContextNestedDataFromDict(g.ToDict())
	if back.SchemaVersion != "2.0" || back.GetNestedValue("development.extra.x", nil) != 1 {
		t.Fatal("roundtrip")
	}
}
