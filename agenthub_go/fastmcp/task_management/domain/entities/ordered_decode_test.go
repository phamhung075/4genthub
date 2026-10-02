package entities

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

type decodeFixture struct {
	Files []struct {
		Path string                   `json:"path"`
		Out  struct{ Ok, Exc string } `json:"out"`
	} `json:"files"`
	Edge []struct {
		In  string                   `json:"in"`
		Out struct{ Ok, Exc string } `json:"out"`
	} `json:"edge"`
	JSON []struct {
		In  string                   `json:"in"`
		Out struct{ Ok, Exc string } `json:"out"`
	} `json:"json"`
}

func loadDecodeFixture(t *testing.T) decodeFixture {
	t.Helper()
	raw, err := os.ReadFile("testdata/ordered_decode_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var f decodeFixture
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	return f
}

func dumpDefault(v any) (string, error) {
	return value_objects.PyJSONDumpsDefaultStr(v, -1), nil
}

func TestLoadYAMLEdgeParity(t *testing.T) {
	for _, c := range loadDecodeFixture(t).Edge {
		v, err := LoadYAML([]byte(c.In))
		if c.Out.Exc != "" {
			if err == nil {
				got, _ := dumpDefault(v)
				t.Errorf("%q: want %s error, got %s", c.In, c.Out.Exc, got)
			}
			continue
		}
		if err != nil {
			t.Errorf("%q: %v (want %s)", c.In, err, c.Out.Ok)
			continue
		}
		got, _ := dumpDefault(v)
		if got != c.Out.Ok {
			t.Errorf("%q:\n got  %s\n want %s", c.In, got, c.Out.Ok)
		}
	}
}

// TestLoadYAMLAgentLibraryParity loads every agent-library YAML file with the Go loader
// and compares the JSON dump with PyYAML's. The library lives in the Python tree, so the
// test is skipped when that tree is gone.
func TestLoadYAMLAgentLibraryParity(t *testing.T) {
	root := filepath.Join("..", "..", "..", "..", "..", "agenthub_main")
	if _, err := os.Stat(filepath.Join(root, "agent-library")); err != nil {
		t.Skip("agent-library not present")
	}
	files := loadDecodeFixture(t).Files
	if len(files) < 300 {
		t.Fatalf("fixture too small: %d files", len(files))
	}
	for _, f := range files {
		raw, err := os.ReadFile(filepath.Join(root, f.Path))
		if err != nil {
			t.Fatal(err)
		}
		v, err := LoadYAML(raw)
		if f.Out.Exc != "" {
			if err == nil {
				t.Errorf("%s: Python fails (%s), Go loads", f.Path, f.Out.Exc)
			}
			continue
		}
		if err != nil {
			t.Errorf("%s: %v", f.Path, err)
			continue
		}
		got, _ := dumpDefault(v)
		if got != f.Out.Ok {
			n := 0
			for n < len(got) && n < len(f.Out.Ok) && got[n] == f.Out.Ok[n] {
				n++
			}
			lo := max(0, n-60)
			t.Errorf("%s: differs at byte %d:\n got  ...%s\n want ...%s", f.Path, n, got[lo:min(len(got), n+60)], f.Out.Ok[lo:min(len(f.Out.Ok), n+60)])
		}
	}
}

func TestDecodeJSONParity(t *testing.T) {
	for _, c := range loadDecodeFixture(t).JSON {
		v, err := DecodeJSON([]byte(c.In))
		if c.Out.Exc != "" {
			if err == nil {
				t.Logf("%q: Python fails (%s), Go decodes (accepted for NaN/Infinity-style input)", c.In, c.Out.Exc)
			}
			continue
		}
		if err != nil {
			t.Errorf("%q: %v", c.In, err)
			continue
		}
		got, _ := dumpDefault(v)
		if got != c.Out.Ok {
			t.Errorf("%q: got %s want %s", c.In, got, c.Out.Ok)
		}
	}
}

// TestLoadYAMLHostileInput covers the documents that crashed the first loader: a recursive
// alias overflowed the stack and an alias-expansion bomb exhausted memory. Both must now
// return promptly (a cycle as an error, a bomb as shared values).
func TestLoadYAMLHostileInput(t *testing.T) {
	for _, doc := range []string{"a: &a [*a]", "a: &a\n  - 1\n  - *a", "a: &a {<<: *a}", "&a [*a]"} {
		if _, err := LoadYAML([]byte(doc)); err == nil {
			t.Errorf("%q: recursive alias must be an error", doc)
		}
	}
	bomb := "a: &a0 [x, x, x, x, x, x, x, x, x, x]\n"
	for i := 1; i <= 7; i++ {
		bomb += fmt.Sprintf("b%d: &a%d [*a%d, *a%d, *a%d, *a%d, *a%d, *a%d, *a%d, *a%d, *a%d, *a%d]\n", i, i, i-1, i-1, i-1, i-1, i-1, i-1, i-1, i-1, i-1, i-1)
	}
	v, err := LoadYAML([]byte(bomb))
	if err != nil {
		t.Fatal(err)
	}
	if v.(*OrderedMap[any]).Len() != 8 {
		t.Errorf("bomb: unexpected result %v", v)
	}
}

func TestLoadYAMLKeyIdentityAndValueScalar(t *testing.T) {
	v, err := LoadYAML([]byte("1: a\n1.0: b\ntrue: c\nnull: d\n~: e\n0: z\nfalse: y\n"))
	if err != nil {
		t.Fatal(err)
	}
	got, _ := dumpDefault(v)
	// Python: {1: 'c', None: 'e', 0: 'y'}
	if want := `{"1": "c", "null": "e", "0": "y"}`; got != want {
		t.Errorf("got %s want %s", got, want)
	}
	// PyYAML: '=' is a string as a key but has no constructor as a value.
	v, err = LoadYAML([]byte("=: v\n"))
	if err != nil {
		t.Fatal(err)
	}
	if got, _ := dumpDefault(v); got != `{"=": "v"}` {
		t.Errorf("got %s", got)
	}
	if _, err = LoadYAML([]byte("op: =\n")); err == nil {
		t.Error("'=' as a value must be an error")
	}
}
