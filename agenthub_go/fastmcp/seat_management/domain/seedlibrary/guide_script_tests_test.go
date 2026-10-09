package seedlibrary

// The guide text every seat renders must name the script-test path that EXISTS, and must state that the
// exit code is read WITHOUT a pipe. Both are CONTENT assertions, and deliberately not digests:
// guides.lock.json already pins the pairing by sha256, and a digest agrees with itself while a wrong
// value stays locked in - it cannot tell a correct command from a confidently wrong one.
//
// The red is not hypothetical. The guide told every seat `cd agenthub_main && ... src/tests/scripts`
// after that tree had been emptied and then removed, so the command exited 5 ("no tests ran") and then
// 2 (`cd` fails); and a reviewer, piping it through `tail`, read a clean summary from a run that had
// failed, because a pipeline reports the LAST command's status. Each assertion below says which of
// those two stale classes it covers.
//
// The copies: the embedded shelf, the repo-side source under ai_docs/operations/seat-guides, and the txt
// sources under scripts/team/4genthub. They are byte-identical today (measured: sha256 equal for both
// pairs), so this file asserts IDENTITY rather than treating the mirror as an independent second opinion.

import (
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

const (
	// guideReviewerFile is the reviewer's block, which documents the same command in its checks list.
	guideReviewerFile = blocksDir + "/guide-reviewer.md"
	// How the command is spelled, and what the path argument must not be. The retired path is checked as
	// the exact string the guides used to carry, not as a bare "src/tests": the frontend suite lives under
	// a src/tests of its own, and that mention is correct.
	canonicalScriptTestCmd = "python3 -m pytest --noconftest -p no:cacheprovider"
	retiredScriptTestPath  = "src/tests/scripts"
	// The rule the command line cannot express on its own: a pipe would hide the very exit code a seat is
	// told to read. Wording is taken from the canonical statement in
	// ai_docs/core-architecture/agenthub-system-architecture.md (3.9): "Read the exit code WITHOUT a pipe".
	noPipeRule = "WITHOUT a pipe"
)

// readEmbeddedGuide returns one guide file's bytes from the embedded shelf, failing loudly on a path that
// does not exist - an empty read would make every assertion below pass for the wrong reason.
func readEmbeddedGuide(t *testing.T, name string) string {
	t.Helper()
	data, err := fs.ReadFile(embedded, name)
	if err != nil {
		t.Fatalf("read %s from the embedded shelf: %v", name, err)
	}
	return string(data)
}

// repoRoot walks up from this test file to the directory that holds the agenthub_go module, the same
// shape FindProjectRoot resolves: a component named agenthub_go, and the root is its parent.
func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller could not resolve this test file: the repo-relative checks cannot be made")
	}
	dir := filepath.Dir(file)
	for {
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatalf("walked to %s without finding a directory named agenthub_go above %s", dir, file)
		}
		if filepath.Base(dir) == "agenthub_go" {
			return parent
		}
		dir = parent
	}
}

// documentedPath extracts the path argument out of the documented command, so the existence check below
// follows the TEXT rather than a constant that could drift from it.
func documentedPath(t *testing.T, text, where string) string {
	t.Helper()
	index := strings.Index(text, canonicalScriptTestCmd)
	if index < 0 {
		t.Fatalf("%s does not document %q at all", where, canonicalScriptTestCmd)
	}
	rest := text[index+len(canonicalScriptTestCmd):]
	fields := strings.Fields(rest)
	if len(fields) < 2 || !strings.HasPrefix(fields[1], "-q") {
		sample := rest
		if len(sample) > 80 {
			sample = sample[:80]
		}
		t.Fatalf("%s documents the command without the `-q` the canonical form ends with: %q", where, sample)
	}
	return fields[0]
}

// A: the path the guide names is the one that EXISTS, checked against git rather than the filesystem, so a
// directory left behind with no tracked test in it cannot keep the guide green.
func TestGuidesNameTheScriptTestPathThatExists(t *testing.T) {
	root := repoRoot(t)
	for _, file := range []string{guideCommonFile, guideReviewerFile} {
		text := readEmbeddedGuide(t, file)

		// (a) the stale-path class: the command it documents, and the path out of that command.
		path := documentedPath(t, text, file)
		cmd := exec.Command("git", "--no-optional-locks", "ls-files", "--", path)
		cmd.Dir = root // the pathspec is repo-relative; the test's own cwd is the package directory
		listed, err := cmd.Output()
		if err != nil {
			t.Fatalf("git ls-files -- %s in %s: %v", path, root, err)
		}
		if len(strings.Fields(string(listed))) == 0 {
			t.Errorf("%s documents `%s`, and git tracks NOTHING there: a documented command that runs zero tests reads as a pass", file, path)
		}
		// (a) the same class, from the other side: the retired path must not come back in the command.
		if strings.Contains(text, retiredScriptTestPath) {
			t.Errorf("%s names %q again; that form is unrunnable since the move to scripts/tests", file, retiredScriptTestPath)
		}
	}
}

// B: the no-pipe rule is stated beside the command. The guide already explains why `--noconftest` matters;
// this is the other half, and it is the one a reviewer was bitten by tonight - a pipe reports the LAST
// command's status, so `... | tail` reads 0 whatever pytest said.
func TestGuidesStateTheNoPipeRuleBesideTheCommand(t *testing.T) {
	text := readEmbeddedGuide(t, guideCommonFile)
	if !strings.Contains(text, noPipeRule) {
		t.Errorf(
			"%s documents the script-test command without stating %q: a seat may pipe the run, and a pipeline reports the LAST command's status, so the failure reads as a clean summary",
			guideCommonFile, noPipeRule,
		)
	}
}

// C: the two copies of the guide text cannot diverge, and the txt sources carry the command too. The mirror
// is DUPLICATIVE today, not independent - both pairs are byte-identical - so identity is the assertion, and
// a divergence is the finding rather than a licence.
func TestGuideCopiesCannotDivergeAndTheTxtSourcesCarryTheCommand(t *testing.T) {
	root := repoRoot(t)
	pairs := []struct{ source, embedded string }{
		{"ai_docs/operations/seat-guides/_common.md", guideCommonFile},
		{"ai_docs/operations/seat-guides/reviewer.md", guideReviewerFile},
	}
	for _, pair := range pairs {
		source := filepath.Join(root, filepath.FromSlash(pair.source))
		data, err := os.ReadFile(source)
		if err != nil {
			t.Errorf("read the publish source %s: %v", pair.source, err)
			continue
		}
		if string(data) != readEmbeddedGuide(t, pair.embedded) {
			t.Errorf("%s and the embedded %s have diverged; the shelf is copied from the source, so one of them is stale", pair.source, pair.embedded)
		}
	}
	for _, txt := range []string{
		"scripts/team/4genthub/area-quality.txt",
		"scripts/team/4genthub/project-4genthub.txt",
	} {
		data, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(txt)))
		if err != nil {
			t.Errorf("read %s: %v", txt, err)
			continue
		}
		text := string(data)
		if !strings.Contains(text, canonicalScriptTestCmd) {
			t.Errorf("%s does not carry the canonical script-test command; the txt sources are publish sources too", txt)
		}
		if strings.Contains(text, retiredScriptTestPath) {
			t.Errorf("%s still names %q", txt, retiredScriptTestPath)
		}
	}
}
