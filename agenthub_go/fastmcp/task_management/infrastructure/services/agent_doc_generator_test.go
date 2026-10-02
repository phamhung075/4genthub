package services

import (
	"agenthub/fastmcp/utilities/pyyaml"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestPyYAMLDumpRendering(t *testing.T) {
	nested := entities.NewOrderedMap[any]()
	inner := entities.NewOrderedMap[any]()
	inner.Set("count", int64(3))
	inner.Set("ratio", 1.0)
	inner.Set("truth", true)
	inner.Set("nothing", nil)
	nested.Set("nested", inner)
	nested.Set("list", []any{"a", int64(1), 1.0})
	nested.Set("num_string", "1.0")
	nested.Set("bool_string", "true")

	out, err := pyyaml.Dump(nested, true)
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{
		"nested:\n",
		"  count: 3\n",
		"  ratio: 1.0\n",
		"  truth: true\n",
		"  nothing: null\n",
		"list:\n",
		"- a",
		"- 1",
		"- 1.0",
		"num_string: '1.0'",
		"bool_string: 'true'",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("dump missing %q in:\n%s", want, out)
		}
	}

	// load -> dump -> load round trip keeps the same shapes.
	reloaded, err := entities.LoadYAML([]byte(out))
	if err != nil {
		t.Fatalf("reload: %v\n%s", err, out)
	}
	root, ok := reloaded.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("reloaded type = %T", reloaded)
	}
	if v, _ := root.Get("num_string"); v != "1.0" {
		t.Fatalf("num_string round trip = %#v", v)
	}
	if v, _ := root.Get("bool_string"); v != "true" {
		t.Fatalf("bool_string round trip = %#v", v)
	}
}

func TestGenerateAgentDocs(t *testing.T) {
	yamlLib := t.TempDir()
	outputDir := t.TempDir()

	codingDir := filepath.Join(yamlLib, "coding_agent")
	if err := os.MkdirAll(filepath.Join(codingDir, "rules"), 0o777); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(yamlLib, "not_an_agent"), 0o777); err != nil {
		t.Fatal(err)
	}
	jobDesc := "name: Coding Agent\nslug: coding-agent\nrole_definition: writes code\n" +
		"when_to_use: always\ngroups:\n  - dev\n  - core\n"
	if err := os.WriteFile(filepath.Join(codingDir, "job_desc.yaml"), []byte(jobDesc), 0o666); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(codingDir, "rules", "r.yaml"), []byte("a: 1\n"), 0o666); err != nil {
		t.Fatal(err)
	}

	g := NewAgentDocGenerator(&yamlLib, &outputDir)
	if err := g.GenerateAgentDocs(nil, false); err != nil {
		t.Fatal(err)
	}

	raw, err := os.ReadFile(filepath.Join(outputDir, "coding_agent.mdc"))
	if err != nil {
		t.Fatal(err)
	}
	md := string(raw)
	for _, want := range []string{
		"# Coding Agent",
		"**Slug:** `coding-agent`",
		"**Role Definition:** writes code",
		"**When to Use:** always",
		"**Groups:** dev, core",
		"## Rules",
		"### r",
		"a: 1",
	} {
		if !strings.Contains(md, want) {
			t.Fatalf("markdown missing %q in:\n%s", want, md)
		}
	}

	// A named agent that does not exist reports the Python message.
	if err := g.GenerateAgentDocs(strPtr("missing_agent"), false); err == nil ||
		err.Error() != "Agent directory 'missing_agent' not found." {
		t.Fatalf("missing agent error = %v", err)
	}

	// clear_all removes the previously generated files.
	if err := g.GenerateAgentDocs(nil, true); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(outputDir, "coding_agent.mdc")); err != nil {
		t.Fatalf("doc should be regenerated: %v", err)
	}
}

func TestGenerateDocsForAssignees(t *testing.T) {
	yamlLib := t.TempDir()
	outputDir := t.TempDir()

	codingDir := filepath.Join(yamlLib, "coding_agent")
	if err := os.MkdirAll(codingDir, 0o777); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(codingDir, "job_desc.yaml"), []byte("name: C\n"), 0o666); err != nil {
		t.Fatal(err)
	}

	g := NewAgentDocGenerator(&yamlLib, &outputDir)
	if err := g.GenerateDocsForAssignees([]string{"@coding", "coding_agent"}, false); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(outputDir, "coding_agent.mdc")); err != nil {
		t.Fatalf("expected generated doc: %v", err)
	}

	// A missing assignee surfaces the same error as generate_agent_docs.
	if err := g.GenerateDocsForAssignees([]string{"@nobody"}, false); err == nil {
		t.Fatal("expected error for a missing assignee")
	}
}

func strPtr(s string) *string { return &s }
