package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"

	"gopkg.in/yaml.v3"
)

const (
	openRigGuidancePath   = "guidance/role.md"
	openRigMCPFragmentRef = "runtime/claude-mcp.fragment.json"
	openRigMCPResourceID  = "agenthub-mcp"
	openRigMCPServerName  = "agenthub_http"
	// OpenRigTokenEnvVar is expanded by Claude Code from the seat's environment, so
	// no credential is ever written into a rendered spec.
	OpenRigTokenEnvVar = "AGENTHUB_TOKEN"
)

// OpenRigSpecFile is one file of a rendered AgentSpec directory; Path is relative to
// the spec root and always uses forward slashes.
type OpenRigSpecFile struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

// OpenRigSpec is an OpenRig AgentSpec directory rendered from a 4genthub agent.
// OpenRig resolves agent_ref only from local:/path: directories, so the cloud serves
// the files and the client writes them to disk.
type OpenRigSpec struct {
	Slug    string            `json:"slug"`
	Name    string            `json:"name"`
	Version string            `json:"version"`
	Files   []OpenRigSpecFile `json:"files"`
}

// quotedString forces double-quoted YAML so versions such as "1.0" stay strings.
type quotedString string

func (q quotedString) MarshalYAML() (any, error) {
	return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Style: yaml.DoubleQuotedStyle, Value: string(q)}, nil
}

type openRigAgentYAML struct {
	Name        string               `yaml:"name"`
	Version     quotedString         `yaml:"version"`
	Description string               `yaml:"description"`
	Defaults    openRigDefaultsYAML  `yaml:"defaults"`
	Profiles    openRigProfilesYAML  `yaml:"profiles"`
	Resources   openRigResourcesYAML `yaml:"resources"`
	Startup     openRigStartupYAML   `yaml:"startup"`
}

type openRigDefaultsYAML struct {
	Runtime string `yaml:"runtime"`
}

type openRigProfilesYAML struct {
	Default openRigProfileYAML `yaml:"default"`
}

type openRigProfileYAML struct {
	Uses openRigUsesYAML `yaml:"uses"`
}

type openRigUsesYAML struct {
	Skills           []string `yaml:"skills"`
	Guidance         []string `yaml:"guidance"`
	Subagents        []string `yaml:"subagents"`
	Plugins          []string `yaml:"plugins"`
	RuntimeResources []string `yaml:"runtime_resources"`
}

type openRigResourcesYAML struct {
	Guidance         []openRigPathResourceYAML `yaml:"guidance"`
	RuntimeResources []openRigRuntimeYAML      `yaml:"runtime_resources"`
}

type openRigPathResourceYAML struct {
	ID   string `yaml:"id"`
	Path string `yaml:"path"`
}

type openRigRuntimeYAML struct {
	ID      string `yaml:"id"`
	Path    string `yaml:"path"`
	Runtime string `yaml:"runtime"`
	Type    string `yaml:"type"`
}

type openRigStartupYAML struct {
	Files   []openRigStartupFileYAML `yaml:"files"`
	Actions []string                 `yaml:"actions"`
}

type openRigStartupFileYAML struct {
	Path         string `yaml:"path"`
	DeliveryHint string `yaml:"delivery_hint"`
	Required     bool   `yaml:"required"`
}

// RenderOpenRigSpec renders the agent as an OpenRig AgentSpec: agent.yaml, the role
// guidance delivered at startup, and a Claude MCP fragment that points the seat back
// at mcpURL (the 4genthub MCP endpoint) with a bearer token read from the seat's env.
func RenderOpenRigSpec(template *amentities.AgentTemplate, config amvo.AgentConfiguration, mcpURL string) (*OpenRigSpec, error) {
	if template == nil {
		return nil, tmvo.ValueErrorf("template is required")
	}
	if !strings.HasPrefix(mcpURL, "http://") && !strings.HasPrefix(mcpURL, "https://") {
		return nil, tmvo.ValueErrorf("mcp url must be http(s), got %q", mcpURL)
	}
	if strings.Contains(template.Slug, ":") {
		return nil, tmvo.ValueErrorf("slug %q contains a colon, which OpenRig reserves for qualified refs", template.Slug)
	}

	agentYAML, err := renderOpenRigAgentYAML(template)
	if err != nil {
		return nil, err
	}
	guidance, err := renderOpenRigGuidance(template, config)
	if err != nil {
		return nil, err
	}
	mcpFragment, err := renderOpenRigMCPFragment(mcpURL)
	if err != nil {
		return nil, err
	}
	return &OpenRigSpec{
		Slug:    template.Slug,
		Name:    template.Name,
		Version: template.Version,
		Files: []OpenRigSpecFile{
			{Path: "agent.yaml", Content: agentYAML},
			{Path: openRigGuidancePath, Content: guidance},
			{Path: openRigMCPFragmentRef, Content: mcpFragment},
		},
	}, nil
}

func renderOpenRigAgentYAML(template *amentities.AgentTemplate) (string, error) {
	spec := openRigAgentYAML{
		Name:        template.Slug,
		Version:     quotedString(template.Version),
		Description: template.Description,
		Defaults:    openRigDefaultsYAML{Runtime: "claude-code"},
		Profiles: openRigProfilesYAML{Default: openRigProfileYAML{Uses: openRigUsesYAML{
			Skills:           []string{},
			Guidance:         []string{},
			Subagents:        []string{},
			Plugins:          []string{},
			RuntimeResources: []string{openRigMCPResourceID},
		}}},
		Resources: openRigResourcesYAML{
			Guidance: []openRigPathResourceYAML{{ID: "role", Path: openRigGuidancePath}},
			RuntimeResources: []openRigRuntimeYAML{{
				ID: openRigMCPResourceID, Path: openRigMCPFragmentRef, Runtime: "claude-code", Type: "claude_mcp_fragment",
			}},
		},
		Startup: openRigStartupYAML{
			Files:   []openRigStartupFileYAML{{Path: openRigGuidancePath, DeliveryHint: "send_text", Required: true}},
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

// renderOpenRigGuidance writes the prompt the seat receives at startup: identity,
// the agent's system prompt, then its rules and output format.
func renderOpenRigGuidance(template *amentities.AgentTemplate, config amvo.AgentConfiguration) (string, error) {
	var b strings.Builder
	fmt.Fprintf(&b, "# %s\n\n", template.Name)
	if desc := strings.TrimSpace(template.Description); desc != "" {
		fmt.Fprintf(&b, "%s\n\n", desc)
	}
	fmt.Fprintf(&b, "%s\n", strings.TrimSpace(config.SystemPrompt))

	if len(config.Rules) > 0 {
		b.WriteString("\n## Rules\n")
		for _, raw := range config.Rules {
			name, body, err := decodeRule(raw)
			if err != nil {
				return "", err
			}
			fmt.Fprintf(&b, "\n### %s\n\n```yaml\n%s```\n", name, body)
		}
	}
	if config.OutputFormat != nil && config.OutputFormat.Len() > 0 {
		body, err := orderedMapToYAML(config.OutputFormat)
		if err != nil {
			return "", err
		}
		fmt.Fprintf(&b, "\n## Output format\n\n```yaml\n%s```\n", body)
	}
	return b.String(), nil
}

// decodeRule reads a rule stored by the loader as compact JSON {"name","content"}.
func decodeRule(raw string) (name, body string, err error) {
	var rule struct {
		Name    string `json:"name"`
		Content any    `json:"content"`
	}
	if err := json.Unmarshal([]byte(raw), &rule); err != nil {
		return "", "", fmt.Errorf("decode rule: %w", err)
	}
	encoded, err := yaml.Marshal(rule.Content)
	if err != nil {
		return "", "", fmt.Errorf("encode rule %q: %w", rule.Name, err)
	}
	return rule.Name, string(encoded), nil
}

func orderedMapToYAML(m any) (string, error) {
	encoded, err := tmvo.PyJSONDumpsCompact(m)
	if err != nil {
		return "", err
	}
	var decoded any
	if err := json.Unmarshal([]byte(encoded), &decoded); err != nil {
		return "", err
	}
	out, err := yaml.Marshal(decoded)
	if err != nil {
		return "", err
	}
	return string(out), nil
}

func renderOpenRigMCPFragment(mcpURL string) (string, error) {
	fragment := map[string]any{
		"mcpServers": map[string]any{
			openRigMCPServerName: map[string]any{
				"type": "http",
				"url":  mcpURL,
				"headers": map[string]string{
					"Accept":        "application/json, text/event-stream",
					"Authorization": "Bearer ${" + OpenRigTokenEnvVar + "}",
				},
			},
		},
	}
	out, err := json.MarshalIndent(fragment, "", "  ")
	if err != nil {
		return "", fmt.Errorf("encode mcp fragment: %w", err)
	}
	return string(out) + "\n", nil
}
