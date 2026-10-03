package services

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/repositories"

	"gopkg.in/yaml.v3"
)

func loadTestTemplate(t *testing.T) *amentities.AgentTemplate {
	t.Helper()
	loader, err := NewYAMLAgentTemplateLoader(newTestLibrary(t))
	if err != nil {
		t.Fatal(err)
	}
	templates := loader.LoadAllAgents()
	if len(templates) != 1 {
		t.Fatalf("templates = %d, want 1", len(templates))
	}
	return templates[0]
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

type fakeTemplateRepo struct {
	repositories.AgentTemplateRepository
	bySlug map[string]*amentities.AgentTemplate
	saves  int
}

func (r *fakeTemplateRepo) FindBySlug(_ context.Context, slug string) (*amentities.AgentTemplate, error) {
	return r.bySlug[slug], nil
}

func (r *fakeTemplateRepo) Save(_ context.Context, template *amentities.AgentTemplate) (*amentities.AgentTemplate, error) {
	r.saves++
	r.bySlug[template.Slug] = template
	return template, nil
}

func TestSeedAgentTemplatesIsIdempotentBySlug(t *testing.T) {
	library := newTestLibrary(t)
	if err := os.RemoveAll(filepath.Join(library, "agents", "broken-agent")); err != nil {
		t.Fatal(err)
	}
	loader, err := NewYAMLAgentTemplateLoader(library)
	if err != nil {
		t.Fatal(err)
	}
	repo := &fakeTemplateRepo{bySlug: map[string]*amentities.AgentTemplate{}}

	if n, err := SeedAgentTemplates(context.Background(), loader, repo); err != nil || n != 1 {
		t.Fatalf("first seed = %d, %v", n, err)
	}
	firstID := repo.bySlug["coding-agent"].ID
	if n, err := SeedAgentTemplates(context.Background(), loader, repo); err != nil || n != 1 {
		t.Fatalf("second seed = %d, %v", n, err)
	}
	if len(repo.bySlug) != 1 || repo.saves != 2 {
		t.Errorf("templates = %d saves = %d", len(repo.bySlug), repo.saves)
	}
	if got := repo.bySlug["coding-agent"].ID; got == nil || firstID == nil || got.String() != firstID.String() {
		t.Errorf("id changed on reseed: %v -> %v", firstID, got)
	}
}

func TestSeedAgentTemplatesFailsOnUnloadableAgent(t *testing.T) {
	loader, err := NewYAMLAgentTemplateLoader(newTestLibrary(t)) // includes broken-agent
	if err != nil {
		t.Fatal(err)
	}
	repo := &fakeTemplateRepo{bySlug: map[string]*amentities.AgentTemplate{}}
	if _, err := SeedAgentTemplates(context.Background(), loader, repo); err == nil {
		t.Fatal("expected error for a partial library")
	}
	if repo.saves != 0 {
		t.Errorf("saved %d templates despite failure", repo.saves)
	}
}
