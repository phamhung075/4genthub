package httpapp

// MCP facade wiring: the project, git branch, agent and unified context facade
// factories FacadeService.get_*_facade uses. app.go's NewApp passes nil for all
// of them today, which makes every manage_project / manage_git_branch /
// manage_agent / manage_context call fail with "facade factory is not
// configured". Each adapter below implements the unexported
// services.*FacadeFactory method signature and builds the real facade over ORM
// repositories, exactly like projectFacadeProvider (app.go) and
// branchFacadeProvider (branch_wiring.go).

import (
	"context"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/factories"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// mcpProjectFacadeFactory is services.FacadeService's project factory over the
// controller-facing projectFacadeProvider (create_project_facade).
type mcpProjectFacadeFactory struct{ provider projectFacadeProvider }

func (f mcpProjectFacadeFactory) CreateProjectFacade(userID *string) (any, error) {
	return f.provider.CreateProjectFacade(userID)
}

// mcpBranchFacadeFactory is services.FacadeService's git branch factory over
// branchFacadeProvider (create_facade).
type mcpBranchFacadeFactory struct{ provider branchFacadeProvider }

func (f mcpBranchFacadeFactory) CreateFacade(projectID, userID *string) (any, error) {
	return f.provider.GetBranchFacade(projectID, userID)
}

// mcpAgentFacadeFactory is AgentFacadeFactory over the real ORM agent
// repository. Python constructs AgentApplicationFacade(AgentRepositoryFactory
// .create(user_id)); project_id only keys the factory cache there and is not
// passed to the repository.
type mcpAgentFacadeFactory struct{ sessions *database.SessionManager }

func (f mcpAgentFacadeFactory) CreateAgentFacade(projectID string, userID *string) (any, error) {
	if userID == nil || *userID == "" {
		return nil, &value_objects.ValueError{Msg: "user_id is required for agent facade creation (no fallback allowed for DDD compliance)"}
	}
	repo, err := infrarepos.NewORMAgentRepository(f.sessions, userID, nil)
	if err != nil {
		return nil, err
	}
	return facades.NewAgentApplicationFacade(repo), nil
}

// mcpContextFacadeFactory is services.FacadeService's unified context factory
// over UnifiedContextFacadeFactory (create_facade).
type mcpContextFacadeFactory struct {
	factory *factories.UnifiedContextFacadeFactory
	ctx     context.Context
}

func (f mcpContextFacadeFactory) CreateFacade(userID, projectID, gitBranchID *string) (any, error) {
	return f.factory.CreateFacade(f.ctx, userID, projectID, gitBranchID)
}

// mcpTokenFacadeFactory is services.FacadeService's token factory over
// infrarepos.NewTokenRepository and facades.NewTokenApplicationFacade.
//
// JWT_SECRET_KEY is REQUIRED here and is read from the environment by
// facades.NewTokenApplicationFacade, which refuses an unset secret with the
// shared auth.JWTSecretNotSetError (500, "Server configuration error: JWT
// secret not set"). That is the SAME decision providers.NewJWTBearerAuthProvider
// and the REST dependency chain make (they refuse without a secret), so every
// component agrees that "unset" means "refuse" and names the variable the same way.
//
// This factory used to invent a value first: when the variable was empty it ran
// os.Setenv("JWT_SECRET_KEY", "default-jwt-secret-key-for-token-facade-32b")
// before building the facade. That made the secret PROCESS-LOCAL state: the
// process that minted a token had the default in its environment and its
// validators accepted the token, while every replica that never minted kept an
// empty environment and refused it. The same token then returned 101 from one
// process and 403 from the others. The default is gone; one decision about the
// secret is used everywhere, so nothing is minted unless the operator set the
// variable.
//
// Operational consequence (do not carry a minted token across a restart): a
// token is only valid where the SAME JWT_SECRET_KEY is configured. That is a
// deployment property, not a database one - the token row stores no secret and
// cannot record it - so the rule lives with the variable in .env.sample.
type mcpTokenFacadeFactory struct {
	sessions *database.SessionManager
}

func (f mcpTokenFacadeFactory) CreateTokenFacade() (any, error) {
	var repo domainrepos.ITokenRepository
	if f.sessions != nil {
		r, err := infrarepos.NewTokenRepository(f.sessions)
		if err != nil {
			return nil, err
		}
		repo = r
	}
	return facades.NewTokenApplicationFacade(repo)
}

// buildMCPFacadeFactories returns the project, git branch, agent, unified
// context and token facade factories that NewFacadeService takes as its third
// to seventh arguments. sessions and ctxFactory are the ones NewApp already
// builds; pass the five results straight through to services.NewFacadeService
// so that none of those factories is nil.
func buildMCPFacadeFactories(ctx context.Context, sessions *database.SessionManager, ctxFactory *factories.UnifiedContextFacadeFactory) (
	project mcpProjectFacadeFactory,
	branch mcpBranchFacadeFactory,
	agent mcpAgentFacadeFactory,
	unifiedContext mcpContextFacadeFactory,
	token mcpTokenFacadeFactory,
) {
	project = mcpProjectFacadeFactory{provider: projectFacadeProvider{sessions: sessions, ctxFactory: ctxFactory}}
	branch = mcpBranchFacadeFactory{provider: branchFacadeProvider{sessions: sessions}}
	agent = mcpAgentFacadeFactory{sessions: sessions}
	unifiedContext = mcpContextFacadeFactory{factory: ctxFactory, ctx: ctx}
	token = mcpTokenFacadeFactory{sessions: sessions}
	return
}
