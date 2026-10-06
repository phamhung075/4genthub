package seatrenderer

import (
	"strings"
	"testing"
)

// Packet 6, step 1: THE JOIN THE WITHDRAWAL RESTS ON, and the one nobody had executed.
//
// The generator writes a limits section for EVERY seat from its own table. After the withdrawal that
// section must come from the render instead, and the render emits it ONLY for a seat whose resolution
// carries a policy module - renderer.go guards the call with `policySet.Role != ""`, and FoldPolicies
// reads only `kind: policy` (policy_fold.go:37). So the fourth sentence of the retirement commit is
// "this must land WITH the policy modules", and the evidence for it is that the same seat, rendered
// twice, differs in exactly that section.
//
// It is the GUARD that is pinned here rather than the emitter: policy_fold_test.go already tests
// RenderPolicyLimits as a function, but renderAgentsMD has one caller and no test reached it, so the
// statement "the limits land in the rendered AGENTS.md" had never run in this repo.
func TestRenderSeatCarriesTheLimitsOnlyWhenTheSeatHasAPolicyModule(t *testing.T) {
	guide := guideModule("guide-common", "## Guide: every seat\n\nshared words\n")
	policy := policyModule("policy.dev", `{"role":"dev","bash":{"patterns":[{"match":"sudo *","approval":"deny","sibling":"ask the lead"}]}}`)

	withPolicy, err := RenderSeat(withMCP(seatFixture("omp"), guide, policy), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat with a policy module: %v", err)
	}
	carrying := fileContent(t, withPolicy, "AGENTS.md")
	for _, want := range []string{
		"## Your limits as seat (dev)",
		"### Refused shell commands",
		"- `sudo *` — instead: ask the lead",
		"## Guide: every seat",
	} {
		if !strings.Contains(carrying, want) {
			t.Fatalf("a seat with a policy module must carry %q in AGENTS.md; got:\n%s", want, carrying)
		}
	}

	// THE SAME SEAT WITHOUT THE POLICY MODULE. The document is still written - the guide is there - so
	// what is absent is the limits section and not the file, which is the distinction the retirement
	// sentence is worded around.
	guidesOnly, err := RenderSeat(withMCP(seatFixture("omp"), guide), testMCPURL)
	if err != nil {
		t.Fatalf("RenderSeat without a policy module: %v", err)
	}
	bare := fileContent(t, guidesOnly, "AGENTS.md")
	if !strings.Contains(bare, "## Guide: every seat") {
		t.Fatalf("the guides-only document must still be written; got:\n%s", bare)
	}
	if strings.Contains(bare, "## Your limits as seat") {
		t.Fatalf("without a policy module the render must not invent a limits section; got:\n%s", bare)
	}
}
