package httpapp

import (
	"context"
	"net/http"

	"agenthub/fastmcp/auth"
	authapi "agenthub/fastmcp/auth/api"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/hooks"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
	interfacelayer "agenthub/fastmcp/task_management/interface"
	"agenthub/fastmcp/task_management/interface/api_controllers"
	taskapicontroller "agenthub/fastmcp/task_management/interface/api_controllers/task_api_controller"
)

// App holds the composed dependency graph.
type App struct {
	Sessions *database.SessionManager

	projects routes.ProjectController
	branches routes.BranchController
	tasks    routes.UserTaskController
	subtasks routes.SubtaskController
	mcpTools *interfacelayer.DDDCompliantMCPTools
}

// NewApp wires repositories, services, hooks and controllers over sessions.
func NewApp(ctx context.Context, sessions *database.SessionManager) (*App, error) {
	authinterface.GetCurrentUserUniversal = auth.GetCurrentUserUniversal
	a := &App{Sessions: sessions}
	factories.UnifiedContextRepositoryBuilder = unifiedContextRepositories
	factories.UnifiedContextEntityLookup = contextEntityLookup{sessions}
	services.SetRepositoryProviderBackend(func() services.RepositoryProviderBackend { return repoBackend{sessions} })
	facades.TokenFacadeRepositoryBackend = func(any) (repositories.ITokenRepository, error) {
		return infrarepos.NewTokenRepository(sessions)
	}
	ctxFactory := factories.NewUnifiedContextFacadeFactory(ctx, sessions)
	a.projects = projectControllerAdapter{c: api_controllers.NewProjectAPIController(projectFacadeProvider{sessions: sessions, ctxFactory: ctxFactory})}
	a.branches = branchControllerAdapter{c: api_controllers.NewBranchAPIController(branchFacadeProvider{sessions}, branchRepoProvider{sessions}), sessions: sessions}
	taskProvider := taskFacadeProvider{sessions: sessions, ctxFactory: ctxFactory, notifier: &services.WebSocketNotificationService{}}
	projectFactory, branchFactory, agentFactory, contextFactory, tokenFactory := buildMCPFacadeFactories(ctx, sessions, ctxFactory)
	facadeService := services.NewFacadeService(taskFacadeFactory{taskProvider}, subtaskFacadeFactory{factory: factories.NewSubtaskFacadeFactory(services.RepositoryProviderService{}.GetInstance()), ctxFactory: ctxFactory, sessions: sessions}, projectFactory, branchFactory, agentFactory, contextFactory, tokenFactory)
	services.SetInstance(facadeService)
	a.tasks = userTaskControllerAdapter{c: taskapicontroller.NewTaskAPIController(facadeService)}
	a.subtasks = subtaskControllerAdapter{c: api_controllers.NewSubtaskAPIController(facadeService).WithSubtaskRepositories(func(userID *string) (repositories.SubtaskRepository, error) {
		return infrarepos.NewORMSubtaskRepository(sessions, userID)
	})}
	manageSeat, err := newManageSeatController(sessions)
	if err != nil {
		return nil, err
	}
	callSeat := newCallSeatController(sessions)
	// The friction channel needs BOTH of its lines together: this composition, which constructs
	// the seat_feedback repository at BOOT (and so needs the table registered), and the mount
	// below. Composed without the table the process dies with `app: unknown table
	// "seat_feedback"`; mounted without the composition the routes answer 500. They landed with
	// the table, and 947bb81b is the entry. See app_boot_test.go for the check that boots this.
	submitFeedback, err := newSubmitFeedbackController(sessions)
	if err != nil {
		return nil, err
	}
	mcpTools, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     facadeService,
		DatabaseAvailable: true,
		ManageSeat:        manageSeat,
		CallSeat:          callSeat,
		SubmitFeedback:    submitFeedback,
	}, nil)
	if err != nil {
		return nil, err
	}
	a.mcpTools = mcpTools
	if err := wireMissedNotificationStore(sessions); err != nil {
		return nil, err
	}
	return a, nil
}

// projectFacadeProvider is FacadeService.get_project_facade for the project controller.
type projectFacadeProvider struct {
	sessions   *database.SessionManager
	ctxFactory *factories.UnifiedContextFacadeFactory
}

func (p projectFacadeProvider) CreateProjectFacade(userID *string) (*facades.ProjectApplicationFacade, error) {
	repoFor := func(uid string) repositories.ProjectRepository {
		var u *string
		if uid != "" {
			u = &uid
		}
		repo, err := infrarepos.NewORMProjectRepository(p.sessions, u)
		if err != nil {
			panic(err)
		}
		return repo
	}
	hk := &hooks.ProjectHooks{ContextFactory: p.ctxFactory}
	build := func(uid string) *services.ProjectManagementService {
		var u *string
		if uid != "" {
			u = &uid
		}
		var branchRepo services.ProjectGitBranchRepositoryPort
		if r, err := newGitBranchRepo(p.sessions, u); err == nil {
			branchRepo = r
		}
		return services.NewProjectManagementService(repoFor(uid), u, nil, branchRepo, taskCounter{p.sessions}, hk)
	}
	return facades.NewProjectApplicationFacadeFromBuilder(build, facades.ProjectRepositoryManagerFunc(repoFor), userID), nil
}

// Handler returns the HTTP mux.
func (a *App) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handleHealth)
	a.registerProjectRoutes(mux)
	a.registerBranchRoutes(mux)
	a.registerTaskRoutes(mux)
	a.registerSubtaskRoutes(mux)
	a.registerSessionStreamRoutes(mux)
	a.registerMCPRoutes(mux)
	authinterface.NewAuthController().RegisterRoutes(mux)
	authapi.NewSupabaseAuthController().RegisterRoutes(mux)
	mountRoutes(mux, newRouteDeps(a))
	mountWebSockets(mux, a.Sessions)
	mountSeatRoutes(mux, a.Sessions)
	mountSeatAdminRoutes(mux, a.Sessions)
	mountSeatRigSpecRoutes(mux, a.Sessions)
	mountSeatStatusRoutes(mux, a.Sessions)
	mountSeatFeedbackRoutes(mux, a.Sessions)
	mountMachineTokenRoutes(mux, a.Sessions)
	mountTeamRoutes(mux, a.Sessions)
	mountMiscRoutes(mux)
	return withCORS(mux)
}

func (a *App) registerProjectRoutes(mux *http.ServeMux) {
	const base = "/api/v2/projects"
	mux.HandleFunc("POST "+base+"/", func(w http.ResponseWriter, r *http.Request) {
		u, ok := currentUser(w, r)
		if !ok {
			return
		}
		_ = r.ParseForm()
		if miss := missingForm(r, "name"); len(miss) > 0 {
			writeMissing(w, "body", miss...)
			return
		}
		body, err := routes.CreateProject(r.Context(), r.PostForm.Get("name"), r.PostForm.Get("description"), u, a.projects)
		writeResult(w, body, err)
	})
	mux.HandleFunc("GET "+base+"/", func(w http.ResponseWriter, r *http.Request) {
		u, ok := currentUser(w, r)
		if !ok {
			return
		}
		body, err := routes.ListProjects(r.Context(), u, a.projects)
		writeResult(w, body, err)
	})
	mux.HandleFunc("GET "+base+"/{id}", func(w http.ResponseWriter, r *http.Request) {
		u, ok := currentUser(w, r)
		if !ok {
			return
		}
		body, err := routes.GetProject(r.Context(), r.PathValue("id"), u, a.projects)
		writeResult(w, body, err)
	})
	mux.HandleFunc("PUT "+base+"/{id}", func(w http.ResponseWriter, r *http.Request) {
		u, ok := currentUser(w, r)
		if !ok {
			return
		}
		if err := r.ParseForm(); err != nil {
			writeDetail(w, http.StatusUnprocessableEntity, "Invalid form")
			return
		}
		var name, desc *string
		if r.PostForm.Has("name") {
			v := r.PostForm.Get("name")
			name = &v
		}
		if r.PostForm.Has("description") {
			v := r.PostForm.Get("description")
			desc = &v
		}
		body, err := routes.UpdateProject(r.Context(), r.PathValue("id"), name, desc, u, a.projects)
		writeResult(w, body, err)
	})
	mux.HandleFunc("DELETE "+base+"/{id}", func(w http.ResponseWriter, r *http.Request) {
		u, ok := currentUser(w, r)
		if !ok {
			return
		}
		body, err := routes.DeleteProject(r.Context(), r.PathValue("id"), u, a.projects)
		writeResult(w, body, err)
	})
	mux.HandleFunc("POST "+base+"/{id}/health-check", func(w http.ResponseWriter, r *http.Request) {
		u, ok := currentUser(w, r)
		if !ok {
			return
		}
		body, err := routes.ProjectHealthCheck(r.Context(), r.PathValue("id"), u, a.projects)
		writeResult(w, body, err)
	})
}
