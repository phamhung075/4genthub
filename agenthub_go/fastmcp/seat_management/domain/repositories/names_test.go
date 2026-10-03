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
