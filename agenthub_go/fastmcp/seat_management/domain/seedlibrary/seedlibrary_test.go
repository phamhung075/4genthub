package seedlibrary

import (
	"strings"
	"testing"
	"testing/fstest"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

const validFile = `slug: developer
name: Developer
description: Writes code
default_runtime: claude-code
role: You write code.
rules:
  - name: Test First
    content: Write a failing test first.
output_format: Reply with a summary.
`

func TestParseValid(t *testing.T) {
	seed, err := Parse("seat-types/developer.yaml", []byte(validFile))
	if err != nil {
		t.Fatal(err)
	}
	if seed.SeatTypeSlug != "developer" || seed.DefaultRuntime != "claude-code" || len(seed.Modules) != 3 {
		t.Fatalf("unexpected seed: %+v", seed)
	}
	if seed.Modules[1].Slug != "developer-rule-test-first" || seed.Modules[2].Kind != resolver.KindDocument {
		t.Fatalf("unexpected modules: %+v", seed.Modules)
	}
}

func TestParseErrorsNameFileAndField(t *testing.T) {
	replace := func(old, new string) string { return strings.Replace(validFile, old, new, 1) }
	cases := map[string]struct{ data, want string }{
		"unknown field": {validFile + "extra: 1\n", "field extra not found"},
		"bad slug":      {replace("slug: developer", "slug: Developer"), "field slug"},
		"empty name":    {replace("name: Developer", "name: ''"), "field name"},
		"bad runtime":   {replace("claude-code", "vim"), "field default_runtime"},
		"empty role":    {replace("role: You write code.", "role: ''"), "empty role"},
		"empty output":  {replace("output_format: Reply with a summary.", "output_format: ''"), "empty output format"},
		"empty rule":    {replace("content: Write a failing test first.", "content: ''"), "field rules[0].content"},
		"duplicate rule": {replace("output_format", "  - name: test-first\n    content: again\noutput_format"),
			"duplicate rule name"},
		"empty file": {"", "file is empty"},
	}
	for name, c := range cases {
		_, err := Parse("seat-types/x.yaml", []byte(c.data))
		if err == nil || !strings.Contains(err.Error(), "seat-types/x.yaml") || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want file name and %q", name, err, c.want)
		}
	}
}

func TestLoadFSSortedAndDeterministic(t *testing.T) {
	fsys := fstest.MapFS{
		"seat-types/b.yaml":  {Data: []byte(strings.Replace(validFile, "developer", "zeta", 1))},
		"seat-types/a.yaml":  {Data: []byte(validFile)},
		"seat-types/ignored": {Data: []byte("not yaml")},
	}
	seeds, err := LoadFS(fsys)
	if err != nil {
		t.Fatal(err)
	}
	if len(seeds) != 2 || seeds[0].SeatTypeSlug != "developer" || seeds[1].SeatTypeSlug != "zeta" {
		t.Fatalf("unexpected seeds: %+v", seeds)
	}
}

func TestLoadFSDuplicateSlug(t *testing.T) {
	fsys := fstest.MapFS{
		"seat-types/a.yaml": {Data: []byte(validFile)},
		"seat-types/b.yaml": {Data: []byte(validFile)},
	}
	if _, err := LoadFS(fsys); err == nil || !strings.Contains(err.Error(), "already defined") {
		t.Fatalf("err = %v, want duplicate slug", err)
	}
}

func TestLoadEmbeddedSet(t *testing.T) {
	seeds, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"architect", "debugger", "developer", "lead", "planner", "researcher", "reviewer", "tester", "writer"}
	if len(seeds) != len(want) {
		t.Fatalf("seeds = %d, want %d", len(seeds), len(want))
	}
	for i, seed := range seeds {
		if seed.SeatTypeSlug != want[i] {
			t.Fatalf("seed %d = %q, want %q", i, seed.SeatTypeSlug, want[i])
		}
		rules := 0
		var role, output bool
		for _, module := range seed.Modules {
			switch {
			case module.Slug == seed.SeatTypeSlug+"-role" && module.Kind == resolver.KindInstruction:
				role = true
			case module.Slug == seed.SeatTypeSlug+"-output-format" && module.Kind == resolver.KindDocument:
				output = true
			case strings.HasPrefix(module.Slug, seed.SeatTypeSlug+"-rule-") && module.Kind == resolver.KindInstruction:
				rules++
			}
		}
		if !role || !output || rules < 3 {
			t.Errorf("%s: role=%v output=%v rules=%d", seed.SeatTypeSlug, role, output, rules)
		}
	}
}
