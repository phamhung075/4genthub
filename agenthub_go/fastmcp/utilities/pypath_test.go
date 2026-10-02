package utilities_test

import (
	"encoding/json"
	"os"
	"testing"

	"agenthub/fastmcp/utilities"
)

func TestPyPathParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/pypath_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		P, R   string
		Norm   string
		Parent string
		Name   string
		Join   string
		Abs    bool
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		if got := utilities.PyPath(c.P); got != c.Norm {
			t.Errorf("PyPath(%q) = %q, want %q", c.P, got, c.Norm)
		}
		if got := utilities.PyParent(c.P); got != c.Parent {
			t.Errorf("PyParent(%q) = %q, want %q", c.P, got, c.Parent)
		}
		if got := utilities.PyName(c.P); got != c.Name {
			t.Errorf("PyName(%q) = %q, want %q", c.P, got, c.Name)
		}
		if got := utilities.PyJoin(c.P, c.R); got != c.Join {
			t.Errorf("PyJoin(%q, %q) = %q, want %q", c.P, c.R, got, c.Join)
		}
		if got := utilities.PyIsAbs(c.P); got != c.Abs {
			t.Errorf("PyIsAbs(%q) = %v, want %v", c.P, got, c.Abs)
		}
	}
}
