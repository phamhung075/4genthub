package services

import (
	"strings"
	"testing"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"

	"gopkg.in/yaml.v3"
)

func loadTestTemplate(t *testing.T) *amentities.AgentTemplate {
	t.Helper()
	outputFormat := tmentities.NewOrderedMap[any]()
	outputFormat.Set("format", "markdown")
	config, err := amvo.NewAgentConfiguration(
		"You are the coding agent.",
		[]string{"read", "write"},
		tmentities.NewOrderedMap[any](),
		[]string{`{"name":"testing","content":{"always_test":true}}`},
		outputFormat,
		tmentities.NewOrderedMap[any](),
	)
	if err != nil {
		t.Fatal(err)
	}
	template := amentities.DefaultAgentTemplate()
	id := amvo.GenerateNewAgentTemplateId()
	template.ID = &id
	template.Slug = "coding-agent"
	template.Name = "Coding Agent"
	template.Description = "Writes code"
	template.Category = "development"
	template.Version = "1.2.3"
	template.DefaultConfiguration = &config
	built, err := amentities.NewAgentTemplate(template)
	if err != nil {
		t.Fatal(err)
	}
	return built
}

func renderTestSpec(t *testing.T) (*OpenRigSpec, map[string]string) {
	t.Helper()
	template := loadTestTemplate(t)
	spec, err := RenderOpenRigSpec(template, *template.DefaultConfiguration, "https://api.example.test/mcp")
	if err != nil {
		t.Fatal(err)
	}
	files := map[string]string{}
	for _, f := range spec.Files {
		files[f.Path] = f.Content
	}
	return spec, files
}

func TestRenderOpenRigSpecFiles(t *testing.T) {
	spec, files := renderTestSpec(t)
	if spec.Slug != "coding-agent" || spec.Version != "1.2.3" {
		t.Fatalf("spec = %s/%s", spec.Slug, spec.Version)
	}
	for _, path := range []string{"agent.yaml", openRigGuidancePath, openRigMCPFragmentRef} {
		if files[path] == "" {
			t.Errorf("missing file %s", path)
		}
	}

	var agent map[string]any
	if err := yaml.Unmarshal([]byte(files["agent.yaml"]), &agent); err != nil {
		t.Fatal(err)
	}
	if agent["name"] != "coding-agent" || agent["version"] != "1.2.3" {
		t.Errorf("agent.yaml name/version = %v/%v", agent["name"], agent["version"])
	}
	if !strings.Contains(files["agent.yaml"], `version: "1.2.3"`) {
		t.Errorf("version must be a quoted string:\n%s", files["agent.yaml"])
	}
}

func TestRenderOpenRigGuidanceCarriesPromptRulesAndFormat(t *testing.T) {
	_, files := renderTestSpec(t)
	guidance := files[openRigGuidancePath]
	for _, want := range []string{"# Coding Agent", "You are the coding agent.", "## Rules", "always_test", "## Output format", "format: markdown"} {
		if !strings.Contains(guidance, want) {
			t.Errorf("guidance missing %q:\n%s", want, guidance)
		}
	}
}

func TestRenderOpenRigMCPFragmentHoldsNoSecret(t *testing.T) {
	_, files := renderTestSpec(t)
	fragment := files[openRigMCPFragmentRef]
	if !strings.Contains(fragment, "Bearer ${AGENTHUB_TOKEN}") || !strings.Contains(fragment, "https://api.example.test/mcp") {
		t.Errorf("fragment = %s", fragment)
	}
}

func TestRenderOpenRigSpecRejectsBadInput(t *testing.T) {
	template := loadTestTemplate(t)
	config := *template.DefaultConfiguration
	if _, err := RenderOpenRigSpec(nil, config, "https://x.test/mcp"); err == nil {
		t.Error("nil template accepted")
	}
	if _, err := RenderOpenRigSpec(template, config, "ftp://x.test/mcp"); err == nil {
		t.Error("non-http url accepted")
	}
	colon := *template
	colon.Slug = "local:coding-agent"
	if _, err := RenderOpenRigSpec(&colon, config, "https://x.test/mcp"); err == nil {
		t.Error("slug with colon accepted")
	}
}

func TestRenderOpenRigSpecIsDeterministic(t *testing.T) {
	template := loadTestTemplate(t)
	config := *template.DefaultConfiguration
	a, err := RenderOpenRigSpec(template, config, "https://x.test/mcp")
	if err != nil {
		t.Fatal(err)
	}
	b, err := RenderOpenRigSpec(template, config, "https://x.test/mcp")
	if err != nil {
		t.Fatal(err)
	}
	for i := range a.Files {
		if a.Files[i] != b.Files[i] {
			t.Errorf("file %s differs between renders", a.Files[i].Path)
		}
	}
}
