// Package repoguards_test is the WITNESS for the commit guards in scripts/git-hooks.
//
// THE RULE THIS FILE PINS: the local agent guide (CLAUDE.local.md) carries ONE documentation block, that
// block names the ai_docs layout by the two git commands instead of drawing it, and the guide does not
// claim the retired index is live.
//
// WHY IT EXISTS, MEASURED 2026-10-17: the block listed 17 folders while the tree held 11
// (`git ls-tree --name-only HEAD:ai_docs`) - eight listed but absent, three present but unlisted. The same
// false claim was hand-corrected twice in one day (c2bf3b23, e18c560d), and a hand-copied tree drifts
// again; this test turns the next drift into a red build. The room's architect ruling,
// `RULING-docs-index-retire-or-regenerate.md` (2026-10-17), is the authority: the tracked tree IS the index,
// and the folder list must not be an enumeration that ages.
//
// THE PAIR IS GONE, MEASURED 2026-10-18: `53b95dee` pruned `.gemini/` (its changelog lists "27 command
// files and two notes"), so `.gemini/gemini.local.md` no longer exists and the copy-drift assertion had
// nothing left to compare - it failed on a missing file, not on drift. The surviving guide keeps the two
// content assertions; a second copy reintroduced later re-adds the pair test with it.
package repoguards_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// agentGuides is the surviving local agent guide. `.gemini/gemini.local.md` was the second copy until
// 53b95dee pruned `.gemini/`; the list stays a list so a reintroduced copy is one line away.
var agentGuides = []string{
	"CLAUDE.local.md",
}

// The block opens at this chapter heading and closes at the chapter separator that follows the rules table.
const (
	docsSectionStart = "### ai_docs/ Structure"
	docsSectionEnd   = "\n---\n"
)

// retiredIndexClaims are the exact sentences the 2026-10-17 retirement deleted. They are matched as
// strings, not as a regexp, so the wording that was removed is the wording the test refuses.
var retiredIndexClaims = []string{
	"├── index.json",                       // the hand-drawn tree entry
	"**index.json**",                       // the machine-readable-index bullet
	"Hooks update index.json",              // "automatic updates" while the hooks were live
	"Post-tool hook**: Updates index.json", // the post-tool hook's claim
	"via index",                            // quick lookup through a stored index
	"Auto-generated index",                 // the tree entry's and rules row's wording
}

// retirementNote is the one sentence allowed to name the file: it says the index is retired.
const retirementNote = "(`ai_docs/index.json`, 2026-10-17)"

// docsSection returns the guide's documentation chapter: the heading through the separator that ends it.
// A missing heading or separator is a failure, not an empty comparison - two empty strings are identical.
func docsSection(t *testing.T, path string) string {
	t.Helper()
	text := readGuide(t, path)
	start := strings.Index(text, docsSectionStart)
	if start < 0 {
		t.Fatalf("%s: no %q heading", path, docsSectionStart)
	}
	rest := text[start:]
	end := strings.Index(rest, docsSectionEnd)
	if end < 0 {
		t.Fatalf("%s: the docs chapter has no closing separator", path)
	}
	return rest[:end]
}

// readGuide reads one guide from the checkout the way a reviewer would: the file on disk.
func readGuide(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(filepath.Join(repoRoot(t), path))
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	return string(body)
}

// TestNoAgentGuideClaimsTheRetiredIndexIsLive pins the retirement's direction: the exact claims deleted on
// 2026-10-17 cannot come back, and the retirement note that names the file must be present instead.
func TestNoAgentGuideClaimsTheRetiredIndexIsLive(t *testing.T) {
	for _, path := range agentGuides {
		body := readGuide(t, path)
		for _, claim := range retiredIndexClaims {
			if strings.Contains(body, claim) {
				t.Errorf("%s still carries %q; the index is retired (2026-10-17) and the tracked tree is the index", path, claim)
			}
		}
		if !strings.Contains(body, retirementNote) {
			t.Errorf("%s cannot name the retirement: %q is missing", path, retirementNote)
		}
	}
}

// TestTheDocsChapterNamesTheLayoutCommands pins the replacement the ruling chose: two commands print the
// layout, and no guide draws the tree again - the enumeration is what drifted from 17 to 11.
func TestTheDocsChapterNamesTheLayoutCommands(t *testing.T) {
	for _, path := range agentGuides {
		section := docsSection(t, path)
		if !strings.Contains(section, "git ls-tree --name-only HEAD:ai_docs") {
			t.Errorf("%s: the docs chapter does not name `git ls-tree --name-only HEAD:ai_docs`", path)
		}
		if !strings.Contains(section, "git ls-files 'ai_docs/**/*.md'") {
			t.Errorf("%s: the docs chapter does not name `git ls-files 'ai_docs/**/*.md'`", path)
		}
		for _, draw := range []string{"├──", "└──"} {
			if strings.Contains(section, draw) {
				t.Errorf("%s: the docs chapter still draws a folder tree (%q); the commands are the layout", path, draw)
			}
		}
	}
}
