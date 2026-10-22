// Package repoguards_test is the WITNESS for the commit guards in scripts/git-hooks.
//
// THE RULE THIS FILE ENFORCES: a path a prune deleted has no live reference, and the prune's claim is a
// check rather than a sentence. testdata/pruned_paths.txt lists what a prune removed; this test asserts
// every entry is gone from the index and that no tracked file outside an explicit allowlist names it.
//
// WHY IT EXISTS, MEASURED 2026-10-18: 53b95dee pruned five legacy Python helpers, .gemini/,
// .automation/ and docker-system/.claude/, and its record claimed "git grep finds no live reference
// to a removed file outside the changelog and one historical doc line". Four live references survived that
// commit - internal/repoguards/agent_docs_block_test.go (which then failed on a missing file),
// ai_docs/core-architecture/agenthub-system-architecture.md:496, AGENTS.md:30 and
// ai_docs/agent-system/repo-agent-rules.md - so the sentence was false at the moment it was written and
// only a run would have said so.
//
// History of a removal lives in the commit that made it (`git log --diff-filter=D`), not in a file.
package repoguards_test

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// allowedLiveReferences names the files that may still name a pruned path, and why. The allowlist is
// exact files, never directories or prefixes: a whole directory on it would hide the next drift inside.
var allowedLiveReferences = map[string]string{
	// The document's own convention is a dated CORRECTED paragraph beside the stale clause; the
	// 2026-10-18 correction names the five helpers it recorded as deleted.
	"ai_docs/core-architecture/agenthub-system-architecture.md": "dated provenance corrections",
	// The guide guard's header records the measurement that retired its pair invariant.
	"agenthub_go/internal/repoguards/agent_docs_block_test.go": "the measurement that retired the pair",
	// The guard's own data and code must name what they scan for.
	"agenthub_go/internal/repoguards/pruned_paths_test.go":      "the guard itself",
	"agenthub_go/internal/repoguards/testdata/pruned_paths.txt": "the guard's data",
}

// TestAPrunedPathWasDeletedByACommit pins the listing's other end: every entry must be a path that
// existed in history and was deleted there. Without this a typo sits in the data file forever, matching
// nothing and guarding nothing - the list would look maintained while being blind.
func TestAPrunedPathWasDeletedByACommit(t *testing.T) {
	root := repoRoot(t)
	// A SHALLOW CLONE CANNOT ANSWER THIS, AND IT MUST SAY SO RATHER THAN ACCUSE THE LISTING. Measured
	// 2026-10-18 (CI run 39156598706): the go job checked out at depth 1, `git log --all` saw no deletion
	// commits, and all nine entries were reported as "a typo or a path that was never tracked" on a tree
	// whose own suite was green. The teeth stay: the guard still refuses, and the refusal names the clone
	// and the one flag that fixes it.
	if strings.TrimSpace(runGit(t, root, "rev-parse", "--is-shallow-repository")) == "true" {
		t.Fatalf("this checkout is a SHALLOW clone, so `git log --all` cannot see the deletion commits the listing is judged against - the entries below are not typos, the history is missing. Check out with full history (`actions/checkout` with `fetch-depth: 0`), then rerun.")
	}
	pruned := readPrunedPaths(t, filepath.Join(root, "agenthub_go", "internal", "repoguards", "testdata", "pruned_paths.txt"))
	if len(pruned) == 0 {
		t.Fatal("testdata/pruned_paths.txt lists nothing: an empty guard passes everything")
	}
	for _, path := range pruned {
		// --all, because a prune may land on a branch that is not an ancestor of this checkout.
		if strings.TrimSpace(runGit(t, root, "log", "--all", "--diff-filter=D", "--format=%H", "-1", "--", path)) == "" {
			t.Errorf("%s has no deletion commit in history: the entry is a typo or a path that was never tracked", path)
		}
	}
}

// TestAPrunedPathHasNoLiveReference walks prune's payload in both directions: a listed path that is
// still tracked is refused (the listing is stale, or the prune did not do its job), and a live
// reference outside the allowlist is refused (the prune left a dangling citation behind).
func TestAPrunedPathHasNoLiveReference(t *testing.T) {
	root := repoRoot(t)
	pruned := readPrunedPaths(t, filepath.Join(root, "agenthub_go", "internal", "repoguards", "testdata", "pruned_paths.txt"))
	if len(pruned) == 0 {
		t.Fatal("testdata/pruned_paths.txt lists nothing: an empty guard passes everything")
	}

	tracked := trackedFiles(t, root)
	for _, path := range pruned {
		if tracked[path] {
			t.Errorf("%s is still tracked: a pruned path that exists again means the list is stale or the prune did not land", path)
		}
	}

	for _, hit := range grepTracked(t, root, pruned) {
		if reason, ok := allowedLiveReferences[hit.file]; ok {
			_ = reason
			continue
		}
		t.Errorf("%s:%d names the pruned path %q; the prune removed it, so the line is a dangling citation (history belongs in the commit message)", hit.file, hit.line, hit.path)
	}
}

// prunedHit is one grep match: the file, the line number and which listed path it named.
type prunedHit struct {
	file string
	line int
	path string
}

// readPrunedPaths reads the listing, refusing a line that is not exactly one repository-relative path:
// a glob or a trailing comment would make the fixed-string scan search for something else.
func readPrunedPaths(t *testing.T, path string) []string {
	t.Helper()
	f, err := os.Open(path)
	if err != nil {
		t.Fatalf("open the pruned-path listing: %v", err)
	}
	defer f.Close()
	var paths []string
	scanner := bufio.NewScanner(f)
	for n := 1; scanner.Scan(); n++ {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.ContainsAny(line, "*?[ ") {
			t.Fatalf("%s:%d: %q is not a single exact path; the scan is a fixed-string grep", path, n, line)
		}
		paths = append(paths, line)
	}
	if err := scanner.Err(); err != nil {
		t.Fatalf("read the pruned-path listing: %v", err)
	}
	return paths
}

// trackedFiles returns the index as a set, so the listing can be checked in one pass.
func trackedFiles(t *testing.T, root string) map[string]bool {
	t.Helper()
	out := runGit(t, root, "ls-files", "-z")
	tracked := make(map[string]bool)
	for _, path := range strings.Split(out, "\x00") {
		if path != "" {
			tracked[path] = true
		}
	}
	return tracked
}

// grepTracked runs ONE fixed-string grep over the tracked tree with the listing as its pattern file,
// and returns every match.
//
// The listing is written to a scratch file WITHOUT its comments first: `git grep -f` takes every line
// as a pattern, so a `#` header would be searched for literally and match half the tree (measured: 6097
// hits and 30 seconds before the fix, two files and under two seconds after).
func grepTracked(t *testing.T, root string, pruned []string) []prunedHit {
	t.Helper()
	if len(pruned) == 0 {
		return nil
	}
	patterns := filepath.Join(t.TempDir(), "patterns.txt")
	if err := os.WriteFile(patterns, []byte(strings.Join(pruned, "\n")+"\n"), 0o600); err != nil {
		t.Fatalf("write the scratch pattern file: %v", err)
	}
	cmd := exec.Command("git", "--no-optional-locks", "grep", "-F", "-n", "-I", "-f", patterns, "--", ".")
	cmd.Dir = root
	out, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 1 {
			return nil // exit 1 is "no match", not a failure
		}
		t.Fatalf("git grep over the pruned paths: %v", err)
	}
	listed := make(map[string]bool, len(pruned))
	for _, p := range pruned {
		listed[p] = true
	}
	var hits []prunedHit
	for _, line := range strings.Split(string(out), "\n") {
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, ":", 3)
		if len(parts) != 3 {
			t.Fatalf("unreadable git grep line %q", line)
		}
		file, text := parts[0], parts[2]
		var number int
		if _, err := fmt.Sscanf(parts[1], "%d", &number); err != nil {
			t.Fatalf("unreadable line number in %q", line)
		}
		for _, p := range pruned {
			if listed[p] && strings.Contains(text, p) {
				hits = append(hits, prunedHit{file: file, line: number, path: p})
			}
		}
	}
	return hits
}

// runGit runs one git command in the checkout and returns its stdout.
func runGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", append([]string{"--no-optional-locks"}, args...)...)
	cmd.Dir = root
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("git %s: %v", strings.Join(args, " "), err)
	}
	return string(out)
}
