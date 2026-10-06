package seedlibrary

// A block file's provenance: COMPUTED for the library side, RECORDED for the migration side.
//
// Packet 6's provenance question, in the form that actually covers the window it was written for.
//
// The library side needs nothing stored: for a library block the module version's own checksum IS
// the digest of the file, because an instruction block is the guide text itself and never an
// envelope around it. So the table below computes path and digest from the bytes the binary holds.
//
// The MIGRATION side needs one recorded thing, and guides.lock.json is it: while both copies exist -
// the library's and the interim files under ai_docs/operations/seat-guides/ - nothing compares them,
// so a hand-edit to a source file is invisible by construction. The lock records the pairing taken
// at copy time (library path and digest, source path and digest), which is what makes that window
// checkable; after the deletion a missing source is the STEADY STATE and is reported as such rather
// than as a failure.
//
// A block whose bytes disagree with its lock entry is REFUSED at load, not merely reported later: a
// stale pairing would make the drift check lie, which is worse than having no check.

import (
	"crypto/sha256"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

// libraryRootPrefix is this package's directory relative to the repository root. Block paths are
// recorded against the REPOSITORY root, not the module root, because that is the base the skill
// blocks' source_path uses and the base a drift check resolves from - the same reason
// sharedModuleFiles spells `agenthub_go/` out in full.
const libraryRootPrefix = "agenthub_go/fastmcp/seat_management/domain/seedlibrary/"

// BlockProvenance is one block file's identity inside the library, plus - for a block copied out of
// a file that still exists - where it was copied from.
type BlockProvenance struct {
	Slug   string
	Kind   resolver.ModuleKind
	Path   string // repository-relative path of the library file
	SHA256 string // sha256 of the bytes the library carries
	Bytes  int
	// SourcePath and SourceSHA256 are empty for a block authored in-tree; they are set for the
	// blocks still living as a copy of an interim file, which is the migration case.
	SourcePath   string
	SourceSHA256 string
}

//go:embed guides.lock.json
var guideLockJSON []byte

type guideLockEntry struct {
	Slug         string `json:"slug"`
	Path         string `json:"path"`
	SHA256       string `json:"sha256"`
	SourcePath   string `json:"source_path"`
	SourceSHA256 string `json:"source_sha256"`
}

func loadGuideLock() (map[string]guideLockEntry, error) { return parseGuideLock(guideLockJSON) }

// sha256HexRe is the one digest rule this file states, the same lowercase-hex form the skill blocks
// record. It lives in the production file because the parser validates against it, not the test.
var sha256HexRe = regexp.MustCompile(`^[0-9a-f]{64}$`)

// parseGuideLock reads the recorded pairing. It takes bytes rather than reading the embedded file so
// the refusals below can be driven with hostile input - the discipline that caught this file's panic,
// where an untested error path crashed precisely when it was asked to refuse.
func parseGuideLock(data []byte) (map[string]guideLockEntry, error) {
	var doc struct {
		Guides []guideLockEntry `json:"guides"`
	}
	if err := json.Unmarshal(data, &doc); err != nil {
		return nil, fmt.Errorf("guides.lock.json: %w", err)
	}
	if len(doc.Guides) == 0 {
		return nil, errors.New("guides.lock.json: no guides recorded")
	}
	out := make(map[string]guideLockEntry, len(doc.Guides))
	for i, e := range doc.Guides {
		if e.Slug == "" || e.Path == "" || e.SHA256 == "" || e.SourcePath == "" || e.SourceSHA256 == "" {
			return nil, fmt.Errorf("guides.lock.json: guides[%d] must state slug, path, sha256, source_path and source_sha256", i)
		}
		// A record whose digest is not a digest would never match, so the shelf would be refused with
		// a message about bytes nobody recorded: refuse the RECORD here instead, where the writer
		// still learns which field is wrong.
		for _, f := range []struct{ name, value string }{{"sha256", e.SHA256}, {"source_sha256", e.SourceSHA256}} {
			if !sha256HexRe.MatchString(f.value) {
				return nil, fmt.Errorf("guides.lock.json: guides[%d].%s = %q, want 64 lowercase hex", i, f.name, f.value)
			}
		}
		for _, f := range []struct{ name, value string }{{"path", e.Path}, {"source_path", e.SourcePath}} {
			if path.IsAbs(f.value) {
				return nil, fmt.Errorf("guides.lock.json: guides[%d].%s must be relative to a root, got %q", i, f.name, f.value)
			}
		}
		if _, dup := out[e.Slug]; dup {
			return nil, fmt.Errorf("guides.lock.json: %s appears twice", e.Slug)
		}
		out[e.Slug] = e
	}
	return out, nil
}

// verifyGuideLocks refuses a shelf whose bytes disagree with the pairing recorded for them, and a
// lock that names a block the shelf does not carry. Both are the same failure: the check would
// otherwise compare against a pairing that is already wrong.
func verifyGuideLocks(digests map[string]string) error {
	lock, err := loadGuideLock()
	if err != nil {
		return err
	}
	for slug, entry := range lock {
		got, ok := digests[slug]
		if !ok {
			return fmt.Errorf("guides.lock.json names %s, which the shelf does not carry", slug)
		}
		if got != entry.SHA256 {
			// short(), never got[:12]: a caller handing a value that is not a digest must get a
			// refusal, not a panic. Found by a test that hands one in - the assertion caught a crash
			// rather than the message it expected, which is what a bounded slice on untrusted input
			// does.
			return fmt.Errorf("%s: the shelf carries %s but guides.lock.json records %s; re-copy the block and re-record the pairing", slug, short(got), short(entry.SHA256))
		}
	}
	return nil
}

// VerifyGuidePairing checks the shelf the BINARY carries against guides.lock.json. Load calls it, so
// a stale pairing cannot reach a seat; LoadFS deliberately does not, because it loads whatever
// filesystem a caller hands it and the lock is a fact about the shipped library, not about a
// synthetic shelf a test builds.
func VerifyGuidePairing() error {
	digests := map[string]string{}
	for _, dir := range []string{blocksDir, sharedModulesDir} {
		names, err := fs.Glob(embedded, dir+"/*")
		if err != nil {
			return err
		}
		for _, name := range names {
			data, err := fs.ReadFile(embedded, name)
			if err != nil {
				return err
			}
			sum := sha256.Sum256(data)
			digests[strings.TrimSuffix(path.Base(name), path.Ext(name))] = hex.EncodeToString(sum[:])
		}
	}
	return verifyGuideLocks(digests)
}

// kindOfBlockFile is the ONE place that maps a block file's extension to its kind. loadBlocks and
// BlockProvenanceTable both need it, and a rule stated twice is a rule that can drift - the table
// would then vouch for a shelf the loader no longer builds, which is the silent divergence this
// whole file exists to make loud.
func kindOfBlockFile(name string) (resolver.ModuleKind, error) {
	switch ext := path.Ext(name); ext {
	case ".json":
		return resolver.KindMCP, nil
	case ".md":
		return resolver.KindInstruction, nil
	default:
		return "", fmt.Errorf("%s: a block file is .json (mcp) or .md (instruction), got %q", name, ext)
	}
}

// BlockProvenanceTable returns one entry per file the shelf carries, sorted by slug: every
// blocks/* file and every file sharedModuleFiles names, because both are library content that
// reaches a seat. Digests are computed from the embedded bytes, so the table cannot disagree with
// what the binary holds; the lock supplies the migration pairing where one exists.
func BlockProvenanceTable() ([]BlockProvenance, error) {
	lock, err := loadGuideLock()
	if err != nil {
		return nil, err
	}
	out := make([]BlockProvenance, 0, 20)

	names, err := fs.Glob(embedded, blocksDir+"/*")
	if err != nil {
		return nil, err
	}
	for _, name := range names {
		kind, err := kindOfBlockFile(name)
		if err != nil {
			// loadBlocks refuses this file; the table must not quietly omit what the loader cannot
			// name, or a drift check built on it would report on a library it never fully saw.
			return nil, err
		}
		entry, err := provenanceOf(name, strings.TrimSuffix(path.Base(name), path.Ext(name)), kind)
		if err != nil {
			return nil, err
		}
		out = append(out, entry)
	}

	// The shared modules' kinds come from the table that mounts them, not from the extension: a
	// shared `.json` file is a tool module, so the extension would name it wrongly.
	for _, f := range sharedModuleFiles {
		entry, err := provenanceOf(sharedModulesDir+"/"+f.file, f.slug, f.kind)
		if err != nil {
			return nil, err
		}
		out = append(out, entry)
	}

	for i := range out {
		if e, ok := lock[out[i].Slug]; ok {
			out[i].SourcePath = e.SourcePath
			out[i].SourceSHA256 = e.SourceSHA256
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Slug < out[j].Slug })
	return out, nil
}

func provenanceOf(name, slug string, kind resolver.ModuleKind) (BlockProvenance, error) {
	data, err := fs.ReadFile(embedded, name)
	if err != nil {
		return BlockProvenance{}, err
	}
	sum := sha256.Sum256(data)
	return BlockProvenance{
		Slug:   slug,
		Kind:   kind,
		Path:   libraryRootPrefix + name,
		SHA256: hex.EncodeToString(sum[:]),
		Bytes:  len(data),
	}, nil
}

// BlockDivergence is one file that disagrees with what the library records for it.
type BlockDivergence struct {
	Slug    string
	Path    string
	Problem string // differs | missing | source-differs | source-gone
	Want    string
	Got     string
}

func (d BlockDivergence) String() string {
	switch d.Problem {
	case "missing":
		return fmt.Sprintf("%s: %s is missing; the library carries %s", d.Slug, d.Path, short(d.Want))
	case "source-gone":
		return fmt.Sprintf("%s: %s is gone; the library copy is the only one left (expected after the migration)", d.Slug, d.Path)
	default:
		return fmt.Sprintf("%s: %s %s; recorded %s, found %s", d.Slug, d.Path, d.Problem, short(d.Want), short(d.Got))
	}
}

func short(digest string) string {
	if len(digest) < 12 {
		return digest
	}
	return digest[:12]
}

// CheckBlockDrift recomputes every recorded digest under root and returns one divergence per file
// that does not match, sorted by slug then problem. It reports BOTH sides of the migration: a
// library block whose file differs from the bytes the binary carries, and - for a block copied out
// of an interim file - that source file differing from the pairing recorded for it.
//
// An absent library file is a divergence rather than a pass, because absence is how a block leaves
// a tree without anybody noticing. An absent SOURCE is different and is reported as source-gone:
// after the migration deletes them, that is the intended state, not a failure.
//
// A root that does not hold the library at all is an error, so a caller cannot read a wrong root as
// everything in step.
//
// ONE BOUND, STATED WHERE THE NEXT READER MEETS IT: the library-side comparison above is only
// meaningful when root is NOT the tree this binary was built from. Pointed at its own build tree it
// compares the embedded bytes against the very files they were embedded from, so an edit that
// triggers a rebuild moves both sides together and the check reports nothing - a check comparing a
// thing to its own shadow. Its real use is a deployed binary against a tree it was not built from.
// The migration pairing is anchored OUTSIDE that shadow, which is what guides.lock.json is for: a
// check on a migration has to be anchored outside the migration.
func CheckBlockDrift(root string) ([]BlockDivergence, error) {
	table, err := BlockProvenanceTable()
	if err != nil {
		return nil, err
	}
	if len(table) == 0 {
		return nil, errors.New("the library carries no blocks")
	}
	first := filepath.Dir(filepath.Join(root, filepath.FromSlash(table[0].Path)))
	if _, err := os.Stat(first); err != nil {
		return nil, fmt.Errorf("%s does not hold the library (looked for %s): %w", root, table[0].Path, err)
	}

	var out []BlockDivergence
	for _, e := range table {
		got, problem, err := digestOf(filepath.Join(root, filepath.FromSlash(e.Path)))
		if err != nil {
			return nil, err
		}
		if problem != "" {
			out = append(out, BlockDivergence{Slug: e.Slug, Path: e.Path, Problem: problem, Want: e.SHA256})
		} else if got != e.SHA256 {
			out = append(out, BlockDivergence{Slug: e.Slug, Path: e.Path, Problem: "differs", Want: e.SHA256, Got: got})
		}

		if e.SourcePath == "" {
			continue
		}
		src, problem, err := digestOf(filepath.Join(root, filepath.FromSlash(e.SourcePath)))
		if err != nil {
			return nil, err
		}
		switch {
		case problem == "missing":
			out = append(out, BlockDivergence{Slug: e.Slug, Path: e.SourcePath, Problem: "source-gone"})
		case src != e.SourceSHA256:
			out = append(out, BlockDivergence{Slug: e.Slug, Path: e.SourcePath, Problem: "source-differs", Want: e.SourceSHA256, Got: src})
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Slug != out[j].Slug {
			return out[i].Slug < out[j].Slug
		}
		return out[i].Problem < out[j].Problem
	})
	return out, nil
}

// digestOf returns the file's sha256, or "missing" as a problem rather than an error: an absent
// file is a reportable state here, and only an unreadable one is a genuine error.
func digestOf(file string) (string, string, error) {
	data, err := os.ReadFile(file)
	switch {
	case os.IsNotExist(err):
		return "", "missing", nil
	case err != nil:
		return "", "", err
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), "", nil
}
