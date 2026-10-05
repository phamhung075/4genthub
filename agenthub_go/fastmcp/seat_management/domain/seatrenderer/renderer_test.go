package seatrenderer

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seedlibrary"

	"gopkg.in/yaml.v3"
)

const testMCPURL = "https://mcp.4genthub.test/mcp"

func seatFixture(runtime string) resolver.ResolvedSeat {
	return resolver.ResolvedSeat{
		SeatType:        "seat.standard",
		SeatTypeVersion: "1.2.0",
		Runtime:         runtime,
		Modules: []resolver.ResolvedModule{
			{Slug: "instr.base", Version: "1.0.0", Kind: resolver.KindInstruction, Content: "Base instruction."},
			{Slug: "doc.guide", Version: "2.0.0", Kind: resolver.KindDocument, Content: "Guide document."},
			{Slug: "skill.alpha", Version: "1.0.0", Kind: resolver.KindSkill, Content: "# Alpha skill\n"},
			{Slug: "mem.gamma", Version: "1.0.0", Kind: resolver.KindMemory, Content: "Gamma memory."},
		},
		Hash: "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
	}
}

func withModules(seat resolver.ResolvedSeat, modules []resolver.ResolvedModule) resolver.ResolvedSeat {
	seat.Modules = modules
	return seat
}

// mcpPlatformModule is the platform's own server block: the same payload the seed library
// publishes as `agenthub-http`, with its url resolved by the renderer from the seat's mcp url.
func mcpPlatformModule() resolver.ResolvedModule {
	return resolver.ResolvedModule{
		Slug: "agenthub-http", Version: "1.2.0", Kind: resolver.KindMCP,
		Content: `{"name":"agenthub_http","type":"http","url":"${AGENTHUB_MCP_URL}","headers":{"Accept":"application/json, text/event-stream","Authorization":"Bearer ${AGENTHUB_TOKEN}"}}`,
	}
}

func sequentialThinkingModule() resolver.ResolvedModule {
	return resolver.ResolvedModule{
		Slug: "sequential-thinking", Version: "1.2.0", Kind: resolver.KindMCP,
		Content: `{"name":"sequential-thinking","type":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-sequential-thinking"]}`,
	}
}

// withMCP appends mounted mcp blocks to a seat copy.
func withMCP(seat resolver.ResolvedSeat, blocks ...resolver.ResolvedModule) resolver.ResolvedSeat {
	modules := append([]resolver.ResolvedModule{}, seat.Modules...)
	seat.Modules = append(modules, blocks...)
	return seat
}

// seedModules renders a seeded seat type's modules as if the resolver had produced them.
func seedModules(t *testing.T, slug string) []resolver.ResolvedModule {
	t.Helper()
	seeds, err := seedlibrary.Load()
	if err != nil {
		t.Fatal(err)
	}
	for _, seed := range seeds {
		if seed.SeatTypeSlug != slug {
			continue
		}
		modules := make([]resolver.ResolvedModule, len(seed.Modules))
		for i, m := range seed.Modules {
			modules[i] = resolver.ResolvedModule{Slug: m.Slug, Version: m.Version, Kind: m.Kind, Content: m.Content}
		}
		return modules
	}
	t.Fatalf("seed %q not found", slug)
	return nil
}

type mcpServerJSON struct {
	Type    string            `json:"type"`
	URL     string            `json:"url"`
	Command string            `json:"command"`
	Args    []string          `json:"args"`
	Headers map[string]string `json:"headers"`
}

func mcpServers(t *testing.T, spec *OpenRigSpec) map[string]mcpServerJSON {
	t.Helper()
	var doc struct {
		MCPServers map[string]mcpServerJSON `json:"mcpServers"`
	}
	if err := json.Unmarshal([]byte(fileContent(t, spec, mcpFragmentPath)), &doc); err != nil {
		t.Fatalf("parse mcp fragment: %v", err)
	}
	return doc.MCPServers
}

func filePaths(spec *OpenRigSpec) []string {
	out := make([]string, len(spec.Files))
	for i, f := range spec.Files {
		out[i] = f.Path
	}
	return out
}

func fileContent(t *testing.T, spec *OpenRigSpec, path string) string {
	t.Helper()
	for _, f := range spec.Files {
		if f.Path == path {
			return f.Content
		}
	}
	t.Fatalf("file %q not rendered", path)
	return ""
}

type parsedAgentYAML struct {
	Name     string `yaml:"name"`
	Version  string `yaml:"version"`
	Defaults struct {
		Runtime string `yaml:"runtime"`
	} `yaml:"defaults"`
	Profiles map[string]struct {
		Uses struct {
			Skills           []string `yaml:"skills"`
			RuntimeResources []string `yaml:"runtime_resources"`
		} `yaml:"uses"`
	} `yaml:"profiles"`
	Resources struct {
		Skills []struct {
			ID   string `yaml:"id"`
			Path string `yaml:"path"`
		} `yaml:"skills"`
		RuntimeResources []struct {
			ID      string `yaml:"id"`
			Path    string `yaml:"path"`
			Runtime string `yaml:"runtime"`
			Type    string `yaml:"type"`
		} `yaml:"runtime_resources"`
	} `yaml:"resources"`
	Startup struct {
		Files []struct {
			Path         string `yaml:"path"`
			DeliveryHint string `yaml:"delivery_hint"`
			Required     bool   `yaml:"required"`
		} `yaml:"files"`
	} `yaml:"startup"`
}

func parseAgentYAML(t *testing.T, spec *OpenRigSpec) parsedAgentYAML {
	t.Helper()
	var parsed parsedAgentYAML
	if err := yaml.Unmarshal([]byte(fileContent(t, spec, agentYAMLPath)), &parsed); err != nil {
		t.Fatalf("parse agent.yaml: %v", err)
	}
	return parsed
}

// assertNoSecret fails if any rendered file carries a literal bearer credential;
// the spec may only reference the token through its environment variable.
func assertNoSecret(t *testing.T, spec *OpenRigSpec) {
	t.Helper()
	token := os.Getenv(OpenRigTokenEnvVar)
	for _, f := range spec.Files {
		if i := strings.Index(f.Content, "Bearer "); i >= 0 && !strings.HasPrefix(f.Content[i+len("Bearer "):], "${") {
			t.Fatalf("file %q carries a literal bearer credential", f.Path)
		}
		if token != "" && strings.Contains(f.Content, token) {
			t.Fatalf("file %q embeds the live %s value", f.Path, OpenRigTokenEnvVar)
		}
	}
}

func TestRenderSeatClaudeCode(t *testing.T) {
	seat := withMCP(seatFixture("claude-code"), mcpPlatformModule())
	spec, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}
	if spec.Slug != "seat.standard" || spec.Version != "1.2.0" {
		t.Fatalf("identity = %q/%q, want seat.standard/1.2.0", spec.Slug, spec.Version)
	}
	wantPaths := []string{
		"agent.yaml",
		"guidance/role.md",
		"skills/skill.alpha/SKILL.md",
		"runtime/claude-mcp.fragment.json",
	}
	if got := filePaths(spec); !reflect.DeepEqual(got, wantPaths) {
		t.Fatalf("file paths = %v, want %v", got, wantPaths)
	}

	guidance := fileContent(t, spec, guidancePath)
	if !strings.HasPrefix(guidance, "<!-- seat-hash: "+seat.Hash+" -->\n") {
		t.Fatalf("guidance does not start with the seat hash comment:\n%s", guidance)
	}
	if !strings.Contains(guidance, "<!-- seat-type-version: 1.2.0 -->") {
		t.Fatalf("guidance missing seat type version:\n%s", guidance)
	}
	instr := strings.Index(guidance, "## instr.base")
	doc := strings.Index(guidance, "## Document: doc.guide")
	mem := strings.Index(guidance, "## Memory: mem.gamma")
	if instr < 0 || doc < instr || mem < doc {
		t.Fatalf("guidance ordering wrong (instruction=%d document=%d memory=%d):\n%s", instr, doc, mem, guidance)
	}
	if !strings.Contains(guidance, "Base instruction.") || !strings.Contains(guidance, "Guide document.") || !strings.Contains(guidance, "Gamma memory.") {
		t.Fatalf("guidance missing module content:\n%s", guidance)
	}

	mcp := fileContent(t, spec, mcpFragmentPath)
	if !strings.Contains(mcp, "Bearer ${"+OpenRigTokenEnvVar+"}") {
		t.Fatalf("mcp fragment missing token indirection:\n%s", mcp)
	}
	if !strings.Contains(mcp, `"url": "`+testMCPURL+`"`) {
		t.Fatalf("mcp fragment missing the resolved platform url:\n%s", mcp)
	}
	var mcpDoc map[string]any
	if err := json.Unmarshal([]byte(mcp), &mcpDoc); err != nil {
		t.Fatalf("mcp fragment is not JSON: %v", err)
	}
	assertNoSecret(t, spec)

	parsed := parseAgentYAML(t, spec)
	if parsed.Name != "seat.standard" || parsed.Version != "1.2.0" {
		t.Fatalf("agent.yaml name/version = %q/%q", parsed.Name, parsed.Version)
	}
	if parsed.Defaults.Runtime != "claude-code" {
		t.Fatalf("defaults.runtime = %q, want claude-code", parsed.Defaults.Runtime)
	}
	if len(parsed.Resources.Skills) != 1 || parsed.Resources.Skills[0].ID != "skill.alpha" || parsed.Resources.Skills[0].Path != "skills/skill.alpha" {
		t.Fatalf("skills resources = %+v", parsed.Resources.Skills)
	}
	if len(parsed.Resources.RuntimeResources) != 1 {
		t.Fatalf("runtime resources = %+v", parsed.Resources.RuntimeResources)
	}
	res := parsed.Resources.RuntimeResources[0]
	if res.ID != "claude-mcp" || res.Path != mcpFragmentPath || res.Runtime != "claude-code" || res.Type != "claude_mcp_fragment" {
		t.Fatalf("mcp runtime resource = %+v", res)
	}
	uses := parsed.Profiles["default"].Uses
	if !reflect.DeepEqual(uses.Skills, []string{"skill.alpha"}) || !reflect.DeepEqual(uses.RuntimeResources, []string{"claude-mcp"}) {
		t.Fatalf("uses = skills %v runtime_resources %v", uses.Skills, uses.RuntimeResources)
	}
	if len(parsed.Startup.Files) != 1 || parsed.Startup.Files[0].Path != guidancePath || parsed.Startup.Files[0].DeliveryHint != "send_text" || !parsed.Startup.Files[0].Required {
		t.Fatalf("startup files = %+v", parsed.Startup.Files)
	}
}

func TestRenderSeatCodex(t *testing.T) {
	seat := seatFixture("codex")
	spec, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}
	wantPaths := []string{
		"agent.yaml",
		"guidance/role.md",
		"skills/skill.alpha/SKILL.md",
	}
	if got := filePaths(spec); !reflect.DeepEqual(got, wantPaths) {
		t.Fatalf("file paths = %v, want %v", got, wantPaths)
	}
	for _, path := range filePaths(spec) {
		if strings.HasPrefix(path, "runtime/") {
			t.Fatalf("codex seat rendered runtime fragment %q", path)
		}
	}
	guidance := fileContent(t, spec, guidancePath)
	if !strings.HasPrefix(guidance, "<!-- seat-hash: "+seat.Hash+" -->") {
		t.Fatalf("guidance missing seat hash:\n%s", guidance)
	}
	assertNoSecret(t, spec)

	parsed := parseAgentYAML(t, spec)
	if parsed.Defaults.Runtime != "codex" {
		t.Fatalf("defaults.runtime = %q, want codex", parsed.Defaults.Runtime)
	}
	if len(parsed.Resources.RuntimeResources) != 0 || len(parsed.Profiles["default"].Uses.RuntimeResources) != 0 {
		t.Fatalf("codex seat has runtime resources: %+v / %v", parsed.Resources.RuntimeResources, parsed.Profiles["default"].Uses.RuntimeResources)
	}
}

func TestRenderSeatUnsupportedRuntimeError(t *testing.T) {
	if _, err := RenderSeat(seatFixture("python"), testMCPURL); err == nil || !strings.Contains(err.Error(), "unsupported runtime") {
		t.Fatalf("error = %v, want unsupported runtime", err)
	}
}

func TestRenderSeatDeterministic(t *testing.T) {
	seat := seatFixture("claude-code")
	first, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("first RenderSeat: %v", err)
	}
	second, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("second RenderSeat: %v", err)
	}
	if !reflect.DeepEqual(first.Files, second.Files) {
		t.Fatal("rendering the same seat twice produced different files")
	}
}

func TestRenderSeatToolModulesMerge(t *testing.T) {
	seat := withModules(seatFixture("claude-code"), []resolver.ResolvedModule{
		{Slug: "instr.base", Version: "1.0.0", Kind: resolver.KindInstruction, Content: "Base instruction."},
		mcpPlatformModule(),
		{Slug: "tool.alpha", Version: "1.0.0", Kind: resolver.KindTool, Content: `{"b":1,"a":2}`},
		{Slug: "tool.zeta", Version: "1.0.0", Kind: resolver.KindTool, Content: `{"a":3}`},
	})
	spec, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}
	wantPaths := []string{
		"agent.yaml",
		"guidance/role.md",
		"runtime/claude-mcp.fragment.json",
		"runtime/claude-settings.fragment.json",
	}
	if got := filePaths(spec); !reflect.DeepEqual(got, wantPaths) {
		t.Fatalf("file paths = %v, want %v", got, wantPaths)
	}
	settings := fileContent(t, spec, settingsFragmentPath)
	wantSettings := "{\n  \"a\": 3,\n  \"b\": 1\n}\n"
	if settings != wantSettings {
		t.Fatalf("settings fragment = %q, want %q", settings, wantSettings)
	}
	parsed := parseAgentYAML(t, spec)
	if len(parsed.Resources.RuntimeResources) != 2 {
		t.Fatalf("runtime resources = %+v", parsed.Resources.RuntimeResources)
	}
	settingsRes := parsed.Resources.RuntimeResources[1]
	if settingsRes.ID != "claude-settings" || settingsRes.Type != "claude_settings_fragment" || settingsRes.Runtime != "claude-code" {
		t.Fatalf("settings runtime resource = %+v", settingsRes)
	}
	if !reflect.DeepEqual(parsed.Profiles["default"].Uses.RuntimeResources, []string{"claude-mcp", "claude-settings"}) {
		t.Fatalf("uses.runtime_resources = %v", parsed.Profiles["default"].Uses.RuntimeResources)
	}
}

func TestMergeToolModulesPermissions(t *testing.T) {
	merge := func(contents ...string) (map[string]any, error) {
		modules := make([]resolver.ResolvedModule, len(contents))
		for i, c := range contents {
			modules[i] = resolver.ResolvedModule{Slug: "tool." + string(rune('a'+i)), Kind: resolver.KindTool, Content: c}
		}
		return mergeToolModules(modules)
	}
	merged, err := merge(
		`{"permissions":{"deny":["x","y"],"allow":["p"],"defaultMode":"plan"},"model":"one"}`,
		`{"permissions":{"deny":["y","z"],"ask":["q"],"defaultMode":"acceptEdits"},"model":"two","env":{"A":"1"}}`,
	)
	if err != nil {
		t.Fatal(err)
	}
	got, _ := json.Marshal(merged)
	want := `{"env":{"A":"1"},"model":"two","permissions":{"allow":["p"],"ask":["q"],"defaultMode":"acceptEdits","deny":["x","y","z"]}}`
	if string(got) != want {
		t.Fatalf("merged = %s\nwant     %s", got, want)
	}

	// an empty list stays a list (never null)
	empty, err := merge(`{"permissions":{"deny":[]}}`)
	if err != nil {
		t.Fatal(err)
	}
	if got, _ := json.Marshal(empty); string(got) != `{"permissions":{"deny":[]}}` {
		t.Fatalf("empty deny list merged to %s", got)
	}

	for name, contents := range map[string][]string{
		"deny not an array":  {`{"permissions":{"deny":"x"}}`},
		"allow not strings":  {`{"permissions":{"allow":[1]}}`},
		"ask not an array":   {`{"permissions":{"deny":["x"]}}`, `{"permissions":{"ask":{"a":1}}}`},
		"permissions scalar": {`{"permissions":"all"}`},
	} {
		if _, err := merge(contents...); err == nil {
			t.Errorf("%s: want an error", name)
		}
	}
}

// The seeded comm-guard keeps its deny rules when another tool module also sets permissions,
// and the seat carries the skill that names seatcheck as the only send path.
func TestRenderSeatKeepsCommGuardNextToAnotherToolModule(t *testing.T) {
	seeds, err := seedlibrary.Load()
	if err != nil {
		t.Fatal(err)
	}
	var modules []resolver.ResolvedModule
	for _, m := range seeds[0].Modules {
		modules = append(modules, resolver.ResolvedModule{Slug: m.Slug, Version: m.Version, Kind: m.Kind, Content: m.Content})
	}
	modules = append(modules, resolver.ResolvedModule{
		Slug: "tool.extra", Version: "1.0.0", Kind: resolver.KindTool,
		Content: `{"permissions":{"deny":["Bash(rm:*)"],"allow":["Read"]}}`,
	})
	spec, err := RenderSeat(withModules(seatFixture("claude-code"), modules), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}
	var settings struct {
		Permissions struct {
			Deny  []string `json:"deny"`
			Allow []string `json:"allow"`
		} `json:"permissions"`
	}
	if err := json.Unmarshal([]byte(fileContent(t, spec, settingsFragmentPath)), &settings); err != nil {
		t.Fatal(err)
	}
	wantDeny := "Bash(rig send:*)|Bash(rig queue:*)|Bash(rig broadcast:*)|Bash(tmux send-keys:*)|Bash(tmux paste-buffer:*)|Bash(rm:*)"
	if strings.Join(settings.Permissions.Deny, "|") != wantDeny || strings.Join(settings.Permissions.Allow, "|") != "Bash(seatcheck send:*)|Bash(rig whoami:*)|Read" {
		t.Fatalf("permissions = %+v", settings.Permissions)
	}
	if skill := fileContent(t, spec, "skills/comm-guard-skill/SKILL.md"); !strings.Contains(skill, "seatcheck send") {
		t.Fatalf("skill does not name seatcheck send:\n%s", skill)
	}
}

func TestRenderSeatToolModuleInvalidJSONError(t *testing.T) {
	seat := withModules(seatFixture("claude-code"), []resolver.ResolvedModule{
		{Slug: "tool.bad", Version: "1.0.0", Kind: resolver.KindTool, Content: `[1,2,3]`},
	})
	if _, err := RenderSeat(seat, testMCPURL); err == nil || !strings.Contains(err.Error(), "tool.bad") {
		t.Fatalf("error = %v, want tool.bad JSON error", err)
	}
}

// A seat can switch runtime while its pinned seat type version keeps the seeded modules, so
// the same modules must render on every runtime: claude-code applies the tool module, codex
// and agy skip it (a tool module is a Claude settings fragment) and keep the skill.
func TestRenderSeatSameModulesOnBothRuntimes(t *testing.T) {
	seeds, err := seedlibrary.Load()
	if err != nil {
		t.Fatal(err)
	}
	var modules []resolver.ResolvedModule
	for _, m := range seeds[0].Modules {
		modules = append(modules, resolver.ResolvedModule{Slug: m.Slug, Version: m.Version, Kind: m.Kind, Content: m.Content})
	}

	claude, err := RenderSeat(withModules(seatFixture("claude-code"), modules), testMCPURL)
	if err != nil {
		t.Fatalf("claude-code: %v", err)
	}
	if settings := fileContent(t, claude, settingsFragmentPath); strings.Count(settings, "Bash(") != 7 {
		t.Fatalf("claude-code settings fragment should carry the 5 denies and the 2 allows:\n%s", settings)
	}

	codex, err := RenderSeat(withModules(seatFixture("codex"), modules), testMCPURL)
	if err != nil {
		t.Fatalf("codex: %v", err)
	}
	rules := fileContent(t, codex, codexRulesPath)
	for _, want := range []string{
		`pattern = ["rig", "send"]`,
		`pattern = ["rig", "queue"]`,
		`pattern = ["rig", "broadcast"]`,
		`pattern = ["tmux", "send-keys"]`,
		`pattern = ["tmux", "paste-buffer"]`,
	} {
		if !strings.Contains(rules, want) {
			t.Fatalf("codex rules missing %s:\n%s", want, rules)
		}
	}
	if got := strings.Count(rules, `decision = "forbidden"`); got != 5 {
		t.Fatalf("codex rules carry %d forbidden rules, want the 5 denies:\n%s", got, rules)
	}
	if strings.Contains(rules, "claude") {
		t.Fatalf("codex rules mention claude:\n%s", rules)
	}
	if skill := fileContent(t, codex, "skills/comm-guard-skill/SKILL.md"); !strings.Contains(skill, "seatcheck send") {
		t.Fatalf("codex skill does not name seatcheck send:\n%s", skill)
	}

	for _, runtime := range []string{"agy", "omp"} {
		spec, err := RenderSeat(withModules(seatFixture(runtime), modules), testMCPURL)
		if err != nil {
			t.Fatalf("%s: %v", runtime, err)
		}
		for _, path := range filePaths(spec) {
			if strings.HasPrefix(path, "runtime/") {
				t.Errorf("%s seat has a runtime file %q", runtime, path)
			}
		}
		if skill := fileContent(t, spec, "skills/comm-guard-skill/SKILL.md"); !strings.Contains(skill, "seatcheck send") {
			t.Fatalf("%s skill does not name seatcheck send:\n%s", runtime, skill)
		}
	}
}

func TestRenderSeatCodexRulesDenyTheDirectSendSurface(t *testing.T) {
	guard := resolver.ResolvedModule{
		Slug: "comm-guard", Version: "1.1.1", Kind: resolver.KindTool,
		Content: `{"permissions":{"deny":["Bash(rig send:*)","Bash(rig queue:*)","Bash(rig broadcast:*)","Bash(tmux send-keys:*)","Bash(tmux paste-buffer:*)"],"allow":["Bash(seatcheck send:*)","Bash(rig whoami:*)"]}}`,
	}

	codex, err := RenderSeat(withModules(seatFixture("codex"), []resolver.ResolvedModule{guard}), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(codex): %v", err)
	}
	rules := fileContent(t, codex, codexRulesPath)
	for _, want := range []string{`pattern = ["rig", "send"]`, `pattern = ["tmux", "paste-buffer"]`} {
		if !strings.Contains(rules, want) {
			t.Fatalf("rules missing %s:\n%s", want, rules)
		}
	}
	// Deny-only on purpose: an `allow` prefix rule would widen what runs outside the sandbox
	// without prompting, which is not what this artefact is for. The justification may still
	// *recommend* the audited path; what must not appear is an allow rule for it.
	if strings.Contains(rules, `decision = "allow"`) || strings.Contains(rules, `pattern = ["seatcheck", "send"]`) {
		t.Fatalf("codex rules widen execution instead of only denying:\n%s", rules)
	}
	for _, path := range filePaths(codex) {
		if strings.Contains(path, "claude") {
			t.Fatalf("codex seat rendered a claude artefact %q", path)
		}
	}

	// The Claude path is untouched and does not gain the codex artefact.
	claude, err := RenderSeat(withModules(seatFixture("claude-code"), []resolver.ResolvedModule{guard}), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(claude-code): %v", err)
	}
	for _, path := range filePaths(claude) {
		if path == codexRulesPath {
			t.Fatalf("claude-code seat rendered the codex rules file")
		}
	}
	if settings := fileContent(t, claude, settingsFragmentPath); !strings.Contains(settings, "Bash(rig send:*)") {
		t.Fatalf("claude-code settings fragment lost the deny list:\n%s", settings)
	}

	// No tool module means no deny list, so no codex rules file either.
	plain, err := RenderSeat(seatFixture("codex"), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(codex, no tools): %v", err)
	}
	for _, path := range filePaths(plain) {
		if path == codexRulesPath {
			t.Fatalf("codex seat without tool modules rendered %q", codexRulesPath)
		}
	}

	// An entry that cannot be a command prefix must be LISTED, never silently dropped: the branch
	// exists so a policy the seat believes it carries is visible in the artefact.
	mixed := resolver.ResolvedModule{
		Slug: "comm-guard", Version: "1.1.1", Kind: resolver.KindTool,
		Content: `{"permissions":{"deny":["Bash(rig send:*)","Read(/etc/shadow)"]}}`,
	}
	spec, err := RenderSeat(withModules(seatFixture("codex"), []resolver.ResolvedModule{mixed}), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(codex, mixed denies): %v", err)
	}
	mixedRules := fileContent(t, spec, codexRulesPath)
	if strings.Count(mixedRules, `decision = "forbidden"`) != 1 {
		t.Fatalf("only the Bash entry is a prefix rule, got:\n%s", mixedRules)
	}
	if !strings.Contains(mixedRules, "#   Read(/etc/shadow)") {
		t.Fatalf("the non-Bash deny entry was dropped instead of listed:\n%s", mixedRules)
	}
}

func TestRenderSeatUnsupportedMCPURL(t *testing.T) {
	seat := withMCP(seatFixture("claude-code"), mcpPlatformModule())
	if _, err := RenderSeat(seat, "ftp://mcp.example"); err == nil || !strings.Contains(err.Error(), "http") {
		t.Fatalf("error = %v, want mcp url error", err)
	}
}

// One mcp block is one whole server: the seat's blocks decide which servers mount, and the
// built-in server travels through the same merge rather than around it.
func TestRenderSeatMCPBlocksMountEveryServer(t *testing.T) {
	spec, err := RenderSeat(withMCP(seatFixture("claude-code"), mcpPlatformModule(), sequentialThinkingModule()), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat([A,B]): %v", err)
	}
	servers := mcpServers(t, spec)
	if len(servers) != 2 || servers["agenthub_http"].URL != testMCPURL || servers["sequential-thinking"].Command != "npx" {
		t.Fatalf("servers from [A,B] = %+v", servers)
	}
	if servers["agenthub_http"].Headers["Authorization"] != "Bearer ${"+OpenRigTokenEnvVar+"}" {
		t.Fatalf("platform headers = %v", servers["agenthub_http"].Headers)
	}
	assertNoSecret(t, spec)

	single, err := RenderSeat(withMCP(seatFixture("claude-code"), mcpPlatformModule()), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat([A]): %v", err)
	}
	if got := mcpServers(t, single); len(got) != 1 {
		t.Fatalf("servers from [A] = %+v, want only agenthub_http", got)
	}
}

// No mcp block mounts NO server: no fragment file, no claude_mcp runtime resource, and no
// dependency on the mcp url at all. A hidden default is exactly what this pins against.
func TestRenderSeatWithoutMCPBlocksMountsNoServer(t *testing.T) {
	spec, err := RenderSeat(seatFixture("claude-code"), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(no mcp blocks): %v", err)
	}
	for _, path := range filePaths(spec) {
		if path == mcpFragmentPath {
			t.Fatalf("a seat with no mcp block rendered %q", path)
		}
	}
	parsed := parseAgentYAML(t, spec)
	if len(parsed.Resources.RuntimeResources) != 0 || len(parsed.Profiles["default"].Uses.RuntimeResources) != 0 {
		t.Fatalf("a seat with no mcp block declared runtime resources: %+v", parsed.Resources.RuntimeResources)
	}
	if _, err := RenderSeat(seatFixture("claude-code"), ""); err != nil {
		t.Fatalf("no mcp block must not need an mcp url: %v", err)
	}
}

// One server mounted twice would be a block that silently does nothing, so it is an error.
func TestRenderSeatMCPDuplicateServerError(t *testing.T) {
	duplicate := resolver.ResolvedModule{
		Slug: "mcp.other", Version: "1.0.0", Kind: resolver.KindMCP,
		Content: `{"name":"agenthub_http","type":"http","url":"https://other.example.test/mcp"}`,
	}
	seat := withMCP(seatFixture("claude-code"), mcpPlatformModule(), duplicate)
	if _, err := RenderSeat(seat, testMCPURL); err == nil || !strings.Contains(err.Error(), "already mounted") {
		t.Fatalf("error = %v, want a duplicate server error naming the block", err)
	}
}

// An mcp block's content is validated at render time, which also covers an overlay override:
// override content never passes the module publish path's secret scan.
func TestRenderSeatMCPBlockInvalidError(t *testing.T) {
	cases := map[string]struct{ content, want string }{
		"secret": {`{"name":"leaky","type":"http","url":"http://x","headers":{"Authorization":"Bearer tok_0123456789abcdefghij"}}`, "credential-shaped"},
		"shape":  {`{"name":"broken","type":"http","command":"npx"}`, "field url is required"},
		"json":   {`[1,2,3]`, "not a server object"},
	}
	for name, c := range cases {
		seat := withMCP(seatFixture("claude-code"), resolver.ResolvedModule{
			Slug: "mcp.bad", Version: "1.0.0", Kind: resolver.KindMCP, Content: c.content,
		})
		if _, err := RenderSeat(seat, testMCPURL); err == nil || !strings.Contains(err.Error(), "mcp.bad") || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want mcp.bad and %q", name, err, c.want)
		}
	}
}

// A tool module narrows permissions inside a mounted server and never mounts one: its JSON
// goes only into the settings fragment, so a server it names cannot reappear through it.
func TestRenderSeatPermissionNarrowsWithinMountedServerOnly(t *testing.T) {
	guard := resolver.ResolvedModule{
		Slug: "comm-guard", Version: "1.1.1", Kind: resolver.KindTool,
		Content: `{"permissions":{"deny":["Bash(rig send:*)"],"allow":["Bash(seatcheck send:*)"]},"mcpServers":{"filesystem":{"type":"stdio","command":"npx"}}}`,
	}

	mounted := withMCP(seatFixture("claude-code"), mcpPlatformModule(), guard)
	spec, err := RenderSeat(mounted, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(mounted): %v", err)
	}
	servers := mcpServers(t, spec)
	if len(servers) != 1 || servers["agenthub_http"].URL != testMCPURL {
		t.Fatalf("a tool module changed the mounted server set: %+v", servers)
	}
	if _, resurrected := servers["filesystem"]; resurrected {
		t.Fatalf("a tool module mounted a server: %+v", servers)
	}
	settings := fileContent(t, spec, settingsFragmentPath)
	if !strings.Contains(settings, "Bash(rig send:*)") || !strings.Contains(settings, "Bash(seatcheck send:*)") {
		t.Fatalf("permission narrowing missing from the settings fragment:\n%s", settings)
	}

	unmounted := withModules(seatFixture("claude-code"), []resolver.ResolvedModule{guard})
	plain, err := RenderSeat(unmounted, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(unmounted): %v", err)
	}
	for _, path := range filePaths(plain) {
		if path == mcpFragmentPath {
			t.Fatalf("a permission fragment resurrected an unmounted server (rendered %q)", path)
		}
	}
}

// The nine seeded seat types ship real server sets: a preconfigured seat for default team
// creation mounts its servers, and role-appropriate types mount more than one. This asserts
// the shipped seeds, not a fixture copy.
func TestRenderSeatSeededTypesMountDifferentServerSets(t *testing.T) {
	lead := withModules(seatFixture("claude-code"), seedModules(t, "lead"))
	developer := withModules(seatFixture("claude-code"), seedModules(t, "developer"))

	leadSpec, err := RenderSeat(lead, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(lead): %v", err)
	}
	developerSpec, err := RenderSeat(developer, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(developer): %v", err)
	}
	t.Logf("lead (mcp_blocks: agenthub-http, sequential-thinking) renders:\n%s", fileContent(t, leadSpec, mcpFragmentPath))
	t.Logf("developer (mcp_blocks: agenthub-http) renders:\n%s", fileContent(t, developerSpec, mcpFragmentPath))

	leadServers := mcpServers(t, leadSpec)
	if len(leadServers) != 2 || leadServers["agenthub_http"].URL != testMCPURL || leadServers["sequential-thinking"].Type != "stdio" {
		t.Fatalf("lead servers = %+v", leadServers)
	}
	developerServers := mcpServers(t, developerSpec)
	if len(developerServers) != 1 {
		t.Fatalf("developer servers = %+v, want only agenthub_http", developerServers)
	}
	if _, ok := developerServers["sequential-thinking"]; ok {
		t.Fatalf("developer mounted a block it does not declare: %+v", developerServers)
	}
}

func writeSpecFiles(t *testing.T, dir string, spec *OpenRigSpec) {
	t.Helper()
	for _, f := range spec.Files {
		path := filepath.Join(dir, filepath.FromSlash(f.Path))
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", filepath.Dir(path), err)
		}
		if err := os.WriteFile(path, []byte(f.Content), 0o644); err != nil {
			t.Fatalf("write %s: %v", path, err)
		}
	}
}

// TestRenderSeatRigValidate writes the rendered spec to disk and validates it with
// the real rig CLI, whose validate path needs a running OpenRig daemon. Set
// OPENRIG_TEST_AGENT_VALIDATE=1 to run it. With the variable set, a missing `rig`,
// an unreachable daemon or an invalid spec all FAIL the test, so the G2 runtime
// validation cannot pass silently on a host without a daemon; without the variable
// the test skips (there is no in-process substitute that would mean the same thing:
// only rig's own validator is the check).
func TestRenderSeatRigValidate(t *testing.T) {
	if os.Getenv("OPENRIG_TEST_AGENT_VALIDATE") != "1" {
		t.Skip("set OPENRIG_TEST_AGENT_VALIDATE=1 to run the rig agent validate check (needs OpenRig and its daemon)")
	}
	rigPath, err := exec.LookPath("rig")
	if err != nil {
		t.Fatalf("OPENRIG_TEST_AGENT_VALIDATE=1 but the rig binary is not on PATH: %v", err)
	}
	seeds, seedErr := seedlibrary.Load()
	if seedErr != nil {
		t.Fatal(seedErr)
	}
	var modules []resolver.ResolvedModule
	for _, m := range seeds[0].Modules {
		modules = append(modules, resolver.ResolvedModule{Slug: m.Slug, Version: m.Version, Kind: m.Kind, Content: m.Content})
	}
	for _, runtime := range []string{"claude-code", "codex", "omp"} {
		t.Run(runtime, func(t *testing.T) {
			spec, err := RenderSeat(withModules(seatFixture(runtime), modules), testMCPURL)
			if err != nil {
				t.Fatalf("RenderSeat: %v", err)
			}
			dir := t.TempDir()
			writeSpecFiles(t, dir, spec)
			out, err := exec.Command(rigPath, "agent", "validate", filepath.Join(dir, "agent.yaml")).CombinedOutput()
			if err != nil {
				t.Fatalf("rig agent validate failed (OPENRIG_TEST_AGENT_VALIDATE=1 requires rig and a running daemon): %v\n%s", err, out)
			}
			if !strings.Contains(string(out), "Agent spec valid") {
				t.Fatalf("unexpected rig output:\n%s", out)
			}
		})
	}
}

func TestRenderSeatAgy(t *testing.T) {
	seat := seatFixture("agy")
	spec, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}
	wantPaths := []string{
		"agent.yaml",
		"guidance/role.md",
		"skills/skill.alpha/SKILL.md",
	}
	if got := filePaths(spec); !reflect.DeepEqual(got, wantPaths) {
		t.Fatalf("file paths = %v, want %v", got, wantPaths)
	}
	for _, path := range filePaths(spec) {
		if strings.HasPrefix(path, "runtime/") {
			t.Fatalf("agy seat rendered runtime fragment %q", path)
		}
	}
	guidance := fileContent(t, spec, guidancePath)
	if !strings.HasPrefix(guidance, "<!-- seat-hash: "+seat.Hash+" -->") {
		t.Fatalf("guidance missing seat hash:\n%s", guidance)
	}
	assertNoSecret(t, spec)

	parsed := parseAgentYAML(t, spec)
	if parsed.Defaults.Runtime != "agy" {
		t.Fatalf("runtime = %q, want agy", parsed.Defaults.Runtime)
	}
}
