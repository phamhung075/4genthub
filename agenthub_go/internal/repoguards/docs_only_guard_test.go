// Package repoguards_test is the WITNESS for the commit guards in scripts/git-hooks.
//
// THE RULE THIS FILE PINS: docs, CHANGELOG and TEST-CHANGELOG change ONCE, in the code commit of a finished
// task. `docs-only-guard` refuses a seat's commit whose ARGUMENTS are all documentation, exempts the owner's
// host and the owner's one-commit flag, and passes when any argument is outside the doc globs.
//
// WHY IT EXISTS, MEASURED 2026-10-17: the rule is what makes a docs bundle need a carrier, and the guard had
// no test at all (`scripts/git-hooks/docs-only-guard` has one commit ever). The carrier that could not land
// sent the room through three wrong answers in one hour - a pin "carries" nothing because pre-commit's
// `types: [file]` drops the gitlink before the guard sees it, and a commit with five docs plus a test file is
// refused at default batching because the FRAMEWORK partitions the hook's files and calls it once per batch.
// The partition is pre-commit's (measured at `pre_commit/xargs.py`), so the cases here pin the SCRIPT's own
// argv contract, which is the half a repository test can hold; addendum 5 of
// `RULING-doc-bundle-carrier-order.md` carries the framework table.
//
// THE SCRIPT IS RUN AS IT SHIPS (`sh scripts/git-hooks/docs-only-guard <paths>`), not re-implemented here.
package repoguards_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// docsOnlyGuardArgs is the parked bundle's five doc paths, spelled as the carrier commit hands them over:
// `TEST-CHANGELOG.md` is deliberately absent, because it is owned by the lanes whose sections it holds.
var docsOnlyGuardArgs = []string{
	"AGENTS.md",
	"ai_docs/core-architecture/seat-skills.md",
	"ai_docs/agent-system/task-workflow-and-reporting.md",
	"CHANGELOG/2026-10-17--agents-section-2-states-the-measured-seat-context.md",
	"CHANGELOG/2026-10-16--the-criteria-vocabulary-a-seat-can-settle.md",
}

// runDocsOnlyGuard runs the shipped guard with the given staged paths and environment, and returns its exit
// code and stderr. The environment is built from scratch, like the trailer guard's harness: an inherited
// OWNER_DOCS_COMMIT would silently exempt every case.
func runDocsOnlyGuard(t *testing.T, paths []string, env map[string]string) (int, string) {
	t.Helper()
	dir := t.TempDir()
	script := filepath.Join(repoRoot(t), "scripts", "git-hooks", "docs-only-guard")
	cmd := exec.Command("sh", append([]string{script}, paths...)...)
	cmd.Dir = dir
	cmd.Env = []string{"PATH=" + os.Getenv("PATH"), "HOME=" + dir}
	for k, v := range env {
		cmd.Env = append(cmd.Env, k+"="+v)
	}
	var stderr strings.Builder
	cmd.Stderr = &stderr
	err := cmd.Run()
	code := 0
	if exitErr, ok := err.(*exec.ExitError); ok {
		code = exitErr.ExitCode()
	} else if err != nil {
		t.Fatalf("run the guard: %v", err)
	}
	return code, stderr.String()
}

// TestASeatsAllDocCommitIsRefusedAndAMixedOnePasses pins the decision the whole carrier order rests on: the
// guard judges its OWN argument list, so the same five docs are refused alone and pass beside one non-doc
// file. The refusal must name the rule, because the message is the instruction a seat reads.
func TestASeatsAllDocCommitIsRefusedAndAMixedOnePasses(t *testing.T) {
	seat := map[string]string{"AGENTHUB_SESSION_NAME": "agenthub--room--seat"}
	t.Run("the bundle alone is refused", func(t *testing.T) {
		code, stderr := runDocsOnlyGuard(t, docsOnlyGuardArgs, seat)
		if code != 1 {
			t.Fatalf("exit %d, want 1 (stderr %q)", code, stderr)
		}
		if !strings.Contains(stderr, "docs-only commit refused") {
			t.Fatalf("stderr %q does not name the refusal", stderr)
		}
	})
	t.Run("the same docs with a test file pass", func(t *testing.T) {
		mixed := append(append([]string{}, docsOnlyGuardArgs...),
			"agenthub_go/internal/repoguards/docs_only_guard_test.go")
		if code, stderr := runDocsOnlyGuard(t, mixed, seat); code != 0 {
			t.Fatalf("exit %d, want 0 (stderr %q)", code, stderr)
		}
	})
	t.Run("one doc path alone is refused", func(t *testing.T) {
		if code, _ := runDocsOnlyGuard(t, docsOnlyGuardArgs[:1], seat); code != 1 {
			t.Fatalf("exit %d, want 1", code)
		}
	})
}

// TestTheDocGlobsCoverEveryShapeTheGuardNames pins the glob list itself, because a path the loop does not
// recognise is a path a docs-only commit could ride: `*.md` at the root, under `ai_docs/`, under any
// `CHANGELOG/`, the two named files, and the plan files.
func TestTheDocGlobsCoverEveryShapeTheGuardNames(t *testing.T) {
	seat := map[string]string{"AGENTHUB_SESSION_NAME": "agenthub--room--seat"}
	for _, doc := range []string{
		"AGENTS.md",
		"ai_docs/agent-system/task-workflow-and-reporting.md",
		"ai_docs/core-architecture/seat-skills.md",
		"CHANGELOG/2026-10-17--one-entry.md",
		"claude-automation/CHANGELOG/2026-10-17--another-entry.md",
		"TEST-CHANGELOG.md",
		"NEXT-GEN2.md",
	} {
		if code, _ := runDocsOnlyGuard(t, []string{doc}, seat); code != 1 {
			t.Fatalf("%s: exit %d, want 1 - the guard's globs must cover the shape they name", doc, code)
		}
	}
}

// TestAGitlinkIsNotADocumentSoTheTypesFilterDropsItFirst pins the measured reason a pin cannot carry the
// bundle: to the script's own loop the gitlink is a non-doc path and passes, so the refusal seen at a pin
// comes from pre-commit's `types: [file]` dropping the gitlink BEFORE the guard is called (addendum 7) - and
// no change to this script can make a pin carry a document.
func TestAGitlinkIsNotADocumentSoTheTypesFilterDropsItFirst(t *testing.T) {
	code, stderr := runDocsOnlyGuard(t, []string{"agenthub_client"},
		map[string]string{"AGENTHUB_SESSION_NAME": "agenthub--room--seat"})
	if code != 0 {
		t.Fatalf("exit %d, want 0: the gitlink is outside the doc globs (stderr %q)", code, stderr)
	}
}

// TestTheOwnerAndTheOwnerFlagAreExempt pins the two exemptions the guard's header states: the owner's host
// has no AGENTHUB_SESSION_NAME, and OWNER_DOCS_COMMIT=1 is the owner's one-commit flag. A missing file list
// is answered 0 too - the framework hands the guard nothing on some invocations, and that is not a docs-only
// commit.
func TestTheOwnerAndTheOwnerFlagAreExempt(t *testing.T) {
	t.Run("the owner's host is exempt", func(t *testing.T) {
		if code, _ := runDocsOnlyGuard(t, docsOnlyGuardArgs, nil); code != 0 {
			t.Fatalf("exit %d, want 0", code)
		}
	})
	t.Run("the owner's flag is exempt", func(t *testing.T) {
		env := map[string]string{"AGENTHUB_SESSION_NAME": "agenthub--room--seat", "OWNER_DOCS_COMMIT": "1"}
		if code, _ := runDocsOnlyGuard(t, docsOnlyGuardArgs, env); code != 0 {
			t.Fatalf("exit %d, want 0", code)
		}
	})
	t.Run("no file list is not a docs commit", func(t *testing.T) {
		seat := map[string]string{"AGENTHUB_SESSION_NAME": "agenthub--room--seat"}
		if code, _ := runDocsOnlyGuard(t, nil, seat); code != 0 {
			t.Fatalf("exit %d, want 0", code)
		}
	})
}
