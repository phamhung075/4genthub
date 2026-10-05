// Token Facade Factory (Python task_management/application/factories/token_facade_factory.py).
//
// The Python factory imports TokenRepository from infrastructure when a session is given;
// the application layer must not import infrastructure, so that construction goes through
// facades.TokenFacadeRepositoryBackend. It implements the Python singleton pattern with
// package-level state.
package factories

import (
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// tokenFacadeFactoryInstance is the class-level `_instance`.
var tokenFacadeFactoryInstance *TokenFacadeFactory

// tokenFacadeFactoryInitialized is the class-level `_initialized`.
var tokenFacadeFactoryInitialized bool

// TokenFacadeFactory mirrors token_facade_factory.TokenFacadeFactory.
type TokenFacadeFactory struct{}

// GetInstance mirrors the get_instance classmethod.
func (f *TokenFacadeFactory) GetInstance() *TokenFacadeFactory {
	factoriesMu.Lock()
	defer factoriesMu.Unlock()
	if tokenFacadeFactoryInstance == nil {
		tokenFacadeFactoryInstance = &TokenFacadeFactory{}
	}
	return tokenFacadeFactoryInstance
}

// zpTokenFacadeFactoryInit mirrors __init__ (skips work when already initialized).
func (f *TokenFacadeFactory) zpTokenFacadeFactoryInit() {
	if tokenFacadeFactoryInitialized {
		return
	}
	tokenFacadeFactoryInitialized = true
}

// CreateTokenFacade mirrors create_token_facade.
func (f *TokenFacadeFactory) CreateTokenFacade(session any) (*facades.TokenApplicationFacade, error) {
	var tokenRepository repositories.ITokenRepository
	if session != nil && facades.TokenFacadeRepositoryBackend != nil {
		repo, err := facades.TokenFacadeRepositoryBackend(session)
		if err != nil {
			return nil, err
		}
		tokenRepository = repo
	}
	return facades.NewTokenApplicationFacade(tokenRepository)
}

// CreateTokenFacadeWithoutRepository mirrors create_token_facade_without_repository.
func (f *TokenFacadeFactory) CreateTokenFacadeWithoutRepository() (*facades.TokenApplicationFacade, error) {
	return facades.NewTokenApplicationFacade(nil)
}
