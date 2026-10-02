package utilities

import (
	"encoding/json"
	"os"
	"testing"
)

func TestPyURLPathParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/urlpath_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		URL  string
		Path string
		Err  string
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		if len(c.URL) < 4 || c.URL[:4] != "http" {
			continue
		}
		got, err := pyURLPath(c.URL)
		if c.Err != "" {
			if err == nil {
				t.Errorf("%q: want error, got path %q", c.URL, got)
			}
			continue
		}
		if err != nil || got != c.Path {
			t.Errorf("%q: got %q (%v) want %q", c.URL, got, err, c.Path)
		}
	}
}
