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
	KindMemory      ModuleKind = "memory"
)

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
	Latest(slug string) (string, bool)
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

// followLatest reports whether a ref version defers to the catalog's latest.
func followLatest(version string) bool {
	return version == "" || version == "latest"
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
		if followLatest(op.Version) {
			return fmt.Errorf("pin %q: version must be concrete", op.Slug)
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
		if followLatest(version) {
			latest, ok := catalog.Latest(slug)
			if !ok {
				return nil, fmt.Errorf("module %s@latest not found in catalog", slug)
			}
			version = latest
		}
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
	case KindMemory:
		return 4
	default:
		return 5
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
