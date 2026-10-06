// Package seatrenderer renders a resolved seat snapshot into a deterministic
// OpenRig AgentSpec directory.
package seatrenderer

import (
	"bytes"
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/skillblock"

	"gopkg.in/yaml.v3"
)

const (
	agentYAMLPath        = "agent.yaml"
	guidancePath         = "guidance/role.md"
	skillFileName        = "SKILL.md"
	mcpFragmentPath      = "runtime/claude-mcp.fragment.json"
	settingsFragmentPath = "runtime/claude-settings.fragment.json"
	codexRulesPath       = "runtime/codex.rules"
	ompMCPPath           = "runtime/omp-mcp.json"
	ompConfigPath        = "runtime/omp-config.yml"
	roleResourceID       = "role"
	mcpResourceID        = "claude-mcp"
	settingsResourceID   = "claude-settings"
	deliveryHintSendText = "send_text"
	typeClaudeMCP        = "claude_mcp_fragment"
	typeClaudeSettings   = "claude_settings_fragment"
)

// quotedString forces double-quoted YAML so versions such as "1.0" stay strings.
type quotedString string

func (q quotedString) MarshalYAML() (any, error) {
	return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Style: yaml.DoubleQuotedStyle, Value: string(q)}, nil
}

type agentYAML struct {
	Name      string        `yaml:"name"`
	Version   quotedString  `yaml:"version"`
	Defaults  defaultsYAML  `yaml:"defaults"`
	Profiles  profilesYAML  `yaml:"profiles"`
	Resources resourcesYAML `yaml:"resources"`
	Startup   startupYAML   `yaml:"startup"`
}

type defaultsYAML struct {
	Runtime string `yaml:"runtime"`
}

type profilesYAML struct {
	Default profileYAML `yaml:"default"`
}

type profileYAML struct {
	Uses usesYAML `yaml:"uses"`
}

type usesYAML struct {
	Skills           []string `yaml:"skills"`
	Guidance         []string `yaml:"guidance"`
	Subagents        []string `yaml:"subagents"`
	Plugins          []string `yaml:"plugins"`
	RuntimeResources []string `yaml:"runtime_resources"`
}

type resourcesYAML struct {
	Skills           []pathResourceYAML    `yaml:"skills"`
	Guidance         []pathResourceYAML    `yaml:"guidance"`
	RuntimeResources []runtimeResourceYAML `yaml:"runtime_resources"`
}

type pathResourceYAML struct {
	ID   string `yaml:"id"`
	Path string `yaml:"path"`
}

type runtimeResourceYAML struct {
	ID      string `yaml:"id"`
	Path    string `yaml:"path"`
	Runtime string `yaml:"runtime"`
	Type    string `yaml:"type"`
}

type startupYAML struct {
	Files   []startupFileYAML `yaml:"files"`
	Actions []string          `yaml:"actions"`
}

type startupFileYAML struct {
	Path         string `yaml:"path"`
	DeliveryHint string `yaml:"delivery_hint"`
	Required     bool   `yaml:"required"`
}

// RenderSeat renders a resolved seat as an OpenRig AgentSpec: agent.yaml, the
// seat guidance, one SKILL.md per skill module, and the runtime fragments the
// seat's runtime supports.
func RenderSeat(seat resolver.ResolvedSeat, mcpURL string) (*OpenRigSpec, error) {
	if err := resolver.CheckRuntime(seat.Runtime); err != nil {
		return nil, err
	}

	// A tool module is a Claude settings fragment: a seat on another runtime does not apply it
	// (a seat can switch runtime while its pinned seat type version keeps the tool module).
	toolModules := modulesOfKind(seat.Modules, resolver.KindTool)
	// An mcp module mounts one MCP server. The seat's mcp blocks decide which servers mount;
	// a seat with none mounts no server and no fragment is rendered.
	mcpModules := modulesOfKind(seat.Modules, resolver.KindMCP)

	runtimeResources := make([]runtimeResourceYAML, 0, 2)
	var mcpFragment, settingsFragment string
	// ONE MCP DOCUMENT, TWO DESTINATIONS. claude-code takes it as a runtime resource; omp takes it as
	// a plain file the client installs, for the same reason the codex seat gets a rules file below:
	// OpenRig has no omp MCP fragment type. omp DOES read an MCP document — measured 2026-10-06 on the
	// real runtime: it reads a project `.mcp.json` at startup, expands ${VAR} in a header and in a
	// stdio server's `env`, and reads `$PI_CODING_AGENT_DIR/.mcp.json` for the agent itself, which is
	// where the client installs this file so each seat carries its own server set without a per-seat
	// cwd and without touching the operator's rig-root file.
	if len(mcpModules) > 0 && (receivesClaudeFragments(seat.Runtime) || seat.Runtime == resolver.RuntimeOmp) {
		fragment, err := renderMCPFragment(mcpModules, mcpURL)
		if err != nil {
			return nil, err
		}
		mcpFragment = fragment
		if receivesClaudeFragments(seat.Runtime) {
			runtimeResources = append(runtimeResources, runtimeResourceYAML{
				ID: mcpResourceID, Path: mcpFragmentPath, Runtime: resolver.RuntimeClaudeCode, Type: typeClaudeMCP,
			})
		}
	}
	if receivesClaudeFragments(seat.Runtime) && len(toolModules) > 0 {
		settings, err := mergeToolModules(toolModules)
		if err != nil {
			return nil, err
		}
		settingsFragment, err = renderSettingsFragment(settings)
		if err != nil {
			return nil, err
		}
		runtimeResources = append(runtimeResources, runtimeResourceYAML{
			ID: settingsResourceID, Path: settingsFragmentPath, Runtime: resolver.RuntimeClaudeCode, Type: typeClaudeSettings,
		})
	}

	// A codex seat gets the seat's Bash deny list as a codex execpolicy rules file. OpenRig has no
	// codex rules runtime-resource type to install it (its only codex fragment type merges a TOML
	// fragment into ~/.codex/config.toml, and config.toml cannot express a per-command deny), so
	// the file travels with the render and the client installs it into a rules/ folder of an
	// active codex config layer. See NEXT_GEN (G3, owner decision 2026-10-05).
	var codexRules string
	if seat.Runtime == resolver.RuntimeCodex && len(toolModules) > 0 {
		merged, err := mergeToolModules(toolModules)
		if err != nil {
			return nil, err
		}
		codexRules = renderCodexRules(merged)
	}

	agentYAML, err := renderAgentYAML(seat, runtimeResources)
	if err != nil {
		return nil, err
	}

	files := []OpenRigSpecFile{
		{Path: agentYAMLPath, Content: agentYAML},
		{Path: guidancePath, Content: renderGuidance(seat)},
	}
	for _, m := range modulesOfKind(seat.Modules, resolver.KindSkill) {
		// A skill module is a block carrying the SKILL.md text plus its source provenance; a
		// module whose content is not a valid block fails here, naming it, rather than writing
		// JSON or untraceable text into the seat's skill file.
		block, err := skillblock.Parse(m.Content)
		if err != nil {
			return nil, fmt.Errorf("skill %q: %w", m.Slug, err)
		}
		files = append(files, OpenRigSpecFile{
			Path:    "skills/" + m.Slug + "/" + skillFileName,
			Content: block.Content,
		})
	}
	if receivesClaudeFragments(seat.Runtime) {
		if mcpFragment != "" {
			files = append(files, OpenRigSpecFile{Path: mcpFragmentPath, Content: mcpFragment})
		}
		if settingsFragment != "" {
			files = append(files, OpenRigSpecFile{Path: settingsFragmentPath, Content: settingsFragment})
		}
	}
	if codexRules != "" {
		// Deliberately a plain file and NOT a runtime resource: OpenRig has no codex resource type
		// that installs rules, and declaring an invented type would be a format the platform does
		// not understand. The client installs this file; see the G3 note.
		files = append(files, OpenRigSpecFile{Path: codexRulesPath, Content: codexRules})
	}
	if seat.Runtime == resolver.RuntimeOmp && mcpFragment != "" {
		// Same shape as the codex rules file and for the same reason. The client installs it as
		// `<seat agent dir>/.mcp.json`; a seat with no mcp block gets NO file, which is the
		// acceptance's "a seat with no mcp block gets none".
		files = append(files, OpenRigSpecFile{Path: ompMCPPath, Content: mcpFragment})
		// AND THE SETTING THAT MAKES THE ENTRY MOUNT, in the same delivery because either half
		// alone fails the seat: see ompMCPStartupTimeoutConfig for the measured root cause.
		files = append(files, OpenRigSpecFile{Path: ompConfigPath, Content: ompMCPStartupTimeoutConfig})
	}

	return &OpenRigSpec{
		Slug:    seat.SeatType,
		Name:    seat.SeatType,
		Version: seat.SeatTypeVersion,
		Files:   files,
	}, nil
}

// receivesClaudeFragments reports whether a runtime takes the Claude MCP and settings fragments.
// Only claude-code does; codex, agy and omp get guidance and skills only. Stated positively so a
// runtime added later defaults to no Claude fragment instead of silently receiving one.
func receivesClaudeFragments(runtime string) bool {
	return runtime == resolver.RuntimeClaudeCode
}

func renderAgentYAML(seat resolver.ResolvedSeat, runtimeResources []runtimeResourceYAML) (string, error) {
	skillResources := make([]pathResourceYAML, 0)
	skillUses := make([]string, 0)
	for _, m := range modulesOfKind(seat.Modules, resolver.KindSkill) {
		skillResources = append(skillResources, pathResourceYAML{ID: m.Slug, Path: "skills/" + m.Slug})
		skillUses = append(skillUses, m.Slug)
	}
	runtimeUses := make([]string, 0, len(runtimeResources))
	for _, r := range runtimeResources {
		runtimeUses = append(runtimeUses, r.ID)
	}

	spec := agentYAML{
		Name:     seat.SeatType,
		Version:  quotedString(seat.SeatTypeVersion),
		Defaults: defaultsYAML{Runtime: seat.Runtime},
		Profiles: profilesYAML{Default: profileYAML{Uses: usesYAML{
			Skills:           skillUses,
			Guidance:         []string{},
			Subagents:        []string{},
			Plugins:          []string{},
			RuntimeResources: runtimeUses,
		}}},
		Resources: resourcesYAML{
			Skills:           skillResources,
			Guidance:         []pathResourceYAML{{ID: roleResourceID, Path: guidancePath}},
			RuntimeResources: runtimeResources,
		},
		Startup: startupYAML{
			Files:   []startupFileYAML{{Path: guidancePath, DeliveryHint: deliveryHintSendText, Required: true}},
			Actions: []string{},
		},
	}

	var buf bytes.Buffer
	enc := yaml.NewEncoder(&buf)
	enc.SetIndent(2)
	if err := enc.Encode(spec); err != nil {
		return "", fmt.Errorf("encode agent.yaml: %w", err)
	}
	if err := enc.Close(); err != nil {
		return "", fmt.Errorf("encode agent.yaml: %w", err)
	}
	return buf.String(), nil
}

// renderGuidance writes the startup prompt: the seat hash and version stamp,
// then instruction, document, and memory modules under per-kind headings.
func renderGuidance(seat resolver.ResolvedSeat) string {
	var b strings.Builder
	fmt.Fprintf(&b, "<!-- seat-hash: %s -->\n", seat.Hash)
	fmt.Fprintf(&b, "<!-- seat-type-version: %s -->\n", seat.SeatTypeVersion)
	for _, m := range modulesOfKind(seat.Modules, resolver.KindInstruction) {
		writeGuidanceSection(&b, "## "+m.Slug, m.Content)
	}
	for _, m := range modulesOfKind(seat.Modules, resolver.KindDocument) {
		writeGuidanceSection(&b, "## Document: "+m.Slug, m.Content)
	}
	for _, m := range modulesOfKind(seat.Modules, resolver.KindMemory) {
		writeGuidanceSection(&b, "## Memory: "+m.Slug, m.Content)
	}
	return b.String()
}

func writeGuidanceSection(b *strings.Builder, heading, content string) {
	b.WriteString("\n")
	b.WriteString(heading)
	b.WriteString("\n\n")
	b.WriteString(content)
	if !strings.HasSuffix(content, "\n") {
		b.WriteByte('\n')
	}
}

// permissionListKeys are the permissions lists that tool modules add to rather than replace,
// so a later module cannot drop another module's deny rule.
var permissionListKeys = []string{"deny", "allow", "ask"}

// renderCodexRules renders the seat's Bash deny list as a codex execpolicy file (Starlark).
// Codex reads `prefix_rule` entries from a `.rules` file in a `rules/` folder of an active config
// layer and applies the most restrictive decision, so `forbidden` blocks a matching command
// without prompting (https://developers.openai.com/codex/exec-policy, "Rules"). The pattern is
// matched against the command's argument list, so a command hidden inside a shell wrapper is a
// limitation of the documented mechanism itself, not of this file.
func renderCodexRules(merged map[string]any) string {
	patterns, skipped := codexBashDenyPatterns(merged)
	var b strings.Builder
	b.WriteString("# OpenRig comm-guard for codex (execpolicy). Generated from the seat's tool modules.\n")
	b.WriteString("# Codex loads this file only when it sits in `rules/` inside an active config layer, for\n")
	b.WriteString("# example ~/.codex/rules/ or a trusted project's .codex/rules/. Rules are experimental.\n")
	b.WriteString("# The most restrictive decision wins: forbidden > prompt > allow.\n")
	for _, pattern := range patterns {
		b.WriteString("\nprefix_rule(\n")
		b.WriteString("    pattern = [" + quotedPattern(pattern) + "],\n")
		b.WriteString("    decision = \"forbidden\",\n")
		b.WriteString("    justification = \"Use `seatcheck send`, the audited send path, instead of a direct command.\",\n")
		b.WriteString(")\n")
	}
	if len(skipped) > 0 {
		b.WriteString("\n# Not expressible as a command-prefix rule; listed rather than dropped:\n")
		for _, entry := range skipped {
			b.WriteString("#   " + entry + "\n")
		}
	}
	return b.String()
}

// codexBashDenyPatterns turns the merged `permissions.deny` entries into codex command prefixes.
// Only `Bash(<command>:*)` can be expressed; anything else comes back as skipped so the caller
// keeps it visible instead of silently dropping a policy the seat believes it carries.
func codexBashDenyPatterns(merged map[string]any) (patterns [][]string, skipped []string) {
	permissions, _ := merged["permissions"].(map[string]any)
	deny, _ := permissions["deny"].([]any)
	seen := make(map[string]bool, len(deny))
	for _, raw := range deny {
		entry, ok := raw.(string)
		if !ok || seen[entry] {
			continue
		}
		seen[entry] = true
		pattern, ok := codexPatternFromBashEntry(entry)
		if !ok {
			skipped = append(skipped, entry)
			continue
		}
		patterns = append(patterns, pattern)
	}
	return patterns, skipped
}

// codexPatternFromBashEntry converts `Bash(rig send:*)` to ["rig", "send"]. The `:*` suffix means
// "any arguments", which is what a codex prefix rule matches.
func codexPatternFromBashEntry(entry string) ([]string, bool) {
	const prefix = "Bash("
	if !strings.HasPrefix(entry, prefix) || !strings.HasSuffix(entry, ")") {
		return nil, false
	}
	command := strings.TrimSuffix(strings.TrimPrefix(entry, prefix), ")")
	command = strings.TrimSuffix(command, ":*")
	fields := strings.Fields(command)
	if len(fields) == 0 {
		return nil, false
	}
	return fields, true
}

func quotedPattern(fields []string) string {
	quoted := make([]string, len(fields))
	for i, field := range fields {
		quoted[i] = fmt.Sprintf("%q", field)
	}
	return strings.Join(quoted, ", ")
}

// mergeToolModules merges tool module JSON objects in module order. A top-level key present
// in several modules takes the later value, except `permissions`: its deny, allow and ask lists
// are the deduplicated union in order of appearance, and its other keys follow later-wins.
func mergeToolModules(modules []resolver.ResolvedModule) (map[string]any, error) {
	merged := make(map[string]any)
	for _, m := range modules {
		var obj map[string]any
		if err := json.Unmarshal([]byte(m.Content), &obj); err != nil {
			return nil, fmt.Errorf("tool module %q: content is not a JSON object: %w", m.Slug, err)
		}
		for key, value := range obj {
			if key != "permissions" {
				merged[key] = value
				continue
			}
			permissions, err := mergePermissions(merged[key], value)
			if err != nil {
				return nil, fmt.Errorf("tool module %q: %w", m.Slug, err)
			}
			merged[key] = permissions
		}
	}
	return merged, nil
}

func mergePermissions(current, incoming any) (map[string]any, error) {
	next, ok := incoming.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("permissions must be a JSON object")
	}
	out := make(map[string]any)
	if previous, ok := current.(map[string]any); ok {
		for key, value := range previous {
			out[key] = value
		}
	}
	for key, value := range next {
		if !slices.Contains(permissionListKeys, key) {
			out[key] = value
			continue
		}
		list, err := stringList(value)
		if err != nil {
			return nil, fmt.Errorf("permissions.%s: %w", key, err)
		}
		union, ok := out[key].([]any)
		if !ok {
			union = []any{}
		}
		for _, entry := range list {
			if !slices.Contains(union, any(entry)) {
				union = append(union, entry)
			}
		}
		out[key] = union
	}
	return out, nil
}

func stringList(value any) ([]string, error) {
	items, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("must be an array of strings")
	}
	out := make([]string, len(items))
	for i, item := range items {
		str, ok := item.(string)
		if !ok {
			return nil, fmt.Errorf("must be an array of strings")
		}
		out[i] = str
	}
	return out, nil
}

// renderMCPFragment merges the seat's mounted mcp blocks, in the seat's resolved order, into
// one MCP fragment: one block is one whole server, keyed by the server name its payload names.
// The platform placeholder in a block's url is resolved from mcpURL; every other ${VAR} is
// left for the client runtime to expand. No block renders no server.
func renderMCPFragment(modules []resolver.ResolvedModule, mcpURL string) (string, error) {
	servers := make(map[string]any, len(modules))
	for _, m := range modules {
		server, err := mcpblock.Parse(m.Content)
		if err != nil {
			return "", fmt.Errorf("mcp module %q: %w", m.Slug, err)
		}
		if _, mounted := servers[server.Name]; mounted {
			return "", fmt.Errorf("mcp module %q: server %q is already mounted by another block", m.Slug, server.Name)
		}
		server = server.WithPlatformURL(mcpURL)
		if server.Type == mcpblock.TypeHTTP {
			if err := mcpblock.CheckURL(server.URL); err != nil {
				return "", fmt.Errorf("mcp module %q: %w", m.Slug, err)
			}
		}
		servers[server.Name] = server.Fragment()
	}
	return marshalJSON(map[string]any{"mcpServers": servers}, "mcp fragment")
}

// ompMCPStartupTimeoutConfig is installed by the client as `<seat agent dir>/config.yml`. It is HALF
// THE DELIVERY: the rendered `runtime/omp-mcp.json` declares the server, and this setting is what
// makes the seat WAIT for it.
//
// THE MEASURED ROOT CAUSE (2026-10-06, owner-found and verified on the live rig): `mcp.startupTimeoutMs`
// defaults to 250 ms — "wait this many milliseconds for initial MCP tool discovery; 0 waits until
// connections settle". A LOCAL stdio server (the deepseek bridge) connects inside that window; a
// REMOTE HTTPS server does not, so a seat's first turn started with the local server only and its
// device list showed no agenthub tools. **THE DEFAULT DELAYS THE MOUNT RATHER THAN PREVENTING IT**
// (measured on the reviewer's own seat: the device appeared between two attempts with NO relaunch), so
// this setting is what makes a seat WAIT for its connections at STARTUP — DETERMINISTIC INSTEAD OF
// EVENTUAL — and the relaunch is what makes an already-RUNNING seat read the setting at all, because
// the config file is read when the process starts.
//
// 0 is the value that means WAIT UNTIL CONNECTIONS SETTLE; it is not "no timeout" and it is not a
// disabled setting.
//
// IT MUST LIVE IN THE AGENT DIRECTORY AND NOT THE ENVIRONMENT: the runner hands the runtime an
// allowlist of environment variables that is DENY BY DEFAULT, so an `MCP_STARTUP_TIMEOUT_MS` variable
// never reaches the process (measured: 14 names reach it, and this is not among them). The agent dir
// is the only per-seat place the runtime reads settings from.
const ompMCPStartupTimeoutConfig = "mcp:\n  startupTimeoutMs: 0\n"

// renderSettingsFragment writes a JSON settings fragment, the shape claude-code takes.
func renderSettingsFragment(settings map[string]any) (string, error) {
	return marshalJSON(settings, "settings fragment")
}

func marshalJSON(v any, label string) (string, error) {
	out, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", fmt.Errorf("encode %s: %w", label, err)
	}
	return string(out) + "\n", nil
}

func modulesOfKind(modules []resolver.ResolvedModule, kind resolver.ModuleKind) []resolver.ResolvedModule {
	out := make([]resolver.ResolvedModule, 0)
	for _, m := range modules {
		if m.Kind == kind {
			out = append(out, m)
		}
	}
	return out
}
