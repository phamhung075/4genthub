package decisions

import (
	"fmt"
	"regexp"
	"strings"
)

// Tier is who decides a question in the decision ladder: a seat, then its lead, then the owner.
//
// A tier decides for itself when Jev's confidence is at or above the threshold on every question;
// otherwise the question moves exactly one tier up, carrying the recommended option so the answer
// above is one word. The owner is the top: nothing escalates past it.
type Tier string

const (
	TierSeat  Tier = "seat"
	TierLead  Tier = "lead"
	TierOwner Tier = "owner"
)

// Tiers is the ladder from the bottom up. The order is the escalation order.
var Tiers = []Tier{TierSeat, TierLead, TierOwner}

// ParseTier validates a tier supplied by a caller.
func ParseTier(raw string) (Tier, error) {
	for _, tier := range Tiers {
		if Tier(raw) == tier {
			return tier, nil
		}
	}
	return "", fmt.Errorf("tier %q is not one of seat, lead, owner", raw)
}

// Next is the tier a question escalates to. The owner has no next tier.
func (t Tier) Next() (Tier, bool) {
	for i, tier := range Tiers {
		if tier == t && i+1 < len(Tiers) {
			return Tiers[i+1], true
		}
	}
	return "", false
}

// Category names what a question is about, for the one rule that is code and not a model. It is a
// free token, so any project can name its own cases; which categories always reach the owner is a
// OwnerOnlySet, not a closed list here.
type Category string

// CategoryGeneral is the category of a question that names none.
const CategoryGeneral Category = "general"

var categoryToken = regexp.MustCompile(`^[a-z0-9][a-z0-9_-]{0,39}$`)

// ParseCategory validates a category supplied by a caller; an empty one is CategoryGeneral.
func ParseCategory(raw string) (Category, error) {
	raw = strings.ToLower(strings.TrimSpace(raw))
	if raw == "" {
		return CategoryGeneral, nil
	}
	if !categoryToken.MatchString(raw) {
		return "", fmt.Errorf("category %q must be 1-40 characters of a-z, 0-9, _ or -", raw)
	}
	return Category(raw), nil
}

// DefaultOwnerOnly are the categories every project sends to the owner: a credential or a spend is
// not made safe by a confident model. A project adds its own on top (ParseOwnerOnly).
var DefaultOwnerOnly = []Category{"credentials", "spend"}

// OwnerOnlySet is the categories that always reach the owner, whatever the confidence. Jev's
// confidence measures how concentrated an answer is, not whether the action is safe, so this is
// decided by configuration and code and never by the model.
type OwnerOnlySet map[Category]struct{}

// ParseOwnerOnly builds the set from the defaults plus a comma-separated project list.
func ParseOwnerOnly(extra string) (OwnerOnlySet, error) {
	set := OwnerOnlySet{}
	for _, category := range DefaultOwnerOnly {
		set[category] = struct{}{}
	}
	for _, raw := range strings.Split(extra, ",") {
		if strings.TrimSpace(raw) == "" {
			continue
		}
		category, err := ParseCategory(raw)
		if err != nil {
			return nil, err
		}
		set[category] = struct{}{}
	}
	return set, nil
}

// Has reports whether the category must reach the owner regardless of confidence.
func (o OwnerOnlySet) Has(c Category) bool {
	_, ok := o[c]
	return ok
}
