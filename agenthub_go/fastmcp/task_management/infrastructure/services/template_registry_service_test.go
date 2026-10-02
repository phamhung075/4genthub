package services

import (
	"strings"
	"testing"
)

func TestTemplateRegistryServiceConstructorDefect(t *testing.T) {
	svc, err := NewTemplateRegistryService(nil)
	if err == nil {
		t.Fatalf("NewTemplateRegistryService did not fail")
	}
	if svc != nil {
		t.Fatalf("NewTemplateRegistryService returned a non-nil service")
	}
	if !strings.HasPrefix(err.Error(), "Template Registry Service requires refactoring") {
		t.Fatalf("unexpected error message: %q", err.Error())
	}
}
