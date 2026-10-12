package seedlibrary

import (
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io/fs"
	"os"
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/seedmap"
)

// seedContentLockPath is the record this file owns and the only place the pairing is written
// down: which content set a seedVersion names. seedmap stamps each seed's version onto every
// module it builds, and a stored seat type version is immutable - so two different content sets
// under one version is not a style question, it is the conflict the version exists to prevent.
//
// It has happened twice, under two labels: a3eb0762 changed guide-common.md under 1.4.1, and
// 39105865 changed blocks/guide-fe-dev.md and blocks/guide-reviewer.md (and re-stamped
// guides.lock.json) under 1.4.2, 3h16m after the bump. guides.lock.json cannot catch that: it
// records where a block was copied FROM, and the same commit that moved the content re-stamps
// it, so it stays green through precisely the drift it should notice.
const seedContentLockPath = "seedcontent.lock.json"

//go:embed seedcontent.lock.json
var seedContentLockJSON []byte

// updateSeedContentLock appends the library as it stands to seedcontent.lock.json. It does NOT
// overwrite: a version already recorded with a different content set is refused, because
// re-stamping is the violation rather than the repair.
var updateSeedContentLock = flag.Bool("update-seedcontent-lock", false,
	"append the library's current content set as the one this seedVersion names")

const seedContentLockWhat = "The content set each seedVersion names, APPEND-ONLY. seedVersion is stamped onto " +
	"every seed module, and a stored seat type version is immutable, so (module, version) must resolve to ONE " +
	"content set forever. Adding a record is the whole of an intentional content change: raise seedVersion in " +
	"domain/seedmap/seedmap.go and run this package's tests with -update-seedcontent-lock. Editing a recorded " +
	"set, or adding a record under a version that already has one, is the drift this file exists to refuse. " +
	"SeedVersion 1.4.2 has no record here on purpose: it named TWO sets (a3eb0762's guide-common under 1.4.1's " +
	"successor, then 39105865's blocks), and recording either one would write down a claim that is false."

type seedContentLock struct {
	What     string              `json:"_what"`
	Versions []seedContentRecord `json:"versions"`
}

type seedContentRecord struct {
	SeedVersion   string            `json:"seed_version"`
	ContentSHA256 string            `json:"content_sha256"`
	Files         map[string]string `json:"files"`
}

// seededDirs are the three sources a seed is built from - the same three the package embeds.
var seededDirs = []string{seatTypesDir, sharedModulesDir, blocksDir}

// libraryContent hashes every file a seed can be built from, keyed by its path in the embedded
// library. Nothing outside these directories reaches a seed, so the map IS the content set.
func libraryContent(t *testing.T) map[string]string {
	t.Helper()
	files := map[string]string{}
	for _, dir := range seededDirs {
		err := fs.WalkDir(embedded, dir, func(name string, entry fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if entry.IsDir() {
				return nil
			}
			data, err := embedded.ReadFile(name)
			if err != nil {
				return err
			}
			sum := sha256.Sum256(data)
			files[name] = hex.EncodeToString(sum[:])
			return nil
		})
		if err != nil {
			t.Fatalf("reading %s from the library: %v", dir, err)
		}
	}
	if len(files) == 0 {
		t.Fatal("the embedded library is empty, so this guard would measure nothing")
	}
	return files
}

// contentSetSHA256 folds a file map into one digest, over sorted paths so the value depends on
// the content and not on map order.
func contentSetSHA256(files map[string]string) string {
	names := make([]string, 0, len(files))
	for name := range files {
		names = append(names, name)
	}
	sort.Strings(names)
	sum := sha256.New()
	for _, name := range names {
		fmt.Fprintf(sum, "%s\x00%s\x00", name, files[name])
	}
	return hex.EncodeToString(sum.Sum(nil))
}

// seededVersion reads the version a seed actually carries, through the package's own builder
// rather than a second copy of the constant: if FromSpec stops stamping seedVersion, this guard
// would be measuring a number nothing uses, so it goes through the seeder's real path.
func seededVersion(t *testing.T) string {
	t.Helper()
	probe, err := seedmap.FromSpec(seedmap.Spec{
		Slug:           "content-lock-probe",
		Name:           "Content lock probe",
		Description:    "probe seat type the guard builds to read the version a seed carries",
		DefaultRuntime: "codex",
		Role:           "probe",
		OutputFormat:   "probe",
	})
	if err != nil {
		t.Fatalf("building the probe seed to read the stamped version: %v", err)
	}
	return probe.Version
}

// contentSetDiff names every way the current library differs from a recorded set.
func contentSetDiff(recorded, current map[string]string) []string {
	var diff []string
	for name, want := range recorded {
		got, ok := current[name]
		switch {
		case !ok:
			diff = append(diff, name+" is recorded but no longer in the library")
		case got != want:
			diff = append(diff, name+" changed")
		}
	}
	for name := range current {
		if _, ok := recorded[name]; !ok {
			diff = append(diff, name+" is in the library but not in the record")
		}
	}
	sort.Strings(diff)
	return diff
}

func parseSeedContentLock(t *testing.T) seedContentLock {
	t.Helper()
	var lock seedContentLock
	if err := json.Unmarshal(seedContentLockJSON, &lock); err != nil {
		t.Fatalf("%s does not parse: %v", seedContentLockPath, err)
	}
	return lock
}

// TestSeedVersionNamesOneContentSet fails when the library changes without the seedVersion
// moving, and equally when the version moves without the new set being recorded. Either repair
// is one commit: the content, the version and this record together.
func TestSeedVersionNamesOneContentSet(t *testing.T) {
	current := libraryContent(t)
	version := seededVersion(t)
	digest := contentSetSHA256(current)

	lock := parseSeedContentLock(t)

	// The record is append-only, and a version that appears twice with two content sets is the
	// violation itself, so each record is checked against its own digest as well as the map.
	recorded := map[string]seedContentRecord{}
	for _, record := range lock.Versions {
		if previous, ok := recorded[record.SeedVersion]; ok {
			if previous.ContentSHA256 != record.ContentSHA256 {
				t.Errorf("seedVersion %s is recorded twice with DIFFERENT content sets (%s and %s): a stored seat type "+
					"version is immutable, so the second record must go under a raised seedVersion instead",
					record.SeedVersion, short(previous.ContentSHA256), short(record.ContentSHA256))
			}
			continue
		}
		if want := contentSetSHA256(record.Files); want != record.ContentSHA256 {
			t.Errorf("seedVersion %s records content_sha256 %s, which its own files map does not reproduce (%s): "+
				"the record is internally inconsistent, so it cannot testify to anything",
				record.SeedVersion, short(record.ContentSHA256), short(want))
		}
		recorded[record.SeedVersion] = record
	}

	if *updateSeedContentLock {
		if record, ok := recorded[version]; ok {
			if diff := contentSetDiff(record.Files, current); len(diff) > 0 {
				t.Fatalf("REFUSING to re-record seedVersion %s: it already names a different content set (%s). "+
					"Re-stamping is the drift, not the repair - raise seedVersion in domain/seedmap/seedmap.go:14 "+
					"and record the new version instead.", version, strings.Join(diff, "; "))
			}
			t.Logf("seedVersion %s is already recorded, and the library matches it: nothing to write", version)
			return
		}
		lock.What = seedContentLockWhat
		lock.Versions = append(lock.Versions, seedContentRecord{
			SeedVersion:   version,
			ContentSHA256: digest,
			Files:         current,
		})
		out, err := json.MarshalIndent(lock, "", "  ")
		if err != nil {
			t.Fatalf("encoding %s: %v", seedContentLockPath, err)
		}
		if err := os.WriteFile(seedContentLockPath, append(out, '\n'), 0o644); err != nil {
			t.Fatalf("writing %s: %v", seedContentLockPath, err)
		}
		t.Logf("recorded seedVersion %s with %d files, content_sha256 %s", version, len(current), short(digest))
		return
	}

	record, ok := recorded[version]
	if !ok {
		t.Fatalf("seedVersion %s names no content set in %s. Either the library moved and the version did not "+
			"(the drift this guard exists for), or the version moved and its set was never recorded. Both repairs "+
			"are the same commit: the content, the seedVersion in domain/seedmap/seedmap.go:14, and this record. "+
			"Record it with: go test ./fastmcp/seat_management/domain/seedlibrary/ "+
			"-run TestSeedVersionNamesOneContentSet -args -update-seedcontent-lock", version, seedContentLockPath)
	}
	if diff := contentSetDiff(record.Files, current); len(diff) > 0 {
		t.Fatalf("seedVersion %s already names a different content set, so (module, %s) resolves to two of them:\n  %s\n"+
			"a stored seat type version is immutable and the seeder refuses to overwrite one. If this change is "+
			"intended, raise seedVersion in domain/seedmap/seedmap.go:14, then record the new version with: go test "+
			"./fastmcp/seat_management/domain/seedlibrary/ -run TestSeedVersionNamesOneContentSet "+
			"-args -update-seedcontent-lock", version, version, strings.Join(diff, "\n  "))
	}
	if want := lock.Versions[len(lock.Versions)-1].SeedVersion; want != version {
		t.Fatalf("the newest recorded content set is seedVersion %s while the seeder stamps %s: the library's own "+
			"history has not been carried forward", want, version)
	}
}

// The embedded FS is read through the package's own `embedded` variable in libraryContent, so
// this assertion keeps that variable from being swapped for another library by accident.
var _ embed.FS = embedded
