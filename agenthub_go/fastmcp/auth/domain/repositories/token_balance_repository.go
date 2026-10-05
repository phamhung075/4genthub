package repositories

import "context"

// ITokenBalanceRepository is the repository interface of the UserTokenBalance
// aggregate. Balance dictionaries carry available_tokens, monthly_quota,
// tokens_consumed_today, tokens_consumed_this_month, total_tokens_consumed,
// last_reset_at and next_reset_at; usage stats carry utilization_percentage and
// days_until_reset instead of the reset timestamps. Methods that return
// `dict | None` in Python return a nil map when the user is not found.
type ITokenBalanceRepository interface {
	GetBalance(ctx context.Context, userID string) (map[string]any, error)
	// CreateBalance fails with an integrity error when a balance already exists.
	CreateBalance(ctx context.Context, userID string, initialTokens, monthlyQuota int) (map[string]any, error)
	// ConsumeTokens atomically deducts tokens and updates the counters; false when
	// the balance is insufficient, ValueError when amount <= 0.
	ConsumeTokens(ctx context.Context, userID string, amount int) (bool, error)
	// AddTokens returns false when the user is not found, ValueError when amount <= 0.
	AddTokens(ctx context.Context, userID string, amount int) (bool, error)
	// UpdateQuota returns false when the user is not found, ValueError when negative.
	UpdateQuota(ctx context.Context, userID string, newQuota int) (bool, error)
	GetUsageStats(ctx context.Context, userID string) (map[string]any, error)
	// ResetMonthlyQuota sets available_tokens = monthly_quota, clears the monthly
	// counter and schedules the next reset on the first day of the next month.
	ResetMonthlyQuota(ctx context.Context, userID string) (bool, error)
	ResetDailyConsumption(ctx context.Context, userID string) (bool, error)
	// CheckAndAutoReset resets when now >= next_reset_at and reports whether it did.
	CheckAndAutoReset(ctx context.Context, userID string) (bool, error)
}
