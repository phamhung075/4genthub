package contextpacks

import (
	"errors"
	"reflect"
	"strings"
	"testing"
)

// doc is the one markdown fixture every compose test reads through a fake reader.
const doc = "# Pack notes\n\nIntro line.\n\n## Alpha\n\nAlpha body.\n\n" +
	"### Alpha one\n\nAlpha one body.\n\n## Beta\n\nBeta body.\n"

func reader(t *testing.T) func(string) (string, error) {
	t.Helper()
	return func(ref string) (string, error) {
		if ref != "notes.md" {
			return "", errors.New("no such file: " + ref)
		}
		return doc, nil
	}
}

func atom(id, address string, order int, priority Priority, situations ...Situation) Atom {
	return Atom{ID: id, Address: address, Order: order, Priority: priority,
		Situations: situations, Runtime: RuntimeAny}
}

// The three locked modes, each with a real input. FRESH is the base walk; HANDOVER adds the
// handover material; POST-COMPACTION is the tagged subset plus the handover material.
func TestComposeProfileThreeModes(t *testing.T) {
	atoms := []Atom{
		atom("alpha", "notes.md#alpha", 1, PriorityCore, SituationFresh),
		atom("alpha-one", "notes.md#alpha/alpha-one", 2, PriorityRecommended, SituationFresh, SituationPostCompaction),
		atom("beta", "notes.md#beta", 3, PriorityOptional, SituationHandover),
	}

	// FRESH: only the fresh-tagged atoms.
	fresh, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("fresh: %v", err)
	}
	if ids := pieceIDs(fresh.Pieces); !reflect.DeepEqual(ids, []string{"alpha", "alpha-one"}) {
		t.Fatalf("fresh pieces = %v, want [alpha alpha-one]", ids)
	}
	// The full-span rule: alpha's piece carries its H3 child, not just its own text.
	if !strings.Contains(fresh.Pieces[0].Text, "### Alpha one") || !strings.Contains(fresh.Pieces[0].Text, "Alpha one body.") {
		t.Errorf("alpha piece is not the FULL span (child missing): %q", fresh.Pieces[0].Text)
	}
	if strings.Contains(fresh.Pieces[0].Text, "Beta body.") {
		t.Errorf("alpha piece ran past the next same-or-higher header: %q", fresh.Pieces[0].Text)
	}

	// HANDOVER: fresh + handover.
	handover, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationHandover, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("handover: %v", err)
	}
	if ids := pieceIDs(handover.Pieces); !reflect.DeepEqual(ids, []string{"alpha", "alpha-one", "beta"}) {
		t.Fatalf("handover pieces = %v, want [alpha alpha-one beta]", ids)
	}

	// POST-COMPACTION: the tagged subset plus handover.
	post, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationPostCompaction, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("post-compaction: %v", err)
	}
	if ids := pieceIDs(post.Pieces); !reflect.DeepEqual(ids, []string{"alpha-one", "beta"}) {
		t.Fatalf("post-compaction pieces = %v, want [alpha-one beta]", ids)
	}
}

// The determinism property: composing twice from the same input gives the same result.
func TestComposeProfileIsDeterministic(t *testing.T) {
	atoms := []Atom{
		atom("b", "notes.md#beta", 2, PriorityOptional, SituationFresh),
		atom("a", "notes.md#alpha", 1, PriorityCore, SituationFresh),
		atom("c", "notes.md", 3, PriorityCore, SituationHandover),
	}
	in := ComposeInput{Atoms: atoms, Situation: SituationHandover, Runtime: RuntimeClaude, ReadFile: reader(t)}
	first, err := ComposeProfile(in)
	if err != nil {
		t.Fatalf("first: %v", err)
	}
	second, err := ComposeProfile(in)
	if err != nil {
		t.Fatalf("second: %v", err)
	}
	if !reflect.DeepEqual(first, second) {
		t.Fatalf("compose is not deterministic:\n first=%+v\nsecond=%+v", first, second)
	}
	// And the walk is ordered by Order, not by declaration order.
	if ids := pieceIDs(first.Pieces); !reflect.DeepEqual(ids, []string{"a", "b", "c"}) {
		t.Fatalf("order = %v, want [a b c] (by Order 1,2,3)", ids)
	}
}

// A required atom joins even when untagged; a missing dependency and a runtime-excluded one are
// both loud.
func TestComposeClosesOverRequires(t *testing.T) {
	withDep := []Atom{
		{ID: "root", Address: "notes.md#alpha", Order: 1, Priority: PriorityCore,
			Situations: []Situation{SituationFresh}, Runtime: RuntimeAny, Requires: []string{"dep"}},
		{ID: "dep", Address: "notes.md#beta", Order: 2, Priority: PriorityCore,
			Situations: []Situation{SituationHandover}, Runtime: RuntimeAny}, // untagged for fresh
	}
	got, err := ComposeProfile(ComposeInput{Atoms: withDep, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("closure: %v", err)
	}
	if ids := pieceIDs(got.Pieces); !reflect.DeepEqual(ids, []string{"root", "dep"}) {
		t.Fatalf("closure pieces = %v, want [root dep]", ids)
	}

	missing := []Atom{{ID: "root", Address: "notes.md#alpha", Order: 1, Priority: PriorityCore,
		Situations: []Situation{SituationFresh}, Runtime: RuntimeAny, Requires: []string{"ghost"}}}
	_, err = ComposeProfile(ComposeInput{Atoms: missing, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err == nil || !strings.Contains(err.Error(), "cannot close") {
		t.Fatalf("missing dependency error = %v, want a loud cannot-close", err)
	}

	excluded := []Atom{
		{ID: "root", Address: "notes.md#alpha", Order: 1, Priority: PriorityCore,
			Situations: []Situation{SituationFresh}, Runtime: RuntimeAny, Requires: []string{"codexonly"}},
		{ID: "codexonly", Address: "notes.md#beta", Order: 2, Priority: PriorityCore,
			Situations: []Situation{SituationFresh}, Runtime: RuntimeCodex},
	}
	_, err = ComposeProfile(ComposeInput{Atoms: excluded, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err == nil || !strings.Contains(err.Error(), "silently thin") {
		t.Fatalf("runtime-excluded dependency error = %v, want a loud refusal", err)
	}
}

// The runtime filter: an atom declared for the other runtime never joins.
func TestComposeFiltersByRuntime(t *testing.T) {
	atoms := []Atom{
		atom("both", "notes.md#alpha", 1, PriorityCore, SituationFresh),
		{ID: "codex", Address: "notes.md#beta", Order: 2, Priority: PriorityCore,
			Situations: []Situation{SituationFresh}, Runtime: RuntimeCodex},
	}
	got, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("compose: %v", err)
	}
	if ids := pieceIDs(got.Pieces); !reflect.DeepEqual(ids, []string{"both"}) {
		t.Fatalf("runtime filter pieces = %v, want [both]", ids)
	}
}

// A profileOnly atom never joins the legacy situation profile.
func TestComposeSkipsProfileOnlyAtoms(t *testing.T) {
	atoms := []Atom{
		atom("normal", "notes.md#alpha", 1, PriorityCore, SituationFresh),
		{ID: "map-only", Address: "notes.md#beta", Order: 2, Priority: PriorityCore,
			Situations: []Situation{SituationFresh}, Runtime: RuntimeAny, ProfileOnly: true},
	}
	got, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("compose: %v", err)
	}
	if ids := pieceIDs(got.Pieces); !reflect.DeepEqual(ids, []string{"normal"}) {
		t.Fatalf("profileOnly pieces = %v, want [normal]", ids)
	}
}

// Over budget the compose REPORTS and never truncates: every piece stays, and the drop order is
// optional first, then larger pieces within a tier.
func TestComposeBudgetReportsAndNeverTruncates(t *testing.T) {
	atoms := []Atom{
		atom("core-small", "notes.md#alpha", 1, PriorityCore, SituationFresh),
		atom("opt-big", "notes.md", 2, PriorityOptional, SituationFresh),
		atom("rec", "notes.md#beta", 3, PriorityRecommended, SituationFresh),
	}
	total := 0
	pre, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("unbudgeted: %v", err)
	}
	total = pre.TotalEstimatedTokens
	limit := total - 1
	got, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t), BudgetTokens: &limit})
	if err != nil {
		t.Fatalf("budgeted: %v", err)
	}
	if len(got.Pieces) != len(pre.Pieces) {
		t.Fatalf("budget truncated the compose: %d pieces, want %d", len(got.Pieces), len(pre.Pieces))
	}
	if got.Budget == nil {
		t.Fatal("over budget but no report")
	}
	if got.Budget.OverageTokens != 1 || got.Budget.LimitTokens != limit {
		t.Errorf("budget = %+v, want limit %d and overage 1", got.Budget, limit)
	}
	if len(got.Budget.DropCandidates) != 3 || got.Budget.DropCandidates[0].AtomID != "opt-big" {
		t.Errorf("drop order = %+v, want opt-big first", got.Budget.DropCandidates)
	}
	// Under budget there is no report at all.
	big := total + 10
	under, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t), BudgetTokens: &big})
	if err != nil {
		t.Fatalf("under budget: %v", err)
	}
	if under.Budget != nil {
		t.Errorf("under budget but a report was emitted: %+v", under.Budget)
	}
}

// A dangling address fails the compose loudly, naming the atom — never a silent drop.
func TestComposeRejectsDanglingAddress(t *testing.T) {
	atoms := []Atom{atom("missing", "notes.md#no-such-section", 1, PriorityCore, SituationFresh)}
	_, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err == nil {
		t.Fatal("a dangling header path composed silently")
	}
	var composeErr *ProfileComposeError
	if !errors.As(err, &composeErr) {
		t.Fatalf("error = %T (%v), want *ProfileComposeError", err, err)
	}
	if !strings.Contains(err.Error(), "missing") || !strings.Contains(err.Error(), "matches no header") {
		t.Errorf("error %q should name the atom and the miss", err)
	}
	// An unreadable source file is equally loud.
	unreadable := []Atom{atom("a", "absent.md#alpha", 1, PriorityCore, SituationFresh)}
	if _, err := ComposeProfile(ComposeInput{Atoms: unreadable, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)}); err == nil {
		t.Error("an unreadable source composed silently")
	}
}

// A named profile composes phases; atom phases and context phases differ, and a missing context
// selection or a missing atom is loud.
func TestComposeNamedProfile(t *testing.T) {
	atoms := []Atom{
		atom("alpha", "notes.md#alpha", 1, PriorityCore, SituationFresh),
		atom("beta", "notes.md#beta", 2, PriorityCore, SituationFresh),
	}
	missionAtom := Atom{ID: "mission-one", Address: "notes.md#beta", Order: 1, Priority: PriorityCore,
		Situations: []Situation{SituationFresh}, Runtime: RuntimeAny}
	profile := Profile{
		ID: "install-v1", Situations: []Situation{SituationFresh}, Runtimes: []Runtime{RuntimeClaude},
		Phases: []ProfilePhase{
			{ID: "p1", Atoms: []string{"alpha"}},
			{ID: "p2", Context: []string{"mission"}},
		},
	}
	got, err := ComposeNamedProfile(
		ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)},
		profile, map[string][]Atom{"mission": {missionAtom}})
	if err != nil {
		t.Fatalf("named profile: %v", err)
	}
	if got.ProfileID != "install-v1" || len(got.Phases) != 2 {
		t.Fatalf("named profile result = %+v", got)
	}
	if got.Phases[0].Kind != "atoms" || got.Phases[0].Pieces[0].PhaseID != "p1" {
		t.Errorf("phase 1 = %+v, want atoms/p1", got.Phases[0])
	}
	if got.Phases[1].Kind != "context" || !reflect.DeepEqual(got.Phases[1].Sources, []string{"mission"}) {
		t.Errorf("phase 2 = %+v, want context with the mission source", got.Phases[1])
	}
	if len(got.Pieces) != 2 {
		t.Errorf("flattened pieces = %d, want 2", len(got.Pieces))
	}

	// A missing context selection must be loud, not silently empty.
	if _, err := ComposeNamedProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)},
		profile, nil); err == nil || !strings.Contains(err.Error(), "did not supply") {
		t.Errorf("missing context error = %v, want a loud refusal", err)
	}
	// A phase naming a missing atom is loud.
	badAtom := profile
	badAtom.Phases = []ProfilePhase{{ID: "p1", Atoms: []string{"ghost"}}}
	if _, err := ComposeNamedProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)},
		badAtom, nil); err == nil || !strings.Contains(err.Error(), "missing atom") {
		t.Errorf("missing atom error = %v, want a loud refusal", err)
	}
	// Situation and runtime applicability are checked.
	wrongSituation := profile
	wrongSituation.Situations = []Situation{SituationHandover}
	if _, err := ComposeNamedProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)},
		wrongSituation, map[string][]Atom{"mission": {missionAtom}}); err == nil {
		t.Error("a profile applied to the wrong situation was accepted")
	}
}

// The source label defaults to library and is overridable per atom.
func TestComposeLabelsSources(t *testing.T) {
	atoms := []Atom{atom("alpha", "notes.md#alpha", 1, PriorityCore, SituationFresh)}
	got, err := ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t)})
	if err != nil {
		t.Fatalf("compose: %v", err)
	}
	if got.Pieces[0].SourceKind != SourceLibrary {
		t.Errorf("default source = %q, want library", got.Pieces[0].SourceKind)
	}
	got, err = ComposeProfile(ComposeInput{Atoms: atoms, Situation: SituationFresh, Runtime: RuntimeClaude, ReadFile: reader(t),
		SourceKindFor: func(Atom) SourceKind { return SourceMission }})
	if err != nil {
		t.Fatalf("compose: %v", err)
	}
	if got.Pieces[0].SourceKind != SourceMission {
		t.Errorf("labelled source = %q, want mission", got.Pieces[0].SourceKind)
	}
}

func pieceIDs(pieces []Piece) []string {
	out := make([]string, 0, len(pieces))
	for _, p := range pieces {
		out = append(out, p.AtomID)
	}
	return out
}
