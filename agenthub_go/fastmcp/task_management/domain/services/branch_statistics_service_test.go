package services

import "testing"

type tk string

func (t tk) StatusValue() any { return string(t) }

type br string

func (b br) BranchID() string { return string(b) }

type fakeTasks []StatusedTask

func (f fakeTasks) FindByGitBranchID(string) ([]StatusedTask, error) { return f, nil }

type fakeBranchRepo struct{ updates []map[string]any }

func (f *fakeBranchRepo) Get(id string) (any, error) {
	if id == "missing" {
		return nil, nil
	}
	return id, nil
}
func (f *fakeBranchRepo) Update(_ string, u map[string]any) (bool, error) {
	f.updates = append(f.updates, u)
	return true, nil
}
func (f *fakeBranchRepo) FindByProjectID(string) ([]IdentifiedBranch, error) {
	return []IdentifiedBranch{br("b1")}, nil
}
func (f *fakeBranchRepo) GetAll() ([]IdentifiedBranch, error) { return nil, nil }

func TestBranchStatistics(t *testing.T) {
	repo := &fakeBranchRepo{}
	s := NewBranchStatisticsService(fakeTasks{tk("done"), tk("in_progress"), tk("blocked"), tk("todo")}, repo)
	st, _ := s.GetBranchStatistics("b1")
	if st.TaskCount != 4 || st.CompletedTaskCount != 1 || st.ProgressPercentage != 25.0 || st.BlockedCount != 1 {
		t.Fatalf("%+v", st)
	}
	if st, _ := s.GetBranchStatistics("missing"); st != nil {
		t.Fatal("missing branch")
	}
	old, nw := "a", "b"
	s.OnTaskUpdated("t", &old, &nw, "", "")
	if len(repo.updates) != 2 || repo.updates[0]["task_count"] != 4 {
		t.Fatalf("%v", repo.updates)
	}
	res, _ := s.RecalculateAllBranches("p")
	if res["b1"].TaskCount != 4 {
		t.Fatal(res)
	}
}
