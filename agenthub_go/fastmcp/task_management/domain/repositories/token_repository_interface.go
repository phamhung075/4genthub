package repositories

import (
	"context"
	"time"
)

// ITokenRepository is the repository interface for API tokens (tokens are
// opaque `any` values at the domain layer, as in Python).
type ITokenRepository interface {
	CreateToken(ctx context.Context, tokenData map[string]any) (any, error)
	GetToken(ctx context.Context, tokenID, userID string) (any, error)
	GetTokenByID(ctx context.Context, tokenID string) (any, error)
	// GetUserTokens pages tokens (Python defaults skip 0, limit 100).
	GetUserTokens(ctx context.Context, userID string, skip, limit int) ([]any, error)
	CountUserTokens(ctx context.Context, userID string) (int, error)
	RevokeToken(ctx context.Context, tokenID, userID string) (bool, error)
	ReactivateToken(ctx context.Context, tokenID, userID string) (bool, error)
	DeleteToken(ctx context.Context, tokenID, userID string) (bool, error)
	UpdateTokenUsage(ctx context.Context, tokenID string) (bool, error)
	CleanupExpiredTokens(ctx context.Context, expiryDate time.Time) (int, error)
}
