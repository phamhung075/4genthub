package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seedmap"
)

// fakeCatalog is an in-memory ModuleRepository keyed by slug@version.
type fakeCatalog struct {
	versions map[string]string
}

func newFakeCatalog() *fakeCatalog { return &fakeCatalog{versions: map[string]string{}} }

func catalogKey(slug, version string) string { return slug + "@" + version }

func (f *fakeCatalog) put(slug, version string) {
	f.versions[catalogKey(slug, version)] = "content"
}

func (f *fakeCatalog) SaveModule(_ context.Context, _ string, slug string, kind resolver.ModuleKind) (*repositories.Module, error) {
	return &repositories.Module{Slug: slug, Kind: kind}, nil
}

func (f *fakeCatalog) AddVersion(_ context.Context, _ string, slug, version, content string) (*repositories.ModuleVersion, error) {
	f.versions[catalogKey(slug, version)] = content
	return &repositories.ModuleVersion{Slug: slug, Version: version, Content: content}, nil
}

func (f *fakeCatalog) GetVersion(_ context.Context, _ string, slug, version string) (*repositories.ModuleVersion, error) {
	content, ok := f.versions[catalogKey(slug, version)]
	if !ok {
		return nil, nil
	}
	return &repositories.ModuleVersion{Slug: slug, Version: version, Content: content}, nil
}

func (f *fakeCatalog) ListLatest(context.Context, string) ([]repositories.ModuleVersion, error) {
	return nil, nil
}

// fakeSeatTypes records what the seeder wrote, so a refusal can be shown to write no type.
type fakeSeatTypes struct {
	saved    []string
	versions []repositories.SeatTypeVersion
}

func newFakeSeatTypes() *fakeSeatTypes { return &fakeSeatTypes{} }

func (f *fakeSeatTypes) Save(_ context.Context, _ string, seatType repositories.SeatType) (*repositories.SeatType, error) {
	f.saved = append(f.saved, seatType.Slug)
	return &seatType, nil
}

func (f *fakeSeatTypes) GetByID(context.Context, string, string) (*repositories.SeatType, error) {
	return nil, nil
}

func (f *fakeSeatTypes) List(context.Context, string) ([]repositories.SeatType, error) {
	return nil, nil
}

func (f *fakeSeatTypes) AddVersion(_ context.Context, _ string, slug, version, runtime string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error) {
	created := repositories.SeatTypeVersion{Slug: slug, Version: version, DefaultRuntime: runtime, ModuleRefs: refs}
	f.versions = append(f.versions, created)
	return &created, nil
}

func (f *fakeSeatTypes) GetVersion(context.Context, string, string, string) (*repositories.SeatTypeVersion, error) {
	return nil, nil
}

func (f *fakeSeatTypes) LatestVersion(context.Context, string, string) (*repositories.SeatTypeVersion, error) {
	return nil, nil
}

// authoredSeed is a seed with one authored module whose slug is <type>-role, plus any extra refs.
func authoredSeed(extra ...resolver.ModuleRef) seedmap.Seed {
	role := seedmap.SeedModule{Slug: "developer-role", Kind: resolver.KindInstruction, Version: "1.3.0", Content: "role"}
	refs := []resolver.ModuleRef{{Slug: role.Slug, Version: role.Version}}
	refs = append(refs, extra...)
	return seedmap.Seed{
		SeatTypeSlug: "developer", SeatTypeName: "Developer", Description: "d",
		DefaultRuntime: "claude-code", Version: "1.3.0",
		Modules: []seedmap.SeedModule{role}, ModuleRefs: refs,
	}
}

// A curated ref the catalog does not hold (the ExtraRefs case) refuses the seed, names the ref and
// the type, and writes no seat type version.
func TestSeedSeatTypesRefusesMissingRef(t *testing.T) {
	catalog, seatTypes := newFakeCatalog(), newFakeSeatTypes()
	seed := authoredSeed(resolver.ModuleRef{Slug: "queue-handoff", Version: "1.0.0"})

	err := SeedSeatTypes(context.Background(), "u", []seedmap.Seed{seed}, catalog, seatTypes)
	if err == nil {
		t.Fatal("a seed whose ref is not in the catalog succeeded")
	}
	if !strings.Contains(err.Error(), "queue-handoff@1.0.0") || !strings.Contains(err.Error(), "developer") {
		t.Errorf("error %q must name the missing ref and the seat type", err)
	}
	if len(seatTypes.versions) != 0 {
		t.Errorf("a refused seed wrote a seat type version: %+v", seatTypes.versions)
	}
	if len(seatTypes.saved) != 0 {
		t.Errorf("a refused seed wrote a seat type: %+v", seatTypes.saved)
	}
}

// After the catalog is published (the publish-skills step), the same seed succeeds.
func TestSeedSeatTypesSucceedsWhenTheCatalogHasTheRefs(t *testing.T) {
	catalog, seatTypes := newFakeCatalog(), newFakeSeatTypes()
	catalog.put("queue-handoff", "1.0.0")
	catalog.put("mission-slice-sop", "1.0.0")
	seed := authoredSeed(
		resolver.ModuleRef{Slug: "queue-handoff", Version: "1.0.0"},
		resolver.ModuleRef{Slug: "mission-slice-sop", Version: "1.0.0"},
	)

	if err := SeedSeatTypes(context.Background(), "u", []seedmap.Seed{seed}, catalog, seatTypes); err != nil {
		t.Fatalf("seed with a published catalog: %v", err)
	}
	if len(seatTypes.versions) != 1 {
		t.Fatalf("versions = %+v, want 1", seatTypes.versions)
	}
	if got := len(seatTypes.versions[0].ModuleRefs); got != 3 {
		t.Errorf("refs = %d, want 3 (authored + the two curated)", got)
	}
}

// Regression: a seed whose refs are exactly its own authored modules still seeds with an empty
// catalog, because the seeder stores those modules before it checks.
func TestSeedSeatTypesAcceptsItsOwnAuthoredModules(t *testing.T) {
	catalog, seatTypes := newFakeCatalog(), newFakeSeatTypes()
	if err := SeedSeatTypes(context.Background(), "u", []seedmap.Seed{authoredSeed()}, catalog, seatTypes); err != nil {
		t.Fatalf("seed of self-authored modules: %v", err)
	}
	if len(seatTypes.versions) != 1 {
		t.Errorf("versions = %+v, want 1", seatTypes.versions)
	}
}
