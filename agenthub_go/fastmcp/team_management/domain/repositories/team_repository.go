// Package repositories defines the persistence ports of the team_management bounded
// context (NEXT_GEN D5, teams and sharing). A team is the account boundary whose members
// share its data; every read is filtered by the caller's membership.
package repositories

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

// Member roles. Slice 1 is single-owner: a team has exactly one owner (its creator) and
// every other member is a viewer.
const (
	RoleOwner  = "owner"
	RoleViewer = "viewer"
)

// MaxTeamNameLength bounds Team.Name in characters; teams.name is unbounded TEXT, so this
// is the only limit.
const MaxTeamNameLength = 200

// Errors reported by TeamRepository; callers match them with errors.Is.
var (
	// ErrTeamExists means the owner already has a team with the slug.
	ErrTeamExists = errors.New("team slug already exists")
	// ErrTeamNotFound means no such team, or the caller is not a member of it.
	ErrTeamNotFound = errors.New("team not found")
	// ErrMemberExists means the team already has that member.
	ErrMemberExists = errors.New("team member already exists")
)

// teamSlugPattern is the OpenRig name rule, the same one room slugs use: a team slug is a
// URL-safe identifier written into paths, so no dots or other punctuation.
var teamSlugPattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`)

// ValidateTeamSlug checks slug against the OpenRig name rule.
func ValidateTeamSlug(slug string) error {
	if !teamSlugPattern.MatchString(slug) {
		return fmt.Errorf("team slug %q must match %s", slug, teamSlugPattern)
	}
	return nil
}

// ValidateTeamName requires a non-empty name of at most MaxTeamNameLength characters.
func ValidateTeamName(name string) error {
	if strings.TrimSpace(name) == "" || utf8.RuneCountInString(name) > MaxTeamNameLength {
		return fmt.Errorf("team name must be 1 to %d characters", MaxTeamNameLength)
	}
	return nil
}

// ValidateRole accepts the two member roles.
func ValidateRole(role string) error {
	if role != RoleOwner && role != RoleViewer {
		return fmt.Errorf("role %q must be %q or %q", role, RoleOwner, RoleViewer)
	}
	return nil
}

// Team is a team, the account boundary its members share. UserID is the owning user.
type Team struct {
	ID        string
	UserID    string
	Slug      string
	Name      string
	CreatedAt time.Time
	UpdatedAt time.Time
}

// TeamMember is one user's membership in a team.
type TeamMember struct {
	ID        string
	TeamID    string
	UserID    string
	Role      string
	CreatedAt time.Time
}

// Membership is a team the caller belongs to, with the caller's role in it.
type Membership struct {
	Team Team
	Role string
}

// TeamRepository stores teams and their members. Create inserts the team and its owner
// membership atomically; Delete removes the team and its member rows, because the
// application layer cascades (there is no foreign key CASCADE).
type TeamRepository interface {
	// Create inserts the team and its owner membership; ErrTeamExists when the owner
	// already has the slug.
	Create(ctx context.Context, slug, name, ownerUserID string) (*Team, error)
	// FindForMember returns the team with the slug when userID is a member of it, or nil.
	// Two teams owned by different users may share a slug, so the lookup is scoped to the
	// caller's membership.
	FindForMember(ctx context.Context, userID, slug string) (*Team, error)
	// ListForMember returns the teams userID belongs to, ordered by slug.
	ListForMember(ctx context.Context, userID string) ([]Membership, error)
	// Delete removes the team and its member rows.
	Delete(ctx context.Context, teamID string) error
	// Membership returns the member row, or nil when userID is not a member.
	Membership(ctx context.Context, teamID, userID string) (*TeamMember, error)
	// ListMembers returns the members, owner first then by user id.
	ListMembers(ctx context.Context, teamID string) ([]TeamMember, error)
	// AddMember inserts a member; ErrMemberExists when the team already has that member.
	AddMember(ctx context.Context, teamID, userID, role string) (*TeamMember, error)
	// UpdateRole changes a member's role; ErrTeamNotFound when the member is absent.
	UpdateRole(ctx context.Context, teamID, userID, role string) error
	// RemoveMember deletes a member row and reports whether it existed.
	RemoveMember(ctx context.Context, teamID, userID string) (bool, error)
}
