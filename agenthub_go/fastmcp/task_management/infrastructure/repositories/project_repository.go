package repositories

// ORM Project Repository (Python infrastructure/repositories/orm/project_repository.py):
// project persistence over database/sql + pgx. The EventPublishingMixin and
// CacheInvalidationMixin side effects are dropped like logging; audit logging (log_access)
// is dropped too.
//
// The selective-field methods go through the small ProjectRepoFieldSelector interface
// declared here.

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/exceptions"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ProjectRepoFieldSelector is the subset of ContextFieldSelector used by
// ORMProjectRepository's selective-field methods. It is declared here because that module is
// not ported yet; a concrete implementation supplies these methods.
type ProjectRepoFieldSelector interface {
	// GetProjectFields is get_project_fields.
	GetProjectFields(projectID string, fields any) *entities.OrderedMap[any]
	// GetCachedFields is get_cached_fields (nil when nothing is cached).
	GetCachedFields(projectID string, fields []string) *entities.OrderedMap[any]
	// CacheFieldMapping is cache_field_mapping.
	CacheFieldMapping(projectID string, fields []string, data *entities.OrderedMap[any])
	// GetOptimalFieldSet is get_optimal_field_set; the result is the FieldSet value.
	GetOptimalFieldSet(operation, entityType string) any
	// GetMetrics is get_metrics.
	GetMetrics() map[string]int
	// EstimateSavings is estimate_savings.
	EstimateSavings(entityType string, fieldSet any) map[string]float64
}

// ORMProjectRepository is Python's ORMProjectRepository.
type ORMProjectRepository struct {
	*UserScopedORMRepository[database.Project]

	projectRepoBranches *ORMRepository[database.ProjectGitBranch]
	projectRepoTasks    *ORMRepository[database.Task]

	// FieldSelector is the optional ContextFieldSelector implementation (nil when none).
	FieldSelector ProjectRepoFieldSelector
}

// Assert the domain interface is implemented.
var _ domainrepos.ProjectRepository = (*ORMProjectRepository)(nil)

// NewORMProjectRepository builds the repository for the projects table. userID nil means
// system mode.
func NewORMProjectRepository(sessions *database.SessionManager, userID *string) (*ORMProjectRepository, error) {
	base, err := NewUserScopedORMRepository[database.Project]("projects", sessions, userID)
	if err != nil {
		return nil, err
	}
	branches, err := NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		return nil, err
	}
	tasks, err := NewORMRepository[database.Task]("tasks", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMProjectRepository{
		UserScopedORMRepository: base,
		projectRepoBranches:     branches,
		projectRepoTasks:        tasks,
	}, nil
}

// WithUser returns a new instance scoped to userID (with_user).
func (r *ORMProjectRepository) WithUser(userID string) (*ORMProjectRepository, error) {
	return NewORMProjectRepository(r.Sessions, &userID)
}

// ---- entity conversion ---------------------------------------------------------

func projectRepoProjectIDString(p *entities.Project) string {
	if p == nil || p.ID == nil {
		return ""
	}
	return p.ID.Value
}

func projectRepoLen[V any](m *entities.OrderedMap[V]) int {
	if m == nil {
		return 0
	}
	return m.Len()
}

func projectRepoOrderedMapToAny[V any](m *entities.OrderedMap[V]) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if m == nil {
		return out
	}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out.Set(k, v)
	}
	return out
}

// projectRepoModelMetadata is the "model_metadata" entry of _entity_to_model_dict.
func projectRepoModelMetadata(p *entities.Project) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("git_branchs_count", projectRepoLen(p.GitBranchs))
	m.Set("registered_agents_count", projectRepoLen(p.RegisteredAgents))
	m.Set("agent_assignments", projectRepoOrderedMapToAny(p.AgentAssignments))
	m.Set("cross_tree_dependencies_count", projectRepoLen(p.CrossTreeDependencies))
	m.Set("active_work_sessions_count", projectRepoLen(p.ActiveWorkSessions))
	m.Set("resource_locks", projectRepoOrderedMapToAny(p.ResourceLocks))
	return m
}

// projectRepoModelToEntity is _model_to_entity. The Python code stores plain status/priority
// dicts in git_branch.all_tasks; the Go GitBranch maps tasks to *Task, so minimal Task values
// carrying id/status/priority reproduce the statistics behaviour.
func (r *ORMProjectRepository) projectRepoModelToEntity(ctx context.Context, s database.DBTX, row *database.Project) (*entities.Project, error) {
	var id *tmvo.ProjectId
	if row.ID != "" {
		v, err := tmvo.NewProjectId(row.ID)
		if err != nil {
			return nil, err
		}
		id = &v
	}
	created, updated := row.CreatedAt, row.UpdatedAt
	ent, err := entities.NewProject(entities.Project{
		BaseTimestampEntity: projectRepoBaseTimestamps(created, updated),
		ID:                  id,
		Name:                row.Name,
		Description:         row.Description,
	})
	if err != nil {
		return nil, err
	}
	branches, err := r.projectRepoBranches.selectRows(ctx, s, ` WHERE `+projectRepoQuote("project_id")+` = $1`, row.ID)
	if err != nil {
		return nil, err
	}
	for _, dbBranch := range branches {
		var branchID *tmvo.GitBranchId
		if dbBranch.ID != "" {
			v, err := tmvo.NewGitBranchId(dbBranch.ID)
			if err != nil {
				return nil, err
			}
			branchID = &v
		}
		gb, err := entities.NewGitBranch(entities.GitBranch{
			BaseTimestampEntity: projectRepoBaseTimestamps(dbBranch.CreatedAt, dbBranch.UpdatedAt),
			ID:                  branchID,
			Name:                dbBranch.Name,
			Description:         dbBranch.Description,
			ProjectID:           dbBranch.ProjectID,
		})
		if err != nil {
			return nil, err
		}
		userID := any(nil)
		if r.UserID != nil {
			userID = *r.UserID
		}
		w, args, err := r.projectRepoTasks.where(NewKwargs("git_branch_id", dbBranch.ID, "user_id", userID), 1)
		if err != nil {
			return nil, err
		}
		tasks, err := r.projectRepoTasks.selectRows(ctx, s, w, args...)
		if err != nil {
			return nil, err
		}
		for _, dbTask := range tasks {
			st, _ := tmvo.TaskStatusFromString(dbTask.Status)
			pr, _ := tmvo.PriorityFromString(dbTask.Priority)
			taskID := tmvo.TaskId{EntityId: tmvo.EntityId{Value: dbTask.ID}}
			gb.AllTasks.Set(dbTask.ID, &entities.Task{ID: &taskID, Status: &st, Priority: &pr})
		}
		ent.GitBranchs.Set(dbBranch.ID, gb)
	}
	return ent, nil
}

// ---- interface methods ---------------------------------------------------------

// Save inserts or updates a project and its new git branches (save).
func (r *ORMProjectRepository) Save(ctx context.Context, project *entities.Project) error {
	projectIDStr := projectRepoProjectIDString(project)
	err := r.Transaction(ctx, func(ctx context.Context) error {
		existing, err := r.ORMRepository.GetByID(ctx, projectIDStr)
		if err != nil {
			return err
		}
		if existing != nil {
			updates := NewKwargs(
				"name", project.Name,
				"description", project.Description,
				"status", "active",
				"model_metadata", projectRepoModelMetadata(project),
				"updated_at", database.TimestampNow(),
			)
			if _, err := r.ORMRepository.Update(ctx, projectIDStr, updates); err != nil {
				return err
			}
		} else {
			data := NewKwargs(
				"id", projectIDStr,
				"name", project.Name,
				"description", project.Description,
				"created_at", project.CreatedAt,
				"updated_at", project.UpdatedAt,
				"status", "active",
				"model_metadata", json.RawMessage("{}"),
			)
			data, err = r.SetUserID(data)
			if err != nil {
				return err
			}
			if _, err := r.ORMRepository.Create(ctx, data); err != nil {
				return err
			}
		}
		if project.GitBranchs != nil {
			for _, branchID := range project.GitBranchs.Keys() {
				branch, _ := project.GitBranchs.Get(branchID)
				existingBranch, err := r.projectRepoBranches.FindOneBy(ctx, NewKwargs("id", branchID, "project_id", projectIDStr))
				if err != nil {
					return err
				}
				if existingBranch != nil {
					continue
				}
				branchData := NewKwargs(
					"id", branchID,
					"project_id", projectIDStr,
					"name", branch.Name,
					"description", branch.Description,
					"created_at", branch.CreatedAt,
					"updated_at", branch.UpdatedAt,
					"assigned_agent_id", branch.AssignedAgentID,
					"priority", projectRepoPriorityString(branch.Priority),
					"status", projectRepoStatusString(branch.Status),
					"task_count", int64(0),
					"completed_task_count", int64(0),
					"model_metadata", json.RawMessage("{}"),
				)
				branchData, err = r.SetUserID(branchData)
				if err != nil {
					return err
				}
				if _, err := r.projectRepoBranches.Create(ctx, branchData); err != nil {
					return err
				}
			}
		}
		return nil
	})
	if err != nil {
		return exceptions.NewDatabaseException("Failed to save project: "+err.Error(), "save", "projects")
	}
	return nil
}

// FindByID loads a project with user isolation.
func (r *ORMProjectRepository) FindByID(ctx context.Context, projectID string) (*entities.Project, error) {
	var out *entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(r.UserScopedORMRepository.scoped(NewKwargs("id", projectID)), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return nil
		}
		out, err = r.projectRepoModelToEntity(ctx, s, rows[0])
		return err
	})
	return out, err
}

// FindAll loads every project of the user ordered by created_at desc.
func (r *ORMProjectRepository) FindAll(ctx context.Context) ([]*entities.Project, error) {
	out, err := r.projectRepoQuery(ctx, r.UserScopedORMRepository.scoped(NewKwargs()), ` ORDER BY `+projectRepoQuote("created_at")+` DESC`)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// Delete removes a project (delete -> delete_project).
func (r *ORMProjectRepository) Delete(ctx context.Context, projectID string) (bool, error) {
	deleted, err := r.DeleteProject(ctx, projectID)
	if err != nil {
		return false, nil
	}
	return deleted, nil
}

// Exists reports whether the project id exists (unfiltered: BaseORMRepository.exists).
func (r *ORMProjectRepository) Exists(ctx context.Context, projectID string) (bool, error) {
	return r.ORMRepository.Exists(ctx, NewKwargs("id", projectID))
}

// Update touches the entity and saves it (update).
func (r *ORMProjectRepository) Update(ctx context.Context, project *entities.Project) error {
	projectIDStr := projectRepoProjectIDString(project)
	exists, err := r.ORMRepository.GetByID(ctx, projectIDStr)
	if err != nil {
		return exceptions.NewDatabaseException("Failed to update project: "+err.Error(), "update", "projects")
	}
	if exists == nil {
		return exceptions.NewResourceNotFoundException("Project", projectIDStr, "")
	}
	if err := project.Touch("repository_update_project"); err != nil {
		return exceptions.NewDatabaseException("Failed to update project: "+err.Error(), "update", "projects")
	}
	if err := r.Save(ctx, project); err != nil {
		return exceptions.NewDatabaseException("Failed to update project: "+err.Error(), "update", "projects")
	}
	return nil
}

// FindByName loads a project by name with user isolation.
func (r *ORMProjectRepository) FindByName(ctx context.Context, name string) (*entities.Project, error) {
	var out *entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(r.UserScopedORMRepository.scoped(NewKwargs("name", name)), 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return nil
		}
		out, err = r.projectRepoModelToEntity(ctx, s, rows[0])
		return err
	})
	return out, err
}

// Count counts every project (unfiltered: BaseORMRepository.count).
func (r *ORMProjectRepository) Count(ctx context.Context) (int, error) {
	return r.ORMRepository.Count(ctx, NewKwargs())
}

// FindProjectsWithAgent lists the distinct projects having a branch assigned to agentID.
func (r *ORMProjectRepository) FindProjectsWithAgent(ctx context.Context, agentID string) ([]*entities.Project, error) {
	var out []*entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		q := "SELECT DISTINCT " + r.projectRepoQualifiedSelectList("p") +
			" FROM " + projectRepoQuote(r.Table.Name) + " p JOIN " + projectRepoQuote("project_git_branchs") +
			" b ON b." + projectRepoQuote("project_id") + " = p." + projectRepoQuote("id")
		var args []any
		if r.UserID != nil {
			args = append(args, *r.UserID)
			q += " WHERE p." + projectRepoQuote("user_id") + " = $1"
			args = append(args, agentID)
			q += " AND b." + projectRepoQuote("assigned_agent_id") + fmt.Sprintf(" = $%d", len(args))
		} else {
			args = append(args, agentID)
			q += " WHERE b." + projectRepoQuote("assigned_agent_id") + " = $1"
		}
		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		var raw []*database.Project
		for rows.Next() {
			row := r.newRow()
			if err := rows.Scan(r.scanDest(row)...); err != nil {
				rows.Close()
				return err
			}
			raw = append(raw, row)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()
		for _, row := range raw {
			ent, err := r.projectRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, ent)
		}
		return nil
	})
	return out, err
}

// FindProjectsByStatus lists the user's projects with the given status.
func (r *ORMProjectRepository) FindProjectsByStatus(ctx context.Context, status string) ([]*entities.Project, error) {
	return r.projectRepoQuery(ctx, r.UserScopedORMRepository.scoped(NewKwargs("status", status)),
		` ORDER BY `+projectRepoQuote("created_at")+` DESC`)
}

// GetProjectHealthSummary computes aggregate project/branch statistics.
func (r *ORMProjectRepository) GetProjectHealthSummary(ctx context.Context) (map[string]any, error) {
	result := map[string]any{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		totalProjects := 0
		if err := s.QueryRowContext(ctx, "SELECT count(*) FROM "+projectRepoQuote(r.Table.Name)).Scan(&totalProjects); err != nil {
			return err
		}
		statusCounts := map[string]any{}
		statusRows, err := s.QueryContext(ctx, "SELECT DISTINCT "+projectRepoQuote("status")+" FROM "+projectRepoQuote(r.Table.Name))
		if err != nil {
			return err
		}
		var statuses []string
		for statusRows.Next() {
			var st string
			if err := statusRows.Scan(&st); err != nil {
				statusRows.Close()
				return err
			}
			statuses = append(statuses, st)
		}
		statusRows.Close()
		if err := statusRows.Err(); err != nil {
			return err
		}
		for _, st := range statuses {
			n := 0
			if err := s.QueryRowContext(ctx, "SELECT count(*) FROM "+projectRepoQuote(r.Table.Name)+
				" WHERE "+projectRepoQuote("status")+" = $1", st).Scan(&n); err != nil {
				return err
			}
			statusCounts[st] = n
		}
		var projectsWithBranches, totalBranches, assignedBranches int
		if err := s.QueryRowContext(ctx, "SELECT count(DISTINCT p."+projectRepoQuote("id")+") FROM "+
			projectRepoQuote(r.Table.Name)+" p JOIN "+projectRepoQuote("project_git_branchs")+
			" b ON b."+projectRepoQuote("project_id")+" = p."+projectRepoQuote("id")).Scan(&projectsWithBranches); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, "SELECT count(*) FROM "+projectRepoQuote("project_git_branchs")).Scan(&totalBranches); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, "SELECT count(*) FROM "+projectRepoQuote("project_git_branchs")+
			" WHERE "+projectRepoQuote("assigned_agent_id")+" IS NOT NULL").Scan(&assignedBranches); err != nil {
			return err
		}
		var average any = 0
		if totalProjects > 0 {
			average = float64(totalBranches) / float64(totalProjects)
		}
		result = map[string]any{
			"total_projects":               totalProjects,
			"projects_by_status":           statusCounts,
			"projects_with_branches":       projectsWithBranches,
			"total_branches":               totalBranches,
			"assigned_branches":            assignedBranches,
			"unassigned_branches":          totalBranches - assignedBranches,
			"average_branches_per_project": average,
		}
		return nil
	})
	return result, err
}

// UnassignAgentFromTree clears the assigned agent of one branch (unassign_agent_from_tree).
func (r *ORMProjectRepository) UnassignAgentFromTree(ctx context.Context, projectID, agentID, gitBranchID string) (map[string]any, error) {
	var out map[string]any
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.projectRepoBranches.where(NewKwargs("id", gitBranchID, "project_id", projectID, "assigned_agent_id", agentID), 1)
		if err != nil {
			return err
		}
		rows, err := r.projectRepoBranches.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return exceptions.NewResourceNotFoundException("Git Branch", gitBranchID, "")
		}
		if _, err := s.ExecContext(ctx, "UPDATE "+projectRepoQuote("project_git_branchs")+
			" SET "+projectRepoQuote("assigned_agent_id")+" = NULL, "+projectRepoQuote("updated_at")+" = $1 WHERE "+
			projectRepoQuote("id")+" = $2", database.TimestampNow(), gitBranchID); err != nil {
			return err
		}
		out = map[string]any{
			"success": true, "project_id": projectID, "git_branch_id": gitBranchID, "unassigned_agent_id": agentID,
		}
		return nil
	})
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to unassign agent: "+err.Error(), "unassign_agent_from_tree", "project_git_branchs")
	}
	return out, nil
}

// ---- ORM-specific methods ------------------------------------------------------

// CreateProject creates a project with authentication validation (create_project).
func (r *ORMProjectRepository) CreateProject(ctx context.Context, name, description string, userID *string) (*entities.Project, error) {
	var out *entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		if userID == nil {
			return exceptions.NewUserAuthenticationRequiredError("Project creation")
		}
		validated, err := domain.ValidateUserID(userID, "Project creation")
		if err != nil {
			return err
		}
		projectID := tmvo.NewUUIDv4()
		data := NewKwargs(
			"id", projectID,
			"name", name,
			"description", description,
			"user_id", validated,
			"status", "active",
			"model_metadata", json.RawMessage("{}"),
		)
		row, err := r.ORMRepository.insert(ctx, s, data)
		if err != nil {
			return err
		}
		out, err = r.projectRepoModelToEntity(ctx, s, row)
		return err
	})
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to create project: "+err.Error(), "create_project", "projects")
	}
	return out, nil
}

// GetProject loads a project by id without user isolation (get_project).
func (r *ORMProjectRepository) GetProject(ctx context.Context, projectID string) (*entities.Project, error) {
	var out *entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, projectID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		out, err = r.projectRepoModelToEntity(ctx, s, row)
		return err
	})
	return out, err
}

// UpdateProject updates a project with an optional "entity" kwarg plus direct updates.
func (r *ORMProjectRepository) UpdateProject(ctx context.Context, projectID string, updates Kwargs) (*entities.Project, error) {
	var out *entities.Project
	err := r.Transaction(ctx, func(ctx context.Context) error {
		row, err := r.ORMRepository.GetByID(ctx, projectID)
		if err != nil {
			return err
		}
		if row == nil {
			return exceptions.NewResourceNotFoundException("Project", projectID, "")
		}
		attrs := NewKwargs()
		if updates != nil {
			if raw, ok := updates.Get("entity"); ok {
				if entity, ok := raw.(*entities.Project); ok {
					attrs.Set("name", entity.Name)
					attrs.Set("description", entity.Description)
					attrs.Set("status", "active")
					attrs.Set("model_metadata", projectRepoModelMetadata(entity))
				}
			}
			for _, key := range updates.Keys() {
				if key == "entity" {
					continue
				}
				if _, ok := r.byAttr[key]; ok {
					v, _ := updates.Get(key)
					attrs.Set(key, v)
				}
			}
		}
		attrs.Set("updated_at", database.TimestampNow())
		if _, err := r.ORMRepository.Update(ctx, projectID, attrs); err != nil {
			return err
		}
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			updated, err := r.ORMRepository.getByID(ctx, s, projectID)
			if err != nil {
				return err
			}
			out, err = r.projectRepoModelToEntity(ctx, s, updated)
			return err
		})
	})
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to update project: "+err.Error(), "update_project", "projects")
	}
	return out, nil
}

// DeleteProject deletes a project row (delete_project); user scoping is bypassed like the
// Python fallback path.
func (r *ORMProjectRepository) DeleteProject(ctx context.Context, projectID string) (bool, error) {
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, projectID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		res, err := s.ExecContext(ctx, "DELETE FROM "+quoteIdent(r.Table.Name)+" WHERE "+r.pkColumn()+" = $1", projectID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// ListProjects lists projects with an optional status filter and pagination.
func (r *ORMProjectRepository) ListProjects(ctx context.Context, status *string, limit, offset int) ([]*entities.Project, error) {
	filters := r.scoped(NewKwargs())
	if status != nil {
		filters.Set("status", *status)
	}
	suffix := ` ORDER BY ` + projectRepoQuote("created_at") + ` DESC`
	suffix += fmt.Sprintf(" LIMIT %d", limit)
	if offset != 0 {
		suffix += fmt.Sprintf(" OFFSET %d", offset)
	}
	return r.projectRepoQuery(ctx, filters, suffix)
}

// GetProjectByName loads a project by name without user isolation.
func (r *ORMProjectRepository) GetProjectByName(ctx context.Context, name string) (*entities.Project, error) {
	var out *entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, " WHERE "+projectRepoQuote("name")+" = $1 LIMIT 1", name)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return nil
		}
		out, err = r.projectRepoModelToEntity(ctx, s, rows[0])
		return err
	})
	return out, err
}

// SearchProjects searches name/description with ILIKE.
func (r *ORMProjectRepository) SearchProjects(ctx context.Context, query string, limit int) ([]*entities.Project, error) {
	var out []*entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		pattern := "%" + query + "%"
		q := "SELECT " + r.selectList() + " FROM " + projectRepoQuote(r.Table.Name) +
			" WHERE " + projectRepoQuote("name") + " ILIKE $1 OR " + projectRepoQuote("description") + " ILIKE $1" +
			" ORDER BY " + projectRepoQuote("created_at") + " DESC" + fmt.Sprintf(" LIMIT %d", limit)
		rows, err := s.QueryContext(ctx, q, pattern)
		if err != nil {
			return err
		}
		var raw []*database.Project
		for rows.Next() {
			row := r.newRow()
			if err := rows.Scan(r.scanDest(row)...); err != nil {
				rows.Close()
				return err
			}
			raw = append(raw, row)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()
		for _, row := range raw {
			ent, err := r.projectRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, ent)
		}
		return nil
	})
	return out, err
}

// GetProjectStatistics returns per-project branch/task statistics.
func (r *ORMProjectRepository) GetProjectStatistics(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	var out *entities.OrderedMap[any]
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, projectID)
		if err != nil {
			return err
		}
		if row == nil {
			return exceptions.NewResourceNotFoundException("Project", projectID, "")
		}
		branches, err := r.projectRepoBranches.selectRows(ctx, s,
			" WHERE "+projectRepoQuote("project_id")+" = $1", row.ID)
		if err != nil {
			return err
		}
		totalBranches := len(branches)
		assignedBranches := 0
		totalTasks := int64(0)
		completedTasks := int64(0)
		for _, b := range branches {
			if b.AssignedAgentID != nil {
				assignedBranches++
			}
			totalTasks += b.TaskCount
			completedTasks += b.CompletedTaskCount
		}
		var completion any = 0
		if totalTasks > 0 {
			completion = float64(completedTasks) / float64(totalTasks) * 100
		}
		out = entities.NewOrderedMap[any]()
		out.Set("project_id", projectID)
		out.Set("project_name", row.Name)
		out.Set("status", row.Status)
		out.Set("total_branches", totalBranches)
		out.Set("assigned_branches", assignedBranches)
		out.Set("unassigned_branches", totalBranches-assignedBranches)
		out.Set("total_tasks", totalTasks)
		out.Set("completed_tasks", completedTasks)
		out.Set("completion_percentage", completion)
		out.Set("created_at", tmvo.IsoFormatNaive(row.CreatedAt))
		out.Set("updated_at", tmvo.IsoFormatNaive(row.UpdatedAt))
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// UpdateStatistics updates a project's updated_at (the statistic columns do not exist on the
// projects table, so the Python attribute writes are no-ops).
func (r *ORMProjectRepository) UpdateStatistics(ctx context.Context, projectID string, branchCount, taskCount, completedTasks, inProgressTasks, todoTasks *int, progressPercentage *float64) (bool, error) {
	updated := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, projectID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		if _, err := s.ExecContext(ctx, "UPDATE "+projectRepoQuote(r.Table.Name)+
			" SET "+projectRepoQuote("updated_at")+" = $1 WHERE "+projectRepoQuote("id")+" = $2",
			database.TimestampNow(), projectID); err != nil {
			return err
		}
		updated = true
		return nil
	})
	if err != nil {
		return false, nil
	}
	return updated, nil
}

// GetProjectSelectiveFields returns only the requested project fields.
func (r *ORMProjectRepository) GetProjectSelectiveFields(ctx context.Context, projectID string, fields any) (*entities.OrderedMap[any], error) {
	if r.FieldSelector == nil {
		return nil, nil
	}
	spec := r.FieldSelector.GetProjectFields(projectID, fields)
	optimized, _ := projectRepoSpecValue(spec, "optimized").(bool)
	fieldList := projectRepoSpecFields(spec)
	if optimized && len(fieldList) > 0 {
		if cached := r.FieldSelector.GetCachedFields(projectID, fieldList); cached != nil {
			return cached, nil
		}
	}
	var out *entities.OrderedMap[any]
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		if optimized && len(fieldList) > 0 {
			w, args, err := r.where(r.UserScopedORMRepository.scoped(NewKwargs("id", projectID)), 1)
			if err != nil {
				return err
			}
			rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
			if err != nil {
				return err
			}
			if len(rows) == 0 {
				return nil
			}
			data := entities.NewOrderedMap[any]()
			for _, f := range fieldList {
				if v, ok := projectRepoFieldValue(rows[0], f); ok {
					data.Set(f, v)
				}
			}
			r.FieldSelector.CacheFieldMapping(projectID, fieldList, data)
			out = data
			return nil
		}
		row, err := r.ORMRepository.getByID(ctx, s, projectID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		out = entities.NewOrderedMap[any]()
		out.Set("id", row.ID)
		out.Set("name", row.Name)
		out.Set("description", row.Description)
		out.Set("created_at", row.CreatedAt)
		out.Set("updated_at", row.UpdatedAt)
		out.Set("status", row.Status)
		return nil
	})
	if err != nil {
		return nil, nil
	}
	return out, nil
}

// ListProjectsSelectiveFields lists projects projecting only the requested fields.
func (r *ORMProjectRepository) ListProjectsSelectiveFields(ctx context.Context, fields any, status *string, limit, offset int) ([]*entities.OrderedMap[any], error) {
	if r.FieldSelector == nil {
		return nil, nil
	}
	if fields == nil {
		fields = r.FieldSelector.GetOptimalFieldSet("list", "project")
	}
	spec := r.FieldSelector.GetProjectFields("list_operation", fields)
	optimized, _ := projectRepoSpecValue(spec, "optimized").(bool)
	fieldList := projectRepoSpecFields(spec)
	if optimized && len(fieldList) > 0 {
		filters := r.scoped(NewKwargs())
		if status != nil {
			filters.Set("status", *status)
		}
		suffix := ` ORDER BY ` + projectRepoQuote("created_at") + ` DESC`
		suffix += fmt.Sprintf(" LIMIT %d", limit)
		if offset != 0 {
			suffix += fmt.Sprintf(" OFFSET %d", offset)
		}
		var out []*entities.OrderedMap[any]
		err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			w, args, err := r.where(filters, 1)
			if err != nil {
				return err
			}
			rows, err := r.selectRows(ctx, s, w+suffix, args...)
			if err != nil {
				return err
			}
			for _, row := range rows {
				data := entities.NewOrderedMap[any]()
				for _, f := range fieldList {
					if v, ok := projectRepoFieldValue(row, f); ok {
						data.Set(f, v)
					}
				}
				out = append(out, data)
			}
			return nil
		})
		if err != nil {
			return nil, nil
		}
		return out, nil
	}
	entitiesList, err := r.ListProjects(ctx, status, limit, offset)
	if err != nil {
		return nil, nil
	}
	out := make([]*entities.OrderedMap[any], 0, len(entitiesList))
	for _, p := range entitiesList {
		data := entities.NewOrderedMap[any]()
		data.Set("id", p.ID)
		data.Set("name", p.Name)
		data.Set("status", "active")
		data.Set("updated_at", p.UpdatedAt)
		out = append(out, data)
	}
	return out, nil
}

// GetFieldSelectorMetrics returns the field selector metrics.
func (r *ORMProjectRepository) GetFieldSelectorMetrics() map[string]int {
	if r.FieldSelector == nil {
		return map[string]int{}
	}
	return r.FieldSelector.GetMetrics()
}

// EstimateFieldOptimizationSavings estimates the savings of a field set.
func (r *ORMProjectRepository) EstimateFieldOptimizationSavings(fieldSet any) map[string]float64 {
	if r.FieldSelector == nil {
		return map[string]float64{}
	}
	return r.FieldSelector.EstimateSavings("project", fieldSet)
}

// CheckNameExists reports whether the name already exists for the user.
func (r *ORMProjectRepository) CheckNameExists(ctx context.Context, name string, excludeProjectID *string) (bool, error) {
	exists := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		filters := r.UserScopedORMRepository.scoped(NewKwargs("name", tmvo.PyStrip(name)))
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		if excludeProjectID != nil {
			args = append(args, *excludeProjectID)
			w += " AND " + projectRepoQuote("id") + fmt.Sprintf(" != $%d", len(args))
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

// ---- helpers -------------------------------------------------------------------

// projectRepoQuery runs a project query and converts every row.
func (r *ORMProjectRepository) projectRepoQuery(ctx context.Context, filters Kwargs, suffix string) ([]*entities.Project, error) {
	var out []*entities.Project
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			ent, err := r.projectRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, ent)
		}
		return nil
	})
	return out, err
}

// projectRepoQualifiedSelectList is the select list with a table alias.
func (r *ORMProjectRepository) projectRepoQualifiedSelectList(alias string) string {
	parts := make([]string, len(r.Table.Columns))
	for i, c := range r.Table.Columns {
		expr := alias + "." + projectRepoQuote(c.Name)
		if c.SQLType == "UUID" {
			expr += "::text AS " + projectRepoQuote(c.Name)
		}
		parts[i] = expr
	}
	return strings.Join(parts, ", ")
}

func projectRepoQuote(s string) string { return quoteIdent(s) }

func projectRepoPriorityString(p *tmvo.Priority) string {
	if p == nil {
		return "medium"
	}
	return p.Value
}

func projectRepoStatusString(s *tmvo.TaskStatus) string {
	if s == nil {
		return "todo"
	}
	return s.Value
}

// projectRepoSpecValue reads a field of the field-selector spec dict.
func projectRepoSpecValue(spec *entities.OrderedMap[any], key string) any {
	if spec == nil {
		return nil
	}
	v, _ := spec.Get(key)
	return v
}

func projectRepoSpecFields(spec *entities.OrderedMap[any]) []string {
	v := projectRepoSpecValue(spec, "fields")
	switch f := v.(type) {
	case []string:
		return f
	case []any:
		out := make([]string, 0, len(f))
		for _, x := range f {
			if s, ok := x.(string); ok {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}

// projectRepoFieldValue maps a Project attribute name to its row value.
func projectRepoFieldValue(row *database.Project, field string) (any, bool) {
	switch field {
	case "id":
		return row.ID, true
	case "name":
		return row.Name, true
	case "description":
		return row.Description, true
	case "status":
		return row.Status, true
	case "created_at":
		return row.CreatedAt, true
	case "updated_at":
		return row.UpdatedAt, true
	case "user_id":
		return row.UserID, true
	case "metadata", "model_metadata":
		return projectContextJSONMap(row.Metadata), true
	}
	return nil, false
}

// projectRepoBaseTimestamps builds the embedded timestamp entity.
func projectRepoBaseTimestamps(created, updated time.Time) base.BaseTimestampEntity {
	c, u := created, updated
	return base.BaseTimestampEntity{CreatedAt: &c, UpdatedAt: &u}
}
