package contextpacks

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// The seat recap store (OPR.0.5.3.5 mini-req 7): the AUTHORED recap written by the OUTGOING
// occupant at the boundary. SEAT-HOMED beside LEARNED — the recap is position knowledge,
// unshareable by construction. RETENTION is superseded-chain versioning: the newest recap is
// RECAP.md and predecessors stay byte-preserved under recap-superseded/.
//
// This port carries the pure half — the chain naming/index, the write gate, and the authoring
// contract's checkable subset. The durable staging (atomic rename, link-based archive, cleanup)
// stays with the daemon because it is OS work; the GATE that staging must pass is here:
// ValidateMarkdownAddressability.
//
// Two validation altitudes, deliberately different:
//   - ADDRESSABILITY is the one HARD gate on write. The recap is composed by address
//     (seat:RECAP.md#...), so an unaddressable recap would fail every handover profile
//     downstream, silently late. Structural, not prose-shaped.
//   - The AUTHORING CONTRACT validates ADVISORY on its checkable subset only: findings flag for
//     review, never gate the boundary (the D2 pattern).

// RecapFilename is the current recap's filename.
const RecapFilename = "RECAP.md"

// RecapChainDirname holds the byte-preserved predecessors.
const RecapChainDirname = "recap-superseded"

// RecapChainEntry is one superseded recap.
type RecapChainEntry struct {
	// Path is the absolute path of the superseded recap.
	Path string
	// SupersededAtMs is the supersession timestamp encoded in the filename (ms epoch).
	SupersededAtMs int64
	// Sequence is the same-millisecond disambiguator (1 for the bare name, 2+ for -N suffixes).
	Sequence int
}

var recapChainName = regexp.MustCompile(`^RECAP-(\d+)(?:-(\d+))?\.md$`)

// ParseRecapChainName parses one chain filename; ok is false for anything that is not a chain
// member.
func ParseRecapChainName(name string) (RecapChainEntry, bool) {
	m := recapChainName.FindStringSubmatch(name)
	if m == nil {
		return RecapChainEntry{}, false
	}
	ms, err := strconv.ParseInt(m[1], 10, 64)
	if err != nil {
		return RecapChainEntry{}, false
	}
	seq := int64(1)
	if m[2] != "" {
		seq, err = strconv.ParseInt(m[2], 10, 64)
		if err != nil {
			return RecapChainEntry{}, false
		}
	}
	return RecapChainEntry{SupersededAtMs: ms, Sequence: int(seq)}, true
}

// RecapChain returns the superseded chain for a directory listing, oldest first. It is pure: the
// caller supplies the directory's entry names and the path join it wants.
func RecapChain(dir string, names []string, joinPath func(dir, name string) string) []RecapChainEntry {
	entries := []RecapChainEntry{}
	for _, name := range names {
		entry, ok := ParseRecapChainName(name)
		if !ok {
			continue
		}
		entry.Path = joinPath(dir, name)
		entries = append(entries, entry)
	}
	sort.SliceStable(entries, func(i, j int) bool {
		if entries[i].SupersededAtMs != entries[j].SupersededAtMs {
			return entries[i].SupersededAtMs < entries[j].SupersededAtMs
		}
		return entries[i].Sequence < entries[j].Sequence
	})
	return entries
}

// Recap authoring-contract finding kinds.
const (
	RecapFindingNoDecisions              = "no-decisions-section"
	RecapFindingNonstandardUnverifiedTag = "nonstandard-unverified-marker"
)

// RecapContractFinding is one advisory finding of the recap authoring contract.
type RecapContractFinding struct {
	Kind string
	Line int
}

var unverifiedWord = regexp.MustCompile(`(?i)unverified`)

// ValidateRecapContract checks the authoring contract's CHECKABLE subset: decisions-with-rationale
// has a structural proxy (a decisions-titled section exists), and the UNVERIFIED marker has a
// canonical grammar (`UNVERIFIED:` uppercase) that must stay findable — a variant marker hides
// exactly the fact it exists to flag. Advisory: findings, never throws.
func ValidateRecapContract(content string) []RecapContractFinding {
	findings := []RecapContractFinding{}
	hasDecisions := false
	for _, s := range ParseMarkdownSections(content) {
		if len(s.HeaderPath) > 0 && strings.Contains(s.HeaderPath[len(s.HeaderPath)-1], "decision") {
			hasDecisions = true
			break
		}
	}
	if !hasDecisions {
		findings = append(findings, RecapContractFinding{Kind: RecapFindingNoDecisions})
	}
	for i, line := range strings.Split(content, "\n") {
		if unverifiedWord.MatchString(line) && !strings.Contains(line, "UNVERIFIED:") {
			findings = append(findings, RecapContractFinding{Kind: RecapFindingNonstandardUnverifiedTag, Line: i})
		}
	}
	return findings
}
