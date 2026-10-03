package seatrenderer

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/agent_management/application/services"
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

func filePaths(spec *services.OpenRigSpec) []string {
	out := make([]string, len(spec.Files))
	for i, f := range spec.Files {
		out[i] = f.Path
	}
	return out
}

func fileContent(t *testing.T, spec *services.OpenRigSpec, path string) string {
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

func parseAgentYAML(t *testing.T, spec *services.OpenRigSpec) parsedAgentYAML {
	t.Helper()
	var parsed parsedAgentYAML
	if err := yaml.Unmarshal([]byte(fileContent(t, spec, agentYAMLPath)), &parsed); err != nil {
		t.Fatalf("parse agent.yaml: %v", err)
	}
	return parsed
}

// assertNoSecret fails if any rendered file carries a literal bearer credential;
// the spec may only reference the token through its environment variable.
func assertNoSecret(t *testing.T, spec *services.OpenRigSpec) {
	t.Helper()
	token := os.Getenv(services.OpenRigTokenEnvVar)
	for _, f := range spec.Files {
		if i := strings.Index(f.Content, "Bearer "); i >= 0 && !strings.HasPrefix(f.Content[i+len("Bearer "):], "${") {
			t.Fatalf("file %q carries a literal bearer credential", f.Path)
		}
		if token != "" && strings.Contains(f.Content, token) {
			t.Fatalf("file %q embeds the live %s value", f.Path, services.OpenRigTokenEnvVar)
		}
	}
}

func TestRenderSeatClaudeCode(t *testing.T) {
	seat := seatFixture("claude-code")
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
	if !strings.Contains(mcp, "Bearer ${"+services.OpenRigTokenEnvVar+"}") {
		t.Fatalf("mcp fragment missing token indirection:\n%s", mcp)
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
	if strings.Join(settings.Permissions.Deny, "|") != wantDeny || strings.Join(settings.Permissions.Allow, "|") != "Bash(seatcheck send:*)|Read" {
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

func TestRenderSeatCodexRejectsToolModules(t *testing.T) {
	seat := withModules(seatFixture("codex"), []resolver.ResolvedModule{
		{Slug: "tool.alpha", Version: "1.0.0", Kind: resolver.KindTool, Content: `{"a":1}`},
	})
	if _, err := RenderSeat(seat, testMCPURL); err == nil || !strings.Contains(err.Error(), "tool modules") {
		t.Fatalf("error = %v, want tool modules rejection", err)
	}
}

func TestRenderSeatUnsupportedMCPURL(t *testing.T) {
	if _, err := RenderSeat(seatFixture("claude-code"), "ftp://mcp.example"); err == nil || !strings.Contains(err.Error(), "http") {
		t.Fatalf("error = %v, want mcp url error", err)
	}
}

func writeSpecFiles(t *testing.T, dir string, spec *services.OpenRigSpec) {
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

// TestRenderSeatRigValidate writes the rendered spec to disk and validates it
// with the real rig CLI. OpenRig's validate endpoint needs a running daemon,
// so a missing daemon skips rather than fails.
func TestRenderSeatRigValidate(t *testing.T) {
	rigPath, err := exec.LookPath("rig")
	if err != nil {
		t.Skip("rig binary not on PATH")
	}
	for _, runtime := range []string{"claude-code", "codex"} {
		t.Run(runtime, func(t *testing.T) {
			spec, err := RenderSeat(seatFixture(runtime), testMCPURL)
			if err != nil {
				t.Fatalf("RenderSeat: %v", err)
			}
			dir := t.TempDir()
			writeSpecFiles(t, dir, spec)
			out, err := exec.Command(rigPath, "agent", "validate", filepath.Join(dir, "agent.yaml")).CombinedOutput()
			if err != nil && strings.Contains(string(out), "Daemon not running") {
				t.Skipf("rig validation needs a running OpenRig daemon: %s", strings.TrimSpace(string(out)))
			}
			if err != nil {
				t.Fatalf("rig agent validate failed: %v\n%s", err, out)
			}
			if !strings.Contains(string(out), "Agent spec valid") {
				t.Fatalf("unexpected rig output:\n%s", out)
			}
		})
	}
}
