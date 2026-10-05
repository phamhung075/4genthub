package contextpacks

// EstimateTokensFromBytes is the cheap stable token estimate shared by store and assembly
// projections: ceil(bytes/4).
func EstimateTokensFromBytes(bytes int) int {
	return (bytes + 3) / 4
}

// EstimateTokensOf estimates the tokens of a string from its UTF-8 BYTE length (the TypeScript
// projection is Buffer.byteLength(text, "utf-8") / 4), so an estimate is always derived from the
// real bytes and never stored.
func EstimateTokensOf(text string) int {
	return EstimateTokensFromBytes(len(text))
}

// Situation selects which atoms a profile composes, per the locked algebra.
type Situation string

// Runtime is an atom's applicability target; "any" serves every runtime.
type Runtime string

// Priority orders what drops first when a token budget binds.
type Priority string

// SourceKind labels where an assembled piece came from.
type SourceKind string

const (
	SituationFresh          Situation = "fresh"
	SituationHandover       Situation = "handover"
	SituationPostCompaction Situation = "post-compaction"

	RuntimeClaude Runtime = "claude"
	RuntimeCodex  Runtime = "codex"
	RuntimeAny    Runtime = "any"

	PriorityCore        Priority = "core"
	PriorityRecommended Priority = "recommended"
	PriorityOptional    Priority = "optional"

	SourceLibrary SourceKind = "library"
	SourceProject SourceKind = "project"
	SourceSeat    SourceKind = "seat"
	SourceMission SourceKind = "mission"
)

// dropOrder is the drop-first ranking: optional, then recommended, then core.
var dropOrder = map[Priority]int{PriorityOptional: 0, PriorityRecommended: 1, PriorityCore: 2}

// Atom is an install atom: an ADDRESS plus composition metadata, never a new file. Token counts
// are derived at compose time and never stored here.
type Atom struct {
	// ID is the stable slug — the join key for order/requires.
	ID string
	// Address is `file` or `file#H2-slug/H3-slug`.
	Address string
	// Situations is the composition selector; never empty.
	Situations []Situation
	// Runtime is never assumed identical across runtimes; RuntimeAny serves both.
	Runtime Runtime
	// Order is the position within the base walk — absorption depends on sequence.
	Order int
	// Requires must close: a required atom joins the profile even when untagged.
	Requires []string
	// Priority is what drops FIRST when a token budget binds.
	Priority Priority
	// ProfileOnly atoms do not join the legacy situation profile.
	ProfileOnly bool
}

// ProfilePhase is one explicit delivery phase: an atom phase selects bytes the pack already
// owns; a context phase inserts configured project/mission/seat/slice sources.
type ProfilePhase struct {
	ID      string
	Atoms   []string
	Context []string
}

// Profile is a named, inspectable selection and sequence over one pack's atom graph.
type Profile struct {
	ID         string
	Situations []Situation
	Runtimes   []Runtime
	Phases     []ProfilePhase
}

// ProfileComposeError is the loud compose failure: a compose stops rather than thinning the walk.
type ProfileComposeError struct{ Msg string }

func (e *ProfileComposeError) Error() string { return e.Msg }

func selectionTags(situation Situation) []Situation {
	switch situation {
	case SituationFresh:
		return []Situation{SituationFresh}
	case SituationHandover:
		return []Situation{SituationFresh, SituationHandover}
	case SituationPostCompaction:
		return []Situation{SituationPostCompaction, SituationHandover}
	}
	return nil
}

func containsSituation(haystack []Situation, needle Situation) bool {
	for _, s := range haystack {
		if s == needle {
			return true
		}
	}
	return false
}

func containsRuntime(haystack []Runtime, needle Runtime) bool {
	for _, r := range haystack {
		if r == needle {
			return true
		}
	}
	return false
}
