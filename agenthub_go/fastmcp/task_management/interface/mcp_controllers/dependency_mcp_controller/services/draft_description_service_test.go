package services

import (
	"testing"
)

func TestDraftDescriptionServiceFlattensManageDependency(t *testing.T) {
	original := AllDescriptionsLoader
	defer func() { AllDescriptionsLoader = original }()

	AllDescriptionsLoader = func() map[string]any {
		return map[string]any{
			"task":      map[string]any{"manage_dependency": map[string]any{"description": "dep"}},
			"something": map[string]any{"other": 1},
		}
	}

	svc := NewDescriptionService()
	flat := svc.GetDependencyManagementDescriptions()
	if flat.Len() != 1 {
		t.Fatalf("len = %d", flat.Len())
	}
	value, ok := flat.Get("manage_dependency")
	if !ok {
		t.Fatal("missing manage_dependency")
	}
	nested, ok := value.(map[string]any)
	if !ok || nested["description"] != "dep" {
		t.Fatalf("value = %v", value)
	}
}
