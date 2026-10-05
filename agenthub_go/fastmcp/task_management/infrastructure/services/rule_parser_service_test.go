package services

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestRuleParserDetectFormat(t *testing.T) {
	s := NewRuleParserService()
	cases := map[string]value_objects.RuleFormat{
		"a.mdc": value_objects.RuleFormatMdc, "a.md": value_objects.RuleFormatMd,
		"a.markdown": value_objects.RuleFormatMd, "a.JSON": value_objects.RuleFormatJson,
		"a.yaml": value_objects.RuleFormatYaml, "a.yml": value_objects.RuleFormatYaml,
		"a.txt": value_objects.RuleFormatTxt, "a.exe": value_objects.RuleFormatTxt,
	}
	for name, want := range cases {
		if got := s.DetectFormat("/x/" + name); got != want {
			t.Errorf("DetectFormat(%q) = %q, want %q", name, got, want)
		}
	}
}

func TestRuleParserMissingFile(t *testing.T) {
	_, err := NewRuleParserService().ParseRuleFile(filepath.Join(t.TempDir(), "nope.md"))
	if err == nil || !strings.HasPrefix(err.Error(), "Rule file not found: ") {
		t.Fatalf("error = %v", err)
	}
}

func TestRuleParserMetadata(t *testing.T) {
	content := "---\ndescription: This is a rule\ntags: [core, web]\n---\n# Title\nBody text\n"
	path := filepath.Join(t.TempDir(), "guide.md")
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}
	got, err := NewRuleParserService().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if got.Metadata.Path != path || got.Metadata.Format != value_objects.RuleFormatMd {
		t.Fatalf("metadata = %+v", got.Metadata)
	}
	if got.Metadata.Author != "rule_parser" || got.Metadata.Version != "1.0" {
		t.Fatalf("author/version = %q/%q", got.Metadata.Author, got.Metadata.Version)
	}
	if got.Metadata.Description != "This is a rule" {
		t.Fatalf("description = %q", got.Metadata.Description)
	}
	tags := map[string]bool{}
	for _, tag := range got.Metadata.Tags {
		tags[tag] = true
	}
	if !tags["core"] || !tags["web"] {
		t.Fatalf("tags = %v", got.Metadata.Tags)
	}
	if got.Metadata.Size != len(content) {
		t.Fatalf("size = %d", got.Metadata.Size)
	}
	if len(got.Metadata.Checksum) != 32 {
		t.Fatalf("checksum = %q", got.Metadata.Checksum)
	}
}

func TestRuleParserMarkdownSections(t *testing.T) {
	content := "---\ntitle: demo\nvariables:\n  a: 1\n---\n# Intro\nSee [[other]] and {{b}}.\n\n# Second\nline\n"
	path := filepath.Join(t.TempDir(), "doc.md")
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}
	got, err := NewRuleParserService().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if keys := got.Sections.Keys(); len(keys) != 2 || keys[0] != "Intro" || keys[1] != "Second" {
		t.Fatalf("sections = %v", keys)
	}
	if v, _ := got.Sections.Get("Intro"); !strings.Contains(v, "See [[other]] and {{b}}.") {
		t.Fatalf("intro = %q", v)
	}
	if len(got.References) != 1 || got.References[0] != "other" {
		t.Fatalf("references = %v", got.References)
	}
	if v, _ := got.Variables.Get("a"); v != int64(1) {
		t.Fatalf("frontmatter variable a = %#v", v)
	}
	if v, ok := got.Variables.Get("b"); !ok || v != nil {
		t.Fatalf("placeholder variable b = %#v", v)
	}
}

func TestRuleParserMarkdownNoSections(t *testing.T) {
	path := filepath.Join(t.TempDir(), "plain.md")
	if err := os.WriteFile(path, []byte("no headers here"), 0o666); err != nil {
		t.Fatal(err)
	}
	got, err := NewRuleParserService().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Sections.Get("content"); v != "no headers here" {
		t.Fatalf("fallback section = %q", v)
	}
}

func TestRuleParserJSON(t *testing.T) {
	content := `{"sections": {"s": "x"}, "variables": {"v": 2}, "deep": {"list": ["[[ref]]"]}}`
	path := filepath.Join(t.TempDir(), "r.json")
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}
	got, err := NewRuleParserService().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Sections.Get("s"); v != "x" {
		t.Fatalf("sections = %v", got.Sections.Keys())
	}
	if v, _ := got.Variables.Get("v"); v != int64(2) {
		t.Fatalf("variables v = %#v", v)
	}
	if len(got.References) != 1 || got.References[0] != "ref" {
		t.Fatalf("references = %v", got.References)
	}
}

func TestRuleParserJSONInvalid(t *testing.T) {
	path := filepath.Join(t.TempDir(), "bad.json")
	if err := os.WriteFile(path, []byte("{nope"), 0o666); err != nil {
		t.Fatal(err)
	}
	_, err := NewRuleParserService().ParseRuleFile(path)
	if err == nil || !strings.HasPrefix(err.Error(), "Invalid JSON content: ") {
		t.Fatalf("error = %v", err)
	}
}

func TestRuleParserYAML(t *testing.T) {
	content := "sections:\n  s: x\nvariables:\n  v: two\nref: '[[wiki]]'\n"
	path := filepath.Join(t.TempDir(), "r.yaml")
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}
	got, err := NewRuleParserService().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Sections.Get("s"); v != "x" {
		t.Fatalf("sections = %v", got.Sections.Keys())
	}
	if v, _ := got.Variables.Get("v"); v != "two" {
		t.Fatalf("variables v = %#v", v)
	}
	if len(got.References) != 1 || got.References[0] != "wiki" {
		t.Fatalf("references = %v", got.References)
	}
}

func TestRuleParserText(t *testing.T) {
	content := "name = 'demo'\nother = plain\nsee [[a]]\n"
	path := filepath.Join(t.TempDir(), "r.txt")
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}
	got, err := NewRuleParserService().ParseRuleFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Variables.Get("name"); v != "demo" {
		t.Fatalf("name = %#v", v)
	}
	if v, _ := got.Variables.Get("other"); v != "plain" {
		t.Fatalf("other = %#v", v)
	}
	if len(got.References) != 1 || got.References[0] != "a" {
		t.Fatalf("references = %v", got.References)
	}
	if v, _ := got.Sections.Get("content"); v != content {
		t.Fatalf("section = %q", v)
	}
}

func TestRuleParserClassification(t *testing.T) {
	s := NewRuleParserService()
	if got := s.classifyRuleType("/rules/core/x.md", ""); got != value_objects.RuleTypeCore {
		t.Errorf("path core = %q", got)
	}
	if got := s.classifyRuleType("/rules/x.md", "this is essential"); got != value_objects.RuleTypeCore {
		t.Errorf("content core = %q", got)
	}
	if got := s.classifyRuleType("/rules/x.md", "a pipeline here"); got != value_objects.RuleTypeWorkflow {
		t.Errorf("content workflow = %q", got)
	}
	if got := s.classifyRuleType("/rules/x.md", "assistant text"); got != value_objects.RuleTypeAgent {
		t.Errorf("content agent = %q", got)
	}
	if got := s.classifyRuleType("/rules/x.md", "repository"); got != value_objects.RuleTypeProject {
		t.Errorf("content project = %q", got)
	}
	if got := s.classifyRuleType("/rules/x.md", "environment"); got != value_objects.RuleTypeContext {
		t.Errorf("content context = %q", got)
	}
	if got := s.classifyRuleType("/rules/x.md", "nothing matches"); got != value_objects.RuleTypeCustom {
		t.Errorf("custom = %q", got)
	}
}

func TestRuleParserExtractDependencies(t *testing.T) {
	content := "@import \"a.md\"\n@include 'b.md'\nrequire \"c.md\"\nfile: \"d.md\"\n"
	deps := NewRuleParserService().extractDependencies(content)
	want := map[string]bool{"a.md": true, "b.md": true, "c.md": true, "d.md": true}
	if len(deps) != len(want) {
		t.Fatalf("deps = %v", deps)
	}
	for _, d := range deps {
		if !want[d] {
			t.Fatalf("unexpected dep %q", d)
		}
	}
}
