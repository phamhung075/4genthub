package seedlibrary

// The seat instructions must carry the CURRENT commit form. The fleet commits with
// `git commit -m "..." -- <paths>` and NO prior `git add`, because the index is shared: a staged
// line can be taken by another seat's commit. A new file is the one exception - `git add -N`
// records an empty blob (e69de29b) so the pathspec commit has something to name without putting
// content in the index. The library's guide-common is the text every seat renders, so it is held
// to that form here, and the pairing check is proven to still refuse a guide that outruns the
// lock rather than being bypassed.

import (
	"io/fs"
	"strings"
	"testing"
)

// guideCommonFile is the embedded shared module every seat type carries: the working procedure a
// seat renders into its own guidance. It is a sharedModulesDir file (see sharedModuleFiles), not a
// blocks/ one, which is why the path is spelled out rather than derived from a slug.
const guideCommonFile = "shared-modules/guide-common.md"

// The rule the new form adds, and the prescription the old form was written as. `oldCommitForm`
// keeps the backticks so it matches the prescription itself rather than any bare mention of the
// command: the guide may still name `git add` for the new-file exception.
const (
	newCommitRule = "do not stage first"
	oldCommitForm = "`git add -- <path>` then"
)

func TestGuideCommonPrescribesTheCurrentCommitForm(t *testing.T) {
	data, err := fs.ReadFile(embedded, guideCommonFile)
	if err != nil {
		t.Fatalf("read %s: %v", guideCommonFile, err)
	}
	text := string(data)

	// A1: the new form's rule is present, so a seat is told not to stage before committing.
	if !strings.Contains(text, newCommitRule) {
		t.Errorf("%s does not say %q; the seats would still stage before committing", guideCommonFile, newCommitRule)
	}
	// A2: the OLD prescription is gone. The shared index is the reason: a staged line can be taken
	// by another seat's commit, so the guide must not tell a seat to run `git add` and then commit.
	if strings.Contains(text, oldCommitForm) {
		t.Errorf("%s still prescribes the old form (%q): the index is shared, so a staged path can be taken by another seat's commit", guideCommonFile, oldCommitForm)
	}
}

// A3 is the negative control: the pairing check is not bypassed. It starts from the shipped shelf
// agreeing with guides.lock.json, then moves guide-common's digest under the lock's OLD record -
// exactly the state the guide text will be in once the commit-form change lands before the lock is
// re-recorded - and requires the same checker VerifyGuidePairing runs to REFUSE, naming the block
// and the recorded digest. The embedded bytes cannot be mutated from a test, so the moved digest is
// the value the checker is handed; the control's first assertion pins that this is the ONLY
// difference from a pairing that passes.
func TestGuidePairingRefusesTheGuideChangedUnderTheOldLock(t *testing.T) {
	if err := VerifyGuidePairing(); err != nil {
		t.Fatalf("the shipped shelf disagrees with its own lock: %v", err)
	}

	lock, err := loadGuideLock()
	if err != nil {
		t.Fatalf("loadGuideLock: %v", err)
	}
	old, ok := lock["guide-common"]
	if !ok {
		t.Fatal("guides.lock.json records no guide-common pairing")
	}

	// The shelf's digests, built the way VerifyGuidePairing builds them, so the mutation below is
	// the only difference from the pairing the first assertion accepted.
	table, err := BlockProvenanceTable()
	if err != nil {
		t.Fatalf("BlockProvenanceTable: %v", err)
	}
	digests := map[string]string{}
	for _, e := range table {
		digests[e.Slug] = e.SHA256
	}
	if digests["guide-common"] != old.SHA256 {
		t.Fatalf("guide-common: the shelf carries %s but the lock records %s; the two must agree before the control moves one of them", short(digests["guide-common"]), short(old.SHA256))
	}

	// guide-common's bytes change (the new commit form) while the lock still records the OLD digest.
	digests["guide-common"] = sha256Hex([]byte("the seat guide, after the commit-form change\n"))
	if digests["guide-common"] == old.SHA256 {
		t.Fatal("test construction: the changed digest equals the recorded one")
	}

	err = verifyGuideLocks(digests)
	if err == nil {
		t.Fatal("verifyGuideLocks accepted a guide whose bytes moved under the lock's old record: the pairing check is bypassed")
	}
	if !strings.Contains(err.Error(), "guide-common") {
		t.Fatalf("refusal does not name the block whose bytes moved: %v", err)
	}
	if !strings.Contains(err.Error(), short(old.SHA256)) {
		t.Fatalf("refusal does not name the recorded (old) digest %s: %v", short(old.SHA256), err)
	}
	t.Logf("guide-common: the changed guide is refused against the old record %s: %v", old.SHA256, err)
}
