package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func testProject() *entities.Project {
	return &entities.Project{
		GitBranchs:         entities.NewOrderedMap[*entities.GitBranch](),
		RegisteredAgents:   entities.NewOrderedMap[*entities.Agent](),
		AgentAssignments:   entities.NewOrderedMap[string](),
		ActiveWorkSessions: entities.NewOrderedMap[*entities.WorkSession](),
		ResourceLocks:      entities.NewOrderedMap[string](),
	}
}

func TestCleanupProjectDataRemovesOrphans(t *testing.T) {
	project := testProject()
	project.RegisteredAgents.Set("agent1", &entities.Agent{})

	// Assignment to a tree that does not exist.
	project.AgentAssignments.Set("missing_tree", "agent1")
	// Assignment to a registered tree but unregistered agent.
	project.GitBranchs.Set("tree1", &entities.GitBranch{})
	project.AgentAssignments.Set("tree1", "ghost")

	// Work session for an unregistered agent.
	project.ActiveWorkSessions.Set("s1", &entities.WorkSession{AgentID: "ghost"})
	// Resource lock held by an unregistered agent.
	project.ResourceLocks.Set("lock1", "ghost")

	cleaned := zpProjectApplicationCleanupProjectData(project)

	want := []string{
		"Removed assignment to tree 'missing_tree'",
		"Removed assignment to tree 'tree1'",
		"Removed orphaned work session 's1'",
		"Unlocked resource 'lock1'",
	}
	if len(cleaned) != len(want) {
		t.Fatalf("cleaned = %v", cleaned)
	}
	for i := range want {
		if cleaned[i] != want[i] {
			t.Fatalf("cleaned[%d] = %q want %q", i, cleaned[i], want[i])
		}
	}
	if project.AgentAssignments.Len() != 0 || project.ActiveWorkSessions.Len() != 0 || project.ResourceLocks.Len() != 0 {
		t.Fatalf("orphans were not removed")
	}
}
