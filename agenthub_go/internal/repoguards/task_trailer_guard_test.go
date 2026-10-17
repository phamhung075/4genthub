// Package repoguards_test is the WITNESS for the commit guards in scripts/git-hooks.
//
// THE RULE THIS FILE ENFORCES: a seat's commit names its hub task in a `Task: <uuid>` trailer, a merge
// commit is exempt, and the owner's host (no AGENTHUB_SESSION_NAME) is exempt. AGENTS.md section 3.4 makes
// the trailer mandatory for every seat commit, and the guard is the only thing that holds the rule.
//
// WHY IT EXISTS, MEASURED: the guard refused two of this lane's own commits on 2026-10-17 - once for no
// trailer and once for an eight-character prefix (`Task: 5ac4a259`) - and nothing in the repository
// pinned either direction. A guard whose refusal is the rule has to be shown refusing in the shape the
// rule says, or the rule lives in a regexp nobody runs. The cases below are the guard's contract as the
// rule states it, not as the script happens to be written: the full uuid passes and its prefix does not,
// because the hub task id is what `4genteam complete --task` takes.
//
// THE SCRIPT IS RUN AS IT SHIPS (`sh scripts/git-hooks/task-trailer-guard <message file>`), not
// re-implemented here: a copy of the regexp would agree with itself and never with the hook.
package repoguards_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// repoRoot resolves the checkout from THIS FILE'S location: `go test` runs with the cwd set to the
// package directory, so a root-relative literal would resolve to nothing.
func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate this test file")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", ".."))
}

// runGuard runs the shipped guard over one message file inside a scratch repository, because the guard's
// own tool (`git interpret-trailers`) needs one, and returns its exit code and stderr.
func runGuard(t *testing.T, message string, seat bool) (int, string) {
	t.Helper()
	dir := t.TempDir()
	if err := exec.Command("git", "-C", dir, "init", "-q").Run(); err != nil {
		t.Fatalf("git init in the scratch repo: %v", err)
	}
	msgFile := filepath.Join(dir, "COMMIT_EDITMSG")
	if err := os.WriteFile(msgFile, []byte(message), 0o600); err != nil {
		t.Fatalf("write the message file: %v", err)
	}
	script := filepath.Join(repoRoot(t), "scripts", "git-hooks", "task-trailer-guard")
	cmd := exec.Command("sh", script, msgFile)
	cmd.Dir = dir
	cmd.Env = []string{"PATH=" + os.Getenv("PATH"), "HOME=" + dir}
	if seat {
		cmd.Env = append(cmd.Env, "AGENTHUB_SESSION_NAME=agenthub--room--seat")
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

// TestASeatCommitCarriesTheFullTaskIdTrailer pins the three answers the rule states: the full uuid
// passes, its eight-character prefix does not (the hub id `complete` takes is the whole one), and a
// message with no trailer at all does not.
func TestASeatCommitCarriesTheFullTaskIdTrailer(t *testing.T) {
	const uuid = "5ac4a259-2641-4cfa-8ee1-0fe13d68f470"
	cases := []struct {
		name    string
		message string
		want    int
		wantErr string
	}{
		{
			name:    "the full uuid passes",
			message: "fix(rail): the four tags retire\n\nTask: " + uuid + "\n",
			want:    0,
		},
		{
			name:    "its eight-character prefix is refused",
			message: "fix(rail): the four tags retire\n\nTask: 5ac4a259\n",
			want:    1,
			wantErr: "task trailer missing",
		},
		{
			name:    "no trailer is refused",
			message: "fix(rail): the four tags retire\n",
			want:    1,
			wantErr: "task trailer missing",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			code, stderr := runGuard(t, tc.message, true)
			if code != tc.want {
				t.Fatalf("exit %d, want %d (stderr %q)", code, tc.want, stderr)
			}
			if tc.wantErr != "" && !strings.Contains(stderr, tc.wantErr) {
				t.Fatalf("stderr %q lacks %q", stderr, tc.wantErr)
			}
		})
	}
}

// TestAMergeAndTheOwnersHostAreExempt pins the two exemptions the guard's own header states: a merge
// commit needs no trailer (it carries no authored change), and the owner's host has no
// AGENTHUB_SESSION_NAME, so nothing is refused there.
func TestAMergeAndTheOwnersHostAreExempt(t *testing.T) {
	t.Run("a merge commit is exempt", func(t *testing.T) {
		code, stderr := runGuard(t, "Merge branch 'main' into the lane\n", true)
		if code != 0 {
			t.Fatalf("exit %d, want 0 (stderr %q)", code, stderr)
		}
	})
	t.Run("the owner's host is exempt", func(t *testing.T) {
		code, stderr := runGuard(t, "fix(rail): the four tags retire\n", false)
		if code != 0 {
			t.Fatalf("exit %d, want 0 (stderr %q)", code, stderr)
		}
	})
}
