// Package utilities ports task_management/infrastructure/utilities.
package utilities

import (
	"os"
	"path/filepath"
)

// Env is the environment and filesystem the project-root search reads, injectable for tests.
type Env struct {
	// Anchor stands in for Python's __file__: the search walks up from it. A Go binary has no
	// source file, so the default is the executable path.
	Anchor string
	Cwd    string
	Getenv func(string) (string, bool)
	Exists func(path string) bool
}

// DefaultEnv reads the real process environment.
func DefaultEnv() Env {
	exe, _ := os.Executable()
	if resolved, err := filepath.EvalSymlinks(exe); err == nil {
		exe = resolved
	}
	cwd, _ := os.Getwd()
	return Env{Anchor: exe, Cwd: cwd, Getenv: os.LookupEnv, Exists: func(p string) bool { _, err := os.Stat(p); return err == nil }}
}

// FindProjectRoot finds the project root by looking for the agenthub_go directory,
// falling back to the data path and finally to a temp directory.
func (e Env) FindProjectRoot() string {
	parentOf := func(p string) string { return filepath.Dir(p) }
	has := func(dir string) bool { return e.Exists(filepath.Join(dir, "agenthub_go")) }

	for cur := e.Anchor; parentOf(cur) != cur; cur = parentOf(cur) {
		if has(cur) {
			return cur
		}
	}
	if has(e.Cwd) {
		return e.Cwd
	}
	// NO path-NAME fallback lives here, deliberately. A second walk used to return the parent of any
	// directory literally named agenthub_go, which took the decision away from Env.Exists - the stub
	// guards Exists, not names, so it could not stop it. A binary under such a path then resolved to
	// that component's parent instead of to its own project, which is red on every host whose build
	// caches sit in agenthub_go/.gotmp (task 0f965914; deleted, not gated: gating would leave an
	// unreachable branch, because a hit at cur means Exists(parentOf(cur)/agenthub_go) already held).
	//
	// The invariant every return below satisfies: a directory that holds agenthub_go, the data path
	// when it exists, or the temp fallback. TestFindProjectRootIsHostIndependent pins it.
	dataPath, ok := e.Getenv("AGENTHUB_DATA_PATH")
	if !ok {
		dataPath = "/data"
	}
	if !e.Exists(dataPath) {
		return "/tmp/agenthub_project"
	}
	return dataPath
}

// EnsureBrainDir creates and returns the brain directory (<project root>/.cursor/brain
// when brainDir is nil; an empty string is the current directory, like Path("")).
func (e Env) EnsureBrainDir(brainDir *string) (string, error) {
	dir := "."
	if brainDir == nil {
		dir = filepath.Join(e.FindProjectRoot(), ".cursor", "brain")
	} else if *brainDir != "" {
		dir = *brainDir
	}
	if err := os.MkdirAll(dir, 0o777); err != nil {
		return "", err
	}
	return dir, nil
}
