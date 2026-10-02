package parsers

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func writeTemp(t *testing.T, name, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), name)
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestDetectFormat(t *testing.T) {
	p := NewRuleContentParser()
	cases := map[string]entities.RuleFormat{
		"a.mdc": entities.RuleFormatMdc, "a.md": entities.RuleFormatMd,
		"a.JSON": entities.RuleFormatJson, "a.yaml": entities.RuleFormatYaml,
		"a.yml": entities.RuleFormatYaml, "a.txt": entities.RuleFormatTxt,
		"a.unknown": entities.RuleFormatTxt, "noext": entities.RuleFormatTxt,
	}
	for name, want := range cases {
		if got := p.DetectFormat("/x/" + name); got != want {
			t.Errorf("DetectFormat(%q) = %q, want %q", name, got, want)
		}
	}
}

func TestParseMarkdownSections(t *testing.T) {
	content := "# Intro\n\nSee [docs](https://example.com).\nHello {{name}} and {{name}}.\n\n## Details\nMore {{other}}\n"
	path := writeTemp(t, "rule.md", content)
	got, err := NewRuleContentParser().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if got.Metadata.Path != path {
		t.Fatalf("metadata path = %q", got.Metadata.Path)
	}
	if got.Metadata.Format != entities.RuleFormatMd {
		t.Fatalf("format = %q", got.Metadata.Format)
	}
	if got.RawContent != content {
		t.Fatalf("raw content mismatch")
	}
	// The first header starts "intro" (nothing precedes it); "details" follows.
	if keys := got.Sections.Keys(); len(keys) != 2 || keys[0] != "intro" || keys[1] != "details" {
		t.Fatalf("sections keys = %v", keys)
	}
	intro, _ := got.Sections.Get("intro")
	if !strings.Contains(intro, "See [docs](https://example.com).") {
		t.Fatalf("intro = %q", intro)
	}
	if len(got.References) != 1 || got.References[0] != "https://example.com" {
		t.Fatalf("references = %v", got.References)
	}
	// Both variables keep the placeholder value equal to the name.
	if v, _ := got.Variables.Get("name"); v != "name" {
		t.Fatalf("name var = %v", v)
	}
	if v, _ := got.Variables.Get("other"); v != "other" {
		t.Fatalf("other var = %v", v)
	}
	// Type is "task" because the content contains "task"? No: the path/content must
	// match, so with neither it falls to general.
	if got.Metadata.Type != entities.RuleTypeGeneral {
		t.Fatalf("type = %q", got.Metadata.Type)
	}
}

func TestParseTypeClassification(t *testing.T) {
	p := NewRuleContentParser()
	if got := p.classifyRuleType("/rules/task_rule.md", "nothing"); got != entities.RuleTypeTask {
		t.Errorf("path task = %q", got)
	}
	if got := p.classifyRuleType("/rules/x.md", "Some CONTEXT here"); got != entities.RuleTypeContext {
		t.Errorf("content context = %q", got)
	}
	if got := p.classifyRuleType("/rules/agent_x.md", "no keywords"); got != entities.RuleTypeAgent {
		t.Errorf("path agent = %q", got)
	}
	if got := p.classifyRuleType("/rules/x.md", "an agent description"); got != entities.RuleTypeAgent {
		t.Errorf("content agent = %q", got)
	}
	// "config" in the content suppresses the content-based agent classification, but the
	// config section pattern only matches at the start of a line, so this is general.
	if got := p.classifyRuleType("/rules/x.md", "an agent with config:"); got != entities.RuleTypeGeneral {
		t.Errorf("agent+config = %q", got)
	}
	if got := p.classifyRuleType("/rules/x.md", "config:\nvalue"); got != entities.RuleTypeConfig {
		t.Errorf("config section = %q", got)
	}
}

func TestParseJSON(t *testing.T) {
	content := `{"reference": "top.md", "variables": {"a": 1}, "sections": {"s1": "x"}, "nested": {"reference": "deep.md"}}`
	path := writeTemp(t, "rule.json", content)
	got, err := NewRuleContentParser().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if got.ParsedContent == nil {
		t.Fatal("nil parsed content")
	}
	if got.Metadata.Type != entities.RuleTypeGeneral {
		t.Fatalf("type = %q", got.Metadata.Type)
	}
	// Top-level keys become sections; dict/list values are json.dumps(..., indent=2).
	if v, _ := got.Sections.Get("nested"); !strings.Contains(v, "\n") {
		t.Fatalf("nested section = %q", v)
	}
	// references includes only the explicit "reference" keys (top and nested).
	refs := map[string]bool{}
	for _, r := range got.References {
		refs[r] = true
	}
	if !refs["top.md"] || !refs["deep.md"] {
		t.Fatalf("references = %v", got.References)
	}
	if v, _ := got.Variables.Get("a"); v != int64(1) {
		t.Fatalf("variables a = %#v", v)
	}
}

func TestParseJSONInvalid(t *testing.T) {
	path := writeTemp(t, "bad.json", "{not json")
	got, err := NewRuleContentParser().ParseRuleFile(path)
	if err != nil {
		t.Fatalf("invalid JSON must not error: %v", err)
	}
	if got.Sections.Len() != 0 || len(got.References) != 0 || got.Variables.Len() != 0 || got.ParsedContent.Len() != 0 {
		t.Fatalf("expected empty results, got %+v", got)
	}
}

func TestParseYAML(t *testing.T) {
	content := "name: demo\nreference: r.md\nvariables:\n  a: 1\n  b: two\n"
	path := writeTemp(t, "rule.yaml", content)
	got, err := NewRuleContentParser().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Variables.Get("a"); v != int64(1) {
		t.Fatalf("yaml var a = %#v", v)
	}
	if len(got.References) != 1 || got.References[0] != "r.md" {
		t.Fatalf("references = %v", got.References)
	}
	if v, _ := got.Sections.Get("name"); v != "demo" {
		t.Fatalf("scalar section = %q", v)
	}
	// Nested mapping uses the YAML dumper.
	if v, _ := got.Sections.Get("variables"); !strings.Contains(v, "a: 1") {
		t.Fatalf("mapping section = %q", v)
	}
}

func TestParseText(t *testing.T) {
	content := "see https://example.com/a and file:///tmp/x and main.go\n${who} and k = v\n"
	path := writeTemp(t, "rule.txt", content)
	got, err := NewRuleContentParser().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Sections.Get("content"); v != content {
		t.Fatalf("text section = %q", v)
	}
	if v, _ := got.Variables.Get("who"); v != "who" {
		t.Fatalf("var who = %v", v)
	}
	found := false
	for _, r := range got.References {
		if r == "https://example.com/a" || r == "file:///tmp/x" || r == "main.go" {
			found = true
		}
	}
	if !found {
		t.Fatalf("references = %v", got.References)
	}
	if chars, _ := got.ParsedContent.Get("characters"); chars != len([]rune(content)) {
		t.Fatalf("characters = %v", chars)
	}
	if lines, _ := got.ParsedContent.Get("lines"); lines != len(strings.Split(content, "\n")) {
		t.Fatalf("lines = %v", lines)
	}
}

func TestExtractDependencies(t *testing.T) {
	// One pattern per line so the greedy include directive cannot swallow the next line.
	content := "[a](mdc:b.md)\n@import \"c.md\"\ninclude: d.md\ndepends_on: [e.md]"
	deps := NewRuleContentParser().extractDependencies(content)
	want := map[string]bool{"b.md": true, "c.md": true, "d.md": true, "e.md": true}
	if len(deps) != len(want) {
		t.Fatalf("deps = %v", deps)
	}
	for _, d := range deps {
		if !want[d] {
			t.Fatalf("unexpected dep %q in %v", d, deps)
		}
	}
}
