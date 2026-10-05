// Package services holds the team_management use cases: the membership rules over a
// TeamRepository. Slice 1 is single-owner — the creator is the team's one owner, every
// membership change is owner-only, and every other member is a viewer with read access.
//
// Teams are addressed by slug. A slug is unique per owner, not globally, so every lookup is
// scoped to the caller's membership (a non-member cannot tell two same-slug teams apart).
package services

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"agenthub/fastmcp/team_management/domain/repositories"
)

// ErrNotTeamOwner means the caller is a member of the team but not its owner.
var ErrNotTeamOwner = errors.New("only the team owner may change membership")

// ErrLastOwner means the operation would leave the team without its owner.
var ErrLastOwner = errors.New("a team must keep exactly one owner")

// ErrSecondOwner means the operation would add a second owner; slice 1 is single-owner.
var ErrSecondOwner = errors.New("a team has exactly one owner")

// ValidationError is a request the caller can fix; the mount answers 400 with its message.
type ValidationError struct{ Msg string }

func (e *ValidationError) Error() string { return e.Msg }

func invalid(format string, args ...any) error {
	return &ValidationError{Msg: fmt.Sprintf(format, args...)}
}

// TeamService applies the membership rules over a TeamRepository.
type TeamService struct {
	repo repositories.TeamRepository
}

// NewTeamService builds the service over a repository.
func NewTeamService(repo repositories.TeamRepository) *TeamService { return &TeamService{repo: repo} }

// Create validates the input and creates the team with the caller as its owner.
func (s *TeamService) Create(ctx context.Context, ownerUserID, slug, name string) (*repositories.Team, error) {
	if strings.TrimSpace(slug) == "" || strings.TrimSpace(name) == "" {
		return nil, invalid("slug and name are required")
	}
	if err := repositories.ValidateTeamSlug(slug); err != nil {
		return nil, invalid("%s", err)
	}
	if err := repositories.ValidateTeamName(name); err != nil {
		return nil, invalid("%s", err)
	}
	return s.repo.Create(ctx, slug, name, ownerUserID)
}

// List returns the teams the caller belongs to, with the caller's role in each.
func (s *TeamService) List(ctx context.Context, userID string) ([]repositories.Membership, error) {
	return s.repo.ListForMember(ctx, userID)
}

// Get returns one team and the caller's role; ErrTeamNotFound when the caller is not a member.
func (s *TeamService) Get(ctx context.Context, userID, slug string) (*repositories.Team, string, error) {
	team, err := s.resolve(ctx, userID, slug)
	if err != nil {
		return nil, "", err
	}
	member, err := s.repo.Membership(ctx, team.ID, userID)
	if err != nil {
		return nil, "", err
	}
	if member == nil {
		return nil, "", repositories.ErrTeamNotFound
	}
	return team, member.Role, nil
}

// Delete removes the team; owner only.
func (s *TeamService) Delete(ctx context.Context, userID, slug string) error {
	team, err := s.resolve(ctx, userID, slug)
	if err != nil {
		return err
	}
	if _, err := s.requireOwner(ctx, team.ID, userID); err != nil {
		return err
	}
	return s.repo.Delete(ctx, team.ID)
}

// ListMembers returns the members of one team; the caller must be a member.
func (s *TeamService) ListMembers(ctx context.Context, userID, slug string) ([]repositories.TeamMember, error) {
	team, err := s.resolve(ctx, userID, slug)
	if err != nil {
		return nil, err
	}
	return s.repo.ListMembers(ctx, team.ID)
}

// AddMember adds a viewer; owner only. Slice 1 allows no second owner, so role must be viewer.
func (s *TeamService) AddMember(ctx context.Context, actorUserID, slug, memberUserID, role string) (*repositories.TeamMember, error) {
	team, err := s.resolve(ctx, actorUserID, slug)
	if err != nil {
		return nil, err
	}
	if _, err := s.requireOwner(ctx, team.ID, actorUserID); err != nil {
		return nil, err
	}
	if err := repositories.ValidateRole(role); err != nil {
		return nil, invalid("%s", err)
	}
	if role != repositories.RoleViewer {
		return nil, ErrSecondOwner
	}
	return s.repo.AddMember(ctx, team.ID, memberUserID, role)
}

// UpdateMemberRole changes a member's role; owner only, and viewer is the only role that can
// be set. Demoting the owner is refused, so the team always keeps its one owner.
func (s *TeamService) UpdateMemberRole(ctx context.Context, actorUserID, slug, memberUserID, role string) (*repositories.TeamMember, error) {
	team, err := s.resolve(ctx, actorUserID, slug)
	if err != nil {
		return nil, err
	}
	if _, err := s.requireOwner(ctx, team.ID, actorUserID); err != nil {
		return nil, err
	}
	if err := repositories.ValidateRole(role); err != nil {
		return nil, invalid("%s", err)
	}
	if role == repositories.RoleOwner {
		return nil, ErrSecondOwner
	}
	target, err := s.requireMember(ctx, team.ID, memberUserID)
	if err != nil {
		return nil, err
	}
	if target.Role == repositories.RoleOwner {
		return nil, ErrLastOwner
	}
	if err := s.repo.UpdateRole(ctx, team.ID, memberUserID, role); err != nil {
		return nil, err
	}
	return s.repo.Membership(ctx, team.ID, memberUserID)
}

// RemoveMember removes a member; owner only. The owner cannot be removed.
func (s *TeamService) RemoveMember(ctx context.Context, actorUserID, slug, memberUserID string) error {
	team, err := s.resolve(ctx, actorUserID, slug)
	if err != nil {
		return err
	}
	if _, err := s.requireOwner(ctx, team.ID, actorUserID); err != nil {
		return err
	}
	target, err := s.requireMember(ctx, team.ID, memberUserID)
	if err != nil {
		return err
	}
	if target.Role == repositories.RoleOwner {
		return ErrLastOwner
	}
	_, err = s.repo.RemoveMember(ctx, team.ID, memberUserID)
	return err
}

// resolve finds the caller's team by slug; ErrTeamNotFound when it is absent or the caller
// is not a member.
func (s *TeamService) resolve(ctx context.Context, userID, slug string) (*repositories.Team, error) {
	team, err := s.repo.FindForMember(ctx, userID, slug)
	if err != nil {
		return nil, err
	}
	if team == nil {
		return nil, repositories.ErrTeamNotFound
	}
	return team, nil
}

// requireMember returns the caller's member row, or ErrTeamNotFound when the team is absent
// or the caller is not a member (a non-member must not learn which of the two it is).
func (s *TeamService) requireMember(ctx context.Context, teamID, userID string) (*repositories.TeamMember, error) {
	member, err := s.repo.Membership(ctx, teamID, userID)
	if err != nil {
		return nil, err
	}
	if member == nil {
		return nil, repositories.ErrTeamNotFound
	}
	return member, nil
}

// requireOwner is requireMember plus the owner check.
func (s *TeamService) requireOwner(ctx context.Context, teamID, userID string) (*repositories.TeamMember, error) {
	member, err := s.requireMember(ctx, teamID, userID)
	if err != nil {
		return nil, err
	}
	if member.Role != repositories.RoleOwner {
		return nil, ErrNotTeamOwner
	}
	return member, nil
}
