package services

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type cdTasks struct{ tasks map[string]*entities.Task }

func (f cdTasks) FindByID(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	return f.tasks[id.Value], nil
}
func (f cdTasks) FindByGitBranchID(context.Context, string) ([]*entities.Task, error) {
	var out []*entities.Task
	for _, t := range f.tasks {
		out = append(out, t)
	}
	return out, nil
}
func (f cdTasks) Delete(_ context.Context, id value_objects.TaskId) (bool, error) {
	delete(f.tasks, id.Value)
	return true, nil
}

type cdSubs struct{}

func (cdSubs) CountByParentTaskID(context.Context, value_objects.TaskId) (int, error) { return 3, nil }
func (cdSubs) DeleteByParentTaskID(context.Context, value_objects.TaskId) (bool, error) {
	return true, nil
}

type cdBranches struct{ b *entities.GitBranch }

func (f cdBranches) FindByID(context.Context, string) (*entities.GitBranch, error) { return f.b, nil }
func (f cdBranches) FindByProjectID(context.Context, string) ([]*entities.GitBranch, error) {
	return []*entities.GitBranch{f.b}, nil
}
func (cdBranches) Delete(context.Context, string) (bool, error) { return true, nil }

type cdProjects struct{ p *entities.Project }

func (f cdProjects) FindByID(context.Context, string) (*entities.Project, error) { return f.p, nil }
func (cdProjects) Delete(context.Context, string) (bool, error)                  { return true, nil }

type cdContexts struct{ deleted []string }

func (f *cdContexts) Delete(_ context.Context, id string) error {
	f.deleted = append(f.deleted, id)
	return nil
}

func TestCascadeDeletion(t *testing.T) {
	tid := value_objects.GenerateNewTaskId()
	cid := "ctx-1"
	tasks := cdTasks{map[string]*entities.Task{tid.Value: {ID: &tid, ContextID: &cid}}}
	bid, _ := value_objects.NewGitBranchId(value_objects.NewUUIDv4())
	contexts := &cdContexts{}
	s := NewCascadeDeletionService(tasks, cdSubs{}, cdBranches{&entities.GitBranch{ID: &bid}}, cdProjects{&entities.Project{}}, contexts)
	st, err := s.DeleteProjectCascade(context.Background(), "p")
	if err != nil {
		t.Fatal(err)
	}
	if st["project_deleted"] != true || st["branches_deleted"] != 1 || st["tasks_deleted"] != 1 ||
		st["subtasks_deleted"] != 3 || st["contexts_deleted"] != 1 {
		t.Fatalf("%v", st)
	}
	ev := st["events_dispatched"].([]string)
	if len(ev) != 1 || ev[0] != "project_deleted" || len(contexts.deleted) != 1 {
		t.Fatalf("%v %v", ev, contexts.deleted)
	}
	if _, err := s.DeleteTaskCascade(context.Background(), "", DeleteScopeTaskFull); err == nil {
		t.Fatal("expected ValueError for empty id")
	}
}
