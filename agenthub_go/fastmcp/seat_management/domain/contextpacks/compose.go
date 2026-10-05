package contextpacks

import (
	"fmt"
	"sort"
)

// The composition algebra (OPR.0.5.3.5 Atom 3):
//
//	FRESH           = the base walk (atoms tagged fresh)
//	HANDOVER        = FRESH + the handover material (atoms tagged handover)
//	POST-COMPACTION = the tagged subset of fresh + the handover material
//
// Every profile is CLOSED over requires; the runtime filter runs per mini-req 3 (claude and codex
// compose different profiles from the SAME graph). Each piece carries a source label. Budgets are
// evaluated AT COMPOSE and, on overage, REPORT the amount and the priority-ordered drop
// candidates — composition never silently truncates (D2: budgets flag for review, never silently
// govern). Every failure is LOUD and names the atom.

// Piece is one composed atom's resolved bytes.
type Piece struct {
	AtomID          string
	Address         string
	SourceKind      SourceKind
	Order           int
	Priority        Priority
	Text            string
	EstimatedTokens int
	// PhaseID is present for named-profile pieces so the flattened stream still carries the phase
	// boundary an inspector saw before apply.
	PhaseID string
}

// ProfilePhaseResult is one named-profile phase's pieces.
type ProfilePhaseResult struct {
	ID              string
	Kind            string // "atoms" or "context"
	Sources         []string
	Pieces          []Piece
	EstimatedTokens int
}

// DropCandidate is one entry of the budget report's drop order.
type DropCandidate struct {
	AtomID          string
	Priority        Priority
	EstimatedTokens int
}

// Budget is present ONLY when the budget binds: the report, never a truncation.
type Budget struct {
	LimitTokens    int
	OverageTokens  int
	DropCandidates []DropCandidate
}

// ComposedProfile is the result of composing one situation (or one named profile).
type ComposedProfile struct {
	Situation            Situation
	Runtime              Runtime
	Pieces               []Piece
	TotalEstimatedTokens int
	// ProfileID is present only for an explicitly selected manifest profile.
	ProfileID string
	Phases    []ProfilePhaseResult
	Budget    *Budget
}

// ComposeInput is one compose request. ReadFile is the caller's fail-loud reader keyed by the
// address's pre-`#` ref, which is what keeps this package free of any OS dependency.
type ComposeInput struct {
	Atoms        []Atom
	Situation    Situation
	Runtime      Runtime
	ReadFile     func(ref string) (string, error)
	BudgetTokens *int
	// SourceKindFor labels each atom's source; nil means every piece is labelled library.
	SourceKindFor func(Atom) SourceKind
}

func resolvePieces(atoms []Atom, readFile func(string) (string, error), sourceKindFor func(Atom) SourceKind, phaseID string) ([]Piece, error) {
	pieces := make([]Piece, 0, len(atoms))
	for _, a := range atoms {
		parsed, err := ParseAddress(a.Address)
		if err != nil {
			return nil, &ProfileComposeError{Msg: fmt.Sprintf("atom %q (%s): %v", a.ID, a.Address, err)}
		}
		fileText, err := readFile(parsed.Ref)
		if err != nil {
			return nil, &ProfileComposeError{Msg: fmt.Sprintf(
				"atom %q (%s): source file %q is unreadable — %v", a.ID, a.Address, parsed.Ref, err)}
		}
		text := fileText
		if len(parsed.HeaderPath) > 0 {
			section, err := ResolveAddress(fileText, parsed.HeaderPath)
			if err != nil {
				return nil, &ProfileComposeError{Msg: fmt.Sprintf("atom %q (%s): %v", a.ID, a.Address, err)}
			}
			text = section.Text
		}
		kind := SourceLibrary
		if sourceKindFor != nil {
			kind = sourceKindFor(a)
		}
		pieces = append(pieces, Piece{
			AtomID: a.ID, Address: a.Address, SourceKind: kind, Order: a.Order, Priority: a.Priority,
			Text: text, EstimatedTokens: EstimateTokensOf(text), PhaseID: phaseID,
		})
	}
	return pieces, nil
}

func budgetReport(pieces []Piece, budgetTokens *int) *Budget {
	total := 0
	for _, p := range pieces {
		total += p.EstimatedTokens
	}
	if budgetTokens == nil || total <= *budgetTokens {
		return nil
	}
	candidates := make([]DropCandidate, 0, len(pieces))
	for _, p := range pieces {
		candidates = append(candidates, DropCandidate{AtomID: p.AtomID, Priority: p.Priority, EstimatedTokens: p.EstimatedTokens})
	}
	// Drop order: optional, then recommended, then core; larger pieces first within a tier (the
	// biggest cheap win leads), then atom id.
	sort.SliceStable(candidates, func(i, j int) bool {
		di, dj := dropOrder[candidates[i].Priority], dropOrder[candidates[j].Priority]
		if di != dj {
			return di < dj
		}
		if candidates[i].EstimatedTokens != candidates[j].EstimatedTokens {
			return candidates[i].EstimatedTokens > candidates[j].EstimatedTokens
		}
		return candidates[i].AtomID < candidates[j].AtomID
	})
	return &Budget{LimitTokens: *budgetTokens, OverageTokens: total - *budgetTokens, DropCandidates: candidates}
}

// ComposeProfile composes one situation profile from the atom graph.
func ComposeProfile(in ComposeInput) (ComposedProfile, error) {
	byID := make(map[string]Atom, len(in.Atoms))
	for _, a := range in.Atoms {
		byID[a.ID] = a
	}
	runtimeFits := func(a Atom) bool { return a.Runtime == RuntimeAny || a.Runtime == in.Runtime }

	// 1. SELECT by situation tag, then filter by runtime.
	tags := selectionTags(in.Situation)
	selected := map[string]Atom{}
	order := []string{}
	for _, a := range in.Atoms {
		if a.ProfileOnly {
			continue
		}
		matched := false
		for _, s := range a.Situations {
			if containsSituation(tags, s) {
				matched = true
				break
			}
		}
		if !matched || !runtimeFits(a) {
			continue
		}
		if _, ok := selected[a.ID]; !ok {
			order = append(order, a.ID)
		}
		selected[a.ID] = a
	}

	// 2. CLOSE over requires: a required atom joins even when untagged. A dependency that exists
	// but is excluded by the RUNTIME filter is a broken graph for this runtime — fail loud.
	queue := append([]string{}, order...)
	for len(queue) > 0 {
		id := queue[len(queue)-1]
		queue = queue[:len(queue)-1]
		// The queue only ever holds ids that were added to selected — the seed at the top and each
		// required atom just below — so a miss is an internal invariant violation, not input. Fail
		// loud rather than closing over the zero Atom, which would silently thin the walk.
		atom, ok := selected[id]
		if !ok {
			return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
				"internal invariant violated: atom %q was queued for closure but is not selected", id)}
		}
		for _, req := range atom.Requires {
			if _, ok := selected[req]; ok {
				continue
			}
			dep, ok := byID[req]
			if !ok {
				return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
					"atom %q requires %q, which is not in the graph — the %s profile cannot close.", id, req, in.Situation)}
			}
			if !runtimeFits(dep) {
				return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
					"atom %q requires %q, but %q is declared runtime=%s and this compose targets runtime=%s — "+
						"the closure would silently thin the %s walk; fix the graph (retag %q or drop the edge).",
					id, req, req, dep.Runtime, in.Runtime, in.Situation, req)}
			}
			selected[req] = dep
			order = append(order, req)
			queue = append(queue, req)
		}
	}

	// 3. ORDER the walk (stable: order, then id — absorption depends on sequence).
	walk := make([]Atom, 0, len(selected))
	for _, a := range selected {
		walk = append(walk, a)
	}
	sort.SliceStable(walk, func(i, j int) bool {
		if walk[i].Order != walk[j].Order {
			return walk[i].Order < walk[j].Order
		}
		return walk[i].ID < walk[j].ID
	})

	// 4. RESOLVE every piece; label its source.
	pieces, err := resolvePieces(walk, in.ReadFile, in.SourceKindFor, "")
	if err != nil {
		return ComposedProfile{}, err
	}
	total := 0
	for _, p := range pieces {
		total += p.EstimatedTokens
	}
	return ComposedProfile{
		Situation: in.Situation, Runtime: in.Runtime, Pieces: pieces,
		TotalEstimatedTokens: total, Budget: budgetReport(pieces, in.BudgetTokens),
	}, nil
}

// ComposeNamedProfile composes one explicit manifest profile. Profiles change only selection and
// sequence: every atom still resolves through the same source graph, while context-source atoms
// are supplied by the caller from its configured roots.
func ComposeNamedProfile(in ComposeInput, profile Profile, contextAtoms map[string][]Atom) (ComposedProfile, error) {
	if !containsSituation(profile.Situations, in.Situation) {
		return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
			"profile %q does not apply to situation %q", profile.ID, in.Situation)}
	}
	if !containsRuntime(profile.Runtimes, in.Runtime) {
		return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
			"profile %q does not apply to runtime %q", profile.ID, in.Runtime)}
	}
	atomsByID := make(map[string]Atom, len(in.Atoms))
	for _, a := range in.Atoms {
		atomsByID[a.ID] = a
	}

	phases := make([]ProfilePhaseResult, 0, len(profile.Phases))
	all := []Piece{}
	for _, phase := range profile.Phases {
		var selected []Atom
		kind := "context"
		if len(phase.Atoms) > 0 {
			kind = "atoms"
			for _, atomID := range phase.Atoms {
				atom, ok := atomsByID[atomID]
				if !ok {
					return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
						"profile %q phase %q references missing atom %q", profile.ID, phase.ID, atomID)}
				}
				selected = append(selected, atom)
			}
		} else {
			for _, source := range phase.Context {
				sourceAtoms := contextAtoms[source]
				if len(sourceAtoms) == 0 {
					return ComposedProfile{}, &ProfileComposeError{Msg: fmt.Sprintf(
						"profile %q phase %q needs %s context, but the caller did not supply its exact selection",
						profile.ID, phase.ID, source)}
				}
				selected = append(selected, sourceAtoms...)
			}
		}
		pieces, err := resolvePieces(selected, in.ReadFile, in.SourceKindFor, phase.ID)
		if err != nil {
			return ComposedProfile{}, err
		}
		total := 0
		for _, p := range pieces {
			total += p.EstimatedTokens
		}
		result := ProfilePhaseResult{ID: phase.ID, Kind: kind, Pieces: pieces, EstimatedTokens: total}
		if len(phase.Context) > 0 {
			result.Sources = append([]string{}, phase.Context...)
		}
		phases = append(phases, result)
		all = append(all, pieces...)
	}
	total := 0
	for _, p := range all {
		total += p.EstimatedTokens
	}
	return ComposedProfile{
		Situation: in.Situation, Runtime: in.Runtime, ProfileID: profile.ID, Phases: phases,
		Pieces: all, TotalEstimatedTokens: total, Budget: budgetReport(all, in.BudgetTokens),
	}, nil
}
