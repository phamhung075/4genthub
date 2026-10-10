package httpapp

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ctxPgFixtures creates the projects / project_git_branchs / branch_contexts / tasks rows a task context
// references, and returns the task and branch context ids. The same four inserts exist as
// taskCtxRepoTestSetup in the repositories package; it is unexported there and that package cannot import
// services, so the httpapp wiring test cannot borrow it.
func ctxPgFixtures(t *testing.T, sessions *database.SessionManager, user string) (string, string) {
	t.Helper()
	ctx := context.Background()
	now := time.Now().UTC()

	projects, err := infrarepos.NewORMRepository[database.Project]("projects", sessions)
	if err != nil {
		t.Fatal(err)
	}
	projectID := tmvo.NewUUIDv4()
	if _, err := projects.Create(ctx, infrarepos.NewKwargs("id", projectID, "name", "p", "user_id", user,
		"created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create project: %v", err)
	}

	gitBranches, err := infrarepos.NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		t.Fatal(err)
	}
	branchID := tmvo.NewUUIDv4()
	if _, err := gitBranches.Create(ctx, infrarepos.NewKwargs("id", branchID, "project_id", projectID,
		"name", "main", "user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create git branch: %v", err)
	}

	branchRepo, err := infrarepos.NewBranchContextRepository(sessions, &user)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := branchRepo.Create(ctx, &entities.BranchContext{ID: branchID, BranchInfo: map[string]any{}, Metadata: map[string]any{}}); err != nil {
		t.Fatalf("create branch context: %v", err)
	}

	tasks, err := infrarepos.NewORMRepository[database.Task]("tasks", sessions)
	if err != nil {
		t.Fatal(err)
	}
	taskID := tmvo.NewUUIDv4()
	if _, err := tasks.Create(ctx, infrarepos.NewKwargs("id", taskID, "title", "t", "description", "",
		"git_branch_id", branchID, "user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create task: %v", err)
	}
	return taskID, branchID
}

// TestAddProgressTwiceReachesTheColumnTheRepositoryReads is the ×2 the gate asked for, over the wiring the
// server itself uses: the four adapters built by unifiedContextRepositories (factories
// .UnifiedContextRepositoryBuilder), two notes written through the service's AddProgress, then read back
// with the repository's own Get on a real database. The service-level unit test beside this one stays green
// with a fake because the fake stores the entity object it was handed - it never crosses the column mapping,
// which is where the notes were being lost. This one crosses it.
func TestAddProgressTwiceReachesTheColumnTheRepositoryReads(t *testing.T) {
	sessions := newMissedNotificationAppEnv(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	taskID, branchID := ctxPgFixtures(t, sessions, user)

	global, project, branch, task, err := unifiedContextRepositories(sessions, &user)
	if err != nil {
		t.Fatalf("unifiedContextRepositories: %v", err)
	}
	// The read the gate named goes through the repository itself, on the same session as the adapters.
	realRepo, err := infrarepos.NewTaskContextRepository(sessions, &user)
	if err != nil {
		t.Fatalf("NewTaskContextRepository: %v", err)
	}

	svc := services.NewUnifiedContextService(global, project, branch, task, nil, nil, nil, nil, &user)
	created, _ := svc.CreateContext(ctx, "task", taskID, ctxPgOM("branch_id", branchID), nil, nil, true)
	if v, _ := created.Get("success"); v != true {
		t.Fatalf("CreateContext failed: keys=%v", created.Keys())
	}

	for _, content := range []string{"first note", "second note"} {
		res, _ := svc.AddProgress(ctx, "task", taskID, content, nil)
		if v, _ := res.Get("success"); v != true {
			t.Fatalf("AddProgress(%q) failed: keys=%v", content, res.Keys())
		}
	}

	tc, err := realRepo.Get(ctx, taskID)
	if err != nil {
		t.Fatalf("repo.Get: %v", err)
	}
	updates, _ := tc.ImplementationNotes["progress_updates"].([]any)
	if len(updates) != 2 {
		t.Fatalf("ImplementationNotes[progress_updates]=%#v after two AddProgress calls; want exactly two notes, no duplicates",
			tc.ImplementationNotes["progress_updates"])
	}
	for i, want := range []string{"first note", "second note"} {
		if got := fmt.Sprint(updates[i]); !strings.Contains(got, want) {
			t.Fatalf("entry %d = %v; want it to carry %q", i, got, want)
		}
	}
	if _, ok := tc.Metadata["implementation_notes"]; ok {
		t.Fatalf("Metadata still carries implementation_notes=%v; the column has two homes",
			tc.Metadata["implementation_notes"])
	}
}

func ctxPgOM(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}
