package seedmap

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/agent_management/application/services"
	amentities "agenthub/fastmcp/agent_management/domain/entities"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/seat_management/domain/resolver"
)

type ruleFixture struct {
	name    string
	content string
}

type agentFixture struct {
	dir         string
	slug        string
	name        string
	description string
	version     string
	prompt      string
	rules       []ruleFixture
	output      string
}

func writeLibraryFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func buildLibrary(t *testing.T, agents ...agentFixture) string {
	t.Helper()
	root := t.TempDir()
	for _, agent := range agents {
		slug := agent.slug
		if slug == "" {
			slug = agent.dir
		}
		dir := filepath.Join(root, "agents", agent.dir)
		writeLibraryFile(t, filepath.Join(dir, "config.yaml"), fmt.Sprintf(
			"agent_info:\n  slug: %s\n  name: %s\n  description: %s\n  category: general\n  version: %s\n",
			slug, agent.name, agent.description, agent.version))
		writeLibraryFile(t, filepath.Join(dir, "capabilities.yaml"), "mcp_tools:\n  tools:\n    - read\n")
		writeLibraryFile(t, filepath.Join(dir, "contexts", strings.ReplaceAll(slug, "-", "_")+"_instructions.yaml"),
			"custom_instructions: \""+agent.prompt+"\"\n")
		for _, rule := range agent.rules {
			writeLibraryFile(t, filepath.Join(dir, "rules", rule.name+".yaml"), rule.content)
		}
		if agent.output != "" {
			writeLibraryFile(t, filepath.Join(dir, "output_format", "output_specification.yaml"),
				"output_specification:\n"+agent.output)
		}
	}
	return root
}

func loadTemplates(t *testing.T, root string) []*amentities.AgentTemplate {
	t.Helper()
	loader, err := services.NewYAMLAgentTemplateLoader(root)
	if err != nil {
		t.Fatal(err)
	}
	templates := loader.LoadAllAgents()
	if len(templates) == 0 {
		t.Fatal("no templates loaded")
	}
	return templates
}

func TestMapRoleModule(t *testing.T) {
	root := buildLibrary(t, agentFixture{
		dir: "coding-agent", name: "Coding Agent", description: "Writes code", version: "1.2.3",
		prompt: "  You are the coding agent.  ",
	})
	seed, err := Map(loadTemplates(t, root)[0])
	if err != nil {
		t.Fatal(err)
	}
	if seed.SeatTypeSlug != "coding-agent" || seed.SeatTypeName != "Coding Agent" || seed.Description != "Writes code" ||
		seed.DefaultRuntime != "claude-code" || seed.Version != "1.2.3" {
		t.Fatalf("unexpected seed identity: %+v", seed)
	}
	if len(seed.Modules) != 1 {
		t.Fatalf("modules = %d, want 1", len(seed.Modules))
	}
	role := seed.Modules[0]
	if role.Slug != "coding-agent-role" || role.Kind != resolver.KindInstruction ||
		role.Version != "1.0.0" || role.Content != "You are the coding agent." {
		t.Fatalf("unexpected role module: %+v", role)
	}
	if len(seed.ModuleRefs) != 1 || seed.ModuleRefs[0] != (resolver.ModuleRef{Slug: "coding-agent-role", Version: "1.0.0"}) {
		t.Fatalf("unexpected refs: %+v", seed.ModuleRefs)
	}
}

func TestMapRulesInOrderAndNormalised(t *testing.T) {
	root := buildLibrary(t, agentFixture{
		dir: "writer-agent", name: "Writer Agent", version: "1.0.0", prompt: "Write.",
		rules: []ruleFixture{
			{name: "Write-Tests_First", content: "always_test: true\n"},
			{name: "Keep-It_Simple", content: "simple: true\n"},
		},
	})
	seed, err := Map(loadTemplates(t, root)[0])
	if err != nil {
		t.Fatal(err)
	}
	// rules/*.yaml load in filename order: Keep-It_Simple.yaml before Write-Tests_First.yaml.
	if len(seed.Modules) != 3 {
		t.Fatalf("modules = %d, want 3", len(seed.Modules))
	}
	keep := seed.Modules[1]
	if keep.Slug != "writer-agent-rule-keep-it-simple" || keep.Kind != resolver.KindInstruction || keep.Version != "1.0.0" {
		t.Fatalf("unexpected keep module: %+v", keep)
	}
	if keep.Content != "### Keep-It_Simple\n\n```yaml\nsimple: true\n```\n" {
		t.Fatalf("keep content = %q", keep.Content)
	}
	write := seed.Modules[2]
	if write.Slug != "writer-agent-rule-write-tests-first" {
		t.Fatalf("write slug = %q", write.Slug)
	}
	if write.Content != "### Write-Tests_First\n\n```yaml\nalways_test: true\n```\n" {
		t.Fatalf("write content = %q", write.Content)
	}
	if seed.ModuleRefs[1].Slug != "writer-agent-rule-keep-it-simple" ||
		seed.ModuleRefs[2].Slug != "writer-agent-rule-write-tests-first" {
		t.Fatalf("refs = %+v", seed.ModuleRefs)
	}
}

func TestMapOutputFormatDocument(t *testing.T) {
	root := buildLibrary(t, agentFixture{
		dir: "format-agent", name: "Format Agent", version: "1.0.0", prompt: "Format.",
		output: "  format: markdown\n  tone: concise\n",
	})
	seed, err := Map(loadTemplates(t, root)[0])
	if err != nil {
		t.Fatal(err)
	}
	if len(seed.Modules) != 2 {
		t.Fatalf("modules = %d, want 2", len(seed.Modules))
	}
	doc := seed.Modules[1]
	if doc.Slug != "format-agent-output-format" || doc.Kind != resolver.KindDocument || doc.Version != "1.0.0" {
		t.Fatalf("unexpected output module: %+v", doc)
	}
	if doc.Content != "```yaml\nformat: markdown\ntone: concise\n```\n" {
		t.Fatalf("output content = %q", doc.Content)
	}
}

func TestMapDuplicateRuleNamesError(t *testing.T) {
	root := buildLibrary(t, agentFixture{
		dir: "dup-rule-agent", name: "Dup", version: "1.0.0", prompt: "Prompt.",
		rules: []ruleFixture{
			{name: "My_Rule", content: "a: true\n"},
			{name: "my-rule", content: "b: true\n"},
		},
	})
	if _, err := Map(loadTemplates(t, root)[0]); err == nil || !strings.Contains(err.Error(), "duplicate rule name") {
		t.Fatalf("err = %v, want duplicate rule name", err)
	}
}

func TestMapEmptySystemPromptError(t *testing.T) {
	template := &amentities.AgentTemplate{
		Slug: "empty-agent", Name: "Empty", Version: "1.0.0",
		DefaultConfiguration: &amvo.AgentConfiguration{SystemPrompt: "   "},
	}
	if _, err := Map(template); err == nil || !strings.Contains(err.Error(), "empty system prompt") {
		t.Fatalf("err = %v, want empty system prompt", err)
	}
}

func TestMapNilErrors(t *testing.T) {
	if _, err := Map(nil); err == nil {
		t.Fatal("nil template: expected error")
	}
	if _, err := Map(&amentities.AgentTemplate{Slug: "no-config", Name: "No Config", Version: "1.0.0"}); err == nil {
		t.Fatal("nil configuration: expected error")
	}
}

func TestMapBadRuleJSONError(t *testing.T) {
	template := &amentities.AgentTemplate{
		Slug: "bad-rule", Name: "Bad", Version: "1.0.0",
		DefaultConfiguration: &amvo.AgentConfiguration{SystemPrompt: "Prompt.", Rules: []string{"not json"}},
	}
	if _, err := Map(template); err == nil {
		t.Fatal("bad rule JSON: expected error")
	}
}

func TestMapDeterministic(t *testing.T) {
	root := buildLibrary(t, agentFixture{
		dir: "det-agent", name: "Det", version: "1.0.0", prompt: "Prompt.",
		rules:  []ruleFixture{{name: "Rule One", content: "one: true\n"}},
		output: "  format: markdown\n",
	})
	template := loadTemplates(t, root)[0]
	first, err := Map(template)
	if err != nil {
		t.Fatal(err)
	}
	second, err := Map(template)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(first, second) {
		t.Fatalf("Map is not deterministic:\n%+v\n%+v", first, second)
	}
}

func TestMapAllDuplicateModuleSlugError(t *testing.T) {
	root := buildLibrary(t,
		agentFixture{dir: "one", slug: "dup-agent", name: "One", version: "1.0.0", prompt: "One."},
		agentFixture{dir: "two", slug: "dup-agent", name: "Two", version: "1.0.0", prompt: "Two."},
	)
	if _, err := MapAll(loadTemplates(t, root)); err == nil || !strings.Contains(err.Error(), "duplicate module slug") {
		t.Fatalf("err = %v, want duplicate module slug", err)
	}
}

func TestMapAllNamesFailingSlug(t *testing.T) {
	template := &amentities.AgentTemplate{
		Slug: "broken-agent", Name: "Broken", Version: "1.0.0",
		DefaultConfiguration: &amvo.AgentConfiguration{SystemPrompt: ""},
	}
	if _, err := MapAll([]*amentities.AgentTemplate{template}); err == nil || !strings.Contains(err.Error(), "broken-agent") {
		t.Fatalf("err = %v, want it to name broken-agent", err)
	}
}

type seedCatalog struct {
	versions map[string]resolver.ModuleVersion
	latest   map[string]string
}

func (c *seedCatalog) Get(slug, version string) (resolver.ModuleVersion, bool) {
	mv, ok := c.versions[slug+"@"+version]
	return mv, ok
}

func (c *seedCatalog) Latest(slug string) (string, bool) {
	v, ok := c.latest[slug]
	return v, ok
}

func catalogFromSeeds(seeds []Seed) *seedCatalog {
	catalog := &seedCatalog{
		versions: make(map[string]resolver.ModuleVersion),
		latest:   make(map[string]string),
	}
	for _, seed := range seeds {
		for _, module := range seed.Modules {
			catalog.versions[module.Slug+"@"+module.Version] = resolver.ModuleVersion{
				Slug: module.Slug, Version: module.Version, Kind: module.Kind, Content: module.Content,
			}
			catalog.latest[module.Slug] = module.Version
		}
	}
	return catalog
}

func TestMapAllRealLibrary(t *testing.T) {
	dir := os.Getenv("AGENT_LIBRARY_DIR_PATH")
	if dir == "" {
		t.Skip("AGENT_LIBRARY_DIR_PATH not set")
	}
	loader, err := services.NewYAMLAgentTemplateLoader(dir)
	if err != nil {
		t.Fatalf("loader: %v", err)
	}
	templates := loader.LoadAllAgents()
	if len(templates) == 0 {
		t.Fatal("no templates loaded from real library")
	}
	seeds, err := MapAll(templates)
	if err != nil {
		t.Fatalf("MapAll: %v", err)
	}
	if len(seeds) != len(templates) {
		t.Fatalf("seeds = %d, templates = %d", len(seeds), len(templates))
	}
	t.Logf("mapped %d templates from %s", len(seeds), dir)
	catalog := catalogFromSeeds(seeds)
	for i, seed := range seeds {
		seatType := resolver.SeatTypeVersion{
			Slug: seed.SeatTypeSlug, Version: seed.Version, Runtime: seed.DefaultRuntime, Modules: seed.ModuleRefs,
		}
		seat, err := resolver.Resolve(catalog, seatType, nil)
		if err != nil {
			t.Fatalf("Resolve %q: %v", seed.SeatTypeSlug, err)
		}
		prompt := strings.TrimSpace(templates[i].DefaultConfiguration.SystemPrompt)
		roleSlug := seed.SeatTypeSlug + "-role"
		found := false
		for _, module := range seat.Modules {
			if module.Slug != roleSlug {
				continue
			}
			found = true
			if !strings.Contains(module.Content, prompt) {
				t.Fatalf("role module of %q does not contain its system prompt", seed.SeatTypeSlug)
			}
		}
		if !found {
			t.Fatalf("role module %q not resolved for %q", roleSlug, seed.SeatTypeSlug)
		}
	}
}
