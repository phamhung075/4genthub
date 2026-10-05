package contextpacks

import (
	"errors"
	"strings"
	"testing"
)

func TestIsSafePackRef(t *testing.T) {
	safe := []string{"notes", "packs/compaction-restore", "a/b/c", "A1._-b"}
	for _, ref := range safe {
		if !IsSafePackRef(ref) {
			t.Errorf("IsSafePackRef(%q) = false, want true", ref)
		}
	}
	unsafe := []string{
		"",                      // empty
		"/etc/passwd",           // absolute
		"a//b",                  // empty interior segment
		"a/",                    // trailing empty segment
		"../escape",             // traversal
		"a/../b",                // interior traversal
		"./a",                   // dotfile segment
		".hidden",               // dotfile
		"a b",                   // whitespace
		"a:b",                   // separator that could forge an id
		"a\nb",                  // newline injection
		"a#b",                   // '#' would forge an address
		strings.Repeat("a", 65), // segment over 64 chars
	}
	for _, ref := range unsafe {
		if IsSafePackRef(ref) {
			t.Errorf("IsSafePackRef(%q) = true, want false", ref)
		}
	}
}

// The acceptance clause: an unsafe ref is REJECTED, never dropped silently.
func TestAssertSafePackRefRejectsRatherThanDrops(t *testing.T) {
	if err := AssertSafePackRef("packs/compaction-restore"); err != nil {
		t.Fatalf("a safe ref was rejected: %v", err)
	}
	err := AssertSafePackRef("../escape")
	if err == nil {
		t.Fatal("a traversal ref was accepted")
	}
	if !strings.Contains(err.Error(), "unsafe pack ref") {
		t.Errorf("error %q should name the refusal", err)
	}
	// It is a plain error, not a silent no-op: callers must branch on it.
	if errors.Is(err, nil) {
		t.Error("refusal should be a non-nil error")
	}
}

func TestIsSafePackVersion(t *testing.T) {
	for _, v := range []string{"1.0.0", "1.0", "2026-10-05", "v1.0.0+build"} {
		if !IsSafePackVersion(v) {
			t.Errorf("IsSafePackVersion(%q) = false, want true", v)
		}
	}
	for _, v := range []string{"", "a/b", "a b", "a@b", "a:b", strings.Repeat("a", 33)} {
		if IsSafePackVersion(v) {
			t.Errorf("IsSafePackVersion(%q) = true, want false", v)
		}
	}
}
