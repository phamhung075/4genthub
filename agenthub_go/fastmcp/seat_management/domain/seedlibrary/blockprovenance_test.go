package seedlibrary

// The provenance pair is computed on the library side and recorded on the migration side, so the
// tests that matter are the ones that prove it REPORTS: a mutated file must be named, an absent
// library file must be named, an absent SOURCE must be reported as the steady state rather than as a
// failure, and a root that does not hold the library must be an error rather than a clean bill.

import (
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

var sha256Hex64 = regexp.MustCompile(`^[0-9a-f]{64}$`)

func TestBlockProvenanceTableCoversEveryFileTheShelfCarries(t *testing.T) {
	table, err := BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	bySlug := map[string]BlockProvenance{}
	for _, e := range table {
		bySlug[e.Slug] = e
		if !sha256Hex64.MatchString(e.SHA256) {
			t.Errorf("%s: sha256 = %q, want 64 lowercase hex", e.Slug, e.SHA256)
		}
		if !strings.HasPrefix(e.Path, libraryRootPrefix) {
			t.Errorf("%s: path %q is not repository-relative under %s", e.Slug, e.Path, libraryRootPrefix)
		}
		if _, err := fs.ReadFile(embedded, strings.TrimPrefix(e.Path, libraryRootPrefix)); err != nil {
			t.Errorf("%s: path %q is not a file the binary carries: %v", e.Slug, e.Path, err)
		}
		if e.Bytes == 0 {
			t.Errorf("%s: recorded 0 bytes", e.Slug)
		}
	}

	// The eleven guides are why the pair exists, and each must carry the interim file it came from.
	want := []string{"guide-common"}
	for _, seat := range guideSeats {
		want = append(want, "guide-"+seat)
	}
	for _, slug := range want {
		e, ok := bySlug[slug]
		if !ok {
			t.Errorf("%s is missing from the provenance table", slug)
			continue
		}
		if e.SourcePath == "" || !sha256Hex64.MatchString(e.SourceSHA256) {
			t.Errorf("%s: source pairing missing (source_path=%q source_sha256=%q)", slug, e.SourcePath, e.SourceSHA256)
		}
	}
	// A block authored in-tree has no source to record, and inventing one would compare the library
	// against itself.
	if e := bySlug["agenthub-http"]; e.SourcePath != "" {
		t.Errorf("agenthub-http: source_path = %q, want empty for an in-tree block", e.SourcePath)
	}
	// The two kinds whose extension would name them wrongly, so the table cannot be built from
	// extensions alone: a shared tool is a .json, and a skill block is a .md.
	for slug, kind := range map[string]string{
		"comm-guard": "tool", "comm-guard-skill": "skill", "agenthub-http": "mcp",
	} {
		if e, ok := bySlug[slug]; !ok {
			t.Errorf("%s is missing from the provenance table", slug)
		} else if string(e.Kind) != kind {
			t.Errorf("%s: kind = %q, want %q", slug, e.Kind, kind)
		}
	}
	t.Logf("provenance table: %d files, %d of them with a recorded source", len(table), len(want))
}

// A shelf whose bytes disagree with the pairing recorded for it is refused, because a stale pairing
// makes the drift check lie. The shipped shelf is the one thing a test cannot mutate, so the
// falsification is the digest map the checker is handed - both refusal branches, each asserted.
func TestGuidePairingRefusesAStaleRecord(t *testing.T) {
	if err := VerifyGuidePairing(); err != nil {
		t.Fatalf("the shipped shelf disagrees with its own lock: %v", err)
	}

	table, err := BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	digests := map[string]string{}
	for _, e := range table {
		digests[e.Slug] = e.SHA256
	}

	// Branch 1: the shelf carries bytes the lock does not record.
	digests["guide-lead"] = strings.Repeat("0", 64)
	err = verifyGuideLocks(digests)
	if err == nil {
		t.Fatal("a shelf disagreeing with the lock was accepted")
	}
	if !strings.Contains(err.Error(), "guides.lock.json records") {
		t.Fatalf("refusal does not name the recorded pairing: %v", err)
	}
	t.Logf("stale bytes refused: %v", err)

	// Branch 2: the lock names a block the shelf does not carry - the same failure from the other
	// side, because the check would compare against a pairing that is already wrong.
	digests["guide-lead"] = "irrelevant"
	delete(digests, "guide-common")
	err = verifyGuideLocks(digests)
	if err == nil {
		t.Fatal("a lock naming an absent block was accepted")
	}
	if !strings.Contains(err.Error(), "which the shelf does not carry") {
		t.Fatalf("refusal does not say the block is absent: %v", err)
	}
	t.Logf("absent block refused: %v", err)
}

// materialise writes the whole library, and the recorded sources, into a temp root.
func materialise(t *testing.T) string {
	t.Helper()
	table, err := BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	root := t.TempDir()
	write := func(rel string, data []byte) {
		dst := filepath.Join(root, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(dst, data, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	for _, e := range table {
		data, err := fs.ReadFile(embedded, strings.TrimPrefix(e.Path, libraryRootPrefix))
		if err != nil {
			t.Fatalf("%s: %v", e.Slug, err)
		}
		write(e.Path, data)
	}
	// The sources are the interim files; their content equals the library copy at this point, which
	// is exactly the state the lock records.
	for _, e := range table {
		if e.SourcePath == "" {
			continue
		}
		write(e.SourcePath, mustReadEmbeddedForTest(t, e.Path))
	}
	return root
}

func mustReadEmbeddedForTest(t *testing.T, repoRel string) []byte {
	t.Helper()
	data, err := fs.ReadFile(embedded, strings.TrimPrefix(repoRel, libraryRootPrefix))
	if err != nil {
		t.Fatalf("%s: %v", repoRel, err)
	}
	return data
}

// The falsification the ledger asked for, on all four shapes at once so the counts can close.
func TestBlockDriftNamesEveryWayAFileCanMove(t *testing.T) {
	root := materialise(t)

	divs, err := CheckBlockDrift(root)
	if err != nil {
		t.Fatalf("CheckBlockDrift on a faithful copy: %v", err)
	}
	if len(divs) != 0 {
		t.Fatalf("a faithful copy reported divergences: %v", divs)
	}

	// 1. a hand-edit to a LIBRARY block
	if err := os.WriteFile(filepath.Join(root, "agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-lead.md"), []byte("## Guide: lead\n\nhand-edited\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	// 2. a library block REMOVED
	if err := os.Remove(filepath.Join(root, "agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-writer.md")); err != nil {
		t.Fatal(err)
	}
	// 3. a hand-edit to the INTERIM SOURCE, which is the window this exists for
	if err := os.WriteFile(filepath.Join(root, "ai_docs/operations/seat-guides/go-dev.md"), []byte("## Guide: go-dev\n\nedited in place\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	// 4. an interim source DELETED, which is the state after the migration
	if err := os.Remove(filepath.Join(root, "ai_docs/operations/seat-guides/web-dev.md")); err != nil {
		t.Fatal(err)
	}

	divs, err = CheckBlockDrift(root)
	if err != nil {
		t.Fatalf("CheckBlockDrift after the edits: %v", err)
	}
	seen := map[string]string{}
	for _, d := range divs {
		seen[d.Slug+"/"+d.Problem] = d.String()
		t.Logf("reported: %s", d)
	}
	for _, want := range []string{
		"guide-lead/differs", "guide-writer/missing", "guide-go-dev/source-differs", "guide-web-dev/source-gone",
	} {
		if _, ok := seen[want]; !ok {
			t.Errorf("expected a %s divergence; got %v", want, seen)
		}
	}
	if len(divs) != 4 {
		t.Errorf("reported %d divergences, want exactly the 4 edited files: %v", len(divs), divs)
	}
}

// A root that is not this library at all must be an error: an empty result would read as "in step",
// which is the failure shape every check in this family exists to avoid.
func TestBlockDriftRefusesARootWithoutTheLibrary(t *testing.T) {
	if _, err := CheckBlockDrift(t.TempDir()); err == nil {
		t.Fatal("a root holding no library reported success")
	}
}
