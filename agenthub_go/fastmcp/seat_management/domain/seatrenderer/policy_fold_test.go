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
	if len(folded.BashRules) != 2 || folded.BashRules[0].Match != "a" || folded.BashRules[1].Match != "c" {
		t.Errorf("bash deny did not union: %+v", folded.BashRules)
	}
	if len(folded.ToolRules) != 1 {
		t.Errorf("tool deny = %+v", folded.ToolRules)
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
	if len(repeated.BashRules) != 1 {
		t.Errorf("bash deny = %+v, want the rule once", repeated.BashRules)
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

// TestRenderPolicyConfigEmitsAnAllowanceFirst: the document the CLIENT installs carries the allowance,
// and it carries it FIRST - the same choice the hand-written generator makes, so the exemption is safe
// under either match order rather than only under first-match.
func TestRenderPolicyConfigEmitsAnAllowanceFirst(t *testing.T) {
	folded, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"dev","bash":{"patterns":[{"match":"rig whoami*","approval":"allow"},{"match":"git push*","approval":"deny","sibling":"commit and tell the lead"}]}}`),
	})
	if err != nil {
		t.Fatalf("FoldPolicies: %v", err)
	}
	doc, err := RenderPolicyConfig(folded)
	if err != nil {
		t.Fatalf("RenderPolicyConfig: %v", err)
	}
	allow := strings.Index(doc, "rig whoami*")
	deny := strings.Index(doc, "git push*")
	if allow < 0 || deny < 0 {
		t.Fatalf("the document lacks a rule:\n%s", doc)
	}
	if allow > deny {
		t.Errorf("the allowance must come first so either match order is safe:\n%s", doc)
	}
	if !strings.Contains(doc, "approval: allow") {
		t.Errorf("the allowance did not reach the document:\n%s", doc)
	}
}

// TestFoldRefusesAMatchThatIsBothAllowedAndDenied: one match cannot be both, and the fold REFUSES
// rather than picking a winner - a seat would then have to guess which one the runtime applied.
func TestFoldRefusesAMatchThatIsBothAllowedAndDenied(t *testing.T) {
	_, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"dev","bash":{"patterns":[{"match":"rig whoami*","approval":"allow"}]}}`),
		policyModule("policy.b", `{"role":"dev","bash":{"patterns":[{"match":"rig whoami*","approval":"deny","sibling":"ask the lead"}]}}`),
	})
	if err == nil {
		t.Fatal("a match declared both allowed and denied was folded instead of refused")
	}
	if !strings.Contains(err.Error(), "both refused and allowed") {
		t.Errorf("error = %q, want it to name the contradiction", err.Error())
	}
}

// TestRenderPolicyLimitsSeparatesTheAllowanceFromTheRefusals: the SEAT reads these words, so an
// allowance listed under a "Refused" heading would tell it the opposite of what its policy says.
func TestRenderPolicyLimitsSeparatesTheAllowanceFromTheRefusals(t *testing.T) {
	folded, err := FoldPolicies([]resolver.ResolvedModule{
		policyModule("policy.a", `{"role":"dev","bash":{"patterns":[{"match":"rig whoami*","approval":"allow"},{"match":"git push*","approval":"deny","sibling":"commit and tell the lead"}]}}`),
	})
	if err != nil {
		t.Fatalf("FoldPolicies: %v", err)
	}
	text := RenderPolicyLimits(folded)
	allowedAt := strings.Index(text, "### Allowed in every approval mode")
	refusedAt := strings.Index(text, "### Refused shell commands")
	whoamiAt := strings.Index(text, "`rig whoami*`")
	pushAt := strings.Index(text, "`git push*`")
	if allowedAt < 0 || refusedAt < 0 || whoamiAt < 0 || pushAt < 0 {
		t.Fatalf("the limits text lacks a section or a rule:\n%s", text)
	}
	if !(allowedAt < whoamiAt && whoamiAt < refusedAt && refusedAt < pushAt) {
		t.Errorf("the allowance belongs under the allowed heading and the denial under the refused one:\n%s", text)
	}
	if strings.Contains(text[:refusedAt], "— instead:") {
		t.Errorf("the allowed section names an alternative, which an allowance does not have:\n%s", text)
	}
}

// TestFoldRefusesASeatScopedAllowance: an allowance is the ROOM OWNER'S act. A seat cannot compose
// itself, so every block in its stack was put there by whoever owns the room - with one exception the
// resolver records, an OVERRIDE, whose content the overlay supplied. At the seat scope that is the
// seat's own act, so the allowance is refused BY NAME with the way out, the same form as the guard's
// refusal of an approval it cannot express.
func TestFoldRefusesASeatScopedAllowance(t *testing.T) {
	const allowRule = `{"role":"dev","bash":{"patterns":[{"match":"rig whoami*","approval":"allow"}]}}`

	seatScoped := policyModule("policy.a", allowRule)
	seatScoped.Overridden = true
	seatScoped.ContentScope = resolver.ScopeSeat

	_, err := FoldPolicies([]resolver.ResolvedModule{seatScoped})
	if err == nil {
		t.Fatal("a seat-scoped allowance was folded instead of refused")
	}
	for _, want := range []string{`"policy.a"`, `"rig whoami*"`, "seat-scoped", "room owner's act", "move the block to the room scope"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error = %q, want it to contain %q", err.Error(), want)
		}
	}

	// POSITIVE CONTROL 1: the same allowance from the ROOM scope folds, so this is a scope rule rather
	// than a ban on allowances.
	roomScoped := policyModule("policy.a", allowRule)
	roomScoped.Overridden = true
	roomScoped.ContentScope = "room" // ScopeRoom is unexported on purpose: only ScopeSeat has a production reader.
	if _, err := FoldPolicies([]resolver.ResolvedModule{roomScoped}); err != nil {
		t.Errorf("a room-scoped allowance was refused: %v", err)
	}

	// POSITIVE CONTROL 2, and the reason the rule keys on the OVERRIDE rather than on the scope alone:
	// an ADDED module carries the owner's PUBLISH and no overlay content, so it folds at any scope.
	// This is the case the ten room policy modules take, and it must not be refused.
	added := policyModule("policy.a", allowRule)
	added.Overridden = false
	added.ContentScope = resolver.ScopeSeat
	if _, err := FoldPolicies([]resolver.ResolvedModule{added}); err != nil {
		t.Errorf("an added module was refused: %v", err)
	}
}
