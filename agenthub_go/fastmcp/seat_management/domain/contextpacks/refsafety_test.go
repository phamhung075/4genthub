package contextpacks

// Cases mirrored from the source's own suite — openrig 1a05af1b,
// `packages/daemon/test/context-pack-ref-safety.test.ts`
// (44c78c466956fbfd174fa3bab0952acf1605ca27), plus the store-recursion matrix that consumes the same
// predicate (`context-pack-store-recursion.test.ts`, "the matrix asserts the per-segment/traversal
// REJECT behavior verbatim"). The 2026-10-10 parity audit took that FILE as the definition of the
// layer, so its literal inputs are held here beside this seat's own — not a re-reading of the port.

import (
	"errors"
	"strings"
	"testing"
)

func TestIsSafePackRef(t *testing.T) {
	safe := []string{
		"notes",
		"packs/compaction-restore",
		"a/b/c",
		"A1._-b",
		"compaction-restore", // the source's single-segment accept
		"a/b/c.d_e-f",        // the source's spacing of dot, underscore and dash
	}
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
		// the source's own rejects, verbatim
		"../evil",
		"packs/../evil",
		"packs/..",
		"/abs/path",
		"packs//nested",
		"packs/",
		".",
		"packs/.hidden",
		"packs/na me",
		"packs/na:me",
		"packs/na\nme",
		"packs/na\tme",
		"packs/" + strings.Repeat("x", 65),
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
	for _, v := range []string{
		"1.0.0", "1.0", "2026-10-05", "v1.0.0+build",
		"2026-08-04", "v1_2+build", // the source's own accepts
	} {
		if !IsSafePackVersion(v) {
			t.Errorf("IsSafePackVersion(%q) = false, want true", v)
		}
	}
	for _, v := range []string{
		"", "a/b", "a b", "a@b", "a:b", strings.Repeat("a", 33),
		// the source's own rejects: R2 (a) ENAMETOOLONG and R2 (b) the colon-borne store id
		strings.Repeat("x", 300), "1.0 0", "1:0:0", "1/0", "@1.0",
	} {
		if IsSafePackVersion(v) {
			t.Errorf("IsSafePackVersion(%q) = true, want false", v)
		}
	}
}
