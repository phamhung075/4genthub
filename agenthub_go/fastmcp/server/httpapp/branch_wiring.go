package httpapp

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
	"agenthub/fastmcp/task_management/interface/api_controllers"
)

// gitBranchRepo adapts ORMGitBranchRepository to services.GitBranchRepositoryPort. Python
// calls git_branch_repo.update(git_branch), but the ORM repository's update takes
// (branch_id, updates), so that call raises TypeError and update_git_branch reports it.
type gitBranchRepo struct {
	*infrarepos.ORMGitBranchRepository
}

func (gitBranchRepo) Update(context.Context, *entities.GitBranch) (bool, error) {
	return false, fmt.Errorf("ORMGitBranchRepository.update() missing 1 required positional argument: 'updates'")
}

var (
	_ services.GitBranchRepositoryPort     = gitBranchRepo{}
	_ facades.GitBranchFacadeBranchRepo    = gitBranchRepo{}
	_ facades.GitBranchFacadeTaskRepo      = (*infrarepos.ORMTaskRepository)(nil)
	_ repositories.GitBranchRepository     = gitBranchRepo{}
	_ api_controllers.BranchFacadeProvider = branchFacadeProvider{}
	_ api_controllers.BranchRepoProvider   = branchRepoProvider{}
	_ facades.GitBranchFacadeRepoProvider  = facadeRepoProvider{}
	_ facades.GitBranchFacadeTaskFactory   = facadeTaskFactory{}
)

func newGitBranchRepo(s *database.SessionManager, userID *string) (gitBranchRepo, error) {
	r, err := infrarepos.NewORMGitBranchRepository(s, userID, false)
	return gitBranchRepo{r}, err
}

func newProjectRepo(s *database.SessionManager, userID *string) (repositories.ProjectRepository, error) {
	return infrarepos.NewORMProjectRepository(s, userID)
}

// facadeRepoProvider is the RepositoryProviderService view GitBranchApplicationFacade uses.
type facadeRepoProvider struct{ sessions *database.SessionManager }

func (p facadeRepoProvider) GetGitBranchRepository(userID *string) (facades.GitBranchFacadeBranchRepo, error) {
	return newGitBranchRepo(p.sessions, userID)
}

func (p facadeRepoProvider) GetTaskRepository(projectID, userID *string) (facades.GitBranchFacadeTaskRepo, error) {
	return infrarepos.NewORMTaskRepository(p.sessions, nil, projectID, nil, userID, false)
}

// facadeTaskFactory is TaskRepositoryFactory.create_repository.
type facadeTaskFactory struct{ sessions *database.SessionManager }

func (f facadeTaskFactory) CreateRepository(_ context.Context, projectID, gitBranchName string, userID *string) (facades.GitBranchFacadeTaskRepo, error) {
	return infrarepos.NewORMTaskRepository(f.sessions, nil, &projectID, &gitBranchName, userID, false)
}

// branchFacadeProvider is FacadeService.get_branch_facade.
type branchFacadeProvider struct{ sessions *database.SessionManager }

func (p branchFacadeProvider) GetBranchFacade(projectID, userID *string) (*facades.GitBranchApplicationFacade, error) {
	projectRepo, err := newProjectRepo(p.sessions, userID)
	if err != nil {
		return nil, err
	}
	branchRepo, err := newGitBranchRepo(p.sessions, userID)
	if err != nil {
		return nil, err
	}
	svc, err := services.NewGitBranchService(projectRepo, branchRepo, nil, userID, nil)
	if err != nil {
		return nil, err
	}
	return facades.NewGitBranchApplicationFacade(svc, facadeRepoProvider{p.sessions}, facadeTaskFactory{p.sessions}, nil, nil, projectID, userID), nil
}

// branchRepoProvider is the RepositoryProviderService view BranchAPIController uses.
type branchRepoProvider struct{ sessions *database.SessionManager }

func (p branchRepoProvider) GetGitBranchRepository(_ any, userID *string) (repositories.GitBranchRepository, error) {
	return newGitBranchRepo(p.sessions, userID)
}

func (p branchRepoProvider) GetProjectRepository(_ any, userID *string) (repositories.ProjectRepository, error) {
	return newProjectRepo(p.sessions, userID)
}

// bulkQueryer runs the bulk-summary SQL; SQLAlchemy ":name" binds become $n.
type bulkQueryer struct{ sessions *database.SessionManager }

type bulkResult struct{ rows []api_controllers.BulkRow }

func (r bulkResult) FetchAll() []api_controllers.BulkRow { return r.rows }
func (r bulkResult) Iterate() []api_controllers.BulkRow  { return r.rows }

// bindNamed rewrites :name placeholders (not ::casts) to $n.
func bindNamed(query string, params map[string]any) (string, []any) {
	var sb strings.Builder
	var args []any
	index := map[string]int{}
	for i := 0; i < len(query); {
		c := query[i]
		if c == ':' && i+1 < len(query) && query[i+1] == ':' {
			sb.WriteString("::")
			i += 2
			continue
		}
		if c == ':' && i+1 < len(query) && (query[i+1] == '_' || query[i+1] >= 'a' && query[i+1] <= 'z' || query[i+1] >= 'A' && query[i+1] <= 'Z') {
			j := i + 1
			for j < len(query) && (query[j] == '_' || query[j] >= 'a' && query[j] <= 'z' || query[j] >= 'A' && query[j] <= 'Z' || query[j] >= '0' && query[j] <= '9') {
				j++
			}
			name := query[i+1 : j]
			n, ok := index[name]
			if !ok {
				args = append(args, params[name])
				n = len(args)
				index[name] = n
			}
			fmt.Fprintf(&sb, "$%d", n)
			i = j
			continue
		}
		sb.WriteByte(c)
		i++
	}
	return sb.String(), args
}

func (q bulkQueryer) Execute(ctx context.Context, query string, params map[string]any) (api_controllers.BulkResult, error) {
	sqlText, args := bindNamed(query, params)
	var out bulkResult
	err := q.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, sqlText, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		cols, err := rows.Columns()
		if err != nil {
			return err
		}
		for rows.Next() {
			vals := make([]any, len(cols))
			ptrs := make([]any, len(cols))
			for i := range vals {
				ptrs[i] = &vals[i]
			}
			if err := rows.Scan(ptrs...); err != nil {
				return err
			}
			out.rows = append(out.rows, vals)
		}
		return rows.Err()
	})
	return out, err
}

// branchResult adapts the typed controller responses to routes.BranchResult.
type branchResult struct {
	success  bool
	message  *string
	errorMsg *string
	dump     modelDumper
}

func (r branchResult) Success() bool                        { return r.success }
func (r branchResult) Message() *string                     { return r.message }
func (r branchResult) Error() *string                       { return r.errorMsg }
func (r branchResult) ModelDump() *entities.OrderedMap[any] { return r.dump.ModelDump() }

// branchControllerAdapter satisfies routes.BranchController.
type branchControllerAdapter struct {
	c        *api_controllers.BranchAPIController
	sessions *database.SessionManager
}

func (a branchControllerAdapter) CreateBranch(ctx context.Context, projectID, name, description, userID string) routes.BranchResult {
	r := a.c.CreateBranch(ctx, projectID, name, description, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) ListBranches(ctx context.Context, projectID *string, userID string) routes.BranchResult {
	pid := ""
	if projectID != nil {
		pid = *projectID
	}
	r := a.c.ListBranches(ctx, pid, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) GetBranch(ctx context.Context, branchID, userID string) routes.BranchResult {
	r := a.c.GetBranch(ctx, branchID, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) UpdateBranch(ctx context.Context, branchID string, name, description, status *string, userID string) routes.BranchResult {
	r := a.c.UpdateBranch(ctx, branchID, name, description, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) DeleteBranch(ctx context.Context, branchID, userID string) routes.BranchResult {
	r := a.c.DeleteBranch(ctx, branchID, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) AssignAgent(ctx context.Context, branchID, agentID, userID string) routes.BranchResult {
	r := a.c.AssignAgent(ctx, branchID, agentID, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) GetBranchTaskCounts(ctx context.Context, branchID, userID string) routes.BranchResult {
	r := a.c.GetBranchTaskCounts(ctx, branchID, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) GetBranchesWithTaskCounts(ctx context.Context, projectID, userID string) routes.BranchResult {
	r := a.c.GetBranchesWithTaskCounts(ctx, projectID, userID, nil)
	return branchResult{r.Success, r.Message, r.Error, r}
}

func (a branchControllerAdapter) GetBulkSummaries(ctx context.Context, projectIDs []string, userID string, includeArchived bool) routes.BranchResult {
	r := a.c.GetBulkSummaries(ctx, projectIDs, userID, includeArchived, bulkQueryer{a.sessions})
	return branchResult{r.Success, r.Message, nil, r}
}

// taskCounter is delete_project's direct Task-model count per branch.
type taskCounter struct{ sessions *database.SessionManager }

var _ services.ProjectTaskCounterPort = taskCounter{}

func (c taskCounter) CountTasksByBranch(ctx context.Context, branchID string) (int, error) {
	var n int
	err := c.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT COUNT(*) FROM tasks WHERE git_branch_id = $1::uuid`, branchID).Scan(&n)
	})
	return n, err
}
