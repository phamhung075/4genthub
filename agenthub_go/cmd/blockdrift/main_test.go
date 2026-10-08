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
	code := run(t.TempDir(), &stdout, &stderr)
	if code != 3 {
		t.Fatalf("code = %d, want 3\nstdout: %s\nstderr: %s", code, stdout.String(), stderr.String())
	}
	if !strings.Contains(stderr.String(), "does not hold the library") {
		t.Errorf("stderr = %q, want it to name the library it could not find", stderr.String())
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
	code := run(root, &stdout, &stderr)
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
