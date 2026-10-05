package repositories

// Tests for the ported ORMAgentRepository against a real PostgreSQL instance
// (AGENTHUB_TEST_PG_URL), using newTestRepoEnv.

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func agentRepoTestNewRepo(t *testing.T, sessions *database.SessionManager, userID string) *ORMAgentRepository {
	t.Helper()
	repo, err := NewORMAgentRepository(sessions, &userID, nil)
	if err != nil {
		t.Fatalf("NewORMAgentRepository: %v", err)
	}
	return repo
}

func agentRepoTestNewAgent(t *testing.T, name, description string, caps ...entities.AgentCapability) *entities.Agent {
	t.Helper()
	id, err := tmvo.NewAgentId(tmvo.NewUUIDv4())
	if err != nil {
		t.Fatal(err)
	}
	capSet := map[entities.AgentCapability]struct{}{}
	for _, c := range caps {
		capSet[c] = struct{}{}
	}
	agent, err := entities.NewAgent(entities.Agent{ID: &id, Name: name, Description: description, Capabilities: capSet})
	if err != nil {
		t.Fatal(err)
	}
	return agent
}

func TestAgentRepoRegisterGetList(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := agentRepoTestNewRepo(t, sessions, user)

	agent := agentRepoTestNewAgent(t, "alpha", "the alpha agent", entities.CapabilityBackendDevelopment)
	registered, err := repo.RegisterAgent(ctx, agent)
	if err != nil {
		t.Fatalf("RegisterAgent: %v", err)
	}
	if registered.Name != "alpha" || registered.ID.String() != agent.ID.String() {
		t.Fatalf("registered = %+v", registered)
	}
	if _, ok := registered.Capabilities[entities.CapabilityBackendDevelopment]; !ok {
		t.Fatal("capability lost")
	}
	if registered.PriorityPreference != "medium" || registered.Timezone != "UTC" {
		t.Fatalf("defaults = %q %q", registered.PriorityPreference, registered.Timezone)
	}

	got, err := repo.GetAgent(ctx, "p", agent.ID.String())
	if err != nil {
		t.Fatalf("GetAgent: %v", err)
	}
	if got["name"] != "alpha" || got["status"] != "available" {
		t.Fatalf("GetAgent = %+v", got)
	}
	if got["availability_score"] != 1.0 {
		t.Fatalf("availability = %+v", got["availability_score"])
	}
	if _, ok := got["model_metadata"].(*entities.OrderedMap[any]); !ok {
		t.Fatalf("model_metadata type = %T", got["model_metadata"])
	}

	list, err := repo.ListAgents(ctx, "p")
	if err != nil {
		t.Fatalf("ListAgents: %v", err)
	}
	if list["total_agents"] != 1 {
		t.Fatalf("total_agents = %+v", list["total_agents"])
	}

	available, err := repo.GetAvailableAgents(ctx)
	if err != nil {
		t.Fatalf("GetAvailableAgents: %v", err)
	}
	if len(available) != 1 || available[0].GetAny("name") != "alpha" {
		t.Fatalf("available = %+v", available)
	}

	byName, err := repo.FindByName(ctx, "@alpha")
	if err != nil || byName == nil || byName.ID != agent.ID.String() {
		t.Fatalf("FindByName = %+v, %v", byName, err)
	}
	byName2, err := repo.FindByName(ctx, "alpha")
	if err != nil || byName2 == nil {
		t.Fatalf("FindByName no prefix = %+v, %v", byName2, err)
	}

	results, err := repo.SearchAgents(ctx, "p", "ALP")
	if err != nil {
		t.Fatalf("SearchAgents: %v", err)
	}
	if len(results) != 1 || results[0].GetAny("name") != "alpha" {
		t.Fatalf("search = %+v", results)
	}
	if results[0].GetAny("model_metadata") != nil {
		t.Fatal("search result must not include model_metadata")
	}

	// Duplicate ID and duplicate name are rejected.
	dupID := *agent
	if _, err := repo.RegisterAgent(ctx, &dupID); err == nil {
		t.Fatal("duplicate ID must fail")
	} else if _, ok := err.(*exceptions.ValidationException); !ok {
		t.Fatalf("duplicate ID error = %T", err)
	}
	dupName := agentRepoTestNewAgent(t, "alpha", "")
	if _, err := repo.RegisterAgent(ctx, dupName); err == nil {
		t.Fatal("duplicate name must fail")
	}

	// Update changes the description.
	agent.Description = "updated"
	updated, err := repo.UpdateAgent(ctx, agent)
	if err != nil {
		t.Fatalf("UpdateAgent: %v", err)
	}
	if updated.Description != "updated" {
		t.Fatalf("description = %q", updated.Description)
	}

	// Unregister removes it and reports the old data.
	removed, err := repo.UnregisterAgent(ctx, "p", agent.ID.String())
	if err != nil {
		t.Fatalf("UnregisterAgent: %v", err)
	}
	agentData, _ := removed["agent_data"].(*entities.OrderedMap[any])
	if agentData == nil || agentData.GetAny("name") != "alpha" {
		t.Fatalf("agent_data = %+v", removed["agent_data"])
	}
	if _, err := repo.GetAgent(ctx, "p", agent.ID.String()); err == nil {
		t.Fatal("GetAgent after delete must fail")
	} else if _, ok := err.(*exceptions.ResourceNotFoundException); !ok {
		t.Fatalf("missing error = %T", err)
	}
	if _, err := repo.UnregisterAgent(ctx, "p", agent.ID.String()); err == nil {
		t.Fatal("UnregisterAgent missing must fail")
	}
}

func TestAgentRepoAssignUnassign(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := agentRepoTestNewRepo(t, sessions, user)

	agent := agentRepoTestNewAgent(t, "assignable", "")
	if _, err := repo.RegisterAgent(ctx, agent); err != nil {
		t.Fatal(err)
	}
	id := agent.ID.String()
	branch := tmvo.NewUUIDv4()

	res, err := repo.AssignAgentToTree(ctx, "p", id, branch)
	if err != nil {
		t.Fatalf("AssignAgentToTree: %v", err)
	}
	if res["success"] != true || res["auto_registered"] != false {
		t.Fatalf("assign = %+v", res)
	}
	got, _ := repo.GetAgent(ctx, "p", id)
	assignments, _ := got["assignments"].([]string)
	if len(assignments) != 1 || assignments[0] != branch {
		t.Fatalf("assignments = %+v", got["assignments"])
	}

	again, err := repo.AssignAgentToTree(ctx, "p", id, branch)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(again["message"].(string), "already assigned") {
		t.Fatalf("again = %+v", again)
	}

	// Unassign a specific branch.
	un, err := repo.UnassignAgentFromTree(ctx, "p", id, &branch)
	if err != nil {
		t.Fatalf("UnassignAgentFromTree: %v", err)
	}
	removed, _ := un["removed_assignments"].([]string)
	if len(removed) != 1 || removed[0] != branch {
		t.Fatalf("removed = %+v", un)
	}

	// Assign twice, then unassign all (nil branch).
	b1, b2 := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	if _, err := repo.AssignAgentToTree(ctx, "p", id, b1); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.AssignAgentToTree(ctx, "p", id, b2); err != nil {
		t.Fatal(err)
	}
	all, err := repo.UnassignAgentFromTree(ctx, "p", id, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(all["removed_assignments"].([]string)) != 2 || len(all["remaining_assignments"].([]string)) != 0 {
		t.Fatalf("unassign all = %+v", all)
	}

	// Auto-register with the "uuid:name" format.
	newID := tmvo.NewUUIDv4()
	auto, err := repo.AssignAgentToTree(ctx, "p", newID+":auto-agent", tmvo.NewUUIDv4())
	if err != nil {
		t.Fatalf("auto assign: %v", err)
	}
	if auto["auto_registered"] != true {
		t.Fatalf("auto = %+v", auto)
	}
	if row, err := repo.FindByName(ctx, "auto-agent"); err != nil || row == nil {
		t.Fatalf("auto name lookup = %+v, %v", row, err)
	}

	// Auto-register with a non-UUID id (binds as uuid5, named from the id).
	if _, err := repo.AssignAgentToTree(ctx, "p", "plain-name-agent", tmvo.NewUUIDv4()); err != nil {
		t.Fatalf("non-uuid auto assign: %v", err)
	}
	if row, err := repo.FindByName(ctx, "plain-name-agent"); err != nil || row == nil {
		t.Fatalf("non-uuid name lookup = %+v, %v", row, err)
	}

	// Unassigning a missing agent fails.
	missing := tmvo.NewUUIDv4()
	if _, err := repo.UnassignAgentFromTree(ctx, "p", missing, nil); err == nil {
		t.Fatal("unassign missing must fail")
	}
}

func TestAgentRepoRebalanceAndIsolation(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()

	repoA := agentRepoTestNewRepo(t, sessions, projectRepoTestUserA)
	repoB := agentRepoTestNewRepo(t, sessions, projectRepoTestUserB)

	empty, err := repoA.RebalanceAgents(ctx, "p")
	if err != nil {
		t.Fatal(err)
	}
	rr, _ := empty["rebalance_result"].(*entities.OrderedMap[any])
	if rr.GetAny("changes_made") != false {
		t.Fatalf("empty rebalance = %+v", rr)
	}

	agentA := agentRepoTestNewAgent(t, "agent-a", "a")
	if _, err := repoA.RegisterAgent(ctx, agentA); err != nil {
		t.Fatal(err)
	}
	if _, err := repoA.AssignAgentToTree(ctx, "p", agentA.ID.String(), tmvo.NewUUIDv4()); err != nil {
		t.Fatal(err)
	}
	balanced, err := repoA.RebalanceAgents(ctx, "p")
	if err != nil {
		t.Fatal(err)
	}
	rr2, _ := balanced["rebalance_result"].(*entities.OrderedMap[any])
	if rr2.GetAny("changes_made") != true {
		t.Fatalf("rebalance = %+v", rr2)
	}

	// SearchAgents only sees the user's agents.
	agentB := agentRepoTestNewAgent(t, "agent-b", "b")
	if _, err := repoB.RegisterAgent(ctx, agentB); err != nil {
		t.Fatal(err)
	}
	searchA, err := repoA.SearchAgents(ctx, "p", "agent-")
	if err != nil {
		t.Fatal(err)
	}
	if len(searchA) != 1 || searchA[0].GetAny("name") != "agent-a" {
		t.Fatalf("search A = %+v", searchA)
	}
	// GetAvailableAgents uses BaseORMRepository.find_by (unscoped), so it leaks across users
	// exactly like Python (the base method applies no user filter).
	availableB, err := repoB.GetAvailableAgents(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(availableB) != 2 {
		t.Fatalf("available B = %+v", availableB)
	}
}

func TestAgentRepoSetupTimestampInactive(t *testing.T) {
	// GetByID for an unknown id returns a not-found ResourceNotFoundException.
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	repo := agentRepoTestNewRepo(t, sessions, projectRepoTestUserA)
	if _, err := repo.GetAgent(ctx, "p", tmvo.NewUUIDv4()); err == nil {
		t.Fatal("missing agent must fail")
	}
}
