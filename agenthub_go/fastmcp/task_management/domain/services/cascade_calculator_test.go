package services

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/services/protocols"
)

type fakeProvider struct{ calls int }

func (f *fakeProvider) GetTaskCascadeData(_ context.Context, id string) (*protocols.TaskCascadeData, error) {
	f.calls++
	if id == "none" {
		return nil, nil
	}
	ctxID := "c1"
	return &protocols.TaskCascadeData{ID: id, GitBranchID: "b", ProjectID: "p", ContextID: &ctxID}, nil
}
func (f *fakeProvider) GetTaskSubtaskIDs(context.Context, string) ([]string, error) {
	return []string{"s1"}, nil
}
func (f *fakeProvider) GetTaskParentTaskIDs(context.Context, string) ([]string, error) {
	return []string{"t0"}, nil
}
func (f *fakeProvider) GetSubtaskCascadeData(context.Context, string) (*protocols.SubtaskCascadeData, error) {
	return nil, nil
}
func (f *fakeProvider) GetBranchCascadeData(context.Context, string) (*protocols.BranchCascadeData, error) {
	return nil, nil
}
func (f *fakeProvider) GetProjectCascadeData(context.Context, string) (*protocols.ProjectCascadeData, error) {
	return nil, nil
}
func (f *fakeProvider) GetContextCascadeData(context.Context, string) (*protocols.ContextCascadeData, error) {
	return nil, nil
}
func (f *fakeProvider) GetRelatedContextIDs(context.Context, string, string) ([]string, error) {
	return []string{"c2", "c1"}, nil
}
func (f *fakeProvider) DetectEntityType(_ context.Context, id string) (*protocols.EntityType, error) {
	if id == "unknown" {
		return nil, nil
	}
	t := EntityTypeTask
	return &t, nil
}

func TestCascade(t *testing.T) {
	p := &fakeProvider{}
	c := NewCascadeCalculator(p)
	ctx := context.Background()
	r, err := c.CalculateCascade(ctx, "t1", nil, true)
	if err != nil || r.EntityType != EntityTypeTask || r.GetAffectedCount() != 7 {
		t.Fatalf("%+v %v", r, err)
	}
	if got := r.AffectedContexts.Items(); len(got) != 2 || got[0] != "c1" {
		t.Fatalf("%v", got)
	}
	r2, _ := c.CalculateCascade(ctx, "t1", nil, true)
	if !r2.CacheHit || p.calls != 1 {
		t.Fatal("cache")
	}
	st := c.GetCacheStats()
	if st["cache_size"] != 1 || st["cache_entries"].([]string)[0] != "t1:auto" {
		t.Fatalf("%v", st)
	}
	if _, err := c.CalculateCascade(ctx, "unknown", nil, true); err == nil || err.Error() != "Could not detect entity type for ID: unknown" {
		t.Fatal(err)
	}
	r3, _ := c.CalculateCascade(ctx, "none", nil, false)
	if r3.GetAffectedCount() != 1 {
		t.Fatal("missing task")
	}
	c.ClearCache()
	if c.GetCacheStats()["cache_size"] != 0 {
		t.Fatal("clear")
	}
}
