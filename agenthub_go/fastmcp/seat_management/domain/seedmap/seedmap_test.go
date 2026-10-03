package seedmap

import (
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

func TestFromSpecRoleModule(t *testing.T) {
	seed, err := FromSpec(Spec{
		Slug: "developer", Name: "Developer", Description: "Writes code", DefaultRuntime: "codex",
		Role: "  You are the developer.  ", OutputFormat: "Reply in markdown.",
	})
	if err != nil {
		t.Fatal(err)
	}
	if seed.SeatTypeSlug != "developer" || seed.SeatTypeName != "Developer" || seed.Description != "Writes code" ||
		seed.DefaultRuntime != "codex" || seed.Version != seedVersion {
		t.Fatalf("unexpected seed identity: %+v", seed)
	}
	role := seed.Modules[0]
	if role.Slug != "developer-role" || role.Kind != resolver.KindInstruction ||
		role.Version != seedVersion || role.Content != "You are the developer." {
		t.Fatalf("unexpected role module: %+v", role)
	}
	if seed.ModuleRefs[0] != (resolver.ModuleRef{Slug: "developer-role", Version: seedVersion}) {
		t.Fatalf("unexpected refs: %+v", seed.ModuleRefs)
	}
}

func TestFromSpecRulesInOrderAndNormalised(t *testing.T) {
	seed, err := FromSpec(Spec{
		Slug: "writer", Role: "Write.", OutputFormat: "Markdown.",
		Rules: []Rule{
			{Name: "Write-Tests_First", Content: "Always test.\n"},
			{Name: "Keep-It_Simple", Content: "Stay simple."},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(seed.Modules) != 4 {
		t.Fatalf("modules = %d, want 4", len(seed.Modules))
	}
	first := seed.Modules[1]
	if first.Slug != "writer-rule-write-tests-first" || first.Kind != resolver.KindInstruction || first.Version != seedVersion {
		t.Fatalf("unexpected first rule: %+v", first)
	}
	if first.Content != "### Write-Tests_First\n\nAlways test.\n" {
		t.Fatalf("first content = %q", first.Content)
	}
	if seed.Modules[2].Slug != "writer-rule-keep-it-simple" {
		t.Fatalf("second slug = %q", seed.Modules[2].Slug)
	}
	if seed.ModuleRefs[1].Slug != "writer-rule-write-tests-first" || seed.ModuleRefs[2].Slug != "writer-rule-keep-it-simple" {
		t.Fatalf("refs = %+v", seed.ModuleRefs)
	}
}

func TestFromSpecOutputFormatDocument(t *testing.T) {
	seed, err := FromSpec(Spec{Slug: "tester", Role: "Test.", OutputFormat: "  Report pass/fail.  "})
	if err != nil {
		t.Fatal(err)
	}
	doc := seed.Modules[len(seed.Modules)-1]
	if doc.Slug != "tester-output-format" || doc.Kind != resolver.KindDocument || doc.Version != seedVersion {
		t.Fatalf("unexpected output module: %+v", doc)
	}
	if doc.Content != "Report pass/fail.\n" {
		t.Fatalf("output content = %q", doc.Content)
	}
}

func TestFromSpecErrors(t *testing.T) {
	cases := map[string]struct {
		spec Spec
		want string
	}{
		"empty role":      {Spec{Slug: "a", Role: "  ", OutputFormat: "x"}, "empty role"},
		"empty output":    {Spec{Slug: "a", Role: "r", OutputFormat: " "}, "empty output format"},
		"empty rule name": {Spec{Slug: "a", Role: "r", OutputFormat: "x", Rules: []Rule{{Name: "--", Content: "c"}}}, "empty name"},
		"duplicate rule": {Spec{Slug: "a", Role: "r", OutputFormat: "x", Rules: []Rule{
			{Name: "My_Rule", Content: "a"}, {Name: "my-rule", Content: "b"}}}, "duplicate rule name"},
	}
	for name, c := range cases {
		if _, err := FromSpec(c.spec); err == nil || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want %q", name, err, c.want)
		}
	}
}

func TestFromSpecDeterministic(t *testing.T) {
	spec := Spec{Slug: "det", Role: "Prompt.", OutputFormat: "md", Rules: []Rule{{Name: "Rule One", Content: "one"}}}
	first, err := FromSpec(spec)
	if err != nil {
		t.Fatal(err)
	}
	second, err := FromSpec(spec)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(first, second) {
		t.Fatalf("FromSpec is not deterministic:\n%+v\n%+v", first, second)
	}
}

func TestFromSpecSharedModules(t *testing.T) {
	shared := []SeedModule{
		{Slug: "guard", Kind: resolver.KindTool, Content: `{"a":1}`},
		{Slug: "guard-skill", Kind: resolver.KindSkill, Content: "skill"},
	}
	claude, err := FromSpec(Spec{Slug: "dev", Role: "Dev.", OutputFormat: "Out.", DefaultRuntime: "claude-code", Shared: shared})
	if err != nil {
		t.Fatal(err)
	}
	if got := slugs(claude); got != "dev-role,dev-output-format,guard,guard-skill" {
		t.Fatalf("claude-code modules = %s", got)
	}
	for _, m := range claude.Modules[2:] {
		if m.Version != seedVersion {
			t.Fatalf("shared module %s version = %q, want %q", m.Slug, m.Version, seedVersion)
		}
	}
	if len(claude.ModuleRefs) != 4 {
		t.Fatalf("module refs = %v, want one per module", claude.ModuleRefs)
	}
	// A tool module is Claude settings JSON: a codex seat type gets only the skill.
	codex, err := FromSpec(Spec{Slug: "dev", Role: "Dev.", OutputFormat: "Out.", DefaultRuntime: "codex", Shared: shared})
	if err != nil {
		t.Fatal(err)
	}
	if got := slugs(codex); got != "dev-role,dev-output-format,guard-skill" {
		t.Fatalf("codex modules = %s", got)
	}
}

func slugs(seed Seed) string {
	out := make([]string, len(seed.Modules))
	for i, m := range seed.Modules {
		out[i] = m.Slug
	}
	return strings.Join(out, ",")
}
