package repositories

// ORM Git Branch Repository (Python
// infrastructure/repositories/orm/git_branch_repository.py): SQLAlchemy-backed git branch
// persistence over database/sql + pgx. Logging is dropped; the performance optimizer is only
// stored on the Python instance and is never used, so the performance mode flag is kept but
// not wired to anything.
//
// The synchronous convenience methods used by the branch statistics service (get, update,
// find_by_project_id, get_all) keep Python's attribute-object shape through
// gitBranchRepoBranch and therefore use a background context instead of a caller context.

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/exceptions"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ORMGitBranchRepository is Python's ORMGitBranchRepository. It embeds the timestamp-aware
// generic repository and keeps Python's manual user_id filtering (it is not a
// UserScopedORMRepository).
type ORMGitBranchRepository struct {
	*BaseTimestampRepository[database.ProjectGitBranch]
	UserScope

	gitBranchRepoProjects *ORMRepository[database.Project]
	gitBranchRepoTasks    *ORMRepository[database.Task]

	// PerformanceMode mirrors Python's performance_mode. The optimizer is unused.
	PerformanceMode bool
}

// Assert the domain interface is implemented.
var _ domainrepos.GitBranchRepository = (*ORMGitBranchRepository)(nil)

// Assert the branch statistics service protocol is implemented.
var _ services.GitBranchRepositoryProtocol = (*ORMGitBranchRepository)(nil)

// gitBranchRepoBranch is the ad-hoc attribute object Python returns from get /
// find_by_project_id / get_all.
type gitBranchRepoBranch struct {
	ID                 string
	ProjectID          string
	TaskCount          int
	CompletedTaskCount int
}

func (b *gitBranchRepoBranch) BranchID() string { return b.ID }

// NewORMGitBranchRepository builds the repository. userID nil means system mode.
func NewORMGitBranchRepository(sessions *database.SessionManager, userID *string, performanceMode bool) (*ORMGitBranchRepository, error) {
	base_, err := NewBaseTimestampRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		return nil, err
	}
	projects, err := NewORMRepository[database.Project]("projects", sessions)
	if err != nil {
		return nil, err
	}
	tasks, err := NewORMRepository[database.Task]("tasks", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMGitBranchRepository{
		BaseTimestampRepository: base_,
		UserScope:               NewUserScope(userID),
		gitBranchRepoProjects:   projects,
		gitBranchRepoTasks:      tasks,
		PerformanceMode:         performanceMode,
	}, nil
}

// WithUser returns a new repository scoped to userID (with_user).
func (r *ORMGitBranchRepository) WithUser(userID string) (*ORMGitBranchRepository, error) {
	return NewORMGitBranchRepository(r.Sessions, &userID, r.PerformanceMode)
}

// ---- helpers --------------------------------------------------------------------

func (r *ORMGitBranchRepository) gitBranchRepoHasUser() bool {
	return r.UserID != nil && *r.UserID != ""
}

// gitBranchRepoEntityToModelDict is _entity_to_model_dict.
func (r *ORMGitBranchRepository) gitBranchRepoEntityToModelDict(gb *entities.GitBranch) (Kwargs, error) {
	if !r.gitBranchRepoHasUser() {
		return nil, &tmvo.ValueError{Msg: "user_id is required for git branch operations"}
	}
	id := ""
	if gb.ID != nil {
		id = gb.ID.Value
	}
	priority := "medium"
	if gb.Priority != nil {
		priority = gb.Priority.Value
	}
	status := "todo"
	if gb.Status != nil {
		status = gb.Status.Value
	}
	return NewKwargs(
		"id", id,
		"project_id", gb.ProjectID,
		"name", gb.Name,
		"description", gb.Description,
		"created_at", gb.CreatedAt,
		"updated_at", gb.UpdatedAt,
		"assigned_agent_id", gb.AssignedAgentID,
		"priority", priority,
		"status", status,
		"task_count", gb.GetTaskCount(),
		"completed_task_count", gb.GetCompletedTaskCount(),
		"user_id", *r.UserID,
		"model_metadata", json.RawMessage("{}"),
	), nil
}

// gitBranchRepoModelToEntity is _model_to_entity. As in Python it loads every task of the
// branch (regardless of owner) into all_tasks.
func (r *ORMGitBranchRepository) gitBranchRepoModelToEntity(ctx context.Context, s database.DBTX, model *database.ProjectGitBranch) (*entities.GitBranch, error) {
	var id *tmvo.GitBranchId
	if model.ID != "" {
		v, err := tmvo.NewGitBranchId(model.ID)
		if err != nil {
			return nil, err
		}
		id = &v
	}
	created, updated := model.CreatedAt, model.UpdatedAt
	gb, err := entities.NewGitBranch(entities.GitBranch{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &updated},
		ID:                  id,
		Name:                model.Name,
		Description:         model.Description,
		ProjectID:           model.ProjectID,
	})
	if err != nil {
		return nil, err
	}
	gb.AssignedAgentID = model.AssignedAgentID
	priority, err := tmvo.PriorityFromString(model.Priority)
	if err != nil {
		return nil, err
	}
	gb.Priority = &priority
	status, err := tmvo.TaskStatusFromString(model.Status)
	if err != nil {
		return nil, err
	}
	gb.Status = &status

	w, args, err := r.gitBranchRepoTasks.where(NewKwargs("git_branch_id", model.ID), 1)
	if err != nil {
		return nil, err
	}
	tasks, err := r.gitBranchRepoTasks.selectRows(ctx, s, w, args...)
	if err != nil {
		return nil, err
	}
	for _, t := range tasks {
		taskID := tmvo.TaskId{EntityId: tmvo.EntityId{Value: t.ID}}
		st, err := tmvo.TaskStatusFromString(t.Status)
		if err != nil {
			return nil, err
		}
		pr, err := tmvo.PriorityFromString(t.Priority)
		if err != nil {
			return nil, err
		}
		gb.AllTasks.Set(t.ID, &entities.Task{ID: &taskID, Status: &st, Priority: &pr, Title: t.Title})
	}
	return gb, nil
}

// gitBranchRepoModelToEntityRow converts one row (find_by_id / find_by_name).
func (r *ORMGitBranchRepository) gitBranchRepoModelToEntityRow(ctx context.Context, s database.DBTX, rows []*database.ProjectGitBranch) (*entities.GitBranch, error) {
	if len(rows) == 0 {
		return nil, nil
	}
	return r.gitBranchRepoModelToEntity(ctx, s, rows[0])
}

// gitBranchRepoModelToEntities is the per-row conversion used by the list finders, which skip
// rows whose conversion fails (Python: except Exception -> continue).
func (r *ORMGitBranchRepository) gitBranchRepoModelToEntities(ctx context.Context, s database.DBTX, rows []*database.ProjectGitBranch) []*entities.GitBranch {
	out := []*entities.GitBranch{}
	for _, row := range rows {
		ent, err := r.gitBranchRepoModelToEntity(ctx, s, row)
		if err != nil {
			continue
		}
		out = append(out, ent)
	}
	return out
}

// gitBranchRepoUpdateAll updates every model_data field except id/project_id/created_at.
func (r *ORMGitBranchRepository) gitBranchRepoUpdateAll(ctx context.Context, s database.DBTX, id string, data Kwargs) error {
	var sets []string
	var args []any
	for _, attr := range data.Keys() {
		if attr == "id" || attr == "project_id" || attr == "created_at" {
			continue
		}
		pos, ok := r.byAttr[attr]
		if !ok {
			continue
		}
		c := r.Table.Columns[pos]
		v, _ := data.Get(attr)
		var bv any
		if v != nil {
			var err error
			bv, err = bind(c, v)
			if err != nil {
				return err
			}
		}
		args = append(args, bv)
		sets = append(sets, quoteIdent(c.Name)+fmt.Sprintf(" = $%d", len(args)))
	}
	args = append(args, id)
	q := fmt.Sprintf("UPDATE %s SET %s WHERE %s = $%d", quoteIdent(r.Table.Name), strings.Join(sets, ", "), r.pkColumn(), len(args))
	_, err := s.ExecContext(ctx, q, args...)
	return err
}

// gitBranchRepoSelectIDs selects the id::text of rows of table matching valueCol=value
// (optionally user-scoped).
func (r *ORMGitBranchRepository) gitBranchRepoSelectIDs(ctx context.Context, s database.DBTX, table, valueCol, idCol, value string, userScoped bool) ([]string, error) {
	args := []any{value}
	conds := []string{quoteIdent(valueCol) + " = $1"}
	if userScoped && r.gitBranchRepoHasUser() {
		args = append(args, *r.UserID)
		conds = append(conds, quoteIdent("user_id")+fmt.Sprintf(" = $%d", len(args)))
	}
	q := "SELECT " + quoteIdent(idCol) + "::text FROM " + quoteIdent(table) + " WHERE " + strings.Join(conds, " AND ")
	rows, err := s.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		out = append(out, id)
	}
	return out, rows.Err()
}

// gitBranchRepoInArgs appends ids to args and returns `col IN ($n, ...)`.
func gitBranchRepoInArgs(col string, ids []string, args *[]any) string {
	holders := make([]string, len(ids))
	for i, id := range ids {
		*args = append(*args, id)
		holders[i] = fmt.Sprintf("$%d", len(*args))
	}
	return quoteIdent(col) + " IN (" + strings.Join(holders, ", ") + ")"
}

func (r *ORMGitBranchRepository) gitBranchRepoUserCond(conds []string, args []any) ([]string, []any) {
	if r.gitBranchRepoHasUser() {
		args = append(args, *r.UserID)
		conds = append(conds, quoteIdent("user_id")+fmt.Sprintf(" = $%d", len(args)))
	}
	return conds, args
}

func gitBranchRepoDelete(ctx context.Context, s database.DBTX, table string, conds []string, args []any) error {
	q := "DELETE FROM " + quoteIdent(table)
	if len(conds) > 0 {
		q += " WHERE " + strings.Join(conds, " AND ")
	}
	_, err := s.ExecContext(ctx, q, args...)
	return err
}

type gitBranchRepoTaskCounts struct {
	total     int
	completed int
}

func (r *ORMGitBranchRepository) gitBranchRepoTaskCounts(ctx context.Context, s database.DBTX, branchID string) (gitBranchRepoTaskCounts, error) {
	var total, completed int
	q := `SELECT count("id"), count(CASE WHEN "status" = 'done' THEN "id" END) FROM "tasks" WHERE "git_branch_id" = $1`
	err := s.QueryRowContext(ctx, q, branchID).Scan(&total, &completed)
	return gitBranchRepoTaskCounts{total: total, completed: completed}, err
}

// ---- save / update --------------------------------------------------------------

// Save is save: it updates an existing branch (by id+project_id) or inserts a new one.
func (r *ORMGitBranchRepository) Save(ctx context.Context, gb *entities.GitBranch) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		id := ""
		if gb.ID != nil {
			id = gb.ID.Value
		}
		var idFilter any
		if id != "" {
			idFilter = id
		}
		w, args, err := r.where(NewKwargs("id", idFilter, "project_id", gb.ProjectID), 1)
		if err != nil {
			return err
		}
		existing, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		data, err := r.gitBranchRepoEntityToModelDict(gb)
		if err != nil {
			return err
		}
		if len(existing) > 0 {
			data.Set("updated_at", database.TimestampNow().UTC())
			return r.gitBranchRepoUpdateAll(ctx, s, id, data)
		}
		_, err = r.insert(ctx, s, data)
		return err
	})
}

// UpdateDomain is update_domain.
func (r *ORMGitBranchRepository) UpdateDomain(ctx context.Context, gb *entities.GitBranch) error {
	if err := gb.Touch("git_branch_manual_update"); err != nil {
		return err
	}
	return r.Save(ctx, gb)
}

// ---- reads ----------------------------------------------------------------------

// FindByID is find_by_id (user filtered; projectID nil/empty means any project).
func (r *ORMGitBranchRepository) FindByID(ctx context.Context, branchID string, projectID *string) (*entities.GitBranch, error) {
	if !r.gitBranchRepoHasUser() {
		return nil, &tmvo.ValueError{Msg: "User authentication required for branch operations"}
	}
	var out *entities.GitBranch
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		filters := NewKwargs("id", branchID, "user_id", *r.UserID)
		if projectID != nil && *projectID != "" {
			filters.Set("project_id", *projectID)
		}
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		out, err = r.gitBranchRepoModelToEntityRow(ctx, s, rows)
		return err
	})
	return out, err
}

// FindByName is find_by_name (no user filter).
func (r *ORMGitBranchRepository) FindByName(ctx context.Context, projectID, branchName string) (*entities.GitBranch, error) {
	var out *entities.GitBranch
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("name", branchName, "project_id", projectID), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		out, err = r.gitBranchRepoModelToEntityRow(ctx, s, rows)
		return err
	})
	return out, err
}

// FindAllByProject is find_all_by_project (user filtered, created_at desc).
func (r *ORMGitBranchRepository) FindAllByProject(ctx context.Context, projectID string) ([]*entities.GitBranch, error) {
	if !r.gitBranchRepoHasUser() {
		return nil, &tmvo.ValueError{Msg: "User authentication required for branch operations"}
	}
	out := []*entities.GitBranch{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("project_id", projectID, "user_id", *r.UserID), 1)
		if err != nil {
			return err
		}
		w += ` ORDER BY ` + quoteIdent("created_at") + ` DESC`
		rows, err := r.selectRows(ctx, s, w, args...)
		if err != nil {
			return err
		}
		out = r.gitBranchRepoModelToEntities(ctx, s, rows)
		return nil
	})
	return out, err
}

// FindAll is find_all (no user filter, created_at desc).
func (r *ORMGitBranchRepository) FindAll(ctx context.Context) ([]*entities.GitBranch, error) {
	out := []*entities.GitBranch{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, ` ORDER BY `+quoteIdent("created_at")+` DESC`)
		if err != nil {
			return err
		}
		out = r.gitBranchRepoModelToEntities(ctx, s, rows)
		return nil
	})
	return out, err
}

// DeleteBranch is delete_branch: a comprehensive cascade delete of everything that references
// the branch, then the branch itself.
func (r *ORMGitBranchRepository) DeleteBranch(ctx context.Context, branchID string) (bool, error) {
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		if r.gitBranchRepoHasUser() {
			branch, err := r.getByID(ctx, s, branchID)
			if err != nil {
				return err
			}
			if branch == nil {
				return nil
			}
			w, args, err := r.gitBranchRepoProjects.where(NewKwargs("id", branch.ProjectID, "user_id", *r.UserID), 1)
			if err != nil {
				return err
			}
			projects, err := r.gitBranchRepoProjects.selectRows(ctx, s, w+" LIMIT 1", args...)
			if err != nil {
				return err
			}
			if len(projects) == 0 {
				return nil
			}
		}

		// Step 1: ContextInheritanceCache for this branch.
		cacheConds := []string{quoteIdent("context_id") + " = $1", quoteIdent("context_level") + " = 'branch'"}
		cacheArgs := []any{branchID}
		cacheConds, cacheArgs = r.gitBranchRepoUserCond(cacheConds, cacheArgs)
		if err := gitBranchRepoDelete(ctx, s, "context_inheritance_cache", cacheConds, cacheArgs); err != nil {
			return err
		}

		// Step 2: ContextDelegation where this branch is source or target.
		delArgs := []any{branchID}
		c1 := "(" + quoteIdent("source_id") + " = $1 AND " + quoteIdent("source_level") + " = 'branch')"
		c2 := "(" + quoteIdent("target_id") + " = $1 AND " + quoteIdent("target_level") + " = 'branch')"
		delConds := []string{"(" + c1 + " OR " + c2 + ")"}
		delConds, delArgs = r.gitBranchRepoUserCond(delConds, delArgs)
		if err := gitBranchRepoDelete(ctx, s, "context_delegations", delConds, delArgs); err != nil {
			return err
		}

		// Step 3: BranchContext ids for this branch.
		branchContextIDs, err := r.gitBranchRepoSelectIDs(ctx, s, "branch_contexts", "branch_id", "id", branchID, true)
		if err != nil {
			return err
		}

		// Step 4: Task ids for this branch.
		taskIDs, err := r.gitBranchRepoSelectIDs(ctx, s, "tasks", "git_branch_id", "id", branchID, true)
		if err != nil {
			return err
		}

		if len(taskIDs) > 0 {
			// Step 5: Subtask records.
			args := []any{}
			conds := []string{gitBranchRepoInArgs("task_id", taskIDs, &args)}
			conds, args = r.gitBranchRepoUserCond(conds, args)
			if err := gitBranchRepoDelete(ctx, s, "subtasks", conds, args); err != nil {
				return err
			}

			// Step 6: TaskAssignee records.
			args = []any{}
			conds = []string{gitBranchRepoInArgs("task_id", taskIDs, &args)}
			conds, args = r.gitBranchRepoUserCond(conds, args)
			if err := gitBranchRepoDelete(ctx, s, "task_assignees", conds, args); err != nil {
				return err
			}

			// Step 7: TaskLabel records.
			args = []any{}
			conds = []string{gitBranchRepoInArgs("task_id", taskIDs, &args)}
			conds, args = r.gitBranchRepoUserCond(conds, args)
			if err := gitBranchRepoDelete(ctx, s, "task_labels", conds, args); err != nil {
				return err
			}

			// Step 8: TaskDependency records (both directions).
			args = []any{}
			cond := "(" + gitBranchRepoInArgs("task_id", taskIDs, &args) + " OR " + gitBranchRepoInArgs("depends_on_task_id", taskIDs, &args) + ")"
			conds = []string{cond}
			conds, args = r.gitBranchRepoUserCond(conds, args)
			if err := gitBranchRepoDelete(ctx, s, "task_dependencies", conds, args); err != nil {
				return err
			}
		}

		// Step 9: TaskContext records referencing this branch directly.
		tcArgs := []any{branchID}
		tcConds := []string{quoteIdent("parent_branch_id") + " = $1"}
		tcConds, tcArgs = r.gitBranchRepoUserCond(tcConds, tcArgs)
		if err := gitBranchRepoDelete(ctx, s, "task_contexts", tcConds, tcArgs); err != nil {
			return err
		}

		// Step 10: TaskContext records referencing this branch's BranchContexts.
		if len(branchContextIDs) > 0 {
			args := []any{}
			conds := []string{gitBranchRepoInArgs("parent_branch_context_id", branchContextIDs, &args)}
			conds, args = r.gitBranchRepoUserCond(conds, args)
			if err := gitBranchRepoDelete(ctx, s, "task_contexts", conds, args); err != nil {
				return err
			}
		}

		// Step 11: Task records for this branch.
		tArgs := []any{branchID}
		tConds := []string{quoteIdent("git_branch_id") + " = $1"}
		tConds, tArgs = r.gitBranchRepoUserCond(tConds, tArgs)
		if err := gitBranchRepoDelete(ctx, s, "tasks", tConds, tArgs); err != nil {
			return err
		}

		// Step 12: BranchContext records for this branch.
		bcArgs := []any{branchID}
		bcConds := []string{quoteIdent("branch_id") + " = $1"}
		bcConds, bcArgs = r.gitBranchRepoUserCond(bcConds, bcArgs)
		if err := gitBranchRepoDelete(ctx, s, "branch_contexts", bcConds, bcArgs); err != nil {
			return err
		}

		// Step 13: the branch itself (no user filter: project ownership was verified).
		res, err := s.ExecContext(ctx, "DELETE FROM "+quoteIdent(r.Table.Name)+" WHERE "+r.pkColumn()+" = $1", branchID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// Delete is delete (project-ownership check, branch user_id not checked).
func (r *ORMGitBranchRepository) Delete(ctx context.Context, projectID, branchID string) (bool, error) {
	if !r.gitBranchRepoHasUser() {
		return false, &tmvo.ValueError{Msg: "User authentication required for branch operations"}
	}
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.gitBranchRepoProjects.where(NewKwargs("id", projectID, "user_id", *r.UserID), 1)
		if err != nil {
			return err
		}
		projects, err := r.gitBranchRepoProjects.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(projects) == 0 {
			return nil
		}
		res, err := s.ExecContext(ctx, "DELETE FROM "+quoteIdent(r.Table.Name)+" WHERE "+quoteIdent("id")+" = $1 AND "+quoteIdent("project_id")+" = $2", branchID, projectID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// Exists is exists (no user filter).
func (r *ORMGitBranchRepository) Exists(ctx context.Context, projectID, branchID string) (bool, error) {
	exists := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("id", branchID, "project_id", projectID), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		exists = len(rows) > 0
		return nil
	})
	return exists, err
}

// CountByProject is count_by_project (no user filter).
func (r *ORMGitBranchRepository) CountByProject(ctx context.Context, projectID string) (int, error) {
	return r.ORMRepository.Count(ctx, NewKwargs("project_id", projectID))
}

// CountAll is count_all.
func (r *ORMGitBranchRepository) CountAll(ctx context.Context) (int, error) {
	return r.ORMRepository.Count(ctx, NewKwargs())
}

// FindByAssignedAgent is find_by_assigned_agent (no user filter, created_at desc).
func (r *ORMGitBranchRepository) FindByAssignedAgent(ctx context.Context, agentID string) ([]*entities.GitBranch, error) {
	out := []*entities.GitBranch{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("assigned_agent_id", agentID), 1)
		if err != nil {
			return err
		}
		w += ` ORDER BY ` + quoteIdent("created_at") + ` DESC`
		rows, err := r.selectRows(ctx, s, w, args...)
		if err != nil {
			return err
		}
		out = r.gitBranchRepoModelToEntities(ctx, s, rows)
		return nil
	})
	return out, err
}

// FindByStatus is find_by_status (no user filter, created_at desc).
func (r *ORMGitBranchRepository) FindByStatus(ctx context.Context, projectID, status string) ([]*entities.GitBranch, error) {
	out := []*entities.GitBranch{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("project_id", projectID, "status", status), 1)
		if err != nil {
			return err
		}
		w += ` ORDER BY ` + quoteIdent("created_at") + ` DESC`
		rows, err := r.selectRows(ctx, s, w, args...)
		if err != nil {
			return err
		}
		out = r.gitBranchRepoModelToEntities(ctx, s, rows)
		return nil
	})
	return out, err
}

// FindAvailableForAssignment is find_available_for_assignment (no user filter).
func (r *ORMGitBranchRepository) FindAvailableForAssignment(ctx context.Context, projectID string) ([]*entities.GitBranch, error) {
	out := []*entities.GitBranch{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{projectID}
		q := "SELECT " + r.selectList() + " FROM " + quoteIdent(r.Table.Name) +
			" WHERE " + quoteIdent("project_id") + "::text = $1::text AND " + quoteIdent("assigned_agent_id") + " IS NULL AND " +
			quoteIdent("status") + " IN ('todo', 'in_progress', 'review')" +
			" ORDER BY " + quoteIdent("priority") + " DESC, " + quoteIdent("created_at") + " ASC"
		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		var raw []*database.ProjectGitBranch
		for rows.Next() {
			row := r.newRow()
			if err := rows.Scan(r.scanDest(row)...); err != nil {
				return err
			}
			raw = append(raw, row)
		}
		if err := rows.Err(); err != nil {
			return err
		}
		out = r.gitBranchRepoModelToEntities(ctx, s, raw)
		return nil
	})
	return out, err
}

// ---- agent assignment -----------------------------------------------------------

// AssignAgent is assign_agent (no user filter, no updated_at change).
func (r *ORMGitBranchRepository) AssignAgent(ctx context.Context, projectID, branchID, agentID string) (bool, error) {
	return r.gitBranchRepoBulkSetAgent(ctx, projectID, branchID, &agentID)
}

// UnassignAgent is unassign_agent.
func (r *ORMGitBranchRepository) UnassignAgent(ctx context.Context, projectID, branchID string) (bool, error) {
	return r.gitBranchRepoBulkSetAgent(ctx, projectID, branchID, nil)
}

func (r *ORMGitBranchRepository) gitBranchRepoBulkSetAgent(ctx context.Context, projectID, branchID string, agentID *string) (bool, error) {
	updated := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var bv any
		if agentID != nil {
			bv = *agentID
		}
		res, err := s.ExecContext(ctx, "UPDATE "+quoteIdent(r.Table.Name)+" SET "+quoteIdent("assigned_agent_id")+" = $1 WHERE "+
			quoteIdent("id")+" = $2 AND "+quoteIdent("project_id")+" = $3", bv, branchID, projectID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		updated = n > 0
		return nil
	})
	return updated, err
}

// ---- project branch summary -----------------------------------------------------

// GetProjectBranchSummary is get_project_branch_summary (no user filter).
func (r *ORMGitBranchRepository) GetProjectBranchSummary(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	out := entities.NewOrderedMap[any]()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var totalBranches int
		var completedBranches, activeBranches, assignedBranches sql.NullInt64
		var totalTasks, totalCompletedTasks sql.NullInt64
		q := "SELECT count(" + quoteIdent("id") + ")," +
			" sum(CASE WHEN " + quoteIdent("status") + " = 'done' THEN 1 ELSE 0 END)," +
			" sum(CASE WHEN " + quoteIdent("status") + " = 'in_progress' THEN 1 ELSE 0 END)," +
			" sum(CASE WHEN " + quoteIdent("assigned_agent_id") + " IS NOT NULL THEN 1 ELSE 0 END)," +
			" sum(" + quoteIdent("task_count") + ")," +
			" sum(" + quoteIdent("completed_task_count") + ")" +
			" FROM " + quoteIdent(r.Table.Name) + " WHERE " + quoteIdent("project_id") + "::text = $1::text"
		if err := s.QueryRowContext(ctx, q, projectID).Scan(&totalBranches, &completedBranches, &activeBranches, &assignedBranches, &totalTasks, &totalCompletedTasks); err != nil {
			return err
		}
		overallProgress := 0.0
		if totalTasks.Valid && totalTasks.Int64 > 0 {
			overallProgress = float64(totalCompletedTasks.Int64) / float64(totalTasks.Int64) * 100.0
		}

		statusBreakdown := entities.NewOrderedMap[any]()
		statusRows, err := s.QueryContext(ctx, "SELECT "+quoteIdent("status")+", count("+quoteIdent("id")+") FROM "+
			quoteIdent(r.Table.Name)+" WHERE "+quoteIdent("project_id")+"::text = $1::text GROUP BY "+quoteIdent("status"), projectID)
		if err != nil {
			return err
		}
		for statusRows.Next() {
			var st string
			var n int
			if err := statusRows.Scan(&st, &n); err != nil {
				statusRows.Close()
				return err
			}
			statusBreakdown.Set(st, n)
		}
		if err := statusRows.Err(); err != nil {
			statusRows.Close()
			return err
		}
		statusRows.Close()

		summary := entities.NewOrderedMap[any]()
		summary.Set("total_branches", totalBranches)
		summary.Set("completed_branches", int(completedBranches.Int64))
		summary.Set("active_branches", int(activeBranches.Int64))
		summary.Set("assigned_branches", int(assignedBranches.Int64))
		tasks := entities.NewOrderedMap[any]()
		tasks.Set("total_tasks", int(totalTasks.Int64))
		tasks.Set("completed_tasks", int(totalCompletedTasks.Int64))
		tasks.Set("overall_progress_percentage", overallProgress)
		var userID any
		if r.UserID != nil {
			userID = *r.UserID
		}
		out.Set("project_id", projectID)
		out.Set("summary", summary)
		out.Set("tasks", tasks)
		out.Set("status_breakdown", statusBreakdown)
		out.Set("user_id", userID)
		out.Set("generated_at", "auto-generated")
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ---- create / interface methods -------------------------------------------------

// CreateBranch is create_branch.
func (r *ORMGitBranchRepository) CreateBranch(ctx context.Context, projectID, branchName, description string) (*entities.GitBranch, error) {
	gb, err := r.gitBranchRepoCreateBranch(ctx, projectID, branchName, description)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to create branch: "+err.Error(), "create_branch", "project_git_branchs")
	}
	return gb, nil
}

func (r *ORMGitBranchRepository) gitBranchRepoCreateBranch(ctx context.Context, projectID, branchName, description string) (*entities.GitBranch, error) {
	branchID := tmvo.GenerateNewGitBranchId()
	now := database.TimestampNow().UTC()
	gb, err := entities.NewGitBranch(entities.GitBranch{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &now, UpdatedAt: &now},
		ID:                  &branchID,
		Name:                branchName,
		Description:         description,
		ProjectID:           projectID,
	})
	if err != nil {
		return nil, err
	}
	if err := r.Save(ctx, gb); err != nil {
		return nil, err
	}
	return gb, nil
}

func gitBranchRepoISO(t *tmvo.GitBranchId) string {
	if t == nil {
		return ""
	}
	return t.Value
}

// CreateGitBranch is create_git_branch.
func (r *ORMGitBranchRepository) CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (map[string]any, error) {
	gb, err := r.CreateBranch(ctx, projectID, gitBranchName, gitBranchDescription)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "CREATE_FAILED"}, nil
	}
	return map[string]any{
		"success": true,
		"git_branch": map[string]any{
			"id":          gitBranchRepoISO(gb.ID),
			"name":        gb.Name,
			"description": gb.Description,
			"project_id":  gb.ProjectID,
			"created_at":  tmvo.IsoFormat(*gb.CreatedAt),
			"updated_at":  tmvo.IsoFormat(*gb.UpdatedAt),
		},
	}, nil
}

// GetGitBranchByID is get_git_branch_by_id.
func (r *ORMGitBranchRepository) GetGitBranchByID(ctx context.Context, gitBranchID string) (map[string]any, error) {
	if !r.gitBranchRepoHasUser() {
		return map[string]any{"success": false, "error": "User authentication required for branch operations", "error_code": "GET_FAILED"}, nil
	}
	var out map[string]any
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("id", gitBranchID, "user_id", *r.UserID), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			out = map[string]any{"success": false, "error": "Git branch not found: " + gitBranchID, "error_code": "NOT_FOUND"}
			return nil
		}
		gb, err := r.gitBranchRepoModelToEntity(ctx, s, rows[0])
		if err != nil {
			return err
		}
		out = map[string]any{
			"success": true,
			"git_branch": map[string]any{
				"id":                   gitBranchRepoISO(gb.ID),
				"name":                 gb.Name,
				"description":          gb.Description,
				"project_id":           gb.ProjectID,
				"created_at":           tmvo.IsoFormat(*gb.CreatedAt),
				"updated_at":           tmvo.IsoFormat(*gb.UpdatedAt),
				"assigned_agent_id":    gb.AssignedAgentID,
				"status":               gb.Status.Value,
				"priority":             gb.Priority.Value,
				"task_count":           gb.GetTaskCount(),
				"completed_task_count": gb.GetCompletedTaskCount(),
				"active_task_count":    gb.GetActiveTaskCount(),
			},
		}
		return nil
	})
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "GET_FAILED"}, nil
	}
	return out, nil
}

// GetGitBranchByName is get_git_branch_by_name.
func (r *ORMGitBranchRepository) GetGitBranchByName(ctx context.Context, projectID, gitBranchName string) (map[string]any, error) {
	gb, err := r.FindByName(ctx, projectID, gitBranchName)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "GET_FAILED"}, nil
	}
	if gb == nil {
		return map[string]any{"success": false, "error": "Git branch not found: " + gitBranchName, "error_code": "NOT_FOUND"}, nil
	}
	return map[string]any{
		"success": true,
		"git_branch": map[string]any{
			"id":                gitBranchRepoISO(gb.ID),
			"name":              gb.Name,
			"description":       gb.Description,
			"project_id":        gb.ProjectID,
			"created_at":        tmvo.IsoFormat(*gb.CreatedAt),
			"updated_at":        tmvo.IsoFormat(*gb.UpdatedAt),
			"assigned_agent_id": gb.AssignedAgentID,
			"status":            gb.Status.Value,
			"priority":          gb.Priority.Value,
		},
	}, nil
}

// ListGitBranchs is list_git_branchs (the Python key typo is preserved).
func (r *ORMGitBranchRepository) ListGitBranchs(ctx context.Context, projectID string) (map[string]any, error) {
	branches, err := r.FindAllByProject(ctx, projectID)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "LIST_FAILED"}, nil
	}
	items := []any{}
	for _, gb := range branches {
		items = append(items, map[string]any{
			"id":                gitBranchRepoISO(gb.ID),
			"name":              gb.Name,
			"description":       gb.Description,
			"project_id":        gb.ProjectID,
			"created_at":        tmvo.IsoFormat(*gb.CreatedAt),
			"updated_at":        tmvo.IsoFormat(*gb.UpdatedAt),
			"assigned_agent_id": gb.AssignedAgentID,
			"status":            gb.Status.Value,
			"priority":          gb.Priority.Value,
		})
	}
	return map[string]any{"success": true, "git_branchs": items, "count": len(items)}, nil
}

// UpdateGitBranch is update_git_branch (no user filter).
func (r *ORMGitBranchRepository) UpdateGitBranch(ctx context.Context, gitBranchID string, gitBranchName, gitBranchDescription *string) (map[string]any, error) {
	var out map[string]any
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.getByID(ctx, s, gitBranchID)
		if err != nil {
			return err
		}
		if row == nil {
			out = map[string]any{"success": false, "error": "Git branch not found: " + gitBranchID, "error_code": "NOT_FOUND"}
			return nil
		}
		var sets []string
		var args []any
		if gitBranchName != nil {
			args = append(args, *gitBranchName)
			sets = append(sets, quoteIdent("name")+fmt.Sprintf(" = $%d", len(args)))
			row.Name = *gitBranchName
		}
		if gitBranchDescription != nil {
			args = append(args, *gitBranchDescription)
			sets = append(sets, quoteIdent("description")+fmt.Sprintf(" = $%d", len(args)))
			row.Description = *gitBranchDescription
		}
		now := database.TimestampNow().UTC()
		args = append(args, now)
		sets = append(sets, quoteIdent("updated_at")+fmt.Sprintf(" = $%d", len(args)))
		row.UpdatedAt = now
		args = append(args, gitBranchID)
		if _, err := s.ExecContext(ctx, "UPDATE "+quoteIdent(r.Table.Name)+" SET "+strings.Join(sets, ", ")+" WHERE "+r.pkColumn()+fmt.Sprintf(" = $%d", len(args)), args...); err != nil {
			return err
		}
		gb, err := r.gitBranchRepoModelToEntity(ctx, s, row)
		if err != nil {
			return err
		}
		out = map[string]any{
			"success": true,
			"message": "Git branch updated successfully",
			"git_branch": map[string]any{
				"id":          gitBranchRepoISO(gb.ID),
				"name":        gb.Name,
				"description": gb.Description,
				"project_id":  gb.ProjectID,
				"updated_at":  tmvo.IsoFormat(*gb.UpdatedAt),
			},
		}
		return nil
	})
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "UPDATE_FAILED"}, nil
	}
	return out, nil
}

// DeleteGitBranch is delete_git_branch.
func (r *ORMGitBranchRepository) DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	deleted, err := r.Delete(ctx, projectID, gitBranchID)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "DELETE_FAILED"}, nil
	}
	if deleted {
		return map[string]any{"success": true, "message": "Git branch " + gitBranchID + " deleted successfully"}, nil
	}
	return map[string]any{"success": false, "error": "Git branch not found: " + gitBranchID, "error_code": "NOT_FOUND"}, nil
}

// AssignAgentToBranch is assign_agent_to_branch.
func (r *ORMGitBranchRepository) AssignAgentToBranch(ctx context.Context, projectID, agentID, gitBranchName string) (map[string]any, error) {
	gb, err := r.FindByName(ctx, projectID, gitBranchName)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "ASSIGN_FAILED"}, nil
	}
	if gb == nil {
		return map[string]any{"success": false, "error": "Git branch not found: " + gitBranchName, "error_code": "NOT_FOUND"}, nil
	}
	assigned, err := r.AssignAgent(ctx, projectID, gb.ID.Value, agentID)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "ASSIGN_FAILED"}, nil
	}
	if assigned {
		return map[string]any{"success": true, "message": "Agent " + agentID + " assigned to branch " + gitBranchName}, nil
	}
	return map[string]any{"success": false, "error": "Failed to assign agent", "error_code": "ASSIGN_FAILED"}, nil
}

// UnassignAgentFromBranch is unassign_agent_from_branch.
func (r *ORMGitBranchRepository) UnassignAgentFromBranch(ctx context.Context, projectID, agentID, gitBranchName string) (map[string]any, error) {
	gb, err := r.FindByName(ctx, projectID, gitBranchName)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "UNASSIGN_FAILED"}, nil
	}
	if gb == nil {
		return map[string]any{"success": false, "error": "Git branch not found: " + gitBranchName, "error_code": "NOT_FOUND"}, nil
	}
	unassigned, err := r.UnassignAgent(ctx, projectID, gb.ID.Value)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": "UNASSIGN_FAILED"}, nil
	}
	if unassigned {
		return map[string]any{"success": true, "message": "Agent " + agentID + " unassigned from branch " + gitBranchName}, nil
	}
	return map[string]any{"success": false, "error": "Failed to unassign agent", "error_code": "UNASSIGN_FAILED"}, nil
}

// GetBranchStatistics is get_branch_statistics (no user filter).
func (r *ORMGitBranchRepository) GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	var out map[string]any
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("id", gitBranchID, "project_id", projectID), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			out = map[string]any{"error": "Branch not found"}
			return nil
		}
		model := rows[0]
		counts, err := r.gitBranchRepoTaskCounts(ctx, s, gitBranchID)
		if err != nil {
			return err
		}
		progress := 0.0
		if counts.total > 0 {
			progress = float64(counts.completed) / float64(counts.total) * 100.0
		}
		out = map[string]any{
			"branch_id":            model.ID,
			"branch_name":          model.Name,
			"project_id":           model.ProjectID,
			"status":               model.Status,
			"priority":             model.Priority,
			"assigned_agent_id":    model.AssignedAgentID,
			"task_count":           counts.total,
			"completed_task_count": counts.completed,
			"progress_percentage":  progress,
			"created_at":           tmvo.IsoFormatNaive(model.CreatedAt),
			"updated_at":           tmvo.IsoFormatNaive(model.UpdatedAt),
		}
		return nil
	})
	if err != nil {
		return map[string]any{"error": err.Error()}, nil
	}
	return out, nil
}

// ArchiveBranch is archive_branch (bulk update: updated_at is not changed).
func (r *ORMGitBranchRepository) ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	return r.gitBranchRepoSetStatus(ctx, projectID, gitBranchID, "cancelled", "archived", "ARCHIVE_FAILED")
}

// RestoreBranch is restore_branch.
func (r *ORMGitBranchRepository) RestoreBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	return r.gitBranchRepoSetStatus(ctx, projectID, gitBranchID, "todo", "restored", "RESTORE_FAILED")
}

func (r *ORMGitBranchRepository) gitBranchRepoSetStatus(ctx context.Context, projectID, gitBranchID, status, verb, errCode string) (map[string]any, error) {
	updated := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx, "UPDATE "+quoteIdent(r.Table.Name)+" SET "+quoteIdent("status")+" = $1 WHERE "+
			quoteIdent("id")+" = $2 AND "+quoteIdent("project_id")+"::text = $3::text", status, gitBranchID, projectID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		updated = int(n)
		return nil
	})
	if err != nil {
		return map[string]any{"success": false, "error": err.Error(), "error_code": errCode}, nil
	}
	if updated > 0 {
		return map[string]any{"success": true, "message": "Git branch " + gitBranchID + " " + verb + " successfully"}, nil
	}
	return map[string]any{"success": false, "error": "Git branch not found: " + gitBranchID, "error_code": "NOT_FOUND"}, nil
}

// ---- performance-optimized methods ---------------------------------------------

// GetBranchesWithTaskCounts is get_branches_with_task_counts.
func (r *ORMGitBranchRepository) GetBranchesWithTaskCounts(projectID string) []*entities.OrderedMap[any] {
	if projectID == "" {
		return []*entities.OrderedMap[any]{}
	}
	if _, ok := tmvo.PyParseUUID(projectID); !ok {
		return []*entities.OrderedMap[any]{}
	}
	out := []*entities.OrderedMap[any]{}
	ctx := context.Background()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{projectID}
		q := `SELECT
			gb."id"::text AS branch_id,
			gb."name" AS branch_name,
			gb."description",
			gb."status" AS branch_status,
			gb."priority",
			gb."created_at",
			gb."updated_at",
			gb."assigned_agent_id"::text,
			gb."user_id"::text,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id") AS total_tasks,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'todo') AS todo_count,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'in_progress') AS in_progress_count,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'done') AS done_count,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'blocked') AS blocked_count,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "priority" = 'urgent') AS urgent_tasks,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "priority" = 'high') AS high_priority_tasks,
			CASE
				WHEN (SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id") > 0
				THEN CAST(
					(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'done') * 100.0 /
					(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id")
					AS INTEGER
				)
				ELSE 0
			END AS completion_percentage
		FROM "project_git_branchs" gb
		WHERE gb."project_id" = $1`
		if r.gitBranchRepoHasUser() {
			args = append(args, *r.UserID)
			q += fmt.Sprintf(` AND gb."user_id" = $%d`, len(args))
		}
		q += ` ORDER BY gb."updated_at" DESC, gb."created_at" DESC`

		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var branchID, branchName, description, branchStatus, priority string
			var createdAt, updatedAt time.Time
			var assignedAgentID, userID *string
			var totalTasks, todoCount, inProgressCount, doneCount, blockedCount, urgentTasks, highPriorityTasks, completionPercentage int
			if err := rows.Scan(&branchID, &branchName, &description, &branchStatus, &priority,
				&createdAt, &updatedAt, &assignedAgentID, &userID,
				&totalTasks, &todoCount, &inProgressCount, &doneCount, &blockedCount,
				&urgentTasks, &highPriorityTasks, &completionPercentage); err != nil {
				return err
			}
			data := entities.NewOrderedMap[any]()
			data.Set("id", branchID)
			data.Set("name", branchName)
			data.Set("description", description)
			data.Set("status", branchStatus)
			data.Set("priority", priority)
			data.Set("created_at", tmvo.IsoFormatNaive(createdAt))
			data.Set("updated_at", tmvo.IsoFormatNaive(updatedAt))
			data.Set("assigned_agent_id", assignedAgentID)
			data.Set("user_id", userID)
			taskCounts := entities.NewOrderedMap[any]()
			taskCounts.Set("total", totalTasks)
			byStatus := entities.NewOrderedMap[any]()
			byStatus.Set("todo", todoCount)
			byStatus.Set("in_progress", inProgressCount)
			byStatus.Set("done", doneCount)
			byStatus.Set("blocked", blockedCount)
			byPriority := entities.NewOrderedMap[any]()
			byPriority.Set("urgent", urgentTasks)
			byPriority.Set("high", highPriorityTasks)
			taskCounts.Set("by_status", byStatus)
			taskCounts.Set("by_priority", byPriority)
			taskCounts.Set("completion_percentage", completionPercentage)
			data.Set("task_counts", taskCounts)
			data.Set("has_tasks", totalTasks > 0)
			data.Set("has_urgent_tasks", urgentTasks > 0)
			data.Set("is_active", inProgressCount > 0)
			data.Set("is_completed", totalTasks > 0 && doneCount == totalTasks)
			out = append(out, data)
		}
		if err := rows.Err(); err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		return []*entities.OrderedMap[any]{}
	}
	return out
}

// GetBranchSummaryStats is get_branch_summary_stats.
func (r *ORMGitBranchRepository) GetBranchSummaryStats(projectID string) *entities.OrderedMap[any] {
	if projectID == "" {
		out := entities.NewOrderedMap[any]()
		out.Set("error", "No project_id provided")
		return out
	}
	out := entities.NewOrderedMap[any]()
	ctx := context.Background()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{projectID}
		q := `SELECT
			COUNT(DISTINCT gb."id") AS total_branches,
			COUNT(DISTINCT CASE WHEN t."id" IS NOT NULL THEN gb."id" END) AS active_branches,
			COUNT(DISTINCT t."id") AS total_tasks,
			COUNT(DISTINCT CASE WHEN t."status" = 'todo' THEN t."id" END) AS todo_tasks,
			COUNT(DISTINCT CASE WHEN t."status" = 'in_progress' THEN t."id" END) AS in_progress_tasks,
			COUNT(DISTINCT CASE WHEN t."status" = 'done' THEN t."id" END) AS done_tasks,
			COUNT(DISTINCT CASE WHEN t."priority" = 'urgent' THEN t."id" END) AS urgent_tasks
		FROM "project_git_branchs" gb
		LEFT JOIN "tasks" t ON t."git_branch_id" = gb."id"
		WHERE gb."project_id" = $1`
		if r.gitBranchRepoHasUser() {
			args = append(args, *r.UserID)
			q += fmt.Sprintf(` AND gb."user_id" = $%d`, len(args))
		}
		var totalBranches, activeBranches, totalTasks, todoTasks, inProgressTasks, doneTasks, urgentTasks int
		if err := s.QueryRowContext(ctx, q, args...).Scan(&totalBranches, &activeBranches, &totalTasks, &todoTasks, &inProgressTasks, &doneTasks, &urgentTasks); err != nil {
			return err
		}
		branches := entities.NewOrderedMap[any]()
		branches.Set("total", totalBranches)
		branches.Set("active", activeBranches)
		branches.Set("inactive", totalBranches-activeBranches)
		tasks := entities.NewOrderedMap[any]()
		tasks.Set("total", totalTasks)
		tasks.Set("todo", todoTasks)
		tasks.Set("in_progress", inProgressTasks)
		tasks.Set("done", doneTasks)
		tasks.Set("urgent", urgentTasks)
		var completion any = 0
		if totalTasks > 0 {
			completion = tmvo.PyRound(float64(doneTasks)/float64(totalTasks)*100, 1)
		}
		out.Set("branches", branches)
		out.Set("tasks", tasks)
		out.Set("completion_percentage", completion)
		return nil
	})
	if err != nil {
		out = entities.NewOrderedMap[any]()
		out.Set("error", err.Error())
	}
	return out
}

// GetSingleBranchWithCounts is get_single_branch_with_counts.
func (r *ORMGitBranchRepository) GetSingleBranchWithCounts(branchID string) *entities.OrderedMap[any] {
	if branchID == "" {
		return nil
	}
	var out *entities.OrderedMap[any]
	ctx := context.Background()
	_ = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{branchID}
		q := `SELECT
			gb."id"::text AS branch_id,
			gb."name" AS branch_name,
			gb."description",
			gb."status" AS branch_status,
			gb."project_id"::text,
			gb."user_id"::text,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id") AS total_tasks,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'todo') AS todo_count,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'in_progress') AS in_progress_count,
			(SELECT COUNT(*) FROM "tasks" WHERE "git_branch_id" = gb."id" AND "status" = 'done') AS done_count
		FROM "project_git_branchs" gb
		WHERE gb."id" = $1`
		if r.gitBranchRepoHasUser() {
			args = append(args, *r.UserID)
			q += fmt.Sprintf(` AND gb."user_id" = $%d`, len(args))
		}
		var branchName, description, branchStatus, projectID, userID string
		var totalTasks, todoCount, inProgressCount, doneCount int
		err := s.QueryRowContext(ctx, q, args...).Scan(&branchID, &branchName, &description, &branchStatus, &projectID, &userID,
			&totalTasks, &todoCount, &inProgressCount, &doneCount)
		if err == sql.ErrNoRows {
			return nil
		}
		if err != nil {
			return err
		}
		out = entities.NewOrderedMap[any]()
		out.Set("id", branchID)
		out.Set("name", branchName)
		out.Set("description", description)
		out.Set("status", branchStatus)
		out.Set("project_id", projectID)
		out.Set("user_id", userID)
		taskCounts := entities.NewOrderedMap[any]()
		taskCounts.Set("total", totalTasks)
		taskCounts.Set("todo", todoCount)
		taskCounts.Set("in_progress", inProgressCount)
		taskCounts.Set("done", doneCount)
		out.Set("task_counts", taskCounts)
		return nil
	})
	return out
}

// CheckNameExistsInProject is check_name_exists_in_project.
func (r *ORMGitBranchRepository) CheckNameExistsInProject(ctx context.Context, projectID, name string, excludeBranchID *string) (bool, error) {
	if !r.gitBranchRepoHasUser() {
		return false, &tmvo.ValueError{Msg: "User authentication required for branch operations"}
	}
	exists := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		filters := NewKwargs("project_id", projectID, "name", tmvo.PyStrip(name), "user_id", *r.UserID)
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		if excludeBranchID != nil {
			args = append(args, *excludeBranchID)
			w += " AND " + quoteIdent("id") + fmt.Sprintf(" != $%d", len(args))
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		exists = len(rows) > 0
		return nil
	})
	return exists, err
}

// FindByIDs is find_by_ids: a lightweight batch load without task data.
func (r *ORMGitBranchRepository) FindByIDs(ctx context.Context, branchIDs []string) *entities.OrderedMap[*entities.GitBranch] {
	out := entities.NewOrderedMap[*entities.GitBranch]()
	if len(branchIDs) == 0 {
		return out
	}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		cond := gitBranchRepoInArgs("id", branchIDs, &args)
		rows, err := r.selectRows(ctx, s, " WHERE "+cond, args...)
		if err != nil {
			return err
		}
		for _, model := range rows {
			var id *tmvo.GitBranchId
			if model.ID != "" {
				v, err := tmvo.NewGitBranchId(model.ID)
				if err != nil {
					return err
				}
				id = &v
			}
			created, updated := model.CreatedAt, model.UpdatedAt
			gb, err := entities.NewGitBranch(entities.GitBranch{
				BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &updated},
				ID:                  id,
				Name:                model.Name,
				Description:         model.Description,
				ProjectID:           model.ProjectID,
			})
			if err != nil {
				return err
			}
			gb.AssignedAgentID = model.AssignedAgentID
			priority, err := tmvo.PriorityFromString(model.Priority)
			if err != nil {
				return err
			}
			gb.Priority = &priority
			status, err := tmvo.TaskStatusFromString(model.Status)
			if err != nil {
				return err
			}
			gb.Status = &status
			out.Set(model.ID, gb)
		}
		return nil
	})
	if err != nil {
		return entities.NewOrderedMap[*entities.GitBranch]()
	}
	return out
}

// ---- synchronous convenience API (branch statistics protocol) -------------------

// Get is get: the branch with task counts, or nil when it does not exist. Errors are
// swallowed like Python (logged only).
func (r *ORMGitBranchRepository) Get(branchID string) (any, error) {
	var out *gitBranchRepoBranch
	ctx := context.Background()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.getByID(ctx, s, branchID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		counts, err := r.gitBranchRepoTaskCounts(ctx, s, branchID)
		if err != nil {
			return err
		}
		out = &gitBranchRepoBranch{ID: row.ID, ProjectID: row.ProjectID, TaskCount: counts.total, CompletedTaskCount: counts.completed}
		return nil
	})
	if err != nil || out == nil {
		return nil, nil
	}
	return out, nil
}

// Update is update: direct field update, returning false on any error (Python catches
// Exception). updated_at is always refreshed.
func (r *ORMGitBranchRepository) Update(branchID string, updates map[string]any) (bool, error) {
	ok := false
	ctx := context.Background()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.getByID(ctx, s, branchID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		var sets []string
		var args []any
		for field, value := range updates {
			if field == "updated_at" {
				continue
			}
			pos, exists := r.byAttr[field]
			if !exists {
				continue
			}
			c := r.Table.Columns[pos]
			var bv any
			if value != nil {
				bv, err = bind(c, value)
				if err != nil {
					return err
				}
			}
			args = append(args, bv)
			sets = append(sets, quoteIdent(c.Name)+fmt.Sprintf(" = $%d", len(args)))
		}
		args = append(args, database.TimestampNow().UTC())
		sets = append(sets, quoteIdent("updated_at")+fmt.Sprintf(" = $%d", len(args)))
		args = append(args, branchID)
		if _, err := s.ExecContext(ctx, "UPDATE "+quoteIdent(r.Table.Name)+" SET "+strings.Join(sets, ", ")+" WHERE "+r.pkColumn()+fmt.Sprintf(" = $%d", len(args)), args...); err != nil {
			return err
		}
		ok = true
		return nil
	})
	if err != nil {
		return false, nil
	}
	return ok, nil
}

// FindByProjectID is find_by_project_id: the simple branch objects used by the branch
// statistics service. Errors are swallowed like Python (logged only).
func (r *ORMGitBranchRepository) FindByProjectID(projectID string) ([]services.IdentifiedBranch, error) {
	out := []services.IdentifiedBranch{}
	ctx := context.Background()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(NewKwargs("project_id", projectID), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w, args...)
		if err != nil {
			return err
		}
		for _, model := range rows {
			counts, err := r.gitBranchRepoTaskCounts(ctx, s, model.ID)
			if err != nil {
				return err
			}
			out = append(out, &gitBranchRepoBranch{ID: model.ID, ProjectID: model.ProjectID, TaskCount: counts.total, CompletedTaskCount: counts.completed})
		}
		return nil
	})
	if err != nil {
		return []services.IdentifiedBranch{}, nil
	}
	return out, nil
}

// GetAll is get_all: every branch as a simple object. Errors are swallowed like Python.
func (r *ORMGitBranchRepository) GetAll() ([]services.IdentifiedBranch, error) {
	out := []services.IdentifiedBranch{}
	ctx := context.Background()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, "")
		if err != nil {
			return err
		}
		for _, model := range rows {
			counts, err := r.gitBranchRepoTaskCounts(ctx, s, model.ID)
			if err != nil {
				return err
			}
			out = append(out, &gitBranchRepoBranch{ID: model.ID, ProjectID: model.ProjectID, TaskCount: counts.total, CompletedTaskCount: counts.completed})
		}
		return nil
	})
	if err != nil {
		return []services.IdentifiedBranch{}, nil
	}
	return out, nil
}
