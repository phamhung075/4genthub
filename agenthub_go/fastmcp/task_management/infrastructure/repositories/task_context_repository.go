package repositories

// Task Context Repository (Python infrastructure/repositories/task_context_repository.py):
// persistence for the unified task-level context (task_contexts table). The Python entity
// keeps progress/insights/next_steps inside the task_data JSON column; they are moved in and
// out on write/read. Cache invalidation and logging are dropped.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TaskContextRepository is Python's TaskContextRepository.
type TaskContextRepository struct {
	*ORMRepository[database.TaskContext]
	UserID *string
}

// NewTaskContextRepository builds the repository.
func NewTaskContextRepository(sessions *database.SessionManager, userID *string) (*TaskContextRepository, error) {
	base, err := NewORMRepository[database.TaskContext]("task_contexts", sessions)
	if err != nil {
		return nil, err
	}
	return &TaskContextRepository{ORMRepository: base, UserID: userID}, nil
}

// WithUser returns a new instance scoped to userID.
func (r *TaskContextRepository) WithUser(userID string) *TaskContextRepository {
	return &TaskContextRepository{ORMRepository: r.ORMRepository, UserID: &userID}
}

// effectiveUserID is _get_effective_user_id.
func (r *TaskContextRepository) effectiveUserID(entity *entities.TaskContextUnified) (string, error) {
	if r.UserID != nil && *r.UserID != "" {
		return *r.UserID, nil
	}
	if entity.Metadata != nil {
		if v, ok := entity.Metadata["user_id"].(string); ok && v != "" {
			return v, nil
		}
	}
	return "", &tmvo.ValueError{Msg: "user_id is required for task context operations"}
}

// taskContextRepoTaskData moves progress/insights/next_steps into task_data.
func taskContextRepoTaskData(entity *entities.TaskContextUnified) map[string]any {
	taskData := entity.TaskData
	if taskData == nil {
		taskData = map[string]any{}
	}
	taskData["progress"] = entity.Progress
	taskData["insights"] = entity.Insights
	taskData["next_steps"] = entity.NextSteps
	return taskData
}

// taskContextRepoImplementationNotes is the column's one home on the write side: the entity's own field, with
// the same empty-map default the other context maps get. It used to be read out of entity.Metadata, which is
// how a service write and a repository read could pass each other without meeting.
func taskContextRepoImplementationNotes(notes map[string]any) map[string]any {
	if notes == nil {
		return map[string]any{}
	}
	return notes
}

func taskContextRepoMetadataValue(metadata map[string]any, key string, fallback any) any {
	if metadata != nil {
		if v, ok := metadata[key]; ok {
			return v
		}
	}
	return fallback
}

// Create inserts a new task context; an existing id raises ValueError.
func (r *TaskContextRepository) Create(ctx context.Context, entity *entities.TaskContextUnified) (*entities.TaskContextUnified, error) {
	var out *entities.TaskContextUnified
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		existing, err := r.ORMRepository.getByID(ctx, s, entity.ID)
		if err != nil {
			return err
		}
		if existing != nil {
			return &tmvo.ValueError{Msg: "Task context already exists: " + entity.ID}
		}
		userID, err := r.effectiveUserID(entity)
		if err != nil {
			return err
		}
		taskData := taskContextRepoTaskData(entity)
		kwargs := NewKwargs(
			"id", entity.ID,
			"task_id", entity.ID,
			"parent_branch_id", entity.BranchID,
			"parent_branch_context_id", entity.BranchID,
			"task_data", taskData,
			"local_overrides", taskContextRepoMetadataValue(entity.Metadata, "local_overrides", map[string]any{}),
			"implementation_notes", taskContextRepoImplementationNotes(entity.ImplementationNotes),
			"delegation_triggers", taskContextRepoMetadataValue(entity.Metadata, "delegation_triggers", map[string]any{}),
			"inheritance_disabled", taskContextRepoMetadataValue(entity.Metadata, "inheritance_disabled", false),
			"force_local_only", taskContextRepoMetadataValue(entity.Metadata, "force_local_only", false),
			"user_id", userID,
			"version", 1,
		)
		row, err := r.ORMRepository.insert(ctx, s, kwargs)
		if err != nil {
			return err
		}
		out = taskContextRepoToEntity(row)
		return nil
	})
	return out, err
}

// Get returns the task context by id (user-filtered), or nil.
func (r *TaskContextRepository) Get(ctx context.Context, contextID string) (*entities.TaskContextUnified, error) {
	var out *entities.TaskContextUnified
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		filters := NewKwargs("id", contextID)
		if r.UserID != nil && *r.UserID != "" {
			filters.Set("user_id", *r.UserID)
		}
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) > 0 {
			out = taskContextRepoToEntity(rows[0])
		}
		return nil
	})
	return out, err
}

// Update replaces the task context and bumps the version.
func (r *TaskContextRepository) Update(ctx context.Context, contextID string, entity *entities.TaskContextUnified) (*entities.TaskContextUnified, error) {
	var out *entities.TaskContextUnified
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return &tmvo.ValueError{Msg: "Task context not found: " + contextID}
		}
		taskData := taskContextRepoTaskData(entity)
		version := int64(1)
		if row.Version != nil {
			version = *row.Version + 1
		}
		userID := branchContextRepoFirstNonEmpty(r.UserID, branchContextRepoAnyString(taskContextRepoMetadataValue(entity.Metadata, "user_id", nil)), &row.UserID)
		values := NewKwargs(
			"parent_branch_id", entity.BranchID,
			"task_data", taskData,
			"local_overrides", taskContextRepoMetadataValue(entity.Metadata, "local_overrides", map[string]any{}),
			"implementation_notes", taskContextRepoImplementationNotes(entity.ImplementationNotes),
			"delegation_triggers", taskContextRepoMetadataValue(entity.Metadata, "delegation_triggers", map[string]any{}),
			"inheritance_disabled", taskContextRepoMetadataValue(entity.Metadata, "inheritance_disabled", false),
			"force_local_only", taskContextRepoMetadataValue(entity.Metadata, "force_local_only", false),
			"user_id", userID,
			"version", version,
		)
		updated, err := globalContextRepoUpdateReturning(r.ORMRepository, ctx, s, contextID, values)
		if err != nil {
			return err
		}
		out = taskContextRepoToEntity(updated)
		return nil
	})
	return out, err
}

// Delete removes the task context; a missing row is false.
func (r *TaskContextRepository) Delete(ctx context.Context, contextID string) (bool, error) {
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		pk := r.Table.Columns[r.byAttr[r.pkAttr]]
		bv, err := bind(pk, contextID)
		if err != nil {
			return err
		}
		res, err := s.ExecContext(ctx, "DELETE FROM "+quoteIdent(r.Table.Name)+" WHERE "+r.pkColumn()+" = $1", bv)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// List returns the task contexts; branch_id maps to parent_branch_id.
func (r *TaskContextRepository) List(ctx context.Context, filters Kwargs) ([]*entities.TaskContextUnified, error) {
	var out []*entities.TaskContextUnified
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		where := NewKwargs()
		if r.UserID != nil && *r.UserID != "" {
			where.Set("user_id", *r.UserID)
		}
		if filters != nil {
			if v, ok := filters.Get("branch_id"); ok {
				where.Set("parent_branch_id", v)
			}
			if v, ok := filters.Get("inheritance_disabled"); ok {
				where.Set("inheritance_disabled", v)
			}
		}
		w, args, err := r.where(where, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w, args...)
		if err != nil {
			return err
		}
		out = make([]*entities.TaskContextUnified, 0, len(rows))
		for _, row := range rows {
			out = append(out, taskContextRepoToEntity(row))
		}
		return nil
	})
	return out, err
}

// taskContextRepoToEntity is _to_entity.
func taskContextRepoToEntity(row *database.TaskContext) *entities.TaskContextUnified {
	taskData := globalContextRepoJSONMap(row.TaskData)

	progress := 0
	if v, ok := taskData["progress"]; ok {
		progress = taskContextRepoInt(v)
	}
	insights := []any{}
	if v, ok := taskData["insights"].([]any); ok {
		insights = v
	}
	nextSteps := []any{}
	if v, ok := taskData["next_steps"].([]any); ok {
		nextSteps = v
	}
	clean := map[string]any{}
	for k, v := range taskData {
		if k == "progress" || k == "insights" || k == "next_steps" {
			continue
		}
		clean[k] = v
	}

	id := ""
	if row.TaskID != nil {
		id = *row.TaskID
	}
	branchID := ""
	if row.ParentBranchID != nil {
		branchID = *row.ParentBranchID
	}

	localOverrides := globalContextRepoJSONMap(row.LocalOverrides)
	implementationNotes := globalContextRepoJSONMap(row.ImplementationNotes)
	delegationTriggers := globalContextRepoJSONMap(row.DelegationTriggers)
	// implementation_notes has ONE home: the entity's own field, written from and read into the column. It
	// used to travel through Metadata on both sides, which is how a write through the service and a read
	// through this repository could pass each other without ever meeting.
	metadata := map[string]any{
		"local_overrides":      localOverrides,
		"delegation_triggers":  delegationTriggers,
		"inheritance_disabled": row.InheritanceDisabled,
		"force_local_only":     row.ForceLocalOnly,
		"version":              row.Version,
		"created_at":           nil,
		"updated_at":           nil,
	}
	if row.CreatedAt != nil {
		metadata["created_at"] = tmvo.IsoFormatNaive(*row.CreatedAt)
	}
	if row.UpdatedAt != nil {
		metadata["updated_at"] = tmvo.IsoFormatNaive(*row.UpdatedAt)
	}
	return &entities.TaskContextUnified{
		ID: id, BranchID: branchID, TaskData: clean, Progress: progress,
		Insights: insights, NextSteps: nextSteps, Metadata: metadata,
		ImplementationNotes: implementationNotes,
	}
}

func taskContextRepoInt(v any) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return 0
}
