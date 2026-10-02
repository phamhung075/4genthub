// Token Balance Repository (Python auth/infrastructure/repositories/token_balance_repository.py):
// persistence for the UserTokenBalance aggregate. Python's session maps to the SessionManager;
// every method re-raises errors, so the Go methods return them.

package repositories

import (
	"context"
	"database/sql"
	"errors"
	"time"

	domainrepos "agenthub/fastmcp/auth/domain/repositories"
	authdb "agenthub/fastmcp/auth/infrastructure/database"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	tmrepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// TokenBalanceRepository is Python's TokenBalanceRepository(session).
type TokenBalanceRepository struct {
	base *tmrepo.ORMRepository[authdb.UserTokenBalance]
}

var _ domainrepos.ITokenBalanceRepository = (*TokenBalanceRepository)(nil)

// NewTokenBalanceRepository builds the repository over user_token_balances.
func NewTokenBalanceRepository(sessions *database.SessionManager) (*TokenBalanceRepository, error) {
	base, err := tmrepo.NewORMRepository[authdb.UserTokenBalance]("user_token_balances", sessions)
	if err != nil {
		return nil, err
	}
	return &TokenBalanceRepository{base: base}, nil
}

const tokenBalanceRepoSelect = `"id"::text, "user_id"::text, "available_tokens", "monthly_quota", ` +
	`"last_reset_at", "next_reset_at", "tokens_consumed_today", "tokens_consumed_this_month", ` +
	`"total_tokens_consumed", "created_at", "updated_at"`

// tokenBalanceFetch loads the balance row for a user, or nil.
func (r *TokenBalanceRepository) tokenBalanceFetch(ctx context.Context, s database.DBTX, userID string) (*authdb.UserTokenBalance, error) {
	bv, err := database.UnifiedUUIDBindParam(userID, database.DialectPostgres)
	if err != nil {
		return nil, err
	}
	row := &authdb.UserTokenBalance{}
	err = s.QueryRowContext(ctx,
		"SELECT "+tokenBalanceRepoSelect+" FROM user_token_balances WHERE user_id = $1 LIMIT 1", bv).
		Scan(&row.ID, &row.UserID, &row.AvailableTokens, &row.MonthlyQuota, &row.LastResetAt,
			&row.NextResetAt, &row.TokensConsumedToday, &row.TokensConsumedThisMonth,
			&row.TotalTokensConsumed, &row.CreatedAt, &row.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return row, nil
}

// tokenBalanceDict is the get_balance / create_balance dictionary.
func tokenBalanceDict(b *authdb.UserTokenBalance) map[string]any {
	return map[string]any{
		"id":                         b.ID,
		"user_id":                    b.UserID,
		"available_tokens":           b.AvailableTokens,
		"monthly_quota":              b.MonthlyQuota,
		"tokens_consumed_today":      b.TokensConsumedToday,
		"tokens_consumed_this_month": b.TokensConsumedThisMonth,
		"total_tokens_consumed":      b.TotalTokensConsumed,
		"last_reset_at":              b.LastResetAt,
		"next_reset_at":              b.NextResetAt,
		"created_at":                 b.CreatedAt,
		"updated_at":                 b.UpdatedAt,
	}
}

// GetBalance is get_balance; nil when the user has no balance.
func (r *TokenBalanceRepository) GetBalance(ctx context.Context, userID string) (map[string]any, error) {
	var out map[string]any
	err := r.base.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		b, err := r.tokenBalanceFetch(ctx, s, userID)
		if err != nil {
			return err
		}
		if b != nil {
			out = tokenBalanceDict(b)
		}
		return nil
	})
	return out, err
}

// CreateBalance is create_balance; it schedules the next reset on the first of next month.
func (r *TokenBalanceRepository) CreateBalance(ctx context.Context, userID string, initialTokens, monthlyQuota int) (map[string]any, error) {
	now := time.Now().UTC()
	nextReset := time.Date(now.Year(), now.Month()+1, 1, 0, 0, 0, 0, time.UTC)
	row, err := r.base.Create(ctx, tmrepo.NewKwargs(
		"id", tmvo.NewUUIDv4(),
		"user_id", userID,
		"available_tokens", initialTokens,
		"monthly_quota", monthlyQuota,
		"last_reset_at", now,
		"next_reset_at", nextReset,
		"tokens_consumed_today", 0,
		"tokens_consumed_this_month", 0,
		"total_tokens_consumed", 0,
	))
	if err != nil {
		return nil, err
	}
	return tokenBalanceDict(row), nil
}

// ConsumeTokens is consume_tokens: auto-reset, then deduct and update the counters.
func (r *TokenBalanceRepository) ConsumeTokens(ctx context.Context, userID string, amount int) (bool, error) {
	if amount <= 0 {
		return false, tmvo.ValueErrorf("Amount must be positive")
	}
	out := false
	err := r.base.Transaction(ctx, func(ctx context.Context) error {
		if _, err := r.checkAndAutoReset(ctx, userID); err != nil {
			return err
		}
		b, err := r.tokenBalanceGet(ctx, userID)
		if err != nil {
			return err
		}
		if b == nil {
			return nil
		}
		if b.AvailableTokens < int64(amount) {
			return nil
		}
		_, err = r.base.Update(ctx, b.ID, tmrepo.NewKwargs(
			"available_tokens", b.AvailableTokens-int64(amount),
			"tokens_consumed_today", b.TokensConsumedToday+int64(amount),
			"tokens_consumed_this_month", b.TokensConsumedThisMonth+int64(amount),
			"total_tokens_consumed", b.TotalTokensConsumed+int64(amount),
		))
		if err != nil {
			return err
		}
		out = true
		return nil
	})
	return out, err
}

// AddTokens is add_tokens.
func (r *TokenBalanceRepository) AddTokens(ctx context.Context, userID string, amount int) (bool, error) {
	if amount <= 0 {
		return false, tmvo.ValueErrorf("Amount must be positive")
	}
	b, err := r.tokenBalanceGet(ctx, userID)
	if err != nil {
		return false, err
	}
	if b == nil {
		return false, nil
	}
	if _, err := r.base.Update(ctx, b.ID, tmrepo.NewKwargs("available_tokens", b.AvailableTokens+int64(amount))); err != nil {
		return false, err
	}
	return true, nil
}

// UpdateQuota is update_quota.
func (r *TokenBalanceRepository) UpdateQuota(ctx context.Context, userID string, newQuota int) (bool, error) {
	if newQuota < 0 {
		return false, tmvo.ValueErrorf("Quota cannot be negative")
	}
	b, err := r.tokenBalanceGet(ctx, userID)
	if err != nil {
		return false, err
	}
	if b == nil {
		return false, nil
	}
	if _, err := r.base.Update(ctx, b.ID, tmrepo.NewKwargs("monthly_quota", newQuota)); err != nil {
		return false, err
	}
	return true, nil
}

// GetUsageStats is get_usage_stats; nil when the user has no balance.
func (r *TokenBalanceRepository) GetUsageStats(ctx context.Context, userID string) (map[string]any, error) {
	b, err := r.tokenBalanceGet(ctx, userID)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, nil
	}
	utilization := 0.0
	if b.MonthlyQuota > 0 {
		consumed := b.MonthlyQuota - b.AvailableTokens
		utilization = float64(consumed) / float64(b.MonthlyQuota) * 100
	}
	daysUntilReset := 0
	if b.NextResetAt != nil {
		if delta := b.NextResetAt.Sub(time.Now().UTC()); delta > 0 {
			daysUntilReset = int(delta / (24 * time.Hour))
		}
	}
	return map[string]any{
		"user_id":                    b.UserID,
		"available_tokens":           b.AvailableTokens,
		"monthly_quota":              b.MonthlyQuota,
		"tokens_consumed_today":      b.TokensConsumedToday,
		"tokens_consumed_this_month": b.TokensConsumedThisMonth,
		"total_tokens_consumed":      b.TotalTokensConsumed,
		"utilization_percentage":     tmvo.PyRound(utilization, 2),
		"days_until_reset":           daysUntilReset,
		"last_reset_at":              b.LastResetAt,
		"next_reset_at":              b.NextResetAt,
	}, nil
}

// ResetMonthlyQuota is reset_monthly_quota.
func (r *TokenBalanceRepository) ResetMonthlyQuota(ctx context.Context, userID string) (bool, error) {
	b, err := r.tokenBalanceGet(ctx, userID)
	if err != nil {
		return false, err
	}
	if b == nil {
		return false, nil
	}
	now := time.Now().UTC()
	nextReset := time.Date(now.Year(), now.Month()+1, 1, 0, 0, 0, 0, time.UTC)
	if _, err := r.base.Update(ctx, b.ID, tmrepo.NewKwargs(
		"available_tokens", b.MonthlyQuota,
		"tokens_consumed_this_month", 0,
		"last_reset_at", now,
		"next_reset_at", nextReset,
	)); err != nil {
		return false, err
	}
	return true, nil
}

// ResetDailyConsumption is reset_daily_consumption.
func (r *TokenBalanceRepository) ResetDailyConsumption(ctx context.Context, userID string) (bool, error) {
	b, err := r.tokenBalanceGet(ctx, userID)
	if err != nil {
		return false, err
	}
	if b == nil {
		return false, nil
	}
	if _, err := r.base.Update(ctx, b.ID, tmrepo.NewKwargs("tokens_consumed_today", 0)); err != nil {
		return false, err
	}
	return true, nil
}

// CheckAndAutoReset is check_and_auto_reset.
func (r *TokenBalanceRepository) CheckAndAutoReset(ctx context.Context, userID string) (bool, error) {
	return r.checkAndAutoReset(ctx, userID)
}

func (r *TokenBalanceRepository) checkAndAutoReset(ctx context.Context, userID string) (bool, error) {
	b, err := r.tokenBalanceGet(ctx, userID)
	if err != nil {
		return false, err
	}
	if b == nil || b.NextResetAt == nil {
		return false, nil
	}
	if !time.Now().UTC().Before(*b.NextResetAt) {
		if _, err := r.ResetMonthlyQuota(ctx, userID); err != nil {
			return false, err
		}
		return true, nil
	}
	return false, nil
}

// tokenBalanceGet loads the balance in its own session (used by the single-step methods).
func (r *TokenBalanceRepository) tokenBalanceGet(ctx context.Context, userID string) (*authdb.UserTokenBalance, error) {
	var out *authdb.UserTokenBalance
	err := r.base.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		b, err := r.tokenBalanceFetch(ctx, s, userID)
		out = b
		return err
	})
	return out, err
}
