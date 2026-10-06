// token_api_controller.go ports
// task_management/interface/api_controllers/token_api_controller.TokenAPIController.
package api_controllers

import (
	"context"

	authpkg "agenthub/fastmcp/auth"
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
//
// It reports two conditions that callers MUST keep distinct:
//   - a non-nil error: the facade could not be built (e.g. an unset JWT_SECRET_KEY, which
//     NewTokenApplicationFacade refuses). The cause is actionable, so callers return it
//     unchanged;
//   - (nil, nil): the resolved facade failed the TokenManageFacade type assertion. That is
//     a composition-root invariant with no cause to carry, so callers deliberately report
//     the bare failure rather than fabricating one.
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
//
// No Go caller exists yet (the REST surface exposes only the nine methods of
// routes.TokenRouteController), so this port keeps its single-value signature and has no
// channel to carry a facade-resolution cause on. The two clauses stay distinct so the
// discard is read as DELIBERATE, not harmless: the first caller wired to this method must
// give it the error return its REST-backed siblings already have instead of extending it.
func (c *TokenAPIController) RevokeUserTokens(ctx context.Context, userID string) *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil {
		// Deliberate discard: no caller exists to carry this cause to (see the doc
		// comment). It is not assumed harmless.
		return nil
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil
	}
	return facade.RevokeUserTokens(ctx, userID)
}

// GetTokenStats mirrors get_token_stats.
//
// Like RevokeUserTokens, this port has no Go caller, so its behaviour is kept deliberately
// and the first caller must add the error return (see that method's doc comment).
func (c *TokenAPIController) GetTokenStats() *entities.OrderedMap[any] {
	facade, err := c.ensureFacade()
	if err != nil {
		// Deliberate discard: no caller exists to carry this cause to (see the doc
		// comment). It is not assumed harmless.
		return nil
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil
	}
	return facade.GetTokenStats()
}

// CleanupExpiredTokens mirrors cleanup_expired_tokens. A facade-resolution failure
// surfaces the cause instead of a nil map (see ensureFacade).
func (c *TokenAPIController) CleanupExpiredTokens(ctx context.Context) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.CleanupExpiredTokens(ctx), nil
}

// ListUserTokens mirrors list_user_tokens(user_id, session, skip, limit). A
// facade-resolution failure surfaces the cause instead of a nil map (see ensureFacade).
func (c *TokenAPIController) ListUserTokens(ctx context.Context, userID string, session any, skip, limit int) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.ListUserTokens(ctx, userID, session, skip, limit), nil
}

// GetTokenDetails mirrors get_token_details. A facade-resolution failure surfaces the
// cause instead of a nil map (see ensureFacade).
func (c *TokenAPIController) GetTokenDetails(ctx context.Context, tokenID, userID string, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.GetTokenDetails(ctx, tokenID, userID, session), nil
}

// RevokeToken mirrors revoke_token. A facade-resolution failure surfaces the cause
// instead of a nil map (see ensureFacade).
func (c *TokenAPIController) RevokeToken(ctx context.Context, tokenID, userID string, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.RevokeToken(ctx, tokenID, userID, session), nil
}

// GenerateAPIToken mirrors generate_api_token. It returns the facade-resolution error,
// as the REST-backed sibling methods now do: an unset JWT_SECRET_KEY makes
// NewTokenApplicationFacade refuse, and that cause must reach the caller as the same
// actionable 500 the REST dependency path raises, not be flattened into a bare
// "Failed to generate token".
func (c *TokenAPIController) GenerateAPIToken(ctx context.Context, userID, name string, scopes []string, expiresInDays int, rateLimit *int, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Failed to generate token"}
	}
	result := facade.CreateAPIToken(ctx, userID, name, scopes, expiresInDays, rateLimit, entities.NewOrderedMap[any](), session)
	if sacSuccess(result) {
		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		out.Set("token_data", sacGet(result, "token"))
		return out, nil
	}
	return result, nil
}

// DeleteToken mirrors delete_token. A facade-resolution failure surfaces the cause
// instead of a nil map (see ensureFacade).
func (c *TokenAPIController) DeleteToken(ctx context.Context, tokenID, userID string, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.DeleteToken(ctx, tokenID, userID, session), nil
}

// ReactivateToken mirrors reactivate_token. A facade-resolution failure surfaces the
// cause instead of a nil map (see ensureFacade).
func (c *TokenAPIController) ReactivateToken(ctx context.Context, tokenID, userID string, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.ReactivateToken(ctx, tokenID, userID, session), nil
}

// RotateToken mirrors rotate_token. A facade-resolution failure surfaces the cause
// instead of a nil map (see ensureFacade).
func (c *TokenAPIController) RotateToken(ctx context.Context, tokenID, userID string, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.RotateToken(ctx, tokenID, userID, session), nil
}

// ValidateToken mirrors validate_token. A facade-resolution failure surfaces the cause
// instead of a nil map (see ensureFacade).
func (c *TokenAPIController) ValidateToken(ctx context.Context, token string, session any) (*entities.OrderedMap[any], error) {
	facade, err := c.ensureFacade()
	if err != nil {
		return nil, err
	}
	if facade == nil {
		// Composition-root invariant: no cause to carry (see ensureFacade).
		return nil, nil
	}
	return facade.ValidateToken(ctx, token, session), nil
}
