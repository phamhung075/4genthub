package services

import (
	"os"
	"path/filepath"
	"testing"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func newTestLibrary(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	agent := filepath.Join(root, "agents", "coding-agent")
	writeFile(t, filepath.Join(agent, "config.yaml"), "agent_info:\n  slug: coding-agent\n  name: Coding Agent\n  description: Writes code\n  category: development\n  version: 1.2.3\n  author: alice\n  migration_date: 2024-01-01\n")
	writeFile(t, filepath.Join(agent, "capabilities.yaml"), "mcp_tools:\n  tools:\n    - read\n    - write\nfile_operations:\n  read: true\n")
	writeFile(t, filepath.Join(agent, "contexts", "coding_agent_instructions.yaml"), "custom_instructions: You are the coding agent.\n")
	writeFile(t, filepath.Join(agent, "rules", "rule1.yaml"), "always_test: true\n")
	writeFile(t, filepath.Join(agent, "output_format", "output_specification.yaml"), "output_specification:\n  format: markdown\n")
	writeFile(t, filepath.Join(agent, "metadata.yaml"), "tags:\n  - a\n---\nother: doc\n")
	// A directory that fails to load (no config) must be skipped, not abort.
	if err := os.MkdirAll(filepath.Join(root, "agents", "broken-agent"), 0o755); err != nil {
		t.Fatal(err)
	}
	return root
}

func TestNewYAMLAgentTemplateLoaderMissingPath(t *testing.T) {
	_, err := NewYAMLAgentTemplateLoader(filepath.Join(t.TempDir(), "nope"))
	if err == nil {
		t.Fatal("expected error")
	}
	if _, ok := err.(*tmvo.ValueError); !ok {
		t.Fatalf("err = %T", err)
	}
}

func TestLoadAllAgents(t *testing.T) {
	loader, err := NewYAMLAgentTemplateLoader(newTestLibrary(t))
	if err != nil {
		t.Fatal(err)
	}
	templates := loader.LoadAllAgents()
	if len(templates) != 1 {
		t.Fatalf("templates = %d, want 1 (broken dir skipped)", len(templates))
	}
	tpl := templates[0]
	if tpl.Slug != "coding-agent" || tpl.Name != "Coding Agent" || tpl.Category != "development" || tpl.Version != "1.2.3" {
		t.Errorf("template = %s/%s/%s/%s", tpl.Slug, tpl.Name, tpl.Category, tpl.Version)
	}
	cfg := tpl.DefaultConfiguration
	if cfg.SystemPrompt != "You are the coding agent." {
		t.Errorf("system_prompt = %q", cfg.SystemPrompt)
	}
	if len(cfg.Tools) != 2 || cfg.Tools[0] != "read" || cfg.Tools[1] != "write" {
		t.Errorf("tools = %v", cfg.Tools)
	}
	if len(cfg.Rules) != 1 {
		t.Errorf("rules = %v", cfg.Rules)
	}
	if v, _ := cfg.Capabilities.Get("file_operations"); v == nil {
		t.Errorf("missing file_operations capability")
	}
	if v, _ := cfg.OutputFormat.Get("format"); v != "markdown" {
		t.Errorf("output_format = %v", v)
	}
	if v, _ := tpl.Metadata.Get("author"); v != "alice" {
		t.Errorf("metadata.author = %v", v)
	}
	if v, _ := tpl.Metadata.Get("source"); v != "agent-library" {
		t.Errorf("metadata.source = %v", v)
	}
	// metadata.yaml is multi-document; only the first document is merged.
	if _, ok := tpl.Metadata.Get("other"); ok {
		t.Errorf("second YAML document should not be merged")
	}
	if v, ok := tpl.Metadata.Get("tags"); !ok || v == nil {
		t.Errorf("metadata.tags missing")
	}
}
