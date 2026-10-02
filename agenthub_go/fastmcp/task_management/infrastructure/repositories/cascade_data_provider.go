package repositories

// SQLAlchemy Cascade Data Provider (Python repositories/orm/cascade_data_provider.py):
// database access for cascade calculations, implementing
// domain/services/protocols.CascadeDataProvider.
//
// Python takes an AsyncSession; Go takes a SessionManager.

import (
	"context"
	"database/sql"
	"errors"

	"agenthub/fastmcp/task_management/domain/services/protocols"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// SQLAlchemyCascadeDataProvider is SQLAlchemyCascadeDataProvider.
type SQLAlchemyCascadeDataProvider struct {
	Sessions *database.SessionManager
}

// NewSQLAlchemyCascadeDataProvider builds the provider.
func NewSQLAlchemyCascadeDataProvider(sessions *database.SessionManager) *SQLAlchemyCascadeDataProvider {
	return &SQLAlchemyCascadeDataProvider{Sessions: sessions}
}

func (p *SQLAlchemyCascadeDataProvider) withSession(ctx context.Context, fn func(ctx context.Context, s database.DBTX) error) error {
	return p.Sessions.WithSession(ctx, fn)
}

// GetTaskCascadeData is get_task_cascade_data.
func (p *SQLAlchemyCascadeDataProvider) GetTaskCascadeData(ctx context.Context, taskID string) (*protocols.TaskCascadeData, error) {
	var out *protocols.TaskCascadeData
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var id, branchID, projectID string
		var contextID sql.NullString
		err := s.QueryRowContext(ctx,
			`SELECT t.id::text, t.git_branch_id::text, b.project_id::text, t.context_id::text
			 FROM tasks t JOIN project_git_branchs b ON t.git_branch_id = b.id
			 WHERE t.id = $1::uuid`, taskID).
			Scan(&id, &branchID, &projectID, &contextID)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		d := &protocols.TaskCascadeData{ID: id, GitBranchID: branchID, ProjectID: projectID}
		if contextID.Valid {
			c := contextID.String
			d.ContextID = &c
		}
		out = d
		return nil
	})
	return out, err
}

// GetTaskSubtaskIDs is get_task_subtask_ids.
func (p *SQLAlchemyCascadeDataProvider) GetTaskSubtaskIDs(ctx context.Context, taskID string) ([]string, error) {
	out := []string{}
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `SELECT id::text FROM subtasks WHERE task_id = $1::uuid`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var id string
			if err := rows.Scan(&id); err != nil {
				return err
			}
			out = append(out, id)
		}
		return rows.Err()
	})
	return out, err
}

// GetTaskParentTaskIDs is get_task_parent_task_ids. Python's raw SQL references
// task_dependencies.dependency_id, a column that does not exist, so the query always
// fails (the defect is preserved).
func (p *SQLAlchemyCascadeDataProvider) GetTaskParentTaskIDs(ctx context.Context, taskID string) ([]string, error) {
	out := []string{}
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT DISTINCT td.task_id FROM task_dependencies td WHERE td.dependency_id = $1`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var id string
			if err := rows.Scan(&id); err != nil {
				return err
			}
			out = append(out, id)
		}
		return rows.Err()
	})
	return out, err
}

// GetSubtaskCascadeData is get_subtask_cascade_data.
func (p *SQLAlchemyCascadeDataProvider) GetSubtaskCascadeData(ctx context.Context, subtaskID string) (*protocols.SubtaskCascadeData, error) {
	var out *protocols.SubtaskCascadeData
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var id, taskID, branchID, projectID string
		var contextID sql.NullString
		err := s.QueryRowContext(ctx,
			`SELECT s.id::text, s.task_id::text, t.git_branch_id::text, b.project_id::text, t.context_id::text
			 FROM subtasks s
			 JOIN tasks t ON s.task_id = t.id
			 JOIN project_git_branchs b ON t.git_branch_id = b.id
			 WHERE s.id = $1::uuid`, subtaskID).
			Scan(&id, &taskID, &branchID, &projectID, &contextID)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		d := &protocols.SubtaskCascadeData{ID: id, TaskID: taskID, GitBranchID: branchID, ProjectID: projectID}
		if contextID.Valid {
			c := contextID.String
			d.ContextID = &c
		}
		out = d
		return nil
	})
	return out, err
}

// GetBranchCascadeData is get_branch_cascade_data.
func (p *SQLAlchemyCascadeDataProvider) GetBranchCascadeData(ctx context.Context, branchID string) (*protocols.BranchCascadeData, error) {
	var out *protocols.BranchCascadeData
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT DISTINCT b.id::text, b.project_id::text, t.id::text, s.id::text
			 FROM project_git_branchs b
			 LEFT JOIN tasks t ON t.git_branch_id = b.id
			 LEFT JOIN subtasks s ON s.task_id = t.id
			 WHERE b.id = $1::uuid`, branchID)
		if err != nil {
			return err
		}
		defer rows.Close()
		var d *protocols.BranchCascadeData
		for rows.Next() {
			var id, projectID string
			var taskID, subtaskID sql.NullString
			if err := rows.Scan(&id, &projectID, &taskID, &subtaskID); err != nil {
				return err
			}
			if d == nil {
				d = &protocols.BranchCascadeData{ID: id, ProjectID: projectID}
			}
			if taskID.Valid {
				d.TaskIDs.Add(taskID.String)
			}
			if subtaskID.Valid {
				d.SubtaskIDs.Add(subtaskID.String)
			}
		}
		if err := rows.Err(); err != nil {
			return err
		}
		out = d
		return nil
	})
	return out, err
}

// GetProjectCascadeData is get_project_cascade_data.
func (p *SQLAlchemyCascadeDataProvider) GetProjectCascadeData(ctx context.Context, projectID string) (*protocols.ProjectCascadeData, error) {
	var out *protocols.ProjectCascadeData
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT DISTINCT b.id::text, t.id::text, s.id::text
			 FROM project_git_branchs b
			 LEFT JOIN tasks t ON t.git_branch_id = b.id
			 LEFT JOIN subtasks s ON s.task_id = t.id
			 WHERE b.project_id = $1::uuid`, projectID)
		if err != nil {
			return err
		}
		defer rows.Close()
		var d *protocols.ProjectCascadeData
		for rows.Next() {
			var branchID sql.NullString
			var taskID, subtaskID sql.NullString
			if err := rows.Scan(&branchID, &taskID, &subtaskID); err != nil {
				return err
			}
			if d == nil {
				d = &protocols.ProjectCascadeData{ID: projectID}
			}
			if branchID.Valid {
				d.BranchIDs.Add(branchID.String)
			}
			if taskID.Valid {
				d.TaskIDs.Add(taskID.String)
			}
			if subtaskID.Valid {
				d.SubtaskIDs.Add(subtaskID.String)
			}
		}
		if err := rows.Err(); err != nil {
			return err
		}
		out = d
		return nil
	})
	return out, err
}

// GetContextCascadeData is get_context_cascade_data.
func (p *SQLAlchemyCascadeDataProvider) GetContextCascadeData(ctx context.Context, contextID string) (*protocols.ContextCascadeData, error) {
	var out *protocols.ContextCascadeData
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT DISTINCT t.id::text, t.git_branch_id::text, b.project_id::text, s.id::text
			 FROM tasks t
			 JOIN project_git_branchs b ON t.git_branch_id = b.id
			 LEFT JOIN subtasks s ON s.task_id = t.id
			 WHERE t.context_id = $1::uuid`, contextID)
		if err != nil {
			return err
		}
		defer rows.Close()
		var d *protocols.ContextCascadeData
		for rows.Next() {
			var taskID, branchID, projectID string
			var subtaskID sql.NullString
			if err := rows.Scan(&taskID, &branchID, &projectID, &subtaskID); err != nil {
				return err
			}
			if d == nil {
				d = &protocols.ContextCascadeData{ID: contextID}
			}
			d.TaskIDs.Add(taskID)
			d.BranchIDs.Add(branchID)
			d.ProjectIDs.Add(projectID)
			if subtaskID.Valid {
				d.SubtaskIDs.Add(subtaskID.String)
			}
		}
		if err := rows.Err(); err != nil {
			return err
		}
		out = d
		return nil
	})
	return out, err
}

// GetRelatedContextIDs is get_related_context_ids; project_id is unused (Python ignores
// it) and any error returns an empty set.
func (p *SQLAlchemyCascadeDataProvider) GetRelatedContextIDs(ctx context.Context, branchID, projectID string) ([]string, error) {
	_ = projectID
	out := []string{}
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT DISTINCT context_id::text FROM tasks t WHERE t.git_branch_id = $1::uuid AND context_id IS NOT NULL`, branchID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var id string
			if err := rows.Scan(&id); err != nil {
				return err
			}
			out = append(out, id)
		}
		return rows.Err()
	})
	if err != nil {
		return []string{}, nil
	}
	return out, nil
}

// DetectEntityType is detect_entity_type; it defaults to context when no table matches.
func (p *SQLAlchemyCascadeDataProvider) DetectEntityType(ctx context.Context, entityID string) (*protocols.EntityType, error) {
	var kind protocols.EntityType
	err := p.withSession(ctx, func(ctx context.Context, s database.DBTX) error {
		checks := []struct {
			table string
			value protocols.EntityType
		}{
			{"tasks", protocols.EntityTypeTask},
			{"subtasks", protocols.EntityTypeSubtask},
			{"project_git_branchs", protocols.EntityTypeBranch},
			{"projects", protocols.EntityTypeProject},
		}
		for _, c := range checks {
			var n int
			if err := s.QueryRowContext(ctx, `SELECT COUNT(*) FROM `+quoteIdent(c.table)+` WHERE id = $1::uuid`, entityID).Scan(&n); err != nil {
				return err
			}
			if n > 0 {
				kind = c.value
				return nil
			}
		}
		kind = protocols.EntityTypeContext
		return nil
	})
	if err != nil {
		return nil, err
	}
	return &kind, nil
}
