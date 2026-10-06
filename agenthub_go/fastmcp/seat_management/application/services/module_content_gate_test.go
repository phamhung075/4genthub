package services

import (
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

// TestValidateModuleContentIsTheGateBothWritersCall pins the refusals a module version must meet,
// whichever writer is asking. The publish route and the seat seeder both call this function now, so
// the cases here are the contract they share - and the last one is the rule that used to live only
// on the route.
func TestValidateModuleContentIsTheGateBothWritersCall(t *testing.T) {
	cases := []struct {
		name    string
		kind    resolver.ModuleKind
		content string
		want    string
	}{
		{"unknown kind", resolver.ModuleKind("bogus"), "x", `kind "bogus" is not a module kind`},
		{"empty content", resolver.KindInstruction, "", "content must be 1 to 65536 bytes"},
		{
			"content over the bound", resolver.KindInstruction,
			strings.Repeat("x", MaxModuleContentBytes+1), "content must be 1 to 65536 bytes",
		},
		{
			"content the kind's renderer cannot read", resolver.KindSkill,
			"this is not a skill block", "skill content",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := ValidateModuleContent(tc.kind, tc.content)
			if err == nil {
				t.Fatalf("content was accepted, want %q", tc.want)
			}
			if !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("error = %q, want it to contain %q", err.Error(), tc.want)
			}
		})
	}

	// The kind with no kind-specific rule, at the bound: accepted.
	if err := ValidateModuleContent(resolver.KindInstruction, "role"); err != nil {
		t.Fatalf("a plain instruction module was refused: %v", err)
	}
	if err := ValidateModuleContent(resolver.KindInstruction, strings.Repeat("x", MaxModuleContentBytes)); err != nil {
		t.Fatalf("content exactly at the bound was refused: %v", err)
	}
}

// THE NEW KIND IS COVERED BY THE SAME GATE, which is the property the gate's own existence buys: the
// policy kind was added after the gate was unified, and it is enforced for BOTH writers - the publish
// route and the seeder - without either of them being told about it.
func TestValidateModuleContentCoversThePolicyKindBothWritersCall(t *testing.T) {
	good := `{"role":"dev","bash":{"patterns":[{"match":"sudo *","approval":"deny","sibling":"ask the lead"}]}}`
	if err := ValidateModuleContent(resolver.KindPolicy, good); err != nil {
		t.Fatalf("a readable policy block was refused: %v", err)
	}
	err := ValidateModuleContent(resolver.KindPolicy, `{"role":"dev","bash":{"patterns":[{"match":"x","approval":"deny"}]}}`)
	if err == nil || !strings.Contains(err.Error(), "sibling") {
		t.Fatalf("a policy whose denial has no sibling was accepted: %v", err)
	}
}

// The secret case is the ONE refusal a caller maps to its own surface (the route answers 422 for it),
// so it is an error the caller can recognise rather than a message to match on.
func TestValidateModuleContentNamesTheSecretCaseForTheCaller(t *testing.T) {
	err := ValidateModuleContent(resolver.KindInstruction, "openssl key: sk-live-abcdefghijklmnopqrstuvwxyz012345")
	if err == nil {
		t.Fatal("a secret in the content was accepted")
	}
	if !errors.Is(err, ErrModuleSecretDetected) {
		t.Fatalf("error = %v, want it to wrap ErrModuleSecretDetected", err)
	}
}
