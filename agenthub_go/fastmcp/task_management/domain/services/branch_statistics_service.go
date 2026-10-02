package services

// BranchStatistics is the branch statistics value object.
type BranchStatistics struct {
	BranchID           string
	TaskCount          int
	CompletedTaskCount int
	InProgressCount    int
	BlockedCount       int
	ProgressPercentage float64
}

// StatusedTask is what the statistics service reads from a task. Python compares
// `task.status == "done"`; a TaskStatus value object never equals a str, so only
// implementations returning a plain string status are counted. StatusValue returns
// the raw status (a string, or a value object that will not match).
type StatusedTask interface{ StatusValue() any }

// IdentifiedBranch is what the service reads from a branch (its id as a string).
type IdentifiedBranch interface{ BranchID() string }

// TaskRepositoryProtocol is the task repository protocol used by the service.
type TaskRepositoryProtocol interface {
	FindByGitBranchID(branchID string) ([]StatusedTask, error)
}

// GitBranchRepositoryProtocol is the git branch repository protocol. Get returns
// nil when the branch does not exist.
type GitBranchRepositoryProtocol interface {
	Get(branchID string) (any, error)
	Update(branchID string, updates map[string]any) (bool, error)
	FindByProjectID(projectID string) ([]IdentifiedBranch, error)
	GetAll() ([]IdentifiedBranch, error)
}

// BranchStatisticsService keeps branch task counts in sync with task states.
// Event handlers swallow errors (Python catches Exception and logs).
type BranchStatisticsService struct {
	taskRepository      TaskRepositoryProtocol
	gitBranchRepository GitBranchRepositoryProtocol
}

// NewBranchStatisticsService builds the service.
func NewBranchStatisticsService(t TaskRepositoryProtocol, g GitBranchRepositoryProtocol) *BranchStatisticsService {
	return &BranchStatisticsService{t, g}
}

func (s *BranchStatisticsService) OnTaskCreated(taskID, branchID, status string) {
	if branchID == "" {
		return
	}
	_, _ = s.recalculate(branchID)
}

// OnTaskUpdated recalculates the old branch (when it changed) and the new one.
// Python iterates a set; here the order is old then new.
func (s *BranchStatisticsService) OnTaskUpdated(taskID string, oldBranchID, newBranchID *string, oldStatus, newStatus string) {
	var branches []string
	if oldBranchID != nil && *oldBranchID != "" && (newBranchID == nil || *oldBranchID != *newBranchID) {
		branches = append(branches, *oldBranchID)
	}
	if newBranchID != nil && *newBranchID != "" {
		branches = append(branches, *newBranchID)
	}
	for _, b := range branches {
		_, _ = s.recalculate(b)
	}
}

func (s *BranchStatisticsService) OnTaskDeleted(taskID, branchID, status string) {
	if branchID == "" {
		return
	}
	_, _ = s.recalculate(branchID)
}

func (s *BranchStatisticsService) counts(branchID string) (BranchStatistics, error) {
	tasks, err := s.taskRepository.FindByGitBranchID(branchID)
	if err != nil {
		return BranchStatistics{}, err
	}
	st := BranchStatistics{BranchID: branchID, TaskCount: len(tasks)}
	for _, t := range tasks {
		switch t.StatusValue() {
		case "done":
			st.CompletedTaskCount++
		case "in_progress":
			st.InProgressCount++
		case "blocked":
			st.BlockedCount++
		}
	}
	if st.TaskCount > 0 {
		st.ProgressPercentage = float64(st.CompletedTaskCount) / float64(st.TaskCount) * 100.0
	}
	return st, nil
}

func (s *BranchStatisticsService) recalculate(branchID string) (BranchStatistics, error) {
	st, err := s.counts(branchID)
	if err != nil {
		return BranchStatistics{}, err
	}
	branch, err := s.gitBranchRepository.Get(branchID)
	if err != nil {
		return BranchStatistics{}, err
	}
	if branch != nil {
		if _, err := s.gitBranchRepository.Update(branchID, map[string]any{
			"task_count": st.TaskCount, "completed_task_count": st.CompletedTaskCount,
			"progress_percentage": st.ProgressPercentage,
		}); err != nil {
			return BranchStatistics{}, err
		}
	}
	return st, nil
}

// RecalculateAllBranches recalculates every branch (of a project when projectID is
// non-empty); branches that fail are skipped.
func (s *BranchStatisticsService) RecalculateAllBranches(projectID string) (map[string]BranchStatistics, error) {
	var branches []IdentifiedBranch
	var err error
	if projectID != "" {
		branches, err = s.gitBranchRepository.FindByProjectID(projectID)
	} else {
		branches, err = s.gitBranchRepository.GetAll()
	}
	if err != nil {
		return nil, err
	}
	results := map[string]BranchStatistics{}
	for _, b := range branches {
		if st, err := s.recalculate(b.BranchID()); err == nil {
			results[b.BranchID()] = st
		}
	}
	return results, nil
}

// GetBranchStatistics returns fresh statistics, or nil when the branch is unknown.
func (s *BranchStatisticsService) GetBranchStatistics(branchID string) (*BranchStatistics, error) {
	branch, err := s.gitBranchRepository.Get(branchID)
	if err != nil || branch == nil {
		return nil, err
	}
	st, err := s.counts(branchID)
	if err != nil {
		return nil, err
	}
	return &st, nil
}
