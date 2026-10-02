package entities

import (
	"encoding/json"
	"os"
	"testing"
)

func TestFnmatchMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/fnmatch_python_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases [][3]any
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		if got := fnmatch(c[0].(string), c[1].(string)); got != c[2].(bool) {
			t.Errorf("fnmatch(%q,%q)=%v python=%v", c[0], c[1], got, c[2])
		}
	}
	t.Logf("%d cases", len(cases))
}
