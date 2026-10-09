package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/seedlibrary"
)

// The distinction this command exists to make: `source-gone` is the state the migration produces on
// purpose, and the other three problems are the divergences a reader must act on. A caller that
// treats all four alike has a gate that can never pass once the interim files are deleted.
func TestPartitionSeparatesSourceGoneFromRealDivergences(t *testing.T) {
	in := []seedlibrary.BlockDivergence{
		{Slug: "a", Problem: "differs"},
		{Slug: "b", Problem: "missing"},
		{Slug: "c", Problem: "source-differs"},
		{Slug: "d", Problem: "source-gone"},
		{Slug: "e", Problem: "source-gone"},
	}
	failures, gone := partition(in)
	if len(failures) != 3 {
		t.Fatalf("failures = %d, want 3: %v", len(failures), failures)
	}
	if len(gone) != 2 {
		t.Fatalf("gone = %d, want 2: %v", len(gone), gone)
	}
	for _, d := range failures {
		if d.Problem == "source-gone" {
			t.Errorf("%s: source-gone reached the failures", d.Slug)
		}
	}
	for _, d := range gone {
		if d.Problem != "source-gone" {
			t.Errorf("%s: %s reached the expected side", d.Slug, d.Problem)
		}
	}
	if failures[0].Slug != "a" || failures[2].Slug != "c" {
		t.Errorf("order was not preserved: %v", failures)
	}
}

func TestPartitionOfNothingIsNothing(t *testing.T) {
	failures, gone := partition(nil)
	if len(failures) != 0 || len(gone) != 0 {
		t.Fatalf("partition(nil) = %v / %v, want empty", failures, gone)
	}
}

// A root that does not hold the library is a REFUSAL, not a pass: the check cannot see the shelf, so
// a clean bill from it would mean "the tree I was pointed at has nothing to compare", which is the
// reading a wrong root must never produce. Exit 3, and the message names what it could not find.
func TestRootWithoutTheLibraryIsRefused(t *testing.T) {
	var stdout, stderr strings.Builder
	code := execute(t.TempDir(), &stdout, &stderr)
	if code != 3 {
		t.Fatalf("code = %d, want 3\nstdout: %s\nstderr: %s", code, stdout.String(), stderr.String())
	}
	if !strings.Contains(stderr.String(), "does not hold the library") {
		t.Errorf("stderr = %q, want it to name the library it could not find", stderr.String())
	}
	table, err := seedlibrary.BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	if !strings.Contains(stderr.String(), "looked for "+table[0].Path) {
		t.Errorf("stderr = %q, want it to name the library path it looked for (%s)", stderr.String(), table[0].Path)
	}
}

// An absent block file is a divergence per block, never a pass, because absence is how a block leaves
// a tree without anybody noticing. The shelf's own directory is taken from the provenance table, so
// this test cannot disagree with the library about where the blocks live.
func TestMissingBlockFilesAreDivergencesNotAPass(t *testing.T) {
	table, err := seedlibrary.BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	if len(table) == 0 {
		t.Fatal("the library carries no blocks")
	}
	root := t.TempDir()
	// The guard CheckBlockDrift applies is that the FIRST block's directory exists, so creating just
	// that directory gets the check past the wrong-root refusal and into the per-file comparisons
	// with nothing to compare against — which is the state under test.
	shelf := filepath.Dir(filepath.Join(root, filepath.FromSlash(table[0].Path)))
	if err := os.MkdirAll(shelf, 0o755); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr strings.Builder
	code := execute(root, &stdout, &stderr)
	if code != 1 {
		t.Fatalf("code = %d, want 1\nstdout: %s\nstderr: %s", code, stdout.String(), stderr.String())
	}
	if got := strings.Count(stdout.String(), "divergence: "); got != len(table) {
		t.Errorf("reported %d divergences, want one per block (%d)\n%s", got, len(table), stdout.String())
	}
	if !strings.Contains(stderr.String(), "divergence(s)") {
		t.Errorf("stderr = %q, want the count on stderr where a hook reads it", stderr.String())
	}
}

// THE GONE-SOURCE CONTRACT, END TO END. After the migration deletes the interim files an absent
// source is the intended state, so the command must PRINT it as expected and still exit 0 — the one
// contract that has to survive the deletion, and until now it was verified only by hand in a copy.
// It drives the whole command rather than partition(), and it asserts the guide BY NAME and the
// count line, so it cannot pass by finding no gone sources at all: the count line has to read one.
func TestGoneSourceIsPrintedAsExpectedAndExitsZero(t *testing.T) {
	const slug = "guide-writer"
	const source = "ai_docs/operations/seat-guides/writer.md"
	root := shelfUnder(t, source)

	var stdout, stderr strings.Builder
	code := execute(root, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("code = %d, want 0: a gone source is the intended state, not a failure\nstdout: %s\nstderr: %s",
			code, stdout.String(), stderr.String())
	}
	want := "expected: " + slug + ": " + source + " is gone; the library copy is the only one left (expected after the migration)"
	if !strings.Contains(stdout.String(), want) {
		t.Errorf("stdout does not carry the expected line\nwant: %s\ngot:\n%s", want, stdout.String())
	}
	if !strings.Contains(stdout.String(), "1 source file(s) already gone") {
		t.Errorf("the count line must report exactly one gone source, not merely a zero exit:\n%s", stdout.String())
	}
	if strings.Contains(stdout.String(), "divergence: ") {
		t.Errorf("nothing else diverges in this fixture:\n%s", stdout.String())
	}
}

// EXIT 2 IS A CONTRACT, NOT A BRANCH IN main(). It was unreachable from any test until the usage
// decision moved into execute(), and it is the status a hook reads to tell a usage mistake from a
// divergence (1) or an unusable root (3). A blank root refuses, prints the usage where a hook can
// read it, and prints NO report — a refusal that also wrote a report would read as a run.
func TestUsageRefusalIsExitTwo(t *testing.T) {
	for _, root := range []string{"", "   ", "\t\n"} {
		var stdout, stderr strings.Builder
		code := execute(root, &stdout, &stderr)
		if code != 2 {
			t.Fatalf("execute(%q) = %d, want 2\nstdout: %s\nstderr: %s", root, code, stdout.String(), stderr.String())
		}
		if !strings.Contains(stderr.String(), "-root is required") {
			t.Errorf("execute(%q): stderr = %q, want the refusal", root, stderr.String())
		}
		if !strings.Contains(stderr.String(), "blockdrift - check the seed library") {
			t.Errorf("execute(%q): stderr = %q, want the usage text", root, stderr.String())
		}
		if stdout.String() != "" {
			t.Errorf("execute(%q): stdout = %q, want nothing: a refusal is not a run", root, stdout.String())
		}
	}
}

// shelfUnder builds a root holding the library's own block files and the interim sources they were
// copied from, minus the one source the caller withholds. The block files are copied verbatim from
// this checkout, which is what the binary embedded, so the only difference from the real tree is the
// withheld source — the fixture cannot pass by diverging on something else.
func shelfUnder(t *testing.T, withholdSource string) string {
	t.Helper()
	table, err := seedlibrary.BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	if len(table) == 0 {
		t.Fatal("the library carries no blocks")
	}
	root := t.TempDir()
	for _, e := range table {
		copyInto(t, root, e.Path)
		if e.SourcePath == "" || e.SourcePath == withholdSource {
			continue
		}
		copyInto(t, root, e.SourcePath)
	}
	return root
}

// copyInto copies one repository-relative file into the fixture root, keeping its path. The package
// sits at agenthub_go/cmd/blockdrift, so three levels up is the root that block paths are recorded
// against.
func copyInto(t *testing.T, root, rel string) {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "..", "..", filepath.FromSlash(rel)))
	if err != nil {
		t.Fatalf("fixture source %s: %v", rel, err)
	}
	dst := filepath.Join(root, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(dst, data, 0o644); err != nil {
		t.Fatal(err)
	}
}
