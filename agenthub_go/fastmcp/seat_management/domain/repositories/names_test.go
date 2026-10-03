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

func TestValidateRuntime(t *testing.T) {
	for _, runtime := range []string{"claude-code", "codex"} {
		if err := ValidateRuntime(runtime); err != nil {
			t.Errorf("ValidateRuntime(%q) = %v", runtime, err)
		}
	}
	for _, runtime := range []string{"", "gemini", "Codex", "claude_code"} {
		if ValidateRuntime(runtime) == nil {
			t.Errorf("ValidateRuntime(%q) = nil, want error", runtime)
		}
	}
}

func TestValidateRoomName(t *testing.T) {
	for _, name := range []string{"Dev", strings.Repeat("n", MaxRoomNameLength), strings.Repeat("é", MaxRoomNameLength)} {
		if err := ValidateRoomName(name); err != nil {
			t.Errorf("ValidateRoomName(%d chars) = %v", len(name), err)
		}
	}
	for _, name := range []string{"", "   ", strings.Repeat("n", MaxRoomNameLength+1)} {
		if ValidateRoomName(name) == nil {
			t.Errorf("ValidateRoomName(%d chars) = nil, want error", len(name))
		}
	}
}

func TestValidateOccupant(t *testing.T) {
	for _, c := range [][2]string{{"codex", ""}, {"codex", "gpt-5"}, {"claude-code", ""}, {"claude-code", "claude-sonnet-5-5"}, {"claude-code", "sonnet"}} {
		if err := ValidateOccupant(c[0], c[1]); err != nil {
			t.Errorf("ValidateOccupant(%q, %q) = %v", c[0], c[1], err)
		}
	}
	for _, c := range [][2]string{{"codex", "claude-sonnet-5-5"}, {"codex", "claude-opus-5-5"}, {"gemini", ""}, {"codex", "a b"}} {
		if ValidateOccupant(c[0], c[1]) == nil {
			t.Errorf("ValidateOccupant(%q, %q) = nil, want error", c[0], c[1])
		}
	}
}

func TestValidateModel(t *testing.T) {
	valid := []string{"", "sonnet", "gpt-5.1", "claude-opus-4-1:thinking", "openai/gpt-4o", "a", strings.Repeat("a", 128)}
	for _, model := range valid {
		if err := ValidateModel(model); err != nil {
			t.Errorf("ValidateModel(%q) = %v", model, err)
		}
	}
	invalid := []string{"-x", ".x", "a b", "a\nb", "é", strings.Repeat("a", 129)}
	for _, model := range invalid {
		if ValidateModel(model) == nil {
			t.Errorf("ValidateModel(%q) = nil, want error", model)
		}
	}
}

func TestParseModuleRef(t *testing.T) {
	ref, err := ParseModuleRef("my-skill@1.2.3")
	if err != nil || ref.Slug != "my-skill" || ref.Version != "1.2.3" {
		t.Fatalf("ParseModuleRef = %+v, %v", ref, err)
	}
	for _, bad := range []string{"", "a", "a@", "@1.0.0", "A@1.0.0", "a@latest", "a@1.0", "a@1.0.0@2"} {
		if _, err := ParseModuleRef(bad); err == nil {
			t.Errorf("ParseModuleRef(%q) = nil, want error", bad)
		}
	}
}

func TestNextPatchVersion(t *testing.T) {
	for in, want := range map[string]string{"1.0.0": "1.0.1", "0.9.9": "0.9.10", "2.3.41": "2.3.42"} {
		if got, err := NextPatchVersion(in); err != nil || got != want {
			t.Errorf("NextPatchVersion(%q) = %q, %v, want %q", in, got, err, want)
		}
	}
	if _, err := NextPatchVersion("latest"); err == nil {
		t.Error("NextPatchVersion(latest) = nil, want error")
	}
}
