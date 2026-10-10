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

// The cases below are MIRROR CASES from the source's own suite
// (packages/daemon/test/markdown-address.test.ts and markdown-address-indentation.test.ts), not
// invented, and each one fails against the rules this file carried before them.

func sectionTitled(t *testing.T, sections []MarkdownSection, title string) MarkdownSection {
	t.Helper()
	for _, s := range sections {
		if s.Title == title {
			return s
		}
	}
	t.Fatalf("no section titled %q in %+v", title, sections)
	return MarkdownSection{}
}

// The source: "keeps inline backtick spans from swallowing later sections" — a backtick fence whose
// INFO STRING contains a backtick does not open a block, so the heading after it is still a section
// and the literal line stays inside the span it was written in.
func TestAFenceOpenerWithABacktickInItsInfoStringDoesNotOpen(t *testing.T) {
	text := "## Setup\n```literal ` backticks```\n## Deploy\ndeploy instructions\n"
	deploy, err := ResolveAddress(text, []string{"deploy"})
	if err != nil || deploy.Text != "## Deploy\ndeploy instructions\n" {
		t.Fatalf("deploy = %q, %v — the backtick info string swallowed the section", deploy.Text, err)
	}
	setup, err := ResolveAddress(text, []string{"setup"})
	if err != nil || !strings.Contains(setup.Text, "```literal ` backticks```") {
		t.Fatalf("setup = %q, %v — the literal line left the section it belongs to", setup.Text, err)
	}
	if f := ValidateMarkdownAddressability(text); len(f) != 0 {
		t.Errorf("findings = %+v, want none", f)
	}
}

// The source: an empty ATX heading is still a span and scope boundary — it ends the section before
// it, owns the children after it under an EMPTY segment, and validates clean, because a blank
// heading is a scope boundary rather than a name to check.
func TestAnEmptyHeadingEndsTheSpanAndOwnsItsChildren(t *testing.T) {
	for _, heading := range []string{"##", "## ", "##\t"} {
		text := "## Setup\nsetup instructions\n" + heading + "\nother section\n### Child\nchild instructions\n"
		setup, err := ResolveAddress(text, []string{"setup"})
		if err != nil || setup.Text != "## Setup\nsetup instructions" {
			t.Errorf("%q: setup span = %q, %v", heading, setup.Text, err)
		}
		if _, err := ResolveAddress(text, []string{"setup", "child"}); err == nil {
			t.Errorf("%q: a child of the empty heading resolved under its predecessor", heading)
		}
		child := sectionTitled(t, ParseMarkdownSections(text), "Child")
		if len(child.HeaderPath) != 2 || child.HeaderPath[0] != "" || child.HeaderPath[1] != "child" {
			t.Errorf("%q: child path = %v, want [\"\" child\"]", heading, child.HeaderPath)
		}
		if f := ValidateMarkdownAddressability(text); len(f) != 0 {
			t.Errorf("%q: findings = %+v, want none", heading, f)
		}
	}
}

// The source: children of an EMPTY H1 stay unaddressable, an empty H4 still terminates an H3's own
// text, and NAMING the H1 releases the following children to top level.
func TestEmptyH1KeepsChildrenUnaddressableAndANamedH1ReleasesThem(t *testing.T) {
	text := "## Setup\n### Child\nchild instructions\n####\nother subsection\n#\n### Independent\nindependent instructions"
	child, err := ResolveAddress(text, []string{"setup", "child"})
	if err != nil || child.OwnText != "### Child\nchild instructions" {
		t.Fatalf("child own text = %q, %v — an empty H4 must terminate it", child.OwnText, err)
	}
	ind := sectionTitled(t, ParseMarkdownSections(text), "Independent")
	if len(ind.HeaderPath) != 2 || ind.HeaderPath[0] != "" {
		t.Fatalf("independent path = %v, want an empty first segment", ind.HeaderPath)
	}
	if _, err := ResolveAddress(text, []string{"independent"}); err == nil {
		t.Error("a child of a blank H1 resolved at top level")
	}
	if f := ValidateMarkdownAddressability(text); len(f) != 0 {
		t.Errorf("findings = %+v, want none", f)
	}
	named := strings.Replace(text, "\n#\n", "\n# Named\n", 1)
	if got, err := ResolveAddress(named, []string{"independent"}); err != nil || !strings.Contains(got.Text, "independent instructions") {
		t.Errorf("a NAMED H1 must release its children to top level: %q, %v", got.Text, err)
	}
}

// The CONTRAST that makes the pair: a NAMED heading whose slug comes out empty ("## ???") is not a
// blank heading, so it and its child are BOTH flagged — silence there would be silent content loss.
func TestANamedHeadingWithAnEmptySlugFlagsTheWholeFamily(t *testing.T) {
	text := "## ???\ntext\n### kid\nchild\n"
	findings := ValidateMarkdownAddressability(text)
	var unaddressable int
	for _, f := range findings {
		if f.Kind == FindingUnaddressableHeader {
			unaddressable++
		}
	}
	if unaddressable != 2 {
		t.Fatalf("unaddressable findings = %d (%+v), want 2 — parent and child", unaddressable, findings)
	}
}

// The source's indentation boundary: one to three leading spaces are a heading, FOUR are an indented
// code block, and a fence opened at three spaces still hides what it contains.
func TestIndentationBoundaryAndIndentedCode(t *testing.T) {
	for spaces := 1; spaces <= 3; spaces++ {
		pad := strings.Repeat(" ", spaces)
		text := "## Selected\nkeep this\n" + pad + "### Child\nchild text\n" + pad + "## Excluded\nother context\n"
		sel, err := ResolveAddress(text, []string{"selected"})
		if err != nil || strings.Contains(sel.Text, "other context") {
			t.Errorf("%d spaces: the indented sibling did not terminate the span: %q, %v", spaces, sel.Text, err)
		}
		if got, err := ResolveAddress(text, []string{"selected", "child"}); err != nil || !strings.Contains(got.OwnText, "child text") {
			t.Errorf("%d spaces: indented child = %q, %v", spaces, got.OwnText, err)
		}
		if got, err := ResolveAddress(text, []string{"excluded"}); err != nil || !strings.Contains(got.Text, "other context") {
			t.Errorf("%d spaces: indented H2 = %q, %v", spaces, got.Text, err)
		}
	}
	text := "## Selected\n\n    ## Code example\n\n   ```md\n  ## Fenced example\n   ```\n\n## Sibling\n"
	var paths []string
	for _, s := range ParseMarkdownSections(text) {
		paths = append(paths, strings.Join(s.HeaderPath, "/"))
	}
	if len(paths) != 2 || paths[0] != "selected" || paths[1] != "sibling" {
		t.Fatalf("paths = %v, want [selected sibling] — four spaces is code, and the fence hides its own", paths)
	}
	sel, err := ResolveAddress(text, []string{"selected"})
	if err != nil || !strings.Contains(sel.Text, "## Code example") || !strings.Contains(sel.Text, "## Fenced example") {
		t.Errorf("selected = %q, %v — the code and fenced examples must stay inside the span", sel.Text, err)
	}
}
