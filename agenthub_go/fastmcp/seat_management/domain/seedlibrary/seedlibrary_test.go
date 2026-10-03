package seedlibrary

import (
	"encoding/json"
	"io/fs"
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

// withShared adds the embedded shared modules to a test filesystem.
func withShared(t *testing.T, fsys fstest.MapFS) fstest.MapFS {
	t.Helper()
	for _, f := range sharedModuleFiles {
		path := sharedModulesDir + "/" + f.file
		data, err := fs.ReadFile(embedded, path)
		if err != nil {
			t.Fatal(err)
		}
		fsys[path] = &fstest.MapFile{Data: data}
	}
	return fsys
}

func TestParseValid(t *testing.T) {
	seed, err := Parse("seat-types/developer.yaml", []byte(validFile), nil)
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
		_, err := Parse("seat-types/x.yaml", []byte(c.data), nil)
		if err == nil || !strings.Contains(err.Error(), "seat-types/x.yaml") || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want file name and %q", name, err, c.want)
		}
	}
}

func TestLoadFSSortedAndDeterministic(t *testing.T) {
	fsys := withShared(t, fstest.MapFS{
		"seat-types/b.yaml":  {Data: []byte(strings.Replace(validFile, "developer", "zeta", 1))},
		"seat-types/a.yaml":  {Data: []byte(validFile)},
		"seat-types/ignored": {Data: []byte("not yaml")},
	})
	seeds, err := LoadFS(fsys)
	if err != nil {
		t.Fatal(err)
	}
	if len(seeds) != 2 || seeds[0].SeatTypeSlug != "developer" || seeds[1].SeatTypeSlug != "zeta" {
		t.Fatalf("unexpected seeds: %+v", seeds)
	}
}

func TestLoadFSDuplicateSlug(t *testing.T) {
	fsys := withShared(t, fstest.MapFS{
		"seat-types/a.yaml": {Data: []byte(validFile)},
		"seat-types/b.yaml": {Data: []byte(validFile)},
	})
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

func TestLoadFSMissingSharedModuleFails(t *testing.T) {
	fsys := fstest.MapFS{"seat-types/a.yaml": {Data: []byte(validFile)}}
	if _, err := LoadFS(fsys); err == nil || !strings.Contains(err.Error(), "comm-guard.json") {
		t.Fatalf("err = %v, want the missing shared module file", err)
	}
}

// Every embedded seat type carries the communication guard: the settings fragment that denies
// direct messaging and the skill that names seatcheck as the only send path.
func TestLoadEmbeddedSeedsCarryCommGuard(t *testing.T) {
	seeds, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	for _, seed := range seeds {
		modules := map[string]seedmapModule{}
		for _, m := range seed.Modules {
			modules[m.Slug] = seedmapModule{kind: m.Kind, content: m.Content}
		}
		tool, skill := modules["comm-guard"], modules["comm-guard-skill"]
		if tool.kind != resolver.KindTool || skill.kind != resolver.KindSkill {
			t.Fatalf("%s: comm-guard kind %q, comm-guard-skill kind %q", seed.SeatTypeSlug, tool.kind, skill.kind)
		}
		var settings struct {
			Permissions struct {
				Deny  []string `json:"deny"`
				Allow []string `json:"allow"`
			} `json:"permissions"`
		}
		if err := json.Unmarshal([]byte(tool.content), &settings); err != nil {
			t.Fatalf("%s: comm-guard is not valid JSON: %v", seed.SeatTypeSlug, err)
		}
		wantDeny := []string{"Bash(rig send:*)", "Bash(rig queue:*)", "Bash(rig broadcast:*)", "Bash(tmux send-keys:*)", "Bash(tmux paste-buffer:*)"}
		if strings.Join(settings.Permissions.Deny, "|") != strings.Join(wantDeny, "|") || strings.Join(settings.Permissions.Allow, "|") != "Bash(seatcheck send:*)" {
			t.Fatalf("%s: permissions = %+v", seed.SeatTypeSlug, settings.Permissions)
		}
		if !strings.Contains(skill.content, "seatcheck send --to <seat> --intent") {
			t.Fatalf("%s: skill does not name seatcheck send:\n%s", seed.SeatTypeSlug, skill.content)
		}
		for _, ref := range seed.ModuleRefs {
			if ref.Slug == "comm-guard" && ref.Version != seed.Version {
				t.Fatalf("%s: comm-guard ref version %q, seed version %q", seed.SeatTypeSlug, ref.Version, seed.Version)
			}
		}
	}
}

type seedmapModule struct {
	kind    resolver.ModuleKind
	content string
}
