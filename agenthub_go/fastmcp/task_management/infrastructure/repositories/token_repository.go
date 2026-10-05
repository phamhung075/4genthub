package repositories

// Token Repository (Python infrastructure/repositories/token_repository.py): API token
// persistence. The Python methods are async but issue synchronous SQLAlchemy calls; the Go
// forms are synchronous. Every Python method swallows exceptions and returns a fallback
// (None / [] / 0 / False), which the Go methods reproduce. The ApiToken fallback model is
// not ported, so get_token_by_id / reactivate / delete / update_usage read APIToken only.
// update_token_usage also drops the optional `operation` argument because the Go
// ITokenRepository interface does not carry it.

import (
	"context"
	"time"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TokenRepository is Python's TokenRepository.
type TokenRepository struct {
	*ORMRepository[database.APIToken]
}

var _ domainrepos.ITokenRepository = (*TokenRepository)(nil)

// NewTokenRepository builds the repository.
func NewTokenRepository(sessions *database.SessionManager) (*TokenRepository, error) {
	base, err := NewORMRepository[database.APIToken]("api_tokens", sessions)
	if err != nil {
		return nil, err
	}
	return &TokenRepository{ORMRepository: base}, nil
}

// CreateToken inserts a token; any failure returns nil, like the Python except clause.
func (r *TokenRepository) CreateToken(ctx context.Context, tokenData map[string]any) (any, error) {
	scopes := tokenData["scopes"]
	if !tmvo.PyTruthy(scopes) {
		scopes = []any{}
	}
	rateLimit := tokenData["rate_limit"]
	if !tmvo.PyTruthy(rateLimit) {
		rateLimit = 1000
	}
	tokenMetadata := tokenData["token_metadata"]
	if !tmvo.PyTruthy(tokenMetadata) {
		tokenMetadata = map[string]any{}
	}
	kwargs := NewKwargs(
		"id", tokenData["id"],
		"user_id", tokenData["user_id"],
		"name", tokenData["name"],
		"token_hash", tokenData["token_hash"],
		"scopes", scopes,
		"expires_at", tokenData["expires_at"],
		"rate_limit", rateLimit,
		"token_metadata", tokenMetadata,
	)
	row, err := r.Create(ctx, kwargs)
	if err != nil {
		return nil, nil
	}
	return row, nil
}

// GetToken returns a token for a user, or nil.
func (r *TokenRepository) GetToken(ctx context.Context, tokenID, userID string) (any, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", tokenID, "user_id", userID))
	if err != nil || row == nil {
		return nil, nil
	}
	return row, nil
}

// GetTokenByID returns a token by id regardless of user, or nil.
func (r *TokenRepository) GetTokenByID(ctx context.Context, tokenID string) (any, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", tokenID))
	if err != nil || row == nil {
		return nil, nil
	}
	return row, nil
}

// GetUserTokens pages a user's tokens, newest first.
func (r *TokenRepository) GetUserTokens(ctx context.Context, userID string, skip, limit int) ([]any, error) {
	out := []any{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, " WHERE user_id = $1 ORDER BY created_at DESC OFFSET $2 LIMIT $3", userID, skip, limit)
		if err != nil {
			return err
		}
		for _, row := range rows {
			out = append(out, any(row))
		}
		return nil
	})
	if err != nil {
		return []any{}, nil
	}
	return out, nil
}

// CountUserTokens counts a user's tokens.
func (r *TokenRepository) CountUserTokens(ctx context.Context, userID string) (int, error) {
	n, err := r.Count(ctx, NewKwargs("user_id", userID))
	if err != nil {
		return 0, nil
	}
	return n, nil
}

// RevokeToken marks a token inactive.
func (r *TokenRepository) RevokeToken(ctx context.Context, tokenID, userID string) (bool, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", tokenID, "user_id", userID))
	if err != nil || row == nil {
		return false, nil
	}
	if _, err := r.Update(ctx, tokenID, NewKwargs("is_active", false)); err != nil {
		return false, nil
	}
	return true, nil
}

// ReactivateToken marks a token active again.
func (r *TokenRepository) ReactivateToken(ctx context.Context, tokenID, userID string) (bool, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", tokenID, "user_id", userID))
	if err != nil || row == nil {
		return false, nil
	}
	if _, err := r.Update(ctx, tokenID, NewKwargs("is_active", true)); err != nil {
		return false, nil
	}
	return true, nil
}

// DeleteToken permanently deletes a user's token.
func (r *TokenRepository) DeleteToken(ctx context.Context, tokenID, userID string) (bool, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", tokenID, "user_id", userID))
	if err != nil || row == nil {
		return false, nil
	}
	deleted, err := r.Delete(ctx, tokenID)
	if err != nil {
		return false, nil
	}
	return deleted, nil
}

// UpdateTokenUsage records last use and increments the usage counter.
func (r *TokenRepository) UpdateTokenUsage(ctx context.Context, tokenID string) (bool, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", tokenID))
	if err != nil || row == nil {
		return false, nil
	}
	if _, err := r.Update(ctx, tokenID, NewKwargs("last_used_at", Now().UTC(), "usage_count", row.UsageCount+1)); err != nil {
		return false, nil
	}
	return true, nil
}

// CleanupExpiredTokens deletes tokens that expired before expiryDate and returns the count.
func (r *TokenRepository) CleanupExpiredTokens(ctx context.Context, expiryDate time.Time) (int, error) {
	count := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		if err := s.QueryRowContext(ctx, "SELECT count(*) FROM "+quoteIdent(r.Table.Name)+" WHERE expires_at < $1", expiryDate).Scan(&count); err != nil {
			return err
		}
		_, err := s.ExecContext(ctx, "DELETE FROM "+quoteIdent(r.Table.Name)+" WHERE expires_at < $1", expiryDate)
		return err
	})
	if err != nil {
		return 0, nil
	}
	return count, nil
}
