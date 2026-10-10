package repositories

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

func mockNewTask(t *testing.T, title, description string) *entities.Task {
	t.Helper()
	id := tmvo.GenerateNewTaskId()
	task, err := entities.NewTask(entities.Task{ID: &id, Title: title, Description: description})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	return task
}

func TestMockTaskRepositorySaveFindAllOrderAndSearch(t *testing.T) {
	ctx := context.Background()
	repo := NewMockTaskRepository()
	a := mockNewTask(t, "Alpha Task", "first")
	b := mockNewTask(t, "Beta Task", "second")
	if _, err := repo.Save(ctx, a); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Save(ctx, b); err != nil {
		t.Fatal(err)
	}
	all, _ := repo.FindAll(ctx)
	if len(all) != 2 || all[0].Title != "Alpha Task" || all[1].Title != "Beta Task" {
		t.Fatalf("insertion order not preserved: %#v", all)
	}
	got, _ := repo.FindByID(ctx, *a.ID)
	if got != a {
		t.Fatalf("FindByID returned %#v", got)
	}
	// search is case-insensitive on title/description
	res, _ := repo.Search(ctx, "beta", nil, 10)
	if len(res) != 1 || res[0] != b {
		t.Fatalf("search mismatch: %#v", res)
	}
	if n, _ := repo.Count(ctx); n != 2 {
		t.Fatalf("count=%d", n)
	}
}

func TestMockTaskRepositoryStatisticsAndIncrement(t *testing.T) {
	ctx := context.Background()
	repo := NewMockTaskRepository()
	todo := mockNewTask(t, "t", "d")
	if _, err := repo.Save(ctx, todo); err != nil {
		t.Fatal(err)
	}
	stats, _ := repo.GetStatistics(ctx)
	if stats["total"] != 1 || stats["pending"] != 0 || stats["in_progress"] != 0 || stats["completed"] != 0 {
		t.Fatalf("stats=%v", stats)
	}
	ok, _ := repo.AtomicIncrementCompletedSubtasks(ctx, *todo.ID)
	if !ok || todo.CompletedSubtasks != 1 {
		t.Fatalf("increment failed ok=%v val=%d", ok, todo.CompletedSubtasks)
	}
}

func TestMockProjectRepositoryUpdateError(t *testing.T) {
	ctx := context.Background()
	repo := NewMockProjectRepository()
	if _, err := repo.Update(ctx, &entities.Project{Name: "x"}); err == nil {
		t.Fatal("expected ValueError for missing project")
	} else if _, ok := err.(*tmvo.ValueError); !ok {
		t.Fatalf("expected *ValueError, got %T", err)
	}
}

func TestMockSubtaskRepositoryProgress(t *testing.T) {
	ctx := context.Background()
	parent := tmvo.GenerateNewTaskId()
	repo := NewMockSubtaskRepository()
	sid := tmvo.GenerateNewTaskId()
	st, err := tmvo.NewTaskStatus("todo")
	if err != nil {
		t.Fatal(err)
	}
	sub := &entities.Subtask{ID: &sid, ParentTaskID: &parent, Title: "s", Status: &st}
	if ok, _ := repo.Save(ctx, sub); !ok {
		t.Fatal("save failed")
	}
	prog, _ := repo.GetSubtaskProgress(ctx, parent)
	if prog["total"] != 1 || prog["completed"] != 0 || prog["pending"] != 1 {
		t.Fatalf("progress=%v", prog)
	}
	if _, err := repo.BulkComplete(ctx, parent); err != nil {
		t.Fatal(err)
	}
	if sub.Status.Value != "completed" {
		t.Fatalf("bulk complete did not update status: %v", sub.Status.Value)
	}
}

func TestMockRepositoryFactoryAndCreateRepositories(t *testing.T) {
	f := NewMockRepositoryFactory()
	if f.GetProjectRepository() != f.GetProjectRepository() {
		t.Fatal("factory must return the same instances")
	}
	m := CreateMockRepositories()
	if got := m.Keys(); len(got) != 4 || got[0] != "project" || got[3] != "subtask" {
		t.Fatalf("key order=%v", got)
	}
	if _, ok := m.Get("task"); !ok {
		t.Fatal("task entry missing")
	}
}
