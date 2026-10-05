package contextpacks

import (
	"errors"
	"strings"
	"testing"
)

func TestSlugifyHeader(t *testing.T) {
	cases := map[string]string{
		"Alpha":               "alpha",
		"Alpha One":           "alpha-one",
		"**Bold** heading":    "bold-heading",
		"`code` and_text":     "code-andtext", // '_' is a stripped marker, as in the TypeScript rule
		"  Many   --  gaps  ": "many-gaps",
		"UPPER Case":          "upper-case",
	}
	for in, want := range cases {
		if got := SlugifyHeader(in); got != want {
			t.Errorf("SlugifyHeader(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseAddress(t *testing.T) {
	got, err := ParseAddress("notes.md")
	if err != nil || got.Ref != "notes.md" || len(got.HeaderPath) != 0 {
		t.Errorf("bare address = %+v, %v", got, err)
	}
	got, err = ParseAddress("notes.md#alpha")
	if err != nil || got.Ref != "notes.md" || len(got.HeaderPath) != 1 || got.HeaderPath[0] != "alpha" {
		t.Errorf("one-level address = %+v, %v", got, err)
	}
	got, err = ParseAddress("packs/note.md#alpha/one")
	if err != nil || got.Ref != "packs/note.md" || len(got.HeaderPath) != 2 {
		t.Errorf("two-level address = %+v, %v", got, err)
	}

	for _, bad := range []string{
		"notes.md#a#b",   // two '#' separators
		"#alpha",         // empty ref
		"notes.md#",      // empty segment
		"notes.md#a/",    // trailing empty segment
		"notes.md#a/b/c", // deeper than H3
	} {
		if _, err := ParseAddress(bad); err == nil {
			t.Errorf("ParseAddress(%q) accepted an illegal form", bad)
		}
	}
}

func TestParseMarkdownSectionsSpanAndOwnText(t *testing.T) {
	sections := ParseMarkdownSections(doc)
	byPath := map[string]MarkdownSection{}
	for _, s := range sections {
		byPath[strings.Join(s.HeaderPath, "/")] = s
	}
	alpha, ok := byPath["alpha"]
	if !ok {
		t.Fatalf("no alpha section: %+v", byPath)
	}
	// FULL span runs to the next same-or-higher header, so the H3 child is included.
	if !strings.Contains(alpha.Text, "### Alpha one") || !strings.Contains(alpha.Text, "Alpha one body.") {
		t.Errorf("alpha full span = %q", alpha.Text)
	}
	if strings.Contains(alpha.Text, "Beta body.") {
		t.Errorf("alpha full span ran past ## Beta: %q", alpha.Text)
	}
	// OWN text stops at the next header of any level.
	if strings.Contains(alpha.OwnText, "Alpha one") {
		t.Errorf("alpha own text leaked into the H3 child: %q", alpha.OwnText)
	}
	if !strings.Contains(alpha.OwnText, "Alpha body.") {
		t.Errorf("alpha own text = %q", alpha.OwnText)
	}
	if _, ok := byPath["alpha/alpha-one"]; !ok {
		t.Errorf("the H3 child is not addressable: %+v", byPath)
	}
}

func TestResolveAddressFailsLoud(t *testing.T) {
	got, err := ResolveAddress(doc, []string{"alpha", "alpha-one"})
	if err != nil {
		t.Fatalf("resolve: %v", err)
	}
	if got.HeaderLine != 8 {
		t.Errorf("header line = %d, want 8", got.HeaderLine)
	}
	// A miss is an error that names the real candidates at that altitude.
	_, err = ResolveAddress(doc, []string{"alpha", "ghost"})
	var addrErr *AddressResolutionError
	if !errors.As(err, &addrErr) {
		t.Fatalf("error = %T (%v), want *AddressResolutionError", err, err)
	}
	if !strings.Contains(err.Error(), "matches no header") || !strings.Contains(err.Error(), "alpha/alpha-one") {
		t.Errorf("miss error %q should list the candidates", err)
	}
	// An empty header path is a caller error.
	if _, err := ResolveAddress(doc, nil); err == nil {
		t.Error("an empty header path resolved instead of failing")
	}
}

func TestResolveAddressRejectsAmbiguity(t *testing.T) {
	ambiguous := "## Alpha\n\nfirst\n\n## Alpha\n\nsecond\n"
	_, err := ResolveAddress(ambiguous, []string{"alpha"})
	if err == nil || !strings.Contains(err.Error(), "AMBIGUOUS") {
		t.Fatalf("duplicate header path error = %v, want a loud ambiguity", err)
	}
}

func TestHeadersInsideFencesAreNotAddresses(t *testing.T) {
	text := "## Real\n\nbody\n\n```\n## Not a header\n```\n\n## After\n\nmore\n"
	sections := ParseMarkdownSections(text)
	for _, s := range sections {
		if s.Title == "Not a header" {
			t.Fatalf("a fenced header became an address: %+v", s)
		}
	}
	if len(sections) != 2 {
		t.Fatalf("sections = %d, want 2 (Real, After)", len(sections))
	}
}

func TestValidateMarkdownAddressabilityFindings(t *testing.T) {
	if f := ValidateMarkdownAddressability(doc); len(f) != 0 {
		t.Errorf("clean document produced findings: %+v", f)
	}
	dup := "## Alpha\n\nfirst\n\n## Alpha\n\nsecond\n"
	findings := ValidateMarkdownAddressability(dup)
	if len(findings) != 1 || findings[0].Kind != FindingDuplicateHeaderPath || len(findings[0].Lines) != 2 {
		t.Fatalf("duplicate findings = %+v", findings)
	}
	unterminated := "## Real\n\nbody\n\n```\n## Swallowed\n"
	findings = ValidateMarkdownAddressability(unterminated)
	var sawFence bool
	for _, f := range findings {
		if f.Kind == FindingUnterminatedFence {
			sawFence = true
		}
	}
	if !sawFence {
		t.Fatalf("unterminated fence not reported: %+v", findings)
	}
}
