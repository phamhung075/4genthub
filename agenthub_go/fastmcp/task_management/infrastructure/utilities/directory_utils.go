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

// FindProjectRoot finds the project root by looking for the agenthub_main directory,
// falling back to the data path and finally to a temp directory.
func (e Env) FindProjectRoot() string {
	parentOf := func(p string) string { return filepath.Dir(p) }
	has := func(dir string) bool { return e.Exists(filepath.Join(dir, "agenthub_main")) }

	for cur := e.Anchor; parentOf(cur) != cur; cur = parentOf(cur) {
		if has(cur) {
			return cur
		}
	}
	if has(e.Cwd) {
		return e.Cwd
	}
	for cur := e.Anchor; parentOf(cur) != cur; cur = parentOf(cur) {
		if filepath.Base(cur) == "agenthub_main" {
			return parentOf(cur)
		}
	}
	dataPath, ok := e.Getenv("AGENTHUB_DATA_PATH")
	if !ok {
		dataPath = "/data"
	}
	if !e.Exists(dataPath) {
		if has(e.Cwd) {
			return e.Cwd
		}
		for cur := e.Anchor; parentOf(cur) != cur; cur = parentOf(cur) {
			if has(cur) {
				return cur
			}
		}
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
