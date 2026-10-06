package services

import (
	"errors"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/modulecontent"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/secretscan"
)

// MaxModuleContentBytes is the size bound a module version's content shares with every writer.
const MaxModuleContentBytes = 65536

// ErrModuleSecretDetected is the one refusal a caller maps to its own surface: the publish route
// answers 422 for it while every other refusal is a 400 there. Everything else is the plain error.
var ErrModuleSecretDetected = errors.New("secret detected in content")

// ValidateModuleContent is THE gate on a module version's content, and it is ONE function because
// there are TWO writers of module versions and only one of them was checking.
//
// The measurement that produced it: `modulecontent` appeared in non-test code at exactly two places,
// both in the publish route, so the gate was ROUTE-ONLY - while `SeedSeatTypes` (the seat seeder)
// wrote through `ModuleRepository.AddVersion` directly. A seeded version could therefore be stored
// with a content the route would have refused with a 400, and the failure surfaced at RENDER time,
// on a seat and on a different route from the seed that caused it - the same shape as the two
// writers of a seat's config.yml, and as the create path that truncated what the entity refuses.
//
// The rule itself is not restated here: the last check is `modulecontent.Validate`, which parses with
// the very renderer that will consume the content. This function adds the checks a caller should not
// be able to pick and choose from - the kind, the size bound, and the secret scan - and it is called
// by both writers, so a rule cannot hold on one and not the other.
func ValidateModuleContent(kind resolver.ModuleKind, content string) error {
	if !resolver.ValidKind(kind) {
		return fmt.Errorf("kind %q is not a module kind", string(kind))
	}
	if content == "" || len(content) > MaxModuleContentBytes {
		return fmt.Errorf("content must be 1 to %d bytes", MaxModuleContentBytes)
	}
	if secretscan.Contains(content) {
		return ErrModuleSecretDetected
	}
	return modulecontent.Validate(kind, content)
}
