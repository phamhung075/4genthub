// Package resolver turns a company-workplace seat definition and its
// overlays into a deterministic, fully pinned snapshot.
package resolver

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"hash"
	"sort"
)

type ModuleKind string

const (
	KindInstruction ModuleKind = "instruction"
	KindDocument    ModuleKind = "document"
	KindSkill       ModuleKind = "skill"
	KindTool        ModuleKind = "tool"
	// KindMCP is one whole MCP server to mount for the seat; KindTool only narrows
	// permissions within a server that a KindMCP block mounted.
	KindMCP    ModuleKind = "mcp"
	KindMemory ModuleKind = "memory"
	// KindPolicy is the seat's limits as data: the role, the runtime settings those limits need, and
	// the rules the runtime enforces. It is its own kind rather than a richer `tool` because `tool`
	// already means a Claude settings fragment, and one kind carrying two parse rules is the
	// duplicate-rule shape this codebase keeps removing.
	KindPolicy ModuleKind = "policy"
)

// ValidKind reports whether kind is one of the module kinds.
func ValidKind(kind ModuleKind) bool {
	switch kind {
	case KindInstruction, KindDocument, KindSkill, KindTool, KindMCP, KindMemory, KindPolicy:
		return true
	}
	return false
}

type ModuleVersion struct {
	Slug    string
	Version string
	Kind    ModuleKind
	Content string
}

type ModuleRef struct {
	Slug    string
	Version string
}

type Catalog interface {
	Get(slug, version string) (ModuleVersion, bool)
}

type SeatTypeVersion struct {
	Slug    string
	Version string
	Runtime string
	Modules []ModuleRef
}

type OpKind string

const (
	OpAdd      OpKind = "add"
	OpRemove   OpKind = "remove"
	OpOverride OpKind = "override"
	OpPin      OpKind = "pin"
)

type Op struct {
	Kind    OpKind
	Slug    string
	Version string
	Content string
}

type Overlay struct {
	Scope string
	Ops   []Op
}

type ResolvedModule struct {
	Slug       string
	Version    string
	Kind       ModuleKind
	Content    string
	Overridden bool
}

type ResolvedSeat struct {
	SeatType        string
	SeatTypeVersion string
	Runtime         string
	Modules         []ResolvedModule
	Hash            string
}

const (
	scopeCompany = "company"
	scopeRoom    = "room"
	scopeSeat    = "seat"
)

var scopeOrder = []string{scopeCompany, scopeRoom, scopeSeat}

// requireConcrete rejects the empty version and the "latest" alias: a resolved seat only moves when
// a new resolved version is published, so no ref may defer to the catalog's newest module.
func requireConcrete(slug, version string) error {
	if version == "" || version == "latest" {
		return fmt.Errorf("module %q: version must be concrete, got %q", slug, version)
	}
	return nil
}

type moduleState struct {
	version    string
	content    string
	overridden bool
}

func Resolve(catalog Catalog, seatType SeatTypeVersion, overlays []Overlay) (ResolvedSeat, error) {
	byScope := make(map[string]Overlay, len(overlays))
	for _, ov := range overlays {
		switch ov.Scope {
		case scopeCompany, scopeRoom, scopeSeat:
		default:
			return ResolvedSeat{}, fmt.Errorf("invalid overlay scope %q", ov.Scope)
		}
		if _, ok := byScope[ov.Scope]; ok {
			return ResolvedSeat{}, fmt.Errorf("duplicate overlay scope %q", ov.Scope)
		}
		byScope[ov.Scope] = ov
	}

	state := make(map[string]*moduleState, len(seatType.Modules))
	for _, ref := range seatType.Modules {
		if err := requireConcrete(ref.Slug, ref.Version); err != nil {
			return ResolvedSeat{}, err
		}
		state[ref.Slug] = &moduleState{version: ref.Version}
	}

	for _, scope := range scopeOrder {
		ov, ok := byScope[scope]
		if !ok {
			continue
		}
		for _, op := range ov.Ops {
			if err := applyOp(state, op); err != nil {
				return ResolvedSeat{}, err
			}
		}
	}

	modules, err := resolveModules(catalog, state)
	if err != nil {
		return ResolvedSeat{}, err
	}
	sortModules(modules)

	seat := ResolvedSeat{
		SeatType:        seatType.Slug,
		SeatTypeVersion: seatType.Version,
		Runtime:         seatType.Runtime,
		Modules:         modules,
	}
	seat.Hash = computeHash(seat.SeatType, seat.SeatTypeVersion, seat.Runtime, modules)
	return seat, nil
}

func applyOp(state map[string]*moduleState, op Op) error {
	switch op.Kind {
	case OpAdd:
		if _, ok := state[op.Slug]; ok {
			return fmt.Errorf("add %q: module already present", op.Slug)
		}
		if err := requireConcrete(op.Slug, op.Version); err != nil {
			return err
		}
		state[op.Slug] = &moduleState{version: op.Version}
	case OpRemove:
		if _, ok := state[op.Slug]; !ok {
			return fmt.Errorf("remove %q: module not present", op.Slug)
		}
		delete(state, op.Slug)
	case OpOverride:
		st, ok := state[op.Slug]
		if !ok {
			return fmt.Errorf("override %q: module not present", op.Slug)
		}
		if op.Content == "" {
			return fmt.Errorf("override %q: content is empty", op.Slug)
		}
		st.content = op.Content
		st.overridden = true
	case OpPin:
		st, ok := state[op.Slug]
		if !ok {
			return fmt.Errorf("pin %q: module not present", op.Slug)
		}
		if err := requireConcrete(op.Slug, op.Version); err != nil {
			return err
		}
		st.version = op.Version
	default:
		return fmt.Errorf("unknown op kind %q", op.Kind)
	}
	return nil
}

func resolveModules(catalog Catalog, state map[string]*moduleState) ([]ResolvedModule, error) {
	modules := make([]ResolvedModule, 0, len(state))
	for slug, st := range state {
		version := st.version
		mv, ok := catalog.Get(slug, version)
		if !ok {
			return nil, fmt.Errorf("module %s@%s not found in catalog", slug, version)
		}
		content := mv.Content
		if st.overridden {
			content = st.content
		}
		modules = append(modules, ResolvedModule{
			Slug:       slug,
			Version:    version,
			Kind:       mv.Kind,
			Content:    content,
			Overridden: st.overridden,
		})
	}
	return modules, nil
}

func sortModules(modules []ResolvedModule) {
	sort.Slice(modules, func(i, j int) bool {
		ri, rj := kindRank(modules[i].Kind), kindRank(modules[j].Kind)
		if ri != rj {
			return ri < rj
		}
		return modules[i].Slug < modules[j].Slug
	})
}

func kindRank(kind ModuleKind) int {
	switch kind {
	case KindInstruction:
		return 0
	case KindDocument:
		return 1
	case KindSkill:
		return 2
	case KindTool:
		return 3
	// mcp sits between tool and memory: both tool and mcp are runtime configuration, and
	// memory stays the last guidance section.
	case KindMCP:
		return 4
	// policy is runtime configuration like tool and mcp, and it sorts after them so the fold sees
	// every rule before anything reads the merged limits.
	case KindPolicy:
		return 5
	case KindMemory:
		return 6
	default:
		return 6
	}
}

// computeHash encodes every field with its length so distinct inputs cannot
// collide by concatenation.
func computeHash(seatType, seatTypeVersion, runtime string, modules []ResolvedModule) string {
	h := sha256.New()
	writeField(h, seatType)
	writeField(h, seatTypeVersion)
	writeField(h, runtime)
	writeUint(h, uint64(len(modules)))
	for _, m := range modules {
		writeField(h, m.Slug)
		writeField(h, m.Version)
		writeField(h, string(m.Kind))
		writeField(h, m.Content)
		if m.Overridden {
			writeUint(h, 1)
		} else {
			writeUint(h, 0)
		}
	}
	return hex.EncodeToString(h.Sum(nil))
}

func writeField(h hash.Hash, s string) {
	writeUint(h, uint64(len(s)))
	h.Write([]byte(s))
}

func writeUint(h hash.Hash, v uint64) {
	var n [8]byte
	binary.BigEndian.PutUint64(n[:], v)
	h.Write(n[:])
}
