package contextpacks

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestParseRecapChainName(t *testing.T) {
	entry, ok := ParseRecapChainName("RECAP-1700000000000.md")
	if !ok || entry.SupersededAtMs != 1700000000000 || entry.Sequence != 1 {
		t.Errorf("bare name = %+v, %v", entry, ok)
	}
	entry, ok = ParseRecapChainName("RECAP-1700000000000-3.md")
	if !ok || entry.Sequence != 3 {
		t.Errorf("suffixed name = %+v, %v", entry, ok)
	}
	for _, bad := range []string{"RECAP.md", "other.md", "RECAP-x.md", "RECAP-1.MD"} {
		if _, ok := ParseRecapChainName(bad); ok {
			t.Errorf("ParseRecapChainName(%q) accepted a non-chain name", bad)
		}
	}
}

func TestRecapChainIsOldestFirst(t *testing.T) {
	names := []string{"RECAP-200.md", "RECAP-100.md", "RECAP-100-2.md", "notes.md"}
	got := RecapChain("/seats/dev", names, func(dir, name string) string { return filepath.Join(dir, name) })
	if len(got) != 3 {
		t.Fatalf("chain = %+v, want 3 entries", got)
	}
	want := []struct {
		ms  int64
		seq int
	}{{100, 1}, {100, 2}, {200, 1}}
	for i, w := range want {
		if got[i].SupersededAtMs != w.ms || got[i].Sequence != w.seq {
			t.Errorf("entry %d = %+v, want ms=%d seq=%d", i, got[i], w.ms, w.seq)
		}
	}
	if got[0].Path != filepath.Join("/seats/dev", "RECAP-100.md") {
		t.Errorf("path = %q", got[0].Path)
	}
}

func TestValidateRecapContract(t *testing.T) {
	good := "## Decisions\n\n- we chose X because Y\n\nUNVERIFIED: the deploy step\n"
	for _, f := range ValidateRecapContract(good) {
		if f.Kind == RecapFindingNoDecisions {
			t.Errorf("a decisions section was not seen: %+v", ValidateRecapContract(good))
		}
	}
	noDecisions := "## Notes\n\nbody\n"
	found := false
	for _, f := range ValidateRecapContract(noDecisions) {
		if f.Kind == RecapFindingNoDecisions {
			found = true
		}
	}
	if !found {
		t.Errorf("missing decisions section not reported: %+v", ValidateRecapContract(noDecisions))
	}
	// A variant marker hides exactly the fact it exists to flag.
	variant := "## Decisions\n\n- chose X\n\nUnverified: the deploy step\n"
	var marker *RecapContractFinding
	for i := range ValidateRecapContract(variant) {
		f := ValidateRecapContract(variant)[i]
		if f.Kind == RecapFindingNonstandardUnverifiedTag {
			marker = &f
		}
	}
	if marker == nil || marker.Line != 4 {
		t.Errorf("variant marker not reported on its line: %+v", ValidateRecapContract(variant))
	}
	// The canonical marker is fine.
	for _, f := range ValidateRecapContract(good) {
		if f.Kind == RecapFindingNonstandardUnverifiedTag {
			t.Errorf("the canonical UNVERIFIED: marker was flagged: %+v", f)
		}
	}
}

// The write gate is addressability: an unaddressable recap must be refused before it can ever be
// composed downstream.
func TestRecapWriteGateIsAddressability(t *testing.T) {
	unaddressable := "## Decisions\n\nfirst\n\n## Decisions\n\nsecond\n"
	findings := ValidateMarkdownAddressability(unaddressable)
	if len(findings) == 0 {
		t.Fatal("a recap with duplicate header paths passed the write gate")
	}
	if findings[0].Kind != FindingDuplicateHeaderPath {
		t.Errorf("finding = %+v, want %s", findings[0], FindingDuplicateHeaderPath)
	}
	// The advisory contract does not gate: prose shape is never refused.
	advisory := "## Notes\n\nunverified text\n"
	if len(ValidateMarkdownAddressability(advisory)) != 0 {
		t.Error("the advisory-only shape was gated by addressability")
	}
	if !strings.Contains(RecapFilename, "RECAP") || !strings.Contains(RecapChainDirname, "superseded") {
		t.Errorf("constants drifted: %q %q", RecapFilename, RecapChainDirname)
	}
}
