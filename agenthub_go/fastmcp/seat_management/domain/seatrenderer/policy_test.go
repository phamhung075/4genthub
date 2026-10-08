package seatrenderer

import (
	"strings"
	"testing"
)

const validPolicy = `{
  "role": "dev",
  "mcp": {"startupTimeoutMs": 0},
  "bash": {"patterns": [
    {"match": "sudo *", "approval": "deny", "sibling": "ask the lead to run it"}
  ]},
  "tools": {"patterns": [
    {"match": "edit", "approval": "deny", "sibling": "write the change to a file and hand it over"}
  ]}
}`

func TestParsePolicyModuleReadsTheBlock(t *testing.T) {
	policy, err := ParsePolicyModule(validPolicy)
	if err != nil {
		t.Fatalf("ParsePolicyModule: %v", err)
	}
	if policy.Role != "dev" {
		t.Errorf("role = %q, want dev", policy.Role)
	}
	if policy.StartupTimeoutMs == nil || *policy.StartupTimeoutMs != 0 {
		t.Errorf("startupTimeoutMs = %v, want a set 0", policy.StartupTimeoutMs)
	}
	if len(policy.BashRules) != 1 || policy.BashRules[0].Match != "sudo *" {
		t.Errorf("bash deny = %+v", policy.BashRules)
	}
	if len(policy.ToolRules) != 1 || policy.ToolRules[0].Match != "edit" {
		t.Errorf("tool deny = %+v", policy.ToolRules)
	}

	// An ABSENT setting is a different fact from a setting of 0, which is why the parse keeps the
	// difference rather than defaulting: a block that does not speak about the startup window must not
	// look like one that sets it.
	bare, err := ParsePolicyModule(`{"role": "lead"}`)
	if err != nil {
		t.Fatalf("ParsePolicyModule(bare): %v", err)
	}
	if bare.StartupTimeoutMs != nil {
		t.Errorf("an absent startupTimeoutMs parsed as %v, want nil", *bare.StartupTimeoutMs)
	}
	if len(bare.BashRules) != 0 || len(bare.ToolRules) != 0 {
		t.Errorf("a block with no rules produced rules: %+v/%+v", bare.BashRules, bare.ToolRules)
	}
}

// TestParsePolicyModuleRefusesADenialWithoutASibling is the reviewer's rule enforced at the layer
// where rules are declared: a denial with a named sibling is a rule, a denial without one is a trap -
// it tells a seat what it may not do and leaves it to guess what it may. Requiring it at PARSE time
// means no block can be published or seeded carrying a trap.
func TestParsePolicyModuleRefusesADenialWithoutASibling(t *testing.T) {
	_, err := ParsePolicyModule(`{"role": "dev", "bash": {"patterns": [{"match": "sudo *", "approval": "deny"}]}}`)
	if err == nil {
		t.Fatal("a denial with no sibling was accepted")
	}
	if !strings.Contains(err.Error(), "sibling") || !strings.Contains(err.Error(), "trap") {
		t.Errorf("error = %q, want it to name the sibling and why it is required", err.Error())
	}
}

func TestParsePolicyModuleNamesWhatItRefuses(t *testing.T) {
	cases := []struct {
		name    string
		content string
		want    string
	}{
		{"not an object", `["nope"]`, "content is not a JSON object"},
		{"no role", `{"mcp": {"startupTimeoutMs": 0}}`, "role is required"},
		{"blank role", `{"role": "   "}`, "role is required"},
		{
			"unknown approval",
			`{"role": "dev", "bash": {"patterns": [{"match": "x", "approval": "ask", "sibling": "s"}]}}`,
			"only \"deny\"",
		},
		{
			"a rule with no match",
			`{"role": "dev", "tools": {"patterns": [{"approval": "deny", "sibling": "s"}]}}`,
			"match is required",
		},
		{"negative startup window", `{"role": "dev", "mcp": {"startupTimeoutMs": -1}}`, "must not be negative"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := ParsePolicyModule(tc.content)
			if err == nil {
				t.Fatalf("accepted, want a refusal naming %q", tc.want)
			}
			if !strings.Contains(err.Error(), tc.want) {
				t.Errorf("error = %q, want it to contain %q", err.Error(), tc.want)
			}
		})
	}
}

// TestParsePolicyModuleAcceptsAnAllowanceWithoutASibling: an allowance IS the sanctioned alternative,
// so requiring a sibling of it would be a second voice saying the same thing. The asymmetry is the
// rule - a denial without a sibling is a trap, an allowance without one is complete.
func TestParsePolicyModuleAcceptsAnAllowanceWithoutASibling(t *testing.T) {
	policy, err := ParsePolicyModule(`{"role":"dev","bash":{"patterns":[{"match":"rig whoami*","approval":"allow"}]}}`)
	if err != nil {
		t.Fatalf("an allowance was refused: %v", err)
	}
	if len(policy.BashRules) != 1 || policy.BashRules[0].Approval != "allow" || policy.BashRules[0].Sibling != "" {
		t.Errorf("bash rules = %+v, want one allowance with no sibling", policy.BashRules)
	}
}

// TestParsePolicyModuleStillRefusesAnUnknownApprovalByName: teaching the guard one more value must not
// widen it. The sentence worth keeping is that an approval it cannot express is refused BY NAME, so it
// can never silently not apply - and the message names BOTH values it can express, so a publisher
// reading only the error knows what to write.
func TestParsePolicyModuleStillRefusesAnUnknownApprovalByName(t *testing.T) {
	_, err := ParsePolicyModule(`{"role":"dev","bash":{"patterns":[{"match":"rig send*","approval":"prompt","sibling":"use seatcheck"}]}}`)
	if err == nil {
		t.Fatal("an approval the kind cannot express was accepted")
	}
	for _, want := range []string{`"prompt"`, `only "deny" and "allow" are`, "silently not apply"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error = %q, want it to contain %q", err.Error(), want)
		}
	}
}
