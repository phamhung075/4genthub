package repositories

import (
	"strings"
	"testing"
)

func TestValidateName(t *testing.T) {
	valid := []string{"dev", "room-1", "A", "a_b", "0", "codex-2", "R2-D2", "trailing-"}
	for _, value := range valid {
		if err := ValidateName("room slug", value); err != nil {
			t.Errorf("ValidateName(%q) = %v, want nil", value, err)
		}
	}

	invalid := []string{"", ".", "a.b", "a b", "-lead", "_lead", "a/b", "café", "pod.member"}
	for _, value := range invalid {
		if err := ValidateName("room slug", value); err == nil {
			t.Errorf("ValidateName(%q) = nil, want error", value)
		}
	}
}

func TestValidateNameErrorNamesField(t *testing.T) {
	err := ValidateName("seat key", "bad.key")
	if err == nil {
		t.Fatal("ValidateName(bad.key) = nil, want error")
	}
	if !strings.Contains(err.Error(), "seat key") || !strings.Contains(err.Error(), "bad.key") {
		t.Fatalf("error %q does not name the field and value", err)
	}
}

func TestValidateModuleSlugAndVersion(t *testing.T) {
	for _, slug := range []string{"a", "my-skill", "a1-b2"} {
		if err := ValidateModuleSlug(slug); err != nil {
			t.Errorf("ValidateModuleSlug(%q) = %v", slug, err)
		}
	}
	for _, slug := range []string{"", "1a", "-a", "A", "a_b", "a.b"} {
		if ValidateModuleSlug(slug) == nil {
			t.Errorf("ValidateModuleSlug(%q) = nil, want error", slug)
		}
	}
	for _, version := range []string{"0.0.0", "1.2.3", "10.20.30"} {
		if err := ValidateConcreteVersion(version); err != nil {
			t.Errorf("ValidateConcreteVersion(%q) = %v", version, err)
		}
	}
	for _, version := range []string{"", "latest", "1.0", "01.0.0", "1.0.0-rc1", "v1.0.0"} {
		if ValidateConcreteVersion(version) == nil {
			t.Errorf("ValidateConcreteVersion(%q) = nil, want error", version)
		}
	}
}
