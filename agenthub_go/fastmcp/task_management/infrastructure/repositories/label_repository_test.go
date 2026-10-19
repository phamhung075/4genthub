package repositories

// Real-PostgreSQL test for ORMLabelRepository.DeleteLabel. task_labels.label_id no longer
// cascades from labels, so deleting a label has to remove its task relationships itself.

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestLabelRepoDeleteRemovesTaskLabels(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "5b1f0c62-7f0e-5b3a-9c47-2f0a8d1e6b94" // real user ids are UUIDs
	projectID, branches := gitBranchRepoTestSetup(t, sessions, user)
	gb, err := branches.CreateBranch(ctx, projectID, "labels", "")
	if err != nil {
		t.Fatal(err)
	}
	taskID := gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "todo", "medium")
	labelID := "label-delete"
	now := time.Now().UTC()
	gitBranchRepoTestCreate[database.Label](t, sessions, "labels", NewKwargs(
		"id", labelID, "name", "deleteme", "color", "#123456", "description", "",
		"user_id", user, "created_at", now, "updated_at", now))
	gitBranchRepoTestCreate[database.TaskLabel](t, sessions, "task_labels", NewKwargs(
		"task_id", taskID, "label_id", labelID, "user_id", user, "applied_at", now))

	labels, err := NewORMLabelRepository(sessions, &user)
	if err != nil {
		t.Fatal(err)
	}
	deleted, err := labels.DeleteLabel(ctx, labelID)
	if err != nil || !deleted {
		t.Fatalf("DeleteLabel = %v, %v", deleted, err)
	}
	if gitBranchRepoTestRowExists(t, sessions, `SELECT count(*) FROM task_labels WHERE label_id = $1`, labelID) {
		t.Fatal("task_labels row still present")
	}
	if !gitBranchRepoTestRowExists(t, sessions, `SELECT count(*) FROM tasks WHERE id = $1`, taskID) {
		t.Fatal("the task was deleted with its label")
	}
	if deleted, err := labels.DeleteLabel(ctx, labelID); err != nil || deleted {
		t.Fatalf("DeleteLabel(again) = %v, %v", deleted, err)
	}
}
