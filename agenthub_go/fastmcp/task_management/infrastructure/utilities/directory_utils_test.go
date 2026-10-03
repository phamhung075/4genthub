package utilities_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/utilities"
)

func TestFindProjectRootParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/dir_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		Dirs   []string
		Anchor string
		Cwd    string
		Data   *string
		Out    string
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for i, c := range cases {
		root, err := filepath.EvalSymlinks(t.TempDir())
		if err != nil {
			t.Fatal(err)
		}
		for _, d := range c.Dirs {
			if err := os.MkdirAll(filepath.Join(root, d), 0o755); err != nil {
				t.Fatal(err)
			}
		}
		env := utilities.DefaultEnv()
		env.Anchor = filepath.Join(root, c.Anchor, "directory_utils.py")
		env.Cwd = filepath.Join(root, c.Cwd)
		// Only paths under root exist: the tree above a TMPDIR inside the repository holds a real
		// agenthub_main directory that the upward search would otherwise find.
		env.Exists = func(p string) bool {
			if p != root && !strings.HasPrefix(p, root+string(filepath.Separator)) {
				return false
			}
			_, err := os.Stat(p)
			return err == nil
		}
		env.Getenv = func(k string) (string, bool) {
			if k == "AGENTHUB_DATA_PATH" && c.Data != nil {
				return filepath.Join(root, *c.Data), true
			}
			return "", false
		}
		got := strings.Replace(env.FindProjectRoot(), root, "<R>", 1)
		if got != c.Out {
			t.Fatalf("case %d (%+v): got %q want %q", i, c, got, c.Out)
		}
	}
}

func TestEnsureBrainDir(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "a", "b")
	got, err := utilities.DefaultEnv().EnsureBrainDir(&dir)
	if err != nil || got != dir {
		t.Fatalf("EnsureBrainDir = %q, %v", got, err)
	}
	if st, err := os.Stat(dir); err != nil || !st.IsDir() {
		t.Fatal("directory not created")
	}
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "agenthub_main"), 0o755); err != nil {
		t.Fatal(err)
	}
	env := utilities.DefaultEnv()
	env.Anchor = filepath.Join(root, "x")
	got, err = env.EnsureBrainDir(nil)
	if want := filepath.Join(root, ".cursor", "brain"); err != nil || got != want {
		t.Fatalf("default brain dir = %q, %v; want %q", got, err, want)
	}
}
