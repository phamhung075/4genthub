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
	if len(got.MissingFiles) != 1 || got.MissingFiles[0] != "missing.md" {
		t.Errorf("missing = %+v", got.MissingFiles)
	}
	if got.EstimatedTokens != EstimateTokensOf(got.Text) {
		t.Errorf("estimate = %d, want %d", got.EstimatedTokens, EstimateTokensOf(got.Text))
	}
}

func TestAssembleBundleFramesAndSkipsMissing(t *testing.T) {
	abs := "/p/a.md"
	pack := BundlePack{
		ID: "context-pack:x:1", Name: "x", Version: "1.0.0", Purpose: "  a purpose  ",
		Files: []BundleFile{
			{Path: "a.md", Role: "prd", Summary: "the prd", AbsolutePath: &abs},
			{Path: "gone.md", Role: "evidence", AbsolutePath: nil},
		},
	}
	read := func(p string) (string, error) {
		if p != "/p/a.md" {
			return "", errors.New("unexpected path")
		}
		return "body text\n\n", nil
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
	if strings.Contains(got.Text, "gone.md") {
		t.Errorf("a missing file was framed into the bundle: %q", got.Text)
	}
	if !strings.HasSuffix(got.Text, "body text\n") {
		t.Errorf("the trailing blank of the content was not trimmed before the join: %q", got.Text)
	}
	if len(got.MissingFiles) != 1 || got.MissingFiles[0].Path != "gone.md" {
		t.Errorf("missing files = %+v", got.MissingFiles)
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
