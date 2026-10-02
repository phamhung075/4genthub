// Package services ports task_management/application/services/*.py.
package services

// OrchestratorService is the basic orchestrator placeholder
// (Python application/services/orchestrator.py).
type OrchestratorService struct {
	UserID *string
}

// NewOrchestratorService mirrors __init__(user_id=None).
func NewOrchestratorService(userID *string) *OrchestratorService {
	return &OrchestratorService{UserID: userID}
}

// WithUser creates a new service instance scoped to a specific user.
func (s *OrchestratorService) WithUser(userID string) *OrchestratorService {
	return NewOrchestratorService(&userID)
}

// serviceUserScopedRepository is the shared port of the repeated Python
// `_get_user_scoped_repository` helper: call repository.with_user(user_id) when a user is
// set and the repository exposes it, otherwise return the repository unchanged. The
// Python `elif hasattr(repository, "user_id")` reconstruction branch has no Go equivalent
// and is intentionally omitted.
func serviceUserScopedRepository(repository any, userID *string) any {
	if userID != nil && *userID != "" {
		if r, ok := repository.(interface{ WithUser(string) any }); ok {
			return r.WithUser(*userID)
		}
	}
	return repository
}

// getUserScopedRepository returns repository.with_user(user_id) when a user is set
// and the repository supports it, otherwise the repository unchanged.
func (s *OrchestratorService) getUserScopedRepository(repository any) any {
	return serviceUserScopedRepository(repository, s.UserID)
}
