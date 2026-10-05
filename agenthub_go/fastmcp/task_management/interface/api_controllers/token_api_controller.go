// token_api_controller.go ports
// task_management/interface/api_controllers/token_api_controller.TokenAPIController.
package api_controllers

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TokenFacadeProvider is the consumer-side view of FacadeService for tokens.
// The signature matches services.FacadeService.GetTokenFacade.
type TokenFacadeProvider interface {
	GetTokenFacade() (any, error)
}

// TokenManageFacade is the token application facade surface used here.
type TokenManageFacade interface {
	RevokeUserTokens(ctx context.Context, userID string) *entities.OrderedMap[any]
	GetTokenStats() *entities.OrderedMap[any]
	CleanupExpiredTokens(ctx context.Context) *entities.OrderedMap[any]
	CreateAPIToken(ctx context.Context, userID, name string, scopes []string, expiresInDays int, rateLimit *int, metadata *entities.OrderedMap[any], session any) *entities.OrderedMap[any]
	ListUserTokens(ctx context.Context, userID string, session any, skip, limit int) *entities.OrderedMap[any]
	GetTokenDetails(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any]
	RevokeToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any]
	DeleteToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any]
	ReactivateToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any]
	RotateToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any]
	ValidateToken(ctx context.Context, token string, session any) *entities.OrderedMap[any]
}

// TokenAPIController mirrors TokenAPIController.
type TokenAPIController struct {
	facadeService TokenFacadeProvider
	tokenFacade   TokenManageFacade
}

// NewTokenAPIController builds the controller. Python uses
// FacadeService.get_instance() and leaves token_facade nil.
func NewTokenAPIController(facadeService TokenFacadeProvider) *TokenAPIController {
	return &TokenAPIController{facadeService: facadeService}
}

// ensureFacade lazily resolves the token facade like the Python `if not self.token_facade`.
func (c *TokenAPIController) ensureFacade() (TokenManageFacade, error) {
	if c.tokenFacade != nil {
		return c.tokenFacade, nil
	}
	raw, err := c.facadeService.GetTokenFacade()
	if err != nil {
		return nil, err
	}
	facade, _ := raw.(TokenManageFacade)
	c.tokenFacade = facade
	return facade, nil
}

// RevokeUserTokens mirrors revoke_user_tokens.
func (c *TokenAPIController) RevokeUserTokens(ctx context.Context, userID string) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.RevokeUserTokens(ctx, userID)
}

// GetTokenStats mirrors get_token_stats.
func (c *TokenAPIController) GetTokenStats() *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.GetTokenStats()
}

// CleanupExpiredTokens mirrors cleanup_expired_tokens.
func (c *TokenAPIController) CleanupExpiredTokens(ctx context.Context) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.CleanupExpiredTokens(ctx)
}

// ListUserTokens mirrors list_user_tokens(user_id, session, skip, limit).
func (c *TokenAPIController) ListUserTokens(ctx context.Context, userID string, session any, skip, limit int) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.ListUserTokens(ctx, userID, session, skip, limit)
}

// GetTokenDetails mirrors get_token_details.
func (c *TokenAPIController) GetTokenDetails(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.GetTokenDetails(ctx, tokenID, userID, session)
}

// RevokeToken mirrors revoke_token.
func (c *TokenAPIController) RevokeToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.RevokeToken(ctx, tokenID, userID, session)
}

// GenerateAPIToken mirrors generate_api_token.
func (c *TokenAPIController) GenerateAPIToken(ctx context.Context, userID, name string, scopes []string, expiresInDays int, rateLimit *int, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	result := facade.CreateAPIToken(ctx, userID, name, scopes, expiresInDays, rateLimit, entities.NewOrderedMap[any](), session)
	if sacSuccess(result) {
		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		out.Set("token_data", sacGet(result, "token"))
		return out
	}
	return result
}

// DeleteToken mirrors delete_token.
func (c *TokenAPIController) DeleteToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.DeleteToken(ctx, tokenID, userID, session)
}

// ReactivateToken mirrors reactivate_token.
func (c *TokenAPIController) ReactivateToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.ReactivateToken(ctx, tokenID, userID, session)
}

// RotateToken mirrors rotate_token.
func (c *TokenAPIController) RotateToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.RotateToken(ctx, tokenID, userID, session)
}

// ValidateToken mirrors validate_token.
func (c *TokenAPIController) ValidateToken(ctx context.Context, token string, session any) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil || facade == nil {
		return nil
	}
	return facade.ValidateToken(ctx, token, session)
}
