package contextpacks

import (
	"errors"
	"strings"
	"testing"
)

func TestAssemblePlainFiles(t *testing.T) {
	alpha, beta := "alpha", "beta"
	got := AssemblePlainFiles([]PlainFileInput{
		{Path: "a.md", Content: &alpha},
		{Path: "missing.md", Content: nil},
		{Path: "b.md", Content: &beta},
	})
	if got.Text != "alpha\n\nbeta" {
		t.Errorf("text = %q, want the two present members joined by a blank line", got.Text)
	}
	if len(got.Files) != 2 || got.Files[0].Path != "a.md" || got.Files[0].EstimatedTokens != EstimateTokensFromBytes(5) {
		t.Errorf("files = %+v", got.Files)
	}
	if len(got.MissingFiles) != 1 || got.MissingFiles[0].Path != "missing.md" {
		t.Errorf("missing = %+v", got.MissingFiles)
	}
	if got.EstimatedTokens != EstimateTokensOf(got.Text) {
		t.Errorf("estimate = %d, want %d", got.EstimatedTokens, EstimateTokensOf(got.Text))
	}
}

func TestAssembleBundleFramesAndSkipsMissing(t *testing.T) {
	abs, absNotes := "/p/a.md", "/p/notes.md"
	pack := BundlePack{
		ID: "context-pack:x:1", Name: "x", Version: "1.0.0", Purpose: "  a purpose  ",
		Files: []BundleFile{
			{Path: "a.md", Role: "prd", Summary: "the prd", AbsolutePath: &abs},
			// No summary: the header must stay `## File: <path> (role: <role>)`, with no separator.
			{Path: "notes.md", Role: "notes", AbsolutePath: &absNotes},
			{Path: "gone.md", Role: "evidence", AbsolutePath: nil},
		},
	}
	read := func(p string) (string, error) {
		switch p {
		case "/p/a.md":
			return "body text\n\n", nil
		case "/p/notes.md":
			return "Note 1", nil
		}
		return "", errors.New("unexpected path")
	}
	got, err := AssembleBundle(pack, read)
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if !strings.HasPrefix(got.Text, "# OpenRig Context Pack: x v1.0.0\n\n") {
		t.Errorf("bundle does not lead with the pack frame: %q", got.Text[:40])
	}
	if !strings.Contains(got.Text, "a purpose") {
		t.Errorf("purpose missing (or untrimmed): %q", got.Text)
	}
	if !strings.Contains(got.Text, "## File: a.md (role: prd) — the prd") {
		t.Errorf("file header missing the role/summary: %q", got.Text)
	}
	if !strings.Contains(got.Text, "## File: notes.md (role: notes)") || strings.Contains(got.Text, "(role: notes) —") {
		t.Errorf("a summary-less file header is wrong: %q", got.Text)
	}
	if strings.Contains(got.Text, "gone.md") {
		t.Errorf("a missing file was framed into the bundle: %q", got.Text)
	}
	// The trim is proved at the JOIN, which is where it is observable: the untrimmed content
	// ("body text\n\n") would leave four newlines before the next header.
	if !strings.Contains(got.Text, "body text\n\n## File: notes.md (role: notes)") {
		t.Errorf("the trailing blank of the content was not trimmed before the join: %q", got.Text)
	}
	if got.Bytes != len(got.Text) {
		t.Errorf("bytes = %d, want the byte length of the text (%d)", got.Bytes, len(got.Text))
	}
	if len(got.MissingFiles) != 1 || got.MissingFiles[0].Path != "gone.md" || got.MissingFiles[0].Role != "evidence" {
		t.Errorf("missing files = %+v, want the path AND the role", got.MissingFiles)
	}
}

func TestAssembleBundleReadErrorIsLoud(t *testing.T) {
	abs := "/p/a.md"
	pack := BundlePack{Name: "x", Version: "1", Files: []BundleFile{{Path: "a.md", Role: "prd", AbsolutePath: &abs}}}
	_, err := AssembleBundle(pack, func(string) (string, error) { return "", errors.New("boom") })
	var packErr *ContextPackError
	if !errors.As(err, &packErr) || packErr.Code != CodeFileReadFailed {
		t.Fatalf("error = %v, want a %s ContextPackError", err, CodeFileReadFailed)
	}
}

func TestAssembleBundleFileEntryCarriesRoleAndProjection(t *testing.T) {
	abs := "/p/a.md"
	pack := BundlePack{Name: "x", Version: "1", Files: []BundleFile{{Path: "a.md", Role: "prd", AbsolutePath: &abs}}}
	got, err := AssembleBundle(pack, func(string) (string, error) { return "body", nil })
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if len(got.Files) != 1 {
		t.Fatalf("files = %+v, want the one present file", got.Files)
	}
	if f := got.Files[0]; f.Path != "a.md" || f.Role != "prd" || f.Bytes != 4 || f.EstimatedTokens != 1 {
		t.Errorf("file entry = %+v, want a.md/prd/4 bytes/1 token in ONE entry", f)
	}
}

func TestAssembleBundleTrimsEndLikeJavaScript(t *testing.T) {
	// Every character JavaScript's trimEnd removes must go; U+0085 (NEL) is Go's unicode.IsSpace
	// whitespace but NOT ECMAScript whitespace, so it must SURVIVE. That control is what separates
	// this trim from strings.TrimSpace, which would have eaten it.
	jsRun := "js\v\f\u00a0\u2003\u2028\u2029\u3000\ufeff"
	nel := "nel\u0085"
	absA, absB := "/p/a.md", "/p/b.md"
	pack := BundlePack{Name: "x", Version: "1", Files: []BundleFile{
		{Path: "a.md", Role: "prd", AbsolutePath: &absA},
		{Path: "b.md", Role: "evidence", AbsolutePath: &absB},
	}}
	got, err := AssembleBundle(pack, func(p string) (string, error) {
		if p == absA {
			return jsRun, nil
		}
		return nel, nil
	})
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if !strings.Contains(got.Text, "\n\njs\n\n") {
		t.Errorf("the ECMAScript whitespace run was not trimmed: %q", got.Text)
	}
	if strings.ContainsAny(got.Text, "\u2003\u2028\u3000\ufeff") {
		t.Errorf("a trimmed character survived into the bundle: %q", got.Text)
	}
	if !strings.HasSuffix(got.Text, "nel\u0085\n") {
		t.Errorf("the NEL was trimmed, and ECMAScript trimEnd keeps it: %q", got.Text)
	}
	if got.Files[0].Bytes != len(jsRun) {
		t.Errorf("bytes = %d, want the UNTRIMMED %d", got.Files[0].Bytes, len(jsRun))
	}
}

// The PURPOSE is trimmed with the source's .trim(), which is not Go's TrimSpace: measured against
// the engine over the whole BMP the two sets differ at exactly two code points — U+FEFF, which
// ECMAScript strips and unicode.IsSpace keeps, and U+0085, which unicode.IsSpace strips and
// ECMAScript keeps. This is the call site the earlier trimEnd fix did not convert, so both ends are
// pinned: the BOM must go and the NEL must stay.
func TestAssembleBundleTrimsThePurposeLikeJavaScript(t *testing.T) {
	abs := "/p/a.md"
	purpose := "\ufeffa BOM-led purpose\u0085"
	// The control that makes this a test of the CALL SITE: the two functions disagree on this exact
	// input, so a swap of jsTrim back to strings.TrimSpace cannot satisfy this and the assertions
	// below at once.
	if strings.TrimSpace(purpose) == jsTrim(purpose) {
		t.Fatalf("this input no longer separates the ECMAScript set from Go's: %q", purpose)
	}
	pack := BundlePack{Name: "x", Version: "1", Purpose: purpose,
		Files: []BundleFile{{Path: "a.md", Role: "prd", AbsolutePath: &abs}}}
	got, err := AssembleBundle(pack, func(string) (string, error) { return "body", nil })
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if !strings.Contains(got.Text, "\n\na BOM-led purpose\u0085\n\n") {
		t.Errorf("the purpose was not trimmed to the ECMAScript set: %q", got.Text)
	}
	if strings.Contains(got.Text, "\ufeff") {
		t.Errorf("the BOM survived the purpose trim, and ECMAScript trim removes it: %q", got.Text)
	}
	if !strings.Contains(got.Text, "a BOM-led purpose\u0085") {
		t.Errorf("the trailing NEL was trimmed, and ECMAScript trim keeps it: %q", got.Text)
	}
}

// ---- the source's own cases, mirrored ---------------------------------------------------------
//
// Basis: openrig 1a05af1b, `packages/daemon/test/context-pack-compose.test.ts`
// (44c78c466956fbfd174fa3bab0952acf1605ca27 for ref-safety, its ATOM-3 block for plain assembly)
// and `packages/daemon/test/context-pack-bundle-assembler.test.ts`
// (62e1e8f21423aeca9372e9932b99486728b7b508). The 2026-10-10 parity audit took these two files as
// the DEFINITION of the layers' behaviour, so the cases are held here rather than a reading of the
// port: a pass that re-reads the port re-derives the same misunderstanding.

func TestAssemblePlainFilesPreservesEOFNewlineBytes(t *testing.T) {
	for _, c := range []struct{ name, a, b string }{
		{"no trailing newline", "A", "B"},
		{"newline on the first", "A\n", "B"},
		{"newline on the second", "A", "B\n"},
		{"newline on both", "A\n", "B\n"},
	} {
		t.Run(c.name, func(t *testing.T) {
			a, b := c.a, c.b
			got := AssemblePlainFiles([]PlainFileInput{
				{Path: "a.md", Content: &a},
				{Path: "b.md", Content: &b},
			})
			want := a + PlainComposeSeparator + b
			if got.Text != want {
				t.Errorf("text = %q, want %q (EOF-newline bytes preserved)", got.Text, want)
			}
			if strings.Contains(got.Text, "# OpenRig Context Pack:") || strings.Contains(got.Text, "## File:") {
				t.Errorf("plain assembly framed the text: %q", got.Text)
			}
			if got.Bytes != len(want) {
				t.Errorf("bytes = %d, want %d", got.Bytes, len(want))
			}
		})
	}
}

// The source pins this with `toEqual([{ path: "absent.md" }])`. The entry TYPE is what makes that
// assertion expressible: before the 2026-10-10 fix the port returned bare strings, so `.Path` was
// undefined on the entry and the source's own assertion did not compile.
func TestAssemblePlainFilesMissingEntriesCarryTheirPath(t *testing.T) {
	present := "present"
	got := AssemblePlainFiles([]PlainFileInput{
		{Path: "present.md", Content: &present},
		{Path: "absent.md", Content: nil},
	})
	if got.Text != "present" {
		t.Errorf("text = %q, want %q", got.Text, "present")
	}
	if len(got.MissingFiles) != 1 || got.MissingFiles[0].Path != "absent.md" {
		t.Errorf("missingFiles = %+v, want [{absent.md}]", got.MissingFiles)
	}
}

func TestAssembleBundleEstimatesTokensFromTheAssembledBytes(t *testing.T) {
	abs := "/abs/a.md"
	pack := BundlePack{Name: "test", Version: "1", Files: []BundleFile{
		{Path: "a.md", Role: "r", AbsolutePath: &abs},
	}}
	got, err := AssembleBundle(pack, func(string) (string, error) { return strings.Repeat("x", 100), nil })
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if got.EstimatedTokens < 25 {
		t.Errorf("estimatedTokens = %d, want >= 25 (ceil(bytes/4) over a 100-byte body)", got.EstimatedTokens)
	}
	if got.EstimatedTokens != EstimateTokensFromBytes(got.Bytes) {
		t.Errorf("estimatedTokens = %d, want the estimate of the assembled bytes %d", got.EstimatedTokens, got.Bytes)
	}
}

// "preserves operator-supplied purpose verbatim (trimmed)": the ENDS come off and the interior line
// break stays, because trim is not a collapse.
func TestAssembleBundleTrimmedPurposeKeepsItsLineBreaks(t *testing.T) {
	pack := BundlePack{Name: "test", Version: "1", Purpose: "  Multi-line purpose\nthat spans  "}
	got, err := AssembleBundle(pack, func(string) (string, error) { return "", nil })
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if !strings.Contains(got.Text, "Multi-line purpose\nthat spans") {
		t.Errorf("the purpose's interior line break was not preserved, or its ends were not trimmed: %q", got.Text)
	}
	if strings.Contains(got.Text, "  Multi-line purpose") {
		t.Errorf("the leading pad survived the trim: %q", got.Text)
	}
}

// "handles a pack with no files (empty bundle, no crash)" — the lists must be EMPTY, not nil, since
// the source's `toEqual([])` distinguishes the two on the wire.
func TestAssembleBundleWithNoFilesIsAnEmptyList(t *testing.T) {
	pack := BundlePack{Name: "test", Version: "1"}
	got, err := AssembleBundle(pack, func(string) (string, error) { return "", nil })
	if err != nil {
		t.Fatalf("assemble: %v", err)
	}
	if got.Files == nil || len(got.Files) != 0 {
		t.Errorf("files = %+v, want an empty, non-nil list", got.Files)
	}
	if got.MissingFiles == nil || len(got.MissingFiles) != 0 {
		t.Errorf("missingFiles = %+v, want an empty, non-nil list", got.MissingFiles)
	}
	if !strings.Contains(got.Text, "# OpenRig Context Pack: test v1") {
		t.Errorf("an empty pack lost its frame: %q", got.Text)
	}
}
