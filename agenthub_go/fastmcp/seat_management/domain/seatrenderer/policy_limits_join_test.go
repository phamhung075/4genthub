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
// It is the GUARD that is pinned here, and the positive half is not new: policy_fold_test.go's
// TestRenderSeatEmitsBothArtifactsFromOneFold already drives RenderSeat with a policy module and
// asserts the refusals appear in AGENTS.md. Measured, not assumed - a `-skip` run of this file covers
// the identical block set as a run without it (204 blocks either way), so this file adds no coverage.
// A grep for `renderAgentsMD` finds only its one code caller (renderer.go:206), which is why "no test
// calls it" was the wrong conclusion to draw: tests reach it THROUGH RenderSeat.
//
// WHAT THIS FILE ADDS is the other half of the guard - no other test asserts that a guide-carrying seat
// WITHOUT a policy module gets a document with no limits section. The positive half below is the CONTROL
// that makes that absence mean something; on its own the absence would also be satisfied by a policy
// path that is simply broken.
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
