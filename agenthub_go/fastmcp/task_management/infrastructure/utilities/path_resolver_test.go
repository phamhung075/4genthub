package utilities

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// testEnv builds an Env backed by a map of existing paths and an environment map.
func testEnv(t *testing.T, cwd string, existing map[string]bool, environ map[string]string) Env {
	t.Helper()
	return Env{
		Anchor: cwd,
		Cwd:    cwd,
		Getenv: func(k string) (string, bool) { v, ok := environ[k]; return v, ok },
		Exists: func(p string) bool { return existing[p] },
	}
}

func TestFindProjectRootByMarkers(t *testing.T) {
	existing := map[string]bool{"/a/b/.git": true}
	env := testEnv(t, "/a/b/c/d", existing, nil)
	if root := FindProjectRootByMarkers(env, nil); root != "/a/b" {
		t.Fatalf("dotgit root = %q", root)
	}

	// No marker anywhere: Python returns the current working directory.
	env2 := testEnv(t, "/a/b/c", map[string]bool{}, nil)
	if root := FindProjectRootByMarkers(env2, nil); root != "/a/b/c" {
		t.Fatalf("no-marker root = %q", root)
	}

	// start_path overrides cwd.
	start := "/x/y"
	env3 := testEnv(t, "/other", map[string]bool{"/x/y/package.json": true}, nil)
	if root := FindProjectRootByMarkers(env3, &start); root != "/x/y" {
		t.Fatalf("start root = %q", root)
	}
}

func TestEnsureProjectStructure(t *testing.T) {
	root := t.TempDir()
	dir, err := EnsureProjectStructure(root)
	if err != nil {
		t.Fatal(err)
	}
	if dir != root+"/.cursor/rules" {
		t.Fatalf("dir = %q", dir)
	}
	if fi, err := os.Stat(dir); err != nil || !fi.IsDir() {
		t.Fatalf("not a directory: %v", err)
	}
}

func TestPathResolverResolutionAndProjectsFile(t *testing.T) {
	root := t.TempDir()
	existing := map[string]bool{}
	environ := map[string]string{}
	env := testEnv(t, root, existing, environ)

	r := &PathResolver{ProjectRoot: root, CursorRulesDir: root + "/.cursor/rules", env: env}
	r.BrainDir = r.resolve(".cursor/rules/brain")
	r.ProjectsFile = r.resolve(r.BrainDir + "/projects.json")
	if r.BrainDir != root+"/.cursor/rules/brain" {
		t.Fatalf("brain = %q", r.BrainDir)
	}

	if err := os.MkdirAll(r.BrainDir, 0o777); err != nil {
		t.Fatal(err)
	}
	if err := r.ensureProjectsFile(); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(r.ProjectsFile)
	if err != nil {
		t.Fatal(err)
	}
	var decoded map[string]any
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("projects file is not JSON: %v", err)
	}
	if _, ok := decoded["projects"]; !ok {
		t.Fatalf("missing projects key: %s", data)
	}

	// Calling it again leaves an existing file untouched (the injected Exists must see it).
	if err := os.WriteFile(r.ProjectsFile, []byte("{}"), 0o666); err != nil {
		t.Fatal(err)
	}
	r.env = testEnv(t, root, map[string]bool{r.ProjectsFile: true}, environ)
	if err := r.ensureProjectsFile(); err != nil {
		t.Fatal(err)
	}
	if again, _ := os.ReadFile(r.ProjectsFile); string(again) != "{}" {
		t.Fatalf("existing file overwritten: %s", again)
	}
}

func TestPathResolverGetTasksJSONPath(t *testing.T) {
	root := t.TempDir()
	r := &PathResolver{ProjectRoot: root, env: testEnv(t, root, map[string]bool{}, map[string]string{})}

	user := "user-1"
	got, err := r.GetTasksJSONPath("proj-1", "main", &user)
	if err != nil {
		t.Fatal(err)
	}
	want := root + "/.cursor/rules/tasks/user-1/proj-1/main/tasks.json"
	if got != want {
		t.Fatalf("path = %q, want %q", got, want)
	}
	if fi, err := os.Stat(filepath.Dir(got)); err != nil || !fi.IsDir() {
		t.Fatalf("tasks parent not created: %v", err)
	}

	// project_id falsy -> legacy path, with the TASKS_JSON_PATH override resolved
	// against the project root.
	r2 := &PathResolver{ProjectRoot: root, env: testEnv(t, root, map[string]bool{}, map[string]string{"TASKS_JSON_PATH": "custom/tasks.json"})}
	got2, err := r2.GetTasksJSONPath("", "main", nil)
	if err != nil {
		t.Fatal(err)
	}
	if got2 != root+"/custom/tasks.json" {
		t.Fatalf("legacy path = %q", got2)
	}
}

func TestPathResolverRulesDirectoryFromSettings(t *testing.T) {
	origProvider, origHTTP := pathResolverRulesProvider, pathResolverIsHTTPMode
	t.Cleanup(func() { pathResolverRulesProvider, pathResolverIsHTTPMode = origProvider, origHTTP })

	root := t.TempDir()
	// Default dual-mode dir does not exist; mode is stdio; no settings file, no env
	// override -> the default is returned.
	pathResolverRulesProvider = func() string { return root + "/does-not-exist" }
	pathResolverIsHTTPMode = func() bool { return false }
	empty := &PathResolver{ProjectRoot: root, env: testEnv(t, root, map[string]bool{}, map[string]string{})}
	if got := empty.GetRulesDirectoryFromSettings(); got != root+"/does-not-exist" {
		t.Fatalf("default rules = %q", got)
	}

	// DOCUMENT_RULES_PATH env override.
	withEnv := &PathResolver{ProjectRoot: root, env: testEnv(t, root, map[string]bool{}, map[string]string{"DOCUMENT_RULES_PATH": "myrules"})}
	if got := withEnv.GetRulesDirectoryFromSettings(); got != root+"/myrules" {
		t.Fatalf("env rules = %q", got)
	}

	// 00_RULES/core/settings.json runtime_constants.DOCUMENT_RULES_PATH.
	settingsDir := filepath.Join(root, "00_RULES", "core")
	if err := os.MkdirAll(settingsDir, 0o777); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(settingsDir, "settings.json"),
		[]byte(`{"runtime_constants": {"DOCUMENT_RULES_PATH": "settings_rules"}}`), 0o666); err != nil {
		t.Fatal(err)
	}
	existing := map[string]bool{filepath.Join(settingsDir, "settings.json"): true}
	fromSettings := &PathResolver{ProjectRoot: root, env: testEnv(t, root, existing, map[string]string{})}
	if got := fromSettings.GetRulesDirectoryFromSettings(); got != root+"/settings_rules" {
		t.Fatalf("settings rules = %q", got)
	}

	// HTTP mode never reads the settings files.
	pathResolverIsHTTPMode = func() bool { return true }
	httpMode := &PathResolver{ProjectRoot: root, env: testEnv(t, root, existing, map[string]string{})}
	if got := httpMode.GetRulesDirectoryFromSettings(); got != root+"/does-not-exist" {
		t.Fatalf("http rules = %q", got)
	}
}

func TestPathResolverLegacyAndAutoRule(t *testing.T) {
	root := t.TempDir()
	r := &PathResolver{ProjectRoot: root, env: testEnv(t, root, map[string]bool{}, map[string]string{})}
	if got := r.GetLegacyTasksJSONPath(); got != root+"/.cursor/rules/tasks/tasks.json" {
		t.Fatalf("legacy = %q", got)
	}
	if got := r.GetAutoRulePath(); got != root+"/.cursor/rules/auto_rule.mdc" {
		t.Fatalf("auto rule = %q", got)
	}
	abs := &PathResolver{ProjectRoot: root, env: testEnv(t, root, map[string]bool{}, map[string]string{"AUTO_RULE_PATH": "/abs/rule.mdc"})}
	if got := abs.GetAutoRulePath(); got != "/abs/rule.mdc" {
		t.Fatalf("abs auto rule = %q", got)
	}
}

func TestGetTasksJSONPathNilUserIsNone(t *testing.T) {
	root := t.TempDir()
	r := &PathResolver{ProjectRoot: root, env: DefaultEnv()}
	got, err := r.GetTasksJSONPath("proj", "main", nil)
	if err != nil {
		t.Fatal(err)
	}
	if want := root + "/.cursor/rules/tasks/None/proj/main/tasks.json"; got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}
