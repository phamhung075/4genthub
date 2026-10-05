package resolver

import (
	"reflect"
	"strings"
	"testing"
)

type memCatalog struct {
	versions map[string]ModuleVersion
}

func (c *memCatalog) Get(slug, version string) (ModuleVersion, bool) {
	mv, ok := c.versions[slug+"@"+version]
	return mv, ok
}

func testCatalog() *memCatalog {
	return &memCatalog{
		versions: map[string]ModuleVersion{
			"instr.base@1.0.0":  {Slug: "instr.base", Version: "1.0.0", Kind: KindInstruction, Content: "base instruction"},
			"instr.base@1.1.0":  {Slug: "instr.base", Version: "1.1.0", Kind: KindInstruction, Content: "newer instruction"},
			"doc.guide@2.0.0":   {Slug: "doc.guide", Version: "2.0.0", Kind: KindDocument, Content: "guide doc"},
			"skill.alpha@1.0.0": {Slug: "skill.alpha", Version: "1.0.0", Kind: KindSkill, Content: "alpha skill"},
			"skill.alpha@1.1.0": {Slug: "skill.alpha", Version: "1.1.0", Kind: KindSkill, Content: "alpha skill v1.1"},
			"tool.beta@3.0.0":   {Slug: "tool.beta", Version: "3.0.0", Kind: KindTool, Content: "beta tool"},
			"mem.gamma@1.0.0":   {Slug: "mem.gamma", Version: "1.0.0", Kind: KindMemory, Content: "gamma memory"},
			"tool.new@1.0.0":    {Slug: "tool.new", Version: "1.0.0", Kind: KindTool, Content: "new tool"},
			"tool.new@2.0.0":    {Slug: "tool.new", Version: "2.0.0", Kind: KindTool, Content: "new tool v2"},
		},
	}
}

func baseSeatType() SeatTypeVersion {
	return SeatTypeVersion{
		Slug:    "seat.standard",
		Version: "1.0.0",
		Runtime: "go1.23",
		Modules: []ModuleRef{
			{Slug: "mem.gamma", Version: "1.0.0"},
			{Slug: "skill.alpha", Version: "1.1.0"},
			{Slug: "tool.beta", Version: "3.0.0"},
			{Slug: "instr.base", Version: "1.0.0"},
			{Slug: "doc.guide", Version: "2.0.0"},
		},
	}
}

func moduleBySlug(t *testing.T, seat ResolvedSeat, slug string) ResolvedModule {
	t.Helper()
	for _, m := range seat.Modules {
		if m.Slug == slug {
			return m
		}
	}
	t.Fatalf("module %q not found in resolved seat", slug)
	return ResolvedModule{}
}

func slugs(modules []ResolvedModule) []string {
	out := make([]string, len(modules))
	for i, m := range modules {
		out[i] = m.Slug
	}
	return out
}

func TestResolveBase(t *testing.T) {
	seat, err := Resolve(testCatalog(), baseSeatType(), nil)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if seat.SeatType != "seat.standard" || seat.SeatTypeVersion != "1.0.0" || seat.Runtime != "go1.23" {
		t.Fatalf("unexpected seat identity: %+v", seat)
	}
	want := []string{"instr.base", "doc.guide", "skill.alpha", "tool.beta", "mem.gamma"}
	if got := slugs(seat.Modules); !reflect.DeepEqual(got, want) {
		t.Fatalf("module order = %v, want %v", got, want)
	}
	doc := moduleBySlug(t, seat, "doc.guide")
	if doc.Kind != KindDocument || doc.Content != "guide doc" || doc.Overridden {
		t.Fatalf("unexpected doc.guide: %+v", doc)
	}
	if len(seat.Hash) != 64 || strings.ToLower(seat.Hash) != seat.Hash {
		t.Fatalf("hash %q is not lowercase hex", seat.Hash)
	}
}

func TestResolveRejectsNonConcreteVersions(t *testing.T) {
	for _, version := range []string{"", "latest"} {
		t.Run("seat type ref "+version, func(t *testing.T) {
			seatType := baseSeatType()
			seatType.Modules[1].Version = version
			if _, err := Resolve(testCatalog(), seatType, nil); err == nil || !strings.Contains(err.Error(), "concrete") {
				t.Fatalf("error = %v, want a concrete-version error", err)
			}
		})
		t.Run("overlay add "+version, func(t *testing.T) {
			overlay := Overlay{Scope: scopeCompany, Ops: []Op{{Kind: OpAdd, Slug: "tool.new", Version: version}}}
			if _, err := Resolve(testCatalog(), baseSeatType(), []Overlay{overlay}); err == nil || !strings.Contains(err.Error(), "concrete") {
				t.Fatalf("error = %v, want a concrete-version error", err)
			}
		})
	}
}

func TestResolveIgnoresNewlyPublishedModuleVersions(t *testing.T) {
	overlay := Overlay{Scope: scopeCompany, Ops: []Op{{Kind: OpAdd, Slug: "tool.new", Version: "1.0.0"}}}
	before, err := Resolve(testCatalog(), baseSeatType(), []Overlay{overlay})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	published := testCatalog()
	published.versions["tool.new@3.0.0"] = ModuleVersion{Slug: "tool.new", Version: "3.0.0", Kind: KindTool, Content: "new tool v3"}
	after, err := Resolve(published, baseSeatType(), []Overlay{overlay})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if before.Hash != after.Hash {
		t.Fatal("publishing a module version changed a seat whose refs are all concrete")
	}
}

func TestResolveAdd(t *testing.T) {
	overlays := []Overlay{{
		Scope: scopeCompany,
		Ops:   []Op{{Kind: OpAdd, Slug: "tool.new", Version: "2.0.0"}},
	}}
	seat, err := Resolve(testCatalog(), baseSeatType(), overlays)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	added := moduleBySlug(t, seat, "tool.new")
	if added.Version != "2.0.0" || added.Kind != KindTool || added.Content != "new tool v2" || added.Overridden {
		t.Fatalf("unexpected added module: %+v", added)
	}
}

func TestResolveAddDuplicateErrors(t *testing.T) {
	cases := map[string][]Overlay{
		"existing base module": {{
			Scope: scopeCompany,
			Ops:   []Op{{Kind: OpAdd, Slug: "tool.beta", Version: "3.0.0"}},
		}},
		"added twice in one scope": {{
			Scope: scopeCompany,
			Ops: []Op{
				{Kind: OpAdd, Slug: "tool.new", Version: "1.0.0"},
				{Kind: OpAdd, Slug: "tool.new", Version: "2.0.0"},
			},
		}},
	}
	for name, overlays := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := Resolve(testCatalog(), baseSeatType(), overlays); err == nil {
				t.Fatal("expected add duplicate error, got nil")
			}
		})
	}
}

func TestResolveRemove(t *testing.T) {
	overlays := []Overlay{{
		Scope: scopeRoom,
		Ops:   []Op{{Kind: OpRemove, Slug: "doc.guide"}},
	}}
	seat, err := Resolve(testCatalog(), baseSeatType(), overlays)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	for _, m := range seat.Modules {
		if m.Slug == "doc.guide" {
			t.Fatal("doc.guide should have been removed")
		}
	}
	if len(seat.Modules) != 4 {
		t.Fatalf("module count = %d, want 4", len(seat.Modules))
	}
}

func TestResolveRemoveAbsentErrors(t *testing.T) {
	overlays := []Overlay{{
		Scope: scopeSeat,
		Ops:   []Op{{Kind: OpRemove, Slug: "tool.new"}},
	}}
	if _, err := Resolve(testCatalog(), baseSeatType(), overlays); err == nil {
		t.Fatal("expected remove absent error, got nil")
	}
}

func TestResolveOverride(t *testing.T) {
	base, err := Resolve(testCatalog(), baseSeatType(), nil)
	if err != nil {
		t.Fatalf("base Resolve: %v", err)
	}
	overlays := []Overlay{{
		Scope: scopeCompany,
		Ops:   []Op{{Kind: OpOverride, Slug: "doc.guide", Content: "company override"}},
	}}
	seat, err := Resolve(testCatalog(), baseSeatType(), overlays)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	doc := moduleBySlug(t, seat, "doc.guide")
	if !doc.Overridden || doc.Content != "company override" || doc.Version != "2.0.0" || doc.Kind != KindDocument {
		t.Fatalf("unexpected overridden module: %+v", doc)
	}
	if seat.Hash == base.Hash {
		t.Fatal("override did not change the hash")
	}
}

func TestResolveOverrideErrors(t *testing.T) {
	cases := map[string]Overlay{
		"absent":        {Scope: scopeCompany, Ops: []Op{{Kind: OpOverride, Slug: "tool.new", Content: "x"}}},
		"empty content": {Scope: scopeCompany, Ops: []Op{{Kind: OpOverride, Slug: "doc.guide", Content: ""}}},
	}
	for name, overlay := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := Resolve(testCatalog(), baseSeatType(), []Overlay{overlay}); err == nil {
				t.Fatal("expected override error, got nil")
			}
		})
	}
}

func TestResolvePin(t *testing.T) {
	overlays := []Overlay{{
		Scope: scopeSeat,
		Ops:   []Op{{Kind: OpPin, Slug: "skill.alpha", Version: "1.0.0"}},
	}}
	seat, err := Resolve(testCatalog(), baseSeatType(), overlays)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	alpha := moduleBySlug(t, seat, "skill.alpha")
	if alpha.Version != "1.0.0" || alpha.Content != "alpha skill" {
		t.Fatalf("unexpected pinned module: %+v", alpha)
	}
}

func TestResolvePinErrors(t *testing.T) {
	cases := map[string]Op{
		"absent":          {Kind: OpPin, Slug: "tool.new", Version: "1.0.0"},
		"empty version":   {Kind: OpPin, Slug: "skill.alpha", Version: ""},
		"latest version":  {Kind: OpPin, Slug: "skill.alpha", Version: "latest"},
		"unknown version": {Kind: OpPin, Slug: "skill.alpha", Version: "9.9.9"},
	}
	for name, op := range cases {
		t.Run(name, func(t *testing.T) {
			overlay := Overlay{Scope: scopeSeat, Ops: []Op{op}}
			if _, err := Resolve(testCatalog(), baseSeatType(), []Overlay{overlay}); err == nil {
				t.Fatal("expected pin error, got nil")
			}
		})
	}
}

func TestResolveScopeOrderIndependentOfInputOrder(t *testing.T) {
	company := Overlay{Scope: scopeCompany, Ops: []Op{{Kind: OpOverride, Slug: "doc.guide", Content: "company"}}}
	room := Overlay{Scope: scopeRoom, Ops: []Op{{Kind: OpOverride, Slug: "doc.guide", Content: "room"}}}
	seatOverlay := Overlay{Scope: scopeSeat, Ops: []Op{{Kind: OpOverride, Slug: "doc.guide", Content: "seat"}}}

	forward, err := Resolve(testCatalog(), baseSeatType(), []Overlay{company, room, seatOverlay})
	if err != nil {
		t.Fatalf("forward Resolve: %v", err)
	}
	reverse, err := Resolve(testCatalog(), baseSeatType(), []Overlay{seatOverlay, room, company})
	if err != nil {
		t.Fatalf("reverse Resolve: %v", err)
	}
	if got := moduleBySlug(t, forward, "doc.guide").Content; got != "seat" {
		t.Fatalf("forward content = %q, want seat (seat scope must win)", got)
	}
	if forward.Hash != reverse.Hash {
		t.Fatalf("hash depends on overlay order: %s != %s", forward.Hash, reverse.Hash)
	}
}

func TestResolveWithinScopeOpsApplyInSliceOrder(t *testing.T) {
	overlay := Overlay{Scope: scopeCompany, Ops: []Op{
		{Kind: OpOverride, Slug: "doc.guide", Content: "first"},
		{Kind: OpOverride, Slug: "doc.guide", Content: "second"},
	}}
	seat, err := Resolve(testCatalog(), baseSeatType(), []Overlay{overlay})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if got := moduleBySlug(t, seat, "doc.guide").Content; got != "second" {
		t.Fatalf("content = %q, want second", got)
	}
}

func TestResolveDuplicateScopeErrors(t *testing.T) {
	overlays := []Overlay{
		{Scope: scopeCompany, Ops: []Op{{Kind: OpRemove, Slug: "doc.guide"}}},
		{Scope: scopeCompany, Ops: []Op{{Kind: OpRemove, Slug: "mem.gamma"}}},
	}
	if _, err := Resolve(testCatalog(), baseSeatType(), overlays); err == nil || !strings.Contains(err.Error(), "duplicate overlay scope") {
		t.Fatalf("expected duplicate scope error, got %v", err)
	}
}

func TestResolveInvalidScopeErrors(t *testing.T) {
	overlays := []Overlay{{Scope: "region", Ops: nil}}
	if _, err := Resolve(testCatalog(), baseSeatType(), overlays); err == nil {
		t.Fatal("expected invalid scope error, got nil")
	}
}

func TestResolveUnknownOpErrors(t *testing.T) {
	overlays := []Overlay{{Scope: scopeCompany, Ops: []Op{{Kind: "replace", Slug: "doc.guide"}}}}
	if _, err := Resolve(testCatalog(), baseSeatType(), overlays); err == nil {
		t.Fatal("expected unknown op error, got nil")
	}
}

func TestResolveMissingCatalogModuleErrors(t *testing.T) {
	cases := map[string]struct {
		seatType SeatTypeVersion
		overlays []Overlay
		want     string
	}{
		"base concrete": {
			seatType: SeatTypeVersion{Slug: "s", Version: "1", Modules: []ModuleRef{{Slug: "ghost", Version: "1.0.0"}}},
			want:     "ghost@1.0.0",
		},
		"added": {
			seatType: SeatTypeVersion{Slug: "s", Version: "1"},
			overlays: []Overlay{{Scope: scopeCompany, Ops: []Op{{Kind: OpAdd, Slug: "ghost", Version: "2.0.0"}}}},
			want:     "ghost@2.0.0",
		},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			_, err := Resolve(testCatalog(), tc.seatType, tc.overlays)
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("error = %v, want it to name %s", err, tc.want)
			}
		})
	}
}

func TestResolveHashDeterministic(t *testing.T) {
	first, err := Resolve(testCatalog(), baseSeatType(), nil)
	if err != nil {
		t.Fatalf("first Resolve: %v", err)
	}
	second, err := Resolve(testCatalog(), baseSeatType(), nil)
	if err != nil {
		t.Fatalf("second Resolve: %v", err)
	}
	if first.Hash != second.Hash {
		t.Fatalf("hash differs across identical calls: %s != %s", first.Hash, second.Hash)
	}

	shuffledType := baseSeatType()
	for i, j := 0, len(shuffledType.Modules)-1; i < j; i, j = i+1, j-1 {
		shuffledType.Modules[i], shuffledType.Modules[j] = shuffledType.Modules[j], shuffledType.Modules[i]
	}
	shuffled, err := Resolve(testCatalog(), shuffledType, nil)
	if err != nil {
		t.Fatalf("shuffled Resolve: %v", err)
	}
	if first.Hash != shuffled.Hash {
		t.Fatalf("hash differs across shuffled inputs: %s != %s", first.Hash, shuffled.Hash)
	}
}

func TestResolveHashChangesWithContent(t *testing.T) {
	base, err := Resolve(testCatalog(), baseSeatType(), nil)
	if err != nil {
		t.Fatalf("base Resolve: %v", err)
	}
	changed := baseSeatType()
	changed.Modules = append([]ModuleRef{{Slug: "tool.new", Version: "1.0.0"}}, changed.Modules...)
	withModule, err := Resolve(testCatalog(), changed, nil)
	if err != nil {
		t.Fatalf("withModule Resolve: %v", err)
	}
	if base.Hash == withModule.Hash {
		t.Fatal("adding a module did not change the hash")
	}
}

func TestResolveSortOrder(t *testing.T) {
	seatType := SeatTypeVersion{
		Slug:    "seat.sort",
		Version: "1.0.0",
		Modules: []ModuleRef{
			{Slug: "tool.zeta", Version: "1.0.0"},
			{Slug: "memory.zeta", Version: "1.0.0"},
			{Slug: "tool.alpha", Version: "1.0.0"},
			{Slug: "memory.alpha", Version: "1.0.0"},
		},
	}
	catalog := &memCatalog{
		versions: map[string]ModuleVersion{
			"tool.zeta@1.0.0":    {Slug: "tool.zeta", Version: "1.0.0", Kind: KindTool, Content: "z"},
			"memory.zeta@1.0.0":  {Slug: "memory.zeta", Version: "1.0.0", Kind: KindMemory, Content: "z"},
			"tool.alpha@1.0.0":   {Slug: "tool.alpha", Version: "1.0.0", Kind: KindTool, Content: "a"},
			"memory.alpha@1.0.0": {Slug: "memory.alpha", Version: "1.0.0", Kind: KindMemory, Content: "a"},
		},
	}
	seat, err := Resolve(catalog, seatType, nil)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	want := []string{"tool.alpha", "tool.zeta", "memory.alpha", "memory.zeta"}
	if got := slugs(seat.Modules); !reflect.DeepEqual(got, want) {
		t.Fatalf("module order = %v, want %v", got, want)
	}
}
