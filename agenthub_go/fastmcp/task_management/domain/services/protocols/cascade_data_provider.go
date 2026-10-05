// Package protocols ports task_management/domain/services/protocols.
package protocols

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// EntityType is the supported entity types for cascade calculation. Python defines
// it in cascade_calculator.py, which this module imports while the calculator only
// imports this module for typing; Go forbids that cycle across packages, so the type
// is declared here and cascade_calculator.go re-exports it as an alias.
type EntityType string

const (
	EntityTypeTask    EntityType = "task"
	EntityTypeSubtask EntityType = "subtask"
	EntityTypeBranch  EntityType = "branch"
	EntityTypeProject EntityType = "project"
	EntityTypeContext EntityType = "context"
)

// EntityTypeValues lists the entity types in declaration order.
var EntityTypeValues = []EntityType{EntityTypeTask, EntityTypeSubtask, EntityTypeBranch, EntityTypeProject, EntityTypeContext}

// TaskCascadeData is the DTO for task cascade information (ContextID nil = None).
type TaskCascadeData struct {
	ID          string
	GitBranchID string
	ProjectID   string
	ContextID   *string
}

// SubtaskCascadeData is the DTO for subtask cascade information.
type SubtaskCascadeData struct {
	ID          string
	TaskID      string
	GitBranchID string
	ProjectID   string
	ContextID   *string
}

// BranchCascadeData is the DTO for branch cascade information.
type BranchCascadeData struct {
	ID         string
	ProjectID  string
	TaskIDs    entities.StringSet
	SubtaskIDs entities.StringSet
}

// ProjectCascadeData is the DTO for project cascade information.
type ProjectCascadeData struct {
	ID         string
	BranchIDs  entities.StringSet
	TaskIDs    entities.StringSet
	SubtaskIDs entities.StringSet
}

// ContextCascadeData is the DTO for context cascade information.
type ContextCascadeData struct {
	ID         string
	TaskIDs    entities.StringSet
	BranchIDs  entities.StringSet
	ProjectIDs entities.StringSet
	SubtaskIDs entities.StringSet
}

// CascadeDataProvider is the data access protocol for cascade calculations. The
// Get*CascadeData and DetectEntityType methods return nil when the entity does not
// exist; set-returning methods return empty slices when there is nothing.
type CascadeDataProvider interface {
	GetTaskCascadeData(ctx context.Context, taskID string) (*TaskCascadeData, error)
	GetTaskSubtaskIDs(ctx context.Context, taskID string) ([]string, error)
	GetTaskParentTaskIDs(ctx context.Context, taskID string) ([]string, error)
	GetSubtaskCascadeData(ctx context.Context, subtaskID string) (*SubtaskCascadeData, error)
	GetBranchCascadeData(ctx context.Context, branchID string) (*BranchCascadeData, error)
	GetProjectCascadeData(ctx context.Context, projectID string) (*ProjectCascadeData, error)
	GetContextCascadeData(ctx context.Context, contextID string) (*ContextCascadeData, error)
	GetRelatedContextIDs(ctx context.Context, branchID, projectID string) ([]string, error)
	DetectEntityType(ctx context.Context, entityID string) (*EntityType, error)
}
