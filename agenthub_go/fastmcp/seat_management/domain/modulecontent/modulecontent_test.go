package modulecontent

import (
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/skillblock"
)

// goodSkillBlock is a block the renderer accepts, built by the parser's own marshaller so this
// test cannot drift from the block shape.
func goodSkillBlock(t *testing.T) string {
	t.Helper()
	block, err := skillblock.Marshal(skillblock.Block{
		Content:    "# A skill\n",
		SourcePath: "skills/a/SKILL.md",
		SHA256:     strings.Repeat("a", 64),
	})
	if err != nil {
		t.Fatalf("Marshal: %v", err)
	}
	return block
}

// Each parsed kind has a content the renderer accepts and a content it refuses, and the refusal
// names the kind. The text kinds accept anything, which is what a validation that "refuses
// everything" would break.
func TestValidatePerKind(t *testing.T) {
	cases := []struct {
		name    string
		kind    resolver.ModuleKind
		content string
		ok      bool
		want    string
	}{
		{"skill block", resolver.KindSkill, "", true, ""},
		{"skill markdown", resolver.KindSkill, "# not a block\n\nplain markdown\n", false, "skill content: content is not one JSON value"},
		{"skill block missing digest", resolver.KindSkill, `{"content":"# x","source_path":"a/SKILL.md"}`, false, "skill content:"},
		{"mcp server", resolver.KindMCP, `{"name":"srv","type":"http","url":"https://example.test/mcp"}`, true, ""},
		{"mcp not json", resolver.KindMCP, "not json", false, "mcp content: content is not one JSON value"},
		{"mcp object without a type", resolver.KindMCP, `{"name":"srv"}`, false, "mcp content: field type must be"},
		{"tool settings object", resolver.KindTool, `{"permissions":{"deny":["Bash(git push:*)"]}}`, true, ""},
		{"tool not json", resolver.KindTool, "not json", false, "tool content: content is not a JSON object"},
		{"tool json array", resolver.KindTool, `[]`, false, "tool content: content is not a JSON object"},
		{"policy block", resolver.KindPolicy, `{"role":"dev","bash":{"patterns":[{"match":"sudo *","approval":"deny","sibling":"ask the lead"}]}}`, true, ""},
		{"policy not json", resolver.KindPolicy, "not json", false, "policy content: content is not a JSON object"},
		{"policy denial with no sibling", resolver.KindPolicy, `{"role":"dev","bash":{"patterns":[{"match":"sudo *","approval":"deny"}]}}`, false, "policy content:"},
		{"instruction text", resolver.KindInstruction, "any text at all\n", true, ""},
		{"document text", resolver.KindDocument, "any text at all\n", true, ""},
		{"memory text", resolver.KindMemory, "any text at all\n", true, ""},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			content := c.content
			if c.kind == resolver.KindSkill && content == "" {
				content = goodSkillBlock(t)
			}
			err := Validate(c.kind, content)
			if c.ok {
				if err != nil {
					t.Fatalf("Validate(%q) = %v, want nil", content, err)
				}
				return
			}
			if err == nil {
				t.Fatalf("Validate(%q) = nil, want an error", content)
			}
			if !strings.Contains(err.Error(), c.want) {
				t.Errorf("Validate(%q) = %q, want it to contain %q", content, err.Error(), c.want)
			}
		})
	}
}

// Every kind the resolver accepts has a rule here. A kind added to resolver.ValidKind without one
// fails this test rather than reaching production as a silent pass. The list comes from
// resolver.Kinds() rather than being written a third time, so THERE IS ONE ENUMERATION of the kind set.
func TestEveryValidKindHasARule(t *testing.T) {
	for _, kind := range resolver.Kinds() {
		if !resolver.ValidKind(kind) {
			t.Fatalf("%q is not a valid kind: resolver.Kinds must track resolver.ValidKind", kind)
		}
		if err := Validate(kind, "probe"); errors.Is(err, ErrNoRule) {
			t.Errorf("kind %q has no content rule: state one in Validate", kind)
		}
	}
}

// An unknown kind is refused rather than allowed through, which is the deliberate default.
func TestUnknownKindIsRefused(t *testing.T) {
	err := Validate(resolver.ModuleKind("widget"), "{}")
	if !errors.Is(err, ErrNoRule) {
		t.Fatalf("Validate(widget) = %v, want ErrNoRule", err)
	}
	if !strings.Contains(err.Error(), "widget") {
		t.Errorf("error %q does not name the kind", err.Error())
	}
}
