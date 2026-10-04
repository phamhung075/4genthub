// Package seatrenderer renders a resolved seat snapshot into a deterministic
// OpenRig AgentSpec directory.
package seatrenderer

import (
	"bytes"
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"agenthub/fastmcp/agent_management/application/services"
	"agenthub/fastmcp/seat_management/domain/resolver"

	"gopkg.in/yaml.v3"
)

const (
	agentYAMLPath        = "agent.yaml"
	guidancePath         = "guidance/role.md"
	skillFileName        = "SKILL.md"
	mcpFragmentPath      = "runtime/claude-mcp.fragment.json"
	settingsFragmentPath = "runtime/claude-settings.fragment.json"
	roleResourceID       = "role"
	mcpResourceID        = "claude-mcp"
	settingsResourceID   = "claude-settings"
	mcpServerName        = "agenthub_http"
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
func RenderSeat(seat resolver.ResolvedSeat, mcpURL string) (*services.OpenRigSpec, error) {
	if err := resolver.CheckRuntime(seat.Runtime); err != nil {
		return nil, err
	}

	// A tool module is a Claude settings fragment: a seat on another runtime does not apply it
	// (a seat can switch runtime while its pinned seat type version keeps the tool module).
	toolModules := modulesOfKind(seat.Modules, resolver.KindTool)

	runtimeResources := make([]runtimeResourceYAML, 0, 2)
	var mcpFragment, settingsFragment string
	// Only claude-code seats get an MCP fragment: OpenRig has no codex/agy/omp MCP fragment resource type, only claude_mcp_fragment.
	if receivesClaudeFragments(seat.Runtime) {
		var err error
		mcpFragment, err = renderMCPFragment(mcpURL)
		if err != nil {
			return nil, err
		}
		runtimeResources = append(runtimeResources, runtimeResourceYAML{
			ID: mcpResourceID, Path: mcpFragmentPath, Runtime: resolver.RuntimeClaudeCode, Type: typeClaudeMCP,
		})
		if len(toolModules) > 0 {
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
	}

	agentYAML, err := renderAgentYAML(seat, runtimeResources)
	if err != nil {
		return nil, err
	}

	files := []services.OpenRigSpecFile{
		{Path: agentYAMLPath, Content: agentYAML},
		{Path: guidancePath, Content: renderGuidance(seat)},
	}
	for _, m := range modulesOfKind(seat.Modules, resolver.KindSkill) {
		files = append(files, services.OpenRigSpecFile{
			Path:    "skills/" + m.Slug + "/" + skillFileName,
			Content: m.Content,
		})
	}
	if receivesClaudeFragments(seat.Runtime) {
		files = append(files, services.OpenRigSpecFile{Path: mcpFragmentPath, Content: mcpFragment})
		if settingsFragment != "" {
			files = append(files, services.OpenRigSpecFile{Path: settingsFragmentPath, Content: settingsFragment})
		}
	}

	return &services.OpenRigSpec{
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

func renderMCPFragment(mcpURL string) (string, error) {
	if !strings.HasPrefix(mcpURL, "http://") && !strings.HasPrefix(mcpURL, "https://") {
		return "", fmt.Errorf("mcp url must be http(s), got %q", mcpURL)
	}
	fragment := map[string]any{
		"mcpServers": map[string]any{
			mcpServerName: map[string]any{
				"type": "http",
				"url":  mcpURL,
				"headers": map[string]string{
					"Accept":        "application/json, text/event-stream",
					"Authorization": "Bearer ${" + services.OpenRigTokenEnvVar + "}",
				},
			},
		},
	}
	return marshalJSON(fragment, "mcp fragment")
}

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
