package tools

import (
	"os"
	"path/filepath"
	"testing"
)

func TestIsProjectRootMarkers(t *testing.T) {
	dir := t.TempDir()
	if IsProjectRoot(dir) {
		t.Fatalf("empty dir reported as project root")
	}
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if !IsProjectRoot(dir) {
		t.Fatalf("go.mod not detected")
	}
	dir2 := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir2, ".cursor", "rules"), 0o755); err != nil {
		t.Fatal(err)
	}
	if !IsProjectRoot(dir2) {
		t.Fatalf(".cursor/rules not detected")
	}
}

func TestFindProjectRootEnvAndUpward(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte(""), 0o644); err != nil {
		t.Fatal(err)
	}
	// The upward search tries .git before the other markers: without one here, a .git above a
	// TMPDIR inside the repository would be found first.
	nested := filepath.Join(dir, "a", "b")
	for _, d := range []string{nested, filepath.Join(dir, ".git")} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	t.Setenv("PROJECT_ROOT_PATH", nested)
	got := FindProjectRoot(nil)
	if got != nested {
		t.Fatalf("env root=%q want %q", got, nested)
	}
	t.Setenv("PROJECT_ROOT_PATH", "")
	got = FindProjectRoot(&nested)
	if got != dir {
		t.Fatalf("upward root=%q want %q", got, dir)
	}
}

func TestEnsureProjectStructure(t *testing.T) {
	dir := t.TempDir()
	got := EnsureProjectStructure(&dir)
	if got != dir {
		t.Fatalf("root=%q", got)
	}
	for _, sub := range []string{"database", ".cursor"} {
		if _, err := os.Stat(filepath.Join(dir, sub)); err != nil {
			t.Errorf("%s not created: %v", sub, err)
		}
	}
}
