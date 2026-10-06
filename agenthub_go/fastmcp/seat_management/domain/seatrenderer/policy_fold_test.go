package seatrenderer

import (
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

func policyModule(slug, content string) resolver.ResolvedModule {
	return resolver.ResolvedModule{Slug: slug, Version: "1.0.0", Kind: resolver.KindPolicy, Content: content}
}

// TestFoldPoliciesUnionsDenyListsAndRefusesDisagreeingScalars is the asymmetry: adding a deny can only
// make a seat safer, so denials union with no winner to argue about, while a scalar two blocks both
// speak about must agree - silent last-writer-wins on a runtime setting is how a second source of
// truth starts.
func TestFoldPoliciesUnionsDenyListsAndRefusesDisagreeingScalars(t *testing.T) {
	folded, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.role", `{"role":"dev","mcp":{"startupTimeoutMs":0},"bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use b"}]}}`),
		policyModule("policy.extra", `{"role":"dev","bash":{"patterns":[{"match":"c","approval":"deny","sibling":"use d"}]},"tools":{"patterns":[{"match":"edit","approval":"deny","sibling":"hand it over"}]}}`),
	})
	if err != nil {
		t.Fatalf("FoldPolicies: %v", err)
	}
	if folded.Role != "dev" {
		t.Errorf("role = %q", folded.Role)
	}
	if folded.StartupTimeoutMs == nil || *folded.StartupTimeoutMs != 0 {
		t.Errorf("startupTimeoutMs = %v, want a set 0", folded.StartupTimeoutMs)
	}
	if len(folded.BashDeny) != 2 || folded.BashDeny[0].Match != "a" || folded.BashDeny[1].Match != "c" {
		t.Errorf("bash deny did not union: %+v", folded.BashDeny)
	}
	if len(folded.ToolDeny) != 1 {
		t.Errorf("tool deny = %+v", folded.ToolDeny)
	}

	// A block that does not speak about a scalar does not veto it: nil is silent, not zero.
	quiet, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.role", `{"role":"dev","mcp":{"startupTimeoutMs":1}}`),
		policyModule("policy.quiet", `{"role":"dev"}`),
	})
	if err != nil {
		t.Fatalf("a silent block vetoed a scalar: %v", err)
	}
	if quiet.StartupTimeoutMs == nil || *quiet.StartupTimeoutMs != 1 {
		t.Errorf("startupTimeoutMs = %v, want the one value a block declared", quiet.StartupTimeoutMs)
	}

	for _, tc := range []struct {
		name string
		a, b string
		want string
	}{
		{"role", `{"role":"dev"}`, `{"role":"lead"}`, "one role"},
		{
			"startup window",
			`{"role":"dev","mcp":{"startupTimeoutMs":1}}`,
			`{"role":"dev","mcp":{"startupTimeoutMs":2}}`,
			"refuses to pick a winner",
		},
		{
			"sibling for one refusal",
			`{"role":"dev","bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use b"}]}}`,
			`{"role":"dev","bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use z"}]}}`,
			"two sanctioned alternatives",
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			_, err := FoldPolicies([]resolver.ResolvedModule{
				policyModule("policy.a", tc.a), policyModule("policy.b", tc.b),
			})
			if err == nil {
				t.Fatalf("a disagreement about %s folded silently", tc.name)
			}
			if !strings.Contains(err.Error(), tc.want) {
				t.Errorf("error = %q, want it to contain %q", err.Error(), tc.want)
			}
		})
	}

	// The same rule declared twice with the SAME sibling is one rule, not a conflict: a block added
	// again at another level must not refuse the render.
	repeated, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"dev","bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use b"}]}}`),
		policyModule("policy.b", `{"role":"dev","bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use b"}]}}`),
	})
	if err != nil {
		t.Fatalf("an identical rule declared twice did not fold: %v", err)
	}
	if len(repeated.BashDeny) != 1 {
		t.Errorf("bash deny = %+v, want the rule once", repeated.BashDeny)
	}
}

// TestRenderSeatEmitsBothArtifactsFromOneFold is the claim that retires the hand-built notice: the
// document the runtime reads and the words the seat reads come from ONE parse. It is asserted from the
// ARTIFACTS rather than from the fold, because two code paths that happen to agree today would pass a
// test written against the fold.
func TestRenderSeatEmitsBothArtifactsFromOneFold(t *testing.T) {
	seat := withMCP(
		seatFixture("omp"),
		policyModule("policy.dev", `{"role":"dev","mcp":{"startupTimeoutMs":0},"bash":{"patterns":[
			{"match":"sudo thing","approval":"deny","sibling":"ask the lead to run it"},
			{"match":"forced delete","approval":"deny","sibling":"remove one named file"}]}}`),
		mcpPlatformModule(),
	)
	spec, err := RenderSeat(seat, testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}
	config := fileContent(t, spec, "runtime/omp-config.yml")
	agents := fileContent(t, spec, "AGENTS.md")

	// The SAME refusals, read out of each artifact: the set in the document is the set in the words.
	for _, match := range []string{"sudo thing", "forced delete"} {
		if !strings.Contains(config, match) {
			t.Errorf("the config document lacks the refusal %q:\n%s", match, config)
		}
		if !strings.Contains(agents, "- `"+match+"`") {
			t.Errorf("the limits text lacks the refusal %q:\n%s", match, agents)
		}
	}
	if strings.Contains(config, "sibling") || strings.Contains(config, "ask the lead to run it") {
		t.Errorf("a sibling reached runtime configuration; it is words for the seat:\n%s", config)
	}
	// The setting the block declared reached the DOCUMENT, not the constant's default path.
	if !strings.Contains(config, "startupTimeoutMs") || !strings.Contains(config, "0") {
		t.Errorf("the declared startup setting did not reach the document:\n%s", config)
	}
	// A seat with no policy block still gets the constant, so the supersession changed one case only.
	plain, err := RenderSeat(withMCP(seatFixture("omp"), mcpPlatformModule()), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat(plain): %v", err)
	}
	if got := fileContent(t, plain, "runtime/omp-config.yml"); got != ompMCPStartupTimeoutConfig {
		t.Errorf("a seat with no policy block did not get the constant:\n%s", got)
	}
}

// TestRenderPolicyConfigOmitsAnAbsentSetting: a setting no block asked for must not appear as a
// literal 0, because "does not speak about it" and "sets it to 0" are different facts.
func TestRenderPolicyConfigOmitsAnAbsentSetting(t *testing.T) {
	silent, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"dev","bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use b"}]}}`),
	})
	if err != nil {
		t.Fatalf("FoldPolicies: %v", err)
	}
	doc, err := RenderPolicyConfig(silent)
	if err != nil {
		t.Fatalf("RenderPolicyConfig: %v", err)
	}
	if strings.Contains(doc, "mcp:") || strings.Contains(doc, "startupTimeoutMs") {
		t.Errorf("an unspoken startup setting reached the document:\n%s", doc)
	}
	if !strings.Contains(doc, "match: a") || !strings.Contains(doc, "approval: deny") {
		t.Errorf("the rule did not reach the document:\n%s", doc)
	}
	if strings.Contains(doc, "sibling") || strings.Contains(doc, "use b") {
		t.Errorf("the sibling is words for the seat, not runtime configuration:\n%s", doc)
	}

	spoken, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"dev","mcp":{"startupTimeoutMs":0}}`),
	})
	if err != nil {
		t.Fatalf("FoldPolicies: %v", err)
	}
	doc, err = RenderPolicyConfig(spoken)
	if err != nil {
		t.Fatalf("RenderPolicyConfig: %v", err)
	}
	if !strings.Contains(doc, "startupTimeoutMs: 0") {
		t.Errorf("a declared 0 did not reach the document:\n%s", doc)
	}
}

// TestRenderPolicyLimitsNamesASiblingForEveryDenial: the words and the rules come from one fold, so a
// denial in the document always has its alternative in the text.
func TestRenderPolicyLimitsNamesASiblingForEveryDenial(t *testing.T) {
	folded, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"reviewer","bash":{"patterns":[{"match":"a","approval":"deny","sibling":"use b"}]},"tools":{"patterns":[{"match":"edit","approval":"deny","sibling":"write your verdict to a file"}]}}`),
	})
	if err != nil {
		t.Fatalf("FoldPolicies: %v", err)
	}
	text := RenderPolicyLimits(folded)
	for _, want := range []string{"reviewer", "`a`", "use b", "`edit`", "write your verdict to a file"} {
		if !strings.Contains(text, want) {
			t.Errorf("the limits text lacks %q:\n%s", want, text)
		}
	}
	// One denial, one alternative: the count is the check that no rule was written without one.
	if got := strings.Count(text, "— instead:"); got != 2 {
		t.Errorf("alternatives = %d, want one per denial (2)", got)
	}
}
