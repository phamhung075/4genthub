package utilities

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFileURLParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/fileurl_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var d struct {
		Names []struct {
			Raw, Want string
			Err       bool
		}
		Paths []struct {
			P, URI, Norm string
			Err          bool
		}
	}
	if err := json.Unmarshal(raw, &d); err != nil {
		t.Fatal(err)
	}
	bad := 0
	for _, c := range d.Names {
		if c.Err {
			continue
		}
		if got := normalizeFileURL(c.Raw); got != c.Want {
			if bad++; bad < 15 {
				t.Errorf("name %q: got %q want %q", c.Raw, got, c.Want)
			}
		}
	}
	for _, c := range d.Paths {
		if c.Err {
			continue
		}
		if strings.Contains(c.P, "..") {
			continue
		}
		if got := "file://" + PyQuote(filepath.Clean(c.P)); got != c.URI {
			t.Errorf("as_uri %q: got %q want %q", c.P, got, c.URI)
		}
		if got := normalizeFileURL(c.URI); got != c.Norm {
			if bad++; bad < 15 {
				t.Errorf("norm %q: got %q want %q", c.URI, got, c.Norm)
			}
		}
	}
}
