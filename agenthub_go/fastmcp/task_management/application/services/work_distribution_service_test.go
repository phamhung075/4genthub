package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func wdTestTask(t *testing.T, id, status string) *entities.Task {
	t.Helper()
	tid, err := value_objects.NewTaskId(id)
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	st, err := value_objects.NewTaskStatus(status)
	if err != nil {
		t.Fatalf("NewTaskStatus: %v", err)
	}
	task, err := entities.NewTask(entities.Task{ID: &tid, Status: &st, Title: "t", Description: "d"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	return task
}

func wdTestAgent(t *testing.T, id string) *entities.Agent {
	t.Helper()
	aid, err := value_objects.NewAgentId(id)
	if err != nil {
		t.Fatalf("NewAgentId: %v", err)
	}
	agent, err := entities.NewAgent(entities.Agent{ID: &aid, Name: "a"})
	if err != nil {
		t.Fatalf("NewAgent: %v", err)
	}
	return agent
}

// TestWorkDistributionPlanMethods mirrors DistributionPlan.add_assignment and
// mark_unassignable: assignments append (task_id, agent_id, role) tuples and
// recommendations keyed by task id.
func TestWorkDistributionPlanMethods(t *testing.T) {
	plan := NewDistributionPlan()
	plan.AddAssignment("t1", "a1", "assignee")
	plan.MarkUnassignable("t2", "No available agents")

	if len(plan.Assignments) != 1 {
		t.Fatalf("assignments len = %d, want 1", len(plan.Assignments))
	}
	if got := plan.Assignments[0]; got != [3]string{"t1", "a1", "assignee"} {
		t.Fatalf("assignment = %v", got)
	}
	if len(plan.UnassignableRaw) != 1 || plan.UnassignableRaw[0] != "t2" {
		t.Fatalf("unassignable = %v, want [t2]", plan.UnassignableRaw)
	}
	if plan.Recommendations["t2"] != "No available agents" {
		t.Fatalf("recommendation = %q", plan.Recommendations["t2"])
	}
}

// TestTaskRequirementsFromTaskDefaults mirrors TaskRequirements.from_task: the Go Task
// has no metadata, so every metadata-derived field keeps its Python default.
func TestTaskRequirementsFromTaskDefaults(t *testing.T) {
	task := wdTestTask(t, "11111111-1111-1111-1111-111111111111", "todo")
	req := TaskRequirementsFromTask(task)

	if req.TaskID != "11111111-1111-1111-1111-111111111111" {
		t.Fatalf("TaskID = %q", req.TaskID)
	}
	if req.RequiredRole != nil {
		t.Fatalf("RequiredRole = %v, want nil", req.RequiredRole)
	}
	if len(req.RequiredExpertise) != 0 || len(req.RequiredSkills) != 0 {
		t.Fatalf("expertise/skills not empty: %v/%v", req.RequiredExpertise, req.RequiredSkills)
	}
	if req.CollaborationNeeded || req.EstimatedHours != 0.0 {
		t.Fatalf("collaboration/estimated = %v/%v", req.CollaborationNeeded, req.EstimatedHours)
	}
}

// TestDistributeRoundRobin mirrors _distribute_round_robin: agents are cycled in order
// and each assignment role is "assignee".
func TestDistributeRoundRobin(t *testing.T) {
	svc := NewWorkDistributionService(nil, nil, nil, nil, nil)
	plan := NewDistributionPlan()
	tasks := []*entities.Task{
		wdTestTask(t, "11111111-1111-1111-1111-111111111111", "todo"),
		wdTestTask(t, "22222222-2222-2222-2222-222222222222", "in_progress"),
		wdTestTask(t, "33333333-3333-3333-3333-333333333333", "todo"),
	}
	agents := []*entities.Agent{
		wdTestAgent(t, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
		wdTestAgent(t, "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
	}

	svc.distributeRoundRobin(tasks, agents, plan)

	want := [][3]string{
		{"11111111-1111-1111-1111-111111111111", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "assignee"},
		{"22222222-2222-2222-2222-222222222222", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "assignee"},
		{"33333333-3333-3333-3333-333333333333", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "assignee"},
	}
	if len(plan.Assignments) != len(want) {
		t.Fatalf("assignments len = %d, want %d", len(plan.Assignments), len(want))
	}
	for i, w := range want {
		if plan.Assignments[i] != w {
			t.Fatalf("assignment %d = %v, want %v", i, plan.Assignments[i], w)
		}
	}
}

// TestGetDistributionAnalyticsEmpty mirrors get_distribution_analytics with no history.
func TestGetDistributionAnalyticsEmpty(t *testing.T) {
	svc := NewWorkDistributionService(nil, nil, nil, nil, nil)
	out, err := svc.GetDistributionAnalytics()
	if err != nil {
		t.Fatalf("GetDistributionAnalytics: %v", err)
	}
	if v, _ := out.Get("message"); v != "No distribution history available" {
		t.Fatalf("message = %v", v)
	}
}
