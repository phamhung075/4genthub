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
		// agenthub_go directory that the upward search would otherwise find.
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
		ret := env.FindProjectRoot()
		got := strings.Replace(ret, root, "<R>", 1)
		if got != c.Out {
			t.Fatalf("case %d (%+v): got %q want %q", i, c, got, c.Out)
		}
		dataPath := "/data"
		if c.Data != nil {
			dataPath = filepath.Join(root, *c.Data)
		}
		assertReturnInvariant(t, env, ret, dataPath)
	}
	t.Logf("parity cases exercised: %d", len(cases))
}

// assertReturnInvariant is the shape every return of FindProjectRoot must have: a directory that
// holds agenthub_go, the data path when it exists, or the documented temp fallback. It is checked per
// case rather than once, because a wrong answer can still LOOK plausible.
func assertReturnInvariant(t *testing.T, env utilities.Env, got string, dataPath string) {
	t.Helper()
	switch {
	case env.Exists(filepath.Join(got, "agenthub_go")):
	case got == dataPath && env.Exists(dataPath):
	case got == "/tmp/agenthub_project":
	default:
		t.Fatalf(
			"return %q is none of: a directory holding agenthub_go, the data path %q, /tmp/agenthub_project",
			got, dataPath,
		)
	}
}

// TestFindProjectRootIsHostIndependent takes the HOST out of the decision. The fixture root lives under
// a directory named agenthub_go, and nothing inside it has an agenthub_go child, so the fixture's own
// answer is the documented fallback. On d1114170 a second walk matched that directory NAME, which
// Env.Exists never sees, and returned the parent of the fixture instead: this case is red there under
// TMPDIR=/tmp, and red on the real tree under the mandated TMPDIR.
func TestFindProjectRootIsHostIndependent(t *testing.T) {
	root := t.TempDir()
	fixture := filepath.Join(root, "agenthub_go", "r")
	if err := os.MkdirAll(filepath.Join(fixture, "m"), 0o755); err != nil {
		t.Fatal(err)
	}
	env := utilities.DefaultEnv()
	env.Anchor = filepath.Join(fixture, "m", "directory_utils.py")
	env.Cwd = filepath.Join(fixture, "m")
	env.Exists = func(p string) bool {
		if p != fixture && !strings.HasPrefix(p, fixture+string(filepath.Separator)) {
			return false
		}
		_, err := os.Stat(p)
		return err == nil
	}
	env.Getenv = func(string) (string, bool) { return "", false }

	got := env.FindProjectRoot()
	if got == root {
		t.Fatalf("returned %q, the parent of the fixture's own agenthub_go: the search matched a NAME", got)
	}
	if want := "/tmp/agenthub_project"; got != want {
		t.Fatalf("FindProjectRoot = %q, want %q", got, want)
	}
	assertReturnInvariant(t, env, got, "/data")
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
	if err := os.Mkdir(filepath.Join(root, "agenthub_go"), 0o755); err != nil {
		t.Fatal(err)
	}
	env := utilities.DefaultEnv()
	env.Anchor = filepath.Join(root, "x")
	got, err = env.EnsureBrainDir(nil)
	if want := filepath.Join(root, ".cursor", "brain"); err != nil || got != want {
		t.Fatalf("default brain dir = %q, %v; want %q", got, err, want)
	}
}
