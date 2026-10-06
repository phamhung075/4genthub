package services

import (
	"context"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/seedmap"
)

// SeedSeatTypes stores each seed's modules and seat type version for one tenant. It is
// idempotent: versions are immutable and re-adding identical content is a no-op, while
// different content under the same version fails instead of being overwritten.
func SeedSeatTypes(ctx context.Context, userID string, seeds []seedmap.Seed, modules repositories.ModuleRepository, seatTypes repositories.SeatTypeRepository) error {
	for _, seed := range seeds {
		for _, m := range seed.Modules {
			if _, err := modules.SaveModule(ctx, userID, m.Slug, m.Kind); err != nil {
				return fmt.Errorf("seed %s: module %s: %w", seed.SeatTypeSlug, m.Slug, err)
			}
			if _, err := modules.AddVersion(ctx, userID, m.Slug, m.Version, m.Content); err != nil {
				return fmt.Errorf("seed %s: module %s@%s: %w", seed.SeatTypeSlug, m.Slug, m.Version, err)
			}
		}
		// Verify every ref this version carries BEFORE writing it, the same way the HTTP publish
		// path does (SeatAdminService.CreateSeatTypeVersion): a ref that is not in the catalog is
		// refused by name rather than written, because a seat type whose refs do not resolve fails
		// every resolve downstream — a 404 that surfaces on a different route from the seed that
		// caused it. The loop above stored this seed's own modules, so this catches exactly the
		// curated refs seedmap appends as ExtraRefs, which nothing here authors: publish them
		// (scripts/openrig_team_setup.py publish-skills) before seeding the seat types.
		for _, ref := range seed.ModuleRefs {
			found, err := modules.GetVersion(ctx, userID, ref.Slug, ref.Version)
			if err != nil {
				return fmt.Errorf("seed %s: verify ref %s@%s: %w", seed.SeatTypeSlug, ref.Slug, ref.Version, err)
			}
			if found == nil {
				return fmt.Errorf("seed %s: module ref %s@%s does not exist — publish the catalog before seeding the seat types",
					seed.SeatTypeSlug, ref.Slug, ref.Version)
			}
		}
		if _, err := seatTypes.Save(ctx, userID, repositories.SeatType{
			Slug: seed.SeatTypeSlug, Name: seed.SeatTypeName, Description: seed.Description,
		}); err != nil {
			return fmt.Errorf("seed %s: %w", seed.SeatTypeSlug, err)
		}
		if _, err := seatTypes.AddVersion(ctx, userID, seed.SeatTypeSlug, seed.Version, seed.DefaultRuntime, seed.ModuleRefs); err != nil {
			return fmt.Errorf("seed %s@%s: %w", seed.SeatTypeSlug, seed.Version, err)
		}
	}
	return nil
}
