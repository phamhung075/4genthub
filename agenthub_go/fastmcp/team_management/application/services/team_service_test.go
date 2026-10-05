package services

import (
	"context"
	"errors"
	"fmt"
	"testing"

	teamrepos "agenthub/fastmcp/team_management/domain/repositories"
)

// fakeTeamRepo is an in-memory TeamRepository; the rules under test live in the service, so
// the fake only stores and returns.
type fakeTeamRepo struct {
	teams   map[string]*teamrepos.Team
	members map[string]map[string]*teamrepos.TeamMember
	bySlug  map[string]string
	n       int
}

func newFakeTeamRepo() *fakeTeamRepo {
	return &fakeTeamRepo{
		teams:   map[string]*teamrepos.Team{},
		members: map[string]map[string]*teamrepos.TeamMember{},
		bySlug:  map[string]string{},
	}
}

func (f *fakeTeamRepo) Create(_ context.Context, slug, name, ownerUserID string) (*teamrepos.Team, error) {
	key := ownerUserID + "/" + slug
	if _, ok := f.bySlug[key]; ok {
		return nil, teamrepos.ErrTeamExists
	}
	f.n++
	id := fmt.Sprintf("team-%d", f.n)
	team := &teamrepos.Team{ID: id, UserID: ownerUserID, Slug: slug, Name: name}
	f.teams[id] = team
	f.bySlug[key] = id
	f.members[id] = map[string]*teamrepos.TeamMember{
		ownerUserID: {ID: id + "-owner", TeamID: id, UserID: ownerUserID, Role: teamrepos.RoleOwner},
	}
	return team, nil
}

func (f *fakeTeamRepo) FindForMember(_ context.Context, userID, slug string) (*teamrepos.Team, error) {
	for id, team := range f.teams {
		if team.Slug != slug {
			continue
		}
		if _, ok := f.members[id][userID]; ok {
			return team, nil
		}
	}
	return nil, nil
}

func (f *fakeTeamRepo) ListForMember(_ context.Context, userID string) ([]teamrepos.Membership, error) {
	var out []teamrepos.Membership
	for id, members := range f.members {
		if m, ok := members[userID]; ok {
			out = append(out, teamrepos.Membership{Team: *f.teams[id], Role: m.Role})
		}
	}
	return out, nil
}

func (f *fakeTeamRepo) Delete(_ context.Context, teamID string) error {
	delete(f.teams, teamID)
	delete(f.members, teamID)
	return nil
}

func (f *fakeTeamRepo) Membership(_ context.Context, teamID, userID string) (*teamrepos.TeamMember, error) {
	if _, ok := f.teams[teamID]; !ok {
		return nil, nil
	}
	return f.members[teamID][userID], nil
}

func (f *fakeTeamRepo) ListMembers(_ context.Context, teamID string) ([]teamrepos.TeamMember, error) {
	var out []teamrepos.TeamMember
	for _, m := range f.members[teamID] {
		out = append(out, *m)
	}
	return out, nil
}

func (f *fakeTeamRepo) AddMember(_ context.Context, teamID, userID, role string) (*teamrepos.TeamMember, error) {
	if _, ok := f.members[teamID][userID]; ok {
		return nil, teamrepos.ErrMemberExists
	}
	f.n++
	m := &teamrepos.TeamMember{ID: fmt.Sprintf("m-%d", f.n), TeamID: teamID, UserID: userID, Role: role}
	f.members[teamID][userID] = m
	return m, nil
}

func (f *fakeTeamRepo) UpdateRole(_ context.Context, teamID, userID, role string) error {
	m, ok := f.members[teamID][userID]
	if !ok {
		return teamrepos.ErrTeamNotFound
	}
	m.Role = role
	return nil
}

func (f *fakeTeamRepo) RemoveMember(_ context.Context, teamID, userID string) (bool, error) {
	if _, ok := f.members[teamID][userID]; !ok {
		return false, nil
	}
	delete(f.members[teamID], userID)
	return true, nil
}

const (
	svcOwner  = "owner-user"
	svcViewer = "viewer-user"
	svcOther  = "other-user"
)

// newTeamFixture builds a service over a repo holding one team owned by svcOwner with
// svcViewer as a viewer.
func newTeamFixture(t *testing.T) (*TeamService, string) {
	t.Helper()
	repo := newFakeTeamRepo()
	svc := NewTeamService(repo)
	team, err := svc.Create(context.Background(), svcOwner, "eng", "Engineering")
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	if _, err := svc.AddMember(context.Background(), svcOwner, team.Slug, svcViewer, teamrepos.RoleViewer); err != nil {
		t.Fatalf("add viewer: %v", err)
	}
	return svc, team.Slug
}

func TestTeamServiceCreateValidatesAndMakesTheCreatorOwner(t *testing.T) {
	repo := newFakeTeamRepo()
	svc := NewTeamService(repo)

	for _, c := range []struct{ slug, name string }{
		{"", "n"}, {"bad.slug", "n"}, {"ok", ""}, {"ok", "   "},
		{"ok", string(make([]rune, teamrepos.MaxTeamNameLength+1))},
	} {
		_, err := svc.Create(context.Background(), svcOwner, c.slug, c.name)
		var invalid *ValidationError
		if !errors.As(err, &invalid) {
			t.Errorf("Create(%q,%q) error = %v, want ValidationError", c.slug, c.name, err)
		}
	}

	team, err := svc.Create(context.Background(), svcOwner, "eng", "Engineering")
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if team.UserID != svcOwner || team.Slug != "eng" {
		t.Fatalf("Create team = %+v", team)
	}
	role, err := repo.Membership(context.Background(), team.ID, svcOwner)
	if err != nil || role == nil || role.Role != teamrepos.RoleOwner {
		t.Fatalf("creator membership = %+v, %v", role, err)
	}

	if _, err := svc.Create(context.Background(), svcOwner, "eng", "Other"); !errors.Is(err, teamrepos.ErrTeamExists) {
		t.Fatalf("duplicate slug error = %v, want ErrTeamExists", err)
	}
}

func TestTeamServiceViewerCannotMutate(t *testing.T) {
	svc, teamID := newTeamFixture(t)
	ctx := context.Background()

	if err := svc.Delete(ctx, svcViewer, teamID); !errors.Is(err, ErrNotTeamOwner) {
		t.Errorf("viewer Delete = %v, want ErrNotTeamOwner", err)
	}
	if _, err := svc.AddMember(ctx, svcViewer, teamID, svcOther, teamrepos.RoleViewer); !errors.Is(err, ErrNotTeamOwner) {
		t.Errorf("viewer AddMember = %v, want ErrNotTeamOwner", err)
	}
	if _, err := svc.UpdateMemberRole(ctx, svcViewer, teamID, svcOther, teamrepos.RoleViewer); !errors.Is(err, ErrNotTeamOwner) {
		t.Errorf("viewer UpdateMemberRole = %v, want ErrNotTeamOwner", err)
	}
	if err := svc.RemoveMember(ctx, svcViewer, teamID, svcOwner); !errors.Is(err, ErrNotTeamOwner) {
		t.Errorf("viewer RemoveMember = %v, want ErrNotTeamOwner", err)
	}

	if members, err := svc.ListMembers(ctx, svcViewer, teamID); err != nil || len(members) != 2 {
		t.Errorf("viewer ListMembers = %d members, %v, want 2", len(members), err)
	}
}

func TestTeamServiceNonMemberSeesNoTeam(t *testing.T) {
	svc, teamID := newTeamFixture(t)
	ctx := context.Background()

	if _, _, err := svc.Get(ctx, svcOther, teamID); !errors.Is(err, teamrepos.ErrTeamNotFound) {
		t.Errorf("Get as non-member = %v, want ErrTeamNotFound", err)
	}
	if _, err := svc.ListMembers(ctx, svcOther, teamID); !errors.Is(err, teamrepos.ErrTeamNotFound) {
		t.Errorf("ListMembers as non-member = %v, want ErrTeamNotFound", err)
	}
	if _, _, err := svc.Get(ctx, svcOther, "no-such-team"); !errors.Is(err, teamrepos.ErrTeamNotFound) {
		t.Errorf("Get unknown team = %v, want ErrTeamNotFound", err)
	}
}

func TestTeamServiceKeepsExactlyOneOwner(t *testing.T) {
	svc, teamID := newTeamFixture(t)
	ctx := context.Background()

	if _, err := svc.AddMember(ctx, svcOwner, teamID, svcOther, teamrepos.RoleOwner); !errors.Is(err, ErrSecondOwner) {
		t.Errorf("AddMember owner = %v, want ErrSecondOwner", err)
	}
	if _, err := svc.UpdateMemberRole(ctx, svcOwner, teamID, svcOwner, teamrepos.RoleOwner); !errors.Is(err, ErrSecondOwner) {
		t.Errorf("promote to owner = %v, want ErrSecondOwner", err)
	}
	if _, err := svc.UpdateMemberRole(ctx, svcOwner, teamID, svcOwner, teamrepos.RoleViewer); !errors.Is(err, ErrLastOwner) {
		t.Errorf("demote the owner = %v, want ErrLastOwner", err)
	}
	if err := svc.RemoveMember(ctx, svcOwner, teamID, svcOwner); !errors.Is(err, ErrLastOwner) {
		t.Errorf("remove the owner = %v, want ErrLastOwner", err)
	}
	if _, err := svc.UpdateMemberRole(ctx, svcOwner, teamID, svcOther, "admin"); err == nil {
		t.Error("invalid role accepted")
	}
}

func TestTeamServiceOwnerManagesViewers(t *testing.T) {
	svc, teamID := newTeamFixture(t)
	ctx := context.Background()

	member, err := svc.AddMember(ctx, svcOwner, teamID, svcOther, teamrepos.RoleViewer)
	if err != nil || member.Role != teamrepos.RoleViewer {
		t.Fatalf("AddMember = %+v, %v", member, err)
	}
	if _, err := svc.AddMember(ctx, svcOwner, teamID, svcOther, teamrepos.RoleViewer); !errors.Is(err, teamrepos.ErrMemberExists) {
		t.Errorf("duplicate AddMember = %v, want ErrMemberExists", err)
	}
	if err := svc.RemoveMember(ctx, svcOwner, teamID, svcOther); err != nil {
		t.Fatalf("RemoveMember: %v", err)
	}
	if err := svc.Delete(ctx, svcOwner, teamID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, _, err := svc.Get(ctx, svcOwner, teamID); !errors.Is(err, teamrepos.ErrTeamNotFound) {
		t.Errorf("Get after Delete = %v, want ErrTeamNotFound", err)
	}
}
