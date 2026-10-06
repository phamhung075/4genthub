package seedlibrary

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seedmap"
	"agenthub/fastmcp/seat_management/domain/skillblock"
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
	seed, err := Parse("seat-types/developer.yaml", []byte(validFile), nil, nil)
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
		"bad module ref": {validFile + "module_refs:\n  - no-version\n", "field module_refs[0]"},
		"empty file":     {"", "file is empty"},
	}
	for name, c := range cases {
		_, err := Parse("seat-types/x.yaml", []byte(c.data), nil, nil)
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
		// A skill module is a block: the SKILL.md text plus its source provenance. The seed
		// authors this skill in-tree, so its digest must match the committed source file.
		skillContent, err := skillblock.Parse(skill.content)
		if err != nil {
			t.Fatalf("%s: comm-guard-skill is not a skill block: %v", seed.SeatTypeSlug, err)
		}
		source, err := fs.ReadFile(embedded, sharedModulesDir+"/comm-guard-skill.md")
		if err != nil {
			t.Fatal(err)
		}
		if sum := sha256.Sum256(source); skillContent.SHA256 != hex.EncodeToString(sum[:]) {
			t.Fatalf("%s: comm-guard-skill sha256 = %q, want the digest of its source file", seed.SeatTypeSlug, skillContent.SHA256)
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
		if strings.Join(settings.Permissions.Deny, "|") != strings.Join(wantDeny, "|") || strings.Join(settings.Permissions.Allow, "|") != "Bash(seatcheck send:*)|Bash(rig whoami:*)" {
			t.Fatalf("%s: permissions = %+v", seed.SeatTypeSlug, settings.Permissions)
		}
		for _, code := range []string{"Exit code 2", "Exit code 3", "Exit code 5"} {
			if !strings.Contains(skillContent.Content, code) {
				t.Fatalf("%s: skill does not explain %q:\n%s", seed.SeatTypeSlug, code, skillContent.Content)
			}
		}
		if !strings.Contains(skillContent.Content, "seatcheck send --to <seat> --intent") {
			t.Fatalf("%s: skill does not name seatcheck send:\n%s", seed.SeatTypeSlug, skillContent.Content)
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

// withBlocks adds the embedded block catalog to a test filesystem.
func withBlocks(t *testing.T, fsys fstest.MapFS) fstest.MapFS {
	t.Helper()
	names, err := fs.Glob(embedded, blocksDir+"/*.json")
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range names {
		data, err := fs.ReadFile(embedded, name)
		if err != nil {
			t.Fatal(err)
		}
		fsys[name] = &fstest.MapFile{Data: data}
	}
	return fsys
}

// Each of the nine seeded seat types mounts the platform server and the deepseek offload bridge,
// and the reasoning roles mount the sequential-thinking server too; the sets are asserted on the
// shipped seeds.
func TestLoadEmbeddedSeedsCarryServerSets(t *testing.T) {
	seeds, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	twoBlocks := map[string]bool{"lead": true, "architect": true, "planner": true, "researcher": true}
	for _, seed := range seeds {
		blocks := map[string]seedmap.SeedModule{}
		for _, m := range seed.Modules {
			if m.Kind == resolver.KindMCP {
				blocks[m.Slug] = m
			}
		}
		platform, ok := blocks["agenthub-http"]
		if !ok {
			t.Fatalf("%s: no agenthub-http mcp block: %+v", seed.SeatTypeSlug, blocks)
		}
		server, err := mcpblock.Parse(platform.Content)
		if err != nil {
			t.Fatalf("%s: platform block: %v", seed.SeatTypeSlug, err)
		}
		if server.Name != "agenthub_http" || server.Type != mcpblock.TypeHTTP || server.URL != mcpblock.PlatformURLPlaceholder {
			t.Fatalf("%s: platform block = %+v", seed.SeatTypeSlug, server)
		}
		if _, found := blocks["sequential-thinking"]; found != twoBlocks[seed.SeatTypeSlug] {
			t.Fatalf("%s: sequential-thinking present = %v, want %v", seed.SeatTypeSlug, found, twoBlocks[seed.SeatTypeSlug])
		}
		// The deepseek offload bridge: every seat type mounts it, because the value it must carry —
		// DSH_ROOT, which points the bridge at its checkout when HOME is the seat directory — cannot
		// come from the seat's process environment (the runner's allowlist drops it).
		offload, ok := blocks["deepseek-offload"]
		if !ok {
			t.Fatalf("%s: no deepseek-offload mcp block: %+v", seed.SeatTypeSlug, blocks)
		}
		bridge, err := mcpblock.Parse(offload.Content)
		if err != nil {
			t.Fatalf("%s: deepseek block: %v", seed.SeatTypeSlug, err)
		}
		if bridge.Name != "deepseek" || bridge.Type != mcpblock.TypeStdio || bridge.Command != "node" {
			t.Fatalf("%s: deepseek block = %+v", seed.SeatTypeSlug, bridge)
		}
		for key, want := range map[string]string{
			"DSH_ROOT":                  "${DSH_ROOT}",
			"DSH_HOME":                  "${DSH_HOME}",
			"DEEPSEEK_MCP_DEFAULT_CWD":  "${DEEPSEEK_MCP_DEFAULT_CWD}",
			"DEEPSEEK_WORKSPACE_ATTACH": "1",
			"DEEPSEEK_MCP_PERMISSION":   "allow",
		} {
			if bridge.Env[key] != want {
				t.Fatalf("%s: deepseek env %s = %q, want %q", seed.SeatTypeSlug, key, bridge.Env[key], want)
			}
		}
		for slug, m := range blocks {
			if m.Version != seed.Version {
				t.Fatalf("%s: block %s version %q, seed version %q", seed.SeatTypeSlug, slug, m.Version, seed.Version)
			}
			if _, err := mcpblock.Parse(m.Content); err != nil {
				t.Fatalf("%s: block %s: %v", seed.SeatTypeSlug, slug, err)
			}
		}
	}
}

// A seat type mounts the blocks it names, and a block becomes a module of kind mcp.
func TestLoadFSSelectsBlocks(t *testing.T) {
	fsys := withBlocks(t, withShared(t, fstest.MapFS{
		"seat-types/a.yaml": {Data: []byte(validFile + "mcp_blocks:\n  - sequential-thinking\n")},
	}))
	seeds, err := LoadFS(fsys)
	if err != nil {
		t.Fatal(err)
	}
	var block *seedmap.SeedModule
	for i := range seeds[0].Modules {
		if seeds[0].Modules[i].Kind == resolver.KindMCP {
			block = &seeds[0].Modules[i]
		}
	}
	if block == nil || block.Slug != "sequential-thinking" || block.Version != seeds[0].Version {
		t.Fatalf("mcp modules = %+v", seeds[0].Modules)
	}
}

func TestParseMCPBlockErrors(t *testing.T) {
	blocks, err := loadBlocks(embedded)
	if err != nil {
		t.Fatal(err)
	}
	cases := map[string]struct{ data, want string }{
		"unknown block":  {validFile + "mcp_blocks:\n  - nope\n", `unknown block "nope"`},
		"duplicate slug": {validFile + "mcp_blocks:\n  - agenthub-http\n  - agenthub-http\n", "already listed"},
	}
	for name, c := range cases {
		_, err := Parse("seat-types/x.yaml", []byte(c.data), nil, blocks)
		if err == nil || !strings.Contains(err.Error(), "seat-types/x.yaml") || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want file name and %q", name, err, c.want)
		}
	}

	// Two blocks mounting the same server name would silently shadow one another.
	colliding := map[string]seedmap.SeedModule{
		"one": {Slug: "one", Kind: resolver.KindMCP, Content: `{"name":"same","type":"http","url":"http://x"}`},
		"two": {Slug: "two", Kind: resolver.KindMCP, Content: `{"name":"same","type":"http","url":"http://y"}`},
	}
	_, err = Parse("seat-types/x.yaml", []byte(validFile+"mcp_blocks:\n  - one\n  - two\n"), nil, colliding)
	if err == nil || !strings.Contains(err.Error(), `server "same" is already mounted`) {
		t.Errorf("collision: err = %v, want a duplicate server error", err)
	}
}

// A block file is validated while the library loads, so a malformed or secret-carrying block
// is refused before it is ever stored.
func TestLoadFSRejectsBadBlockFile(t *testing.T) {
	cases := map[string]struct{ content, want string }{
		"malformed": {`{"name":"x","type":"http"}`, "field url is required"},
		"secret":    {`{"name":"x","type":"http","url":"http://x","headers":{"Authorization":"Bearer tok_0123456789abcdefghij"}}`, "credential-shaped"},
	}
	for name, c := range cases {
		fsys := withShared(t, fstest.MapFS{
			"blocks/broken.json": {Data: []byte(c.content)},
			"seat-types/a.yaml":  {Data: []byte(validFile)},
		})
		if _, err := LoadFS(fsys); err == nil || !strings.Contains(err.Error(), "broken.json") || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want broken.json and %q", name, err, c.want)
		}
	}
}

// The file name is the module slug, so it must match the module slug rule.
func TestLoadFSRejectsBadBlockFileName(t *testing.T) {
	fsys := withShared(t, fstest.MapFS{
		"blocks/Nope.json":  {Data: []byte(`{"name":"x","type":"http","url":"http://x"}`)},
		"seat-types/a.yaml": {Data: []byte(validFile)},
	})
	if _, err := LoadFS(fsys); err == nil || !strings.Contains(err.Error(), "block file name") {
		t.Errorf("err = %v, want a block file name error", err)
	}
}

// skillInventory is the slice of ai_docs/agent-system/skill-library.json this test consumes:
// the skill rows, the per-seat curation and the skills no default set wires.
type skillInventory struct {
	Count  int `json:"count"`
	Skills []struct {
		Name string `json:"name"`
	} `json:"skills"`
	SeatCuration map[string][]struct {
		Skill string `json:"skill"`
	} `json:"seat_curation"`
	UnusedByDefault []string `json:"unused_by_default"`
}

// loadSkillInventory reads the committed inventory the publish path consumes. The path is
// relative to this package directory, which is the working directory `go test` uses.
func loadSkillInventory(t *testing.T) skillInventory {
	t.Helper()
	path := filepath.Join("..", "..", "..", "..", "..", "ai_docs", "agent-system", "skill-library.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read skill inventory: %v", err)
	}
	var inventory skillInventory
	if err := json.Unmarshal(data, &inventory); err != nil {
		t.Fatalf("parse skill inventory: %v", err)
	}
	if inventory.Count != len(inventory.Skills) {
		t.Fatalf("inventory count %d != %d skill rows", inventory.Count, len(inventory.Skills))
	}
	return inventory
}

// Every seeded seat type carries exactly its curated skill refs from the inventory, every ref
// names a skill the inventory contains, and a skill in no default set stays unwired. The
// curation is the same committed data the publish path consumes, so an edit that is not
// mirrored into a seat YAML fails here.
func TestLoadEmbeddedSeedsCarryCuratedSkillRefs(t *testing.T) {
	inventory := loadSkillInventory(t)
	seeds, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	bySlug := make(map[string]seedmap.Seed, len(seeds))
	for _, seed := range seeds {
		bySlug[seed.SeatTypeSlug] = seed
	}
	if len(bySlug) != len(inventory.SeatCuration) {
		t.Fatalf("seeds = %d, curation seats = %d", len(bySlug), len(inventory.SeatCuration))
	}
	inInventory := make(map[string]bool, len(inventory.Skills))
	for _, row := range inventory.Skills {
		inInventory[row.Name] = true
	}

	for seat, entries := range inventory.SeatCuration {
		seed, ok := bySlug[seat]
		if !ok {
			t.Fatalf("seat %q has a curation but no seed", seat)
		}
		// The refs a seed carries beyond the modules it authors are its curated skills.
		authored := make(map[string]bool, len(seed.Modules))
		for _, module := range seed.Modules {
			authored[module.Slug] = true
		}
		refs := make(map[string]bool)
		for _, ref := range seed.ModuleRefs {
			if !authored[ref.Slug] {
				refs[ref.Slug] = true
			}
		}
		want := make(map[string]bool, len(entries))
		for _, entry := range entries {
			if !inInventory[entry.Skill] {
				t.Errorf("%s: curated skill %q is not in the inventory", seat, entry.Skill)
			}
			want[entry.Skill] = true
			if !refs[entry.Skill] {
				t.Errorf("%s: curated skill %q is not referenced by the seed", seat, entry.Skill)
			}
		}
		for slug := range refs {
			if !want[slug] {
				t.Errorf("%s: seed references skill %q that its curation does not assign", seat, slug)
			}
		}
	}

	// A skill in no default set is available in the catalog but wired nowhere.
	for _, name := range inventory.UnusedByDefault {
		for seat, seed := range bySlug {
			for _, ref := range seed.ModuleRefs {
				if ref.Slug == name {
					t.Errorf("%s: unused-by-default skill %q is wired into the seed", seat, name)
				}
			}
		}
	}
}
