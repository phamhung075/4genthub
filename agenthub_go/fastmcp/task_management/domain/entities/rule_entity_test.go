package entities

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestRuleContentValidation(t *testing.T) {
	md := &RuleContentRuleMetadata{}
	if _, err := NewRuleContentRuleContent(md, "", nil, nil, nil, nil); err == nil || err.Error() != "Rule content cannot be empty" {
		t.Fatalf("empty: %v", err)
	}
	if _, err := NewRuleContentRuleContent(nil, "x", nil, nil, nil, nil); err == nil || err.Error() != "Rule metadata is required" {
		t.Fatalf("nil metadata: %v", err)
	}
	if c, err := NewRuleContentRuleContent(md, "x", nil, nil, nil, nil); err != nil || c.Metadata != md {
		t.Fatalf("ok: %v", err)
	}
}

func TestRuleDefaultContent(t *testing.T) {
	md := NewRuleMetadata("p", value_objects.RuleFormatMdc, value_objects.RuleTypeCore, 0, 0, "", nil)
	r := NewRule(md, nil, nil)
	if r.Content == nil || r.Content.Metadata != md || r.Content.Sections.Len() != 0 || md.Author != "system" || md.Version != "1.0" {
		t.Fatalf("default content/metadata: %+v %+v", r.Content, md)
	}
	md.AddTag("a")
	md.AddTag("a")
	if len(md.Tags) != 1 || !md.HasTag("a") {
		t.Fatal("tags")
	}
}
