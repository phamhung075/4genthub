package task

import (
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// DependencyInfo is information about a single task dependency.
type DependencyInfo struct {
	TaskID               string
	Title                string
	Status               string
	Priority             string
	CompletionPercentage float64
	IsBlocking           bool
	IsBlocked            bool
	EstimatedEffort      *string
	Assignees            []string
	UpdatedAt            *time.Time
}

// NewDependencyInfo mirrors DependencyInfo.__post_init__ (assignees default []).
func NewDependencyInfo(r DependencyInfo) *DependencyInfo {
	if r.Assignees == nil {
		r.Assignees = []string{}
	}
	return &r
}

// DependencyChain represents a chain of task dependencies.
type DependencyChain struct {
	ChainID             string
	Tasks               []DependencyInfo
	TotalTasks          int
	CompletedTasks      int
	BlockedTasks        int
	ChainStatus         string
	EstimatedCompletion *string
}

// CompletionPercentage is the completion_percentage property.
func (c DependencyChain) CompletionPercentage() float64 {
	if c.TotalTasks == 0 {
		return 0.0
	}
	return (float64(c.CompletedTasks) / float64(c.TotalTasks)) * 100
}

// IsBlocked is the is_blocked property.
func (c DependencyChain) IsBlocked() bool { return c.BlockedTasks > 0 }

// NextTask is the next_task property: first todo task that is not blocked.
func (c DependencyChain) NextTask() *DependencyInfo {
	for i := range c.Tasks {
		t := &c.Tasks[i]
		if t.Status == "todo" && !t.IsBlocked {
			return t
		}
	}
	return nil
}

// DependencyRelationships is the complete dependency relationship information.
type DependencyRelationships struct {
	TaskID string

	DependsOn []DependencyInfo
	Blocks    []DependencyInfo

	UpstreamChains   []DependencyChain
	DownstreamChains []DependencyChain

	TotalDependencies     int
	CompletedDependencies int
	BlockedDependencies   int

	CanStart         bool
	IsBlocked        bool
	IsBlockingOthers bool

	DependencySummary string
	NextActions       []string
	BlockingReasons   []string
}

// NewDependencyRelationships mirrors __post_init__ (nil slices become []).
func NewDependencyRelationships(r DependencyRelationships) *DependencyRelationships {
	if r.DependsOn == nil {
		r.DependsOn = []DependencyInfo{}
	}
	if r.Blocks == nil {
		r.Blocks = []DependencyInfo{}
	}
	if r.UpstreamChains == nil {
		r.UpstreamChains = []DependencyChain{}
	}
	if r.DownstreamChains == nil {
		r.DownstreamChains = []DependencyChain{}
	}
	if r.NextActions == nil {
		r.NextActions = []string{}
	}
	if r.BlockingReasons == nil {
		r.BlockingReasons = []string{}
	}
	return &r
}

// DependencyCompletionPercentage is the dependency_completion_percentage property.
func (r DependencyRelationships) DependencyCompletionPercentage() float64 {
	if r.TotalDependencies == 0 {
		return 100.0
	}
	return (float64(r.CompletedDependencies) / float64(r.TotalDependencies)) * 100
}

// GetBlockingChainInfo is get_blocking_chain_info.
func (r DependencyRelationships) GetBlockingChainInfo() *entities.OrderedMap[any] {
	blockingTasks := []any{}
	for _, dep := range r.DependsOn {
		if dep.Status != "done" && dep.Status != "cancelled" {
			d := entities.NewOrderedMap[any]()
			d.Set("task_id", dep.TaskID)
			d.Set("title", dep.Title)
			d.Set("status", dep.Status)
			d.Set("priority", dep.Priority)
			blockingTasks = append(blockingTasks, d)
		}
	}
	blockingChains := []any{}
	for _, chain := range r.UpstreamChains {
		if chain.IsBlocked() || chain.ChainStatus != "completed" {
			var nextTitle any
			if nt := chain.NextTask(); nt != nil {
				nextTitle = nt.Title
			}
			d := entities.NewOrderedMap[any]()
			d.Set("chain_id", chain.ChainID)
			d.Set("status", chain.ChainStatus)
			d.Set("completion_percentage", chain.CompletionPercentage())
			d.Set("next_task", nextTitle)
			blockingChains = append(blockingChains, d)
		}
	}
	suggestions := []string{}
	if len(blockingTasks) > 0 {
		suggestions = append(suggestions, fmt.Sprintf("Complete %d blocking task(s)", len(blockingTasks)))
	}
	if len(blockingChains) > 0 {
		suggestions = append(suggestions, fmt.Sprintf("Resolve %d blocked chain(s)", len(blockingChains)))
	}
	m := entities.NewOrderedMap[any]()
	m.Set("is_blocked", r.IsBlocked)
	m.Set("blocking_tasks", blockingTasks)
	m.Set("blocking_chains", blockingChains)
	m.Set("resolution_suggestions", suggestions)
	return m
}

// GetWorkflowGuidance is get_workflow_guidance.
func (r DependencyRelationships) GetWorkflowGuidance() *entities.OrderedMap[any] {
	recommended := []string{}
	if r.CanStart {
		recommended = append(recommended, "Task is ready to start - no blocking dependencies")
	} else {
		recommended = append(recommended,
			fmt.Sprintf("Wait for %d dependencies to complete", len(r.DependsOn)),
			"Consider working on dependency tasks first",
			"Check if any dependencies can be parallelized",
		)
	}
	priority := []string{}
	if r.IsBlockingOthers {
		priority = append(priority, fmt.Sprintf("High priority - blocking %d other task(s)", len(r.Blocks)))
	}
	m := entities.NewOrderedMap[any]()
	m.Set("can_start_immediately", r.CanStart)
	m.Set("recommended_actions", recommended)
	m.Set("priority_suggestions", priority)
	m.Set("estimated_wait_time", nil)
	return m
}
