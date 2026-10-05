// Token consumption application service, ported from
// agenthub_main/src/fastmcp/auth/application/services/token_consumption_service.py.
package services

import (
	"context"
	"fmt"

	authconfig "agenthub/fastmcp/auth/config"
	domainrepos "agenthub/fastmcp/auth/domain/repositories"
	tmvalueobjects "agenthub/fastmcp/task_management/domain/value_objects"
)

// TokenConsumptionResult is the result of a token consumption attempt.
type TokenConsumptionResult struct {
	Success          bool
	RemainingBalance *int
	Consumed         *int
	ErrorMessage     *string
	ErrorCode        *string
	Operation        *string
}

// TokenBalanceResult is the result of getting token balance / usage stats.
type TokenBalanceResult struct {
	Success      bool
	Balance      map[string]any
	ErrorMessage *string
}

// TokenAdditionResult is the result of adding tokens / updating quota.
type TokenAdditionResult struct {
	Success      bool
	NewBalance   *int
	Added        *int
	ErrorMessage *string
}

// TokenConsumptionService handles token consumption, additions, balances and quotas.
type TokenConsumptionService struct {
	TokenRepository domainrepos.ITokenBalanceRepository
}

// NewTokenConsumptionService mirrors TokenConsumptionService.__init__; the Python sessions
// argument only exists to build the default repository, so the Go constructor takes the
// repository directly.
func NewTokenConsumptionService(tokenRepository domainrepos.ITokenBalanceRepository) *TokenConsumptionService {
	return &TokenConsumptionService{TokenRepository: tokenRepository}
}

func tokenConsumptionCost(operation string, customCost *int) int {
	if customCost != nil {
		return *customCost
	}
	return authconfig.GetOperationCost(operation, 1)
}

func walletAvailableTokens(balance map[string]any) int {
	if balance == nil {
		return 0
	}
	f, _ := tmvalueobjects.PyFloat(balance["available_tokens"])
	return int(f)
}

// ConsumeTokensForOperation is consume_tokens_for_operation.
func (s *TokenConsumptionService) ConsumeTokensForOperation(ctx context.Context, userID, operation string, customCost *int) TokenConsumptionResult {
	cost := tokenConsumptionCost(operation, customCost)

	if cost == 0 {
		zero := 0
		msg := "Operation is free - no tokens consumed"
		return TokenConsumptionResult{Success: true, Consumed: &zero, Operation: &operation, ErrorMessage: &msg}
	}

	balance, err := s.TokenRepository.GetBalance(ctx, userID)
	if err != nil {
		msg := fmt.Sprintf("Token consumption failed: %s", err.Error())
		code := "CONSUMPTION_ERROR"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code, Operation: &operation}
	}
	if balance == nil {
		if _, err := s.TokenRepository.CreateBalance(ctx, userID, 10000, 10000); err != nil {
			msg := fmt.Sprintf("Token consumption failed: %s", err.Error())
			code := "CONSUMPTION_ERROR"
			return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code, Operation: &operation}
		}
	}

	success, err := s.TokenRepository.ConsumeTokens(ctx, userID, cost)
	if err != nil {
		msg := fmt.Sprintf("Token consumption failed: %s", err.Error())
		code := "CONSUMPTION_ERROR"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code, Operation: &operation}
	}

	if !success {
		balance, _ = s.TokenRepository.GetBalance(ctx, userID)
		available := walletAvailableTokens(balance)
		msg := fmt.Sprintf("Insufficient tokens. Required: %d, Available: %d", cost, available)
		code := "INSUFFICIENT_TOKENS"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code, Operation: &operation}
	}

	balance, _ = s.TokenRepository.GetBalance(ctx, userID)
	remaining := walletAvailableTokens(balance)
	return TokenConsumptionResult{Success: true, RemainingBalance: &remaining, Consumed: &cost, Operation: &operation}
}

// ConsumeTokens is consume_tokens.
func (s *TokenConsumptionService) ConsumeTokens(ctx context.Context, userID string, amount int, operation *string) TokenConsumptionResult {
	if amount <= 0 {
		msg := "Token amount must be positive"
		code := "INVALID_AMOUNT"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code}
	}

	balance, err := s.TokenRepository.GetBalance(ctx, userID)
	if err != nil {
		msg := fmt.Sprintf("Token consumption failed: %s", err.Error())
		code := "CONSUMPTION_ERROR"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code}
	}
	if balance == nil {
		if _, err := s.TokenRepository.CreateBalance(ctx, userID, 10000, 10000); err != nil {
			msg := fmt.Sprintf("Token consumption failed: %s", err.Error())
			code := "CONSUMPTION_ERROR"
			return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code}
		}
	}

	success, err := s.TokenRepository.ConsumeTokens(ctx, userID, amount)
	if err != nil {
		msg := fmt.Sprintf("Token consumption failed: %s", err.Error())
		code := "CONSUMPTION_ERROR"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code}
	}

	if !success {
		balance, _ = s.TokenRepository.GetBalance(ctx, userID)
		available := walletAvailableTokens(balance)
		msg := fmt.Sprintf("Insufficient tokens. Required: %d, Available: %d", amount, available)
		code := "INSUFFICIENT_TOKENS"
		return TokenConsumptionResult{Success: false, ErrorMessage: &msg, ErrorCode: &code, Operation: operation}
	}

	balance, _ = s.TokenRepository.GetBalance(ctx, userID)
	remaining := walletAvailableTokens(balance)
	return TokenConsumptionResult{Success: true, RemainingBalance: &remaining, Consumed: &amount, Operation: operation}
}

// AddTokens is add_tokens.
func (s *TokenConsumptionService) AddTokens(ctx context.Context, userID string, amount int, reason *string) TokenAdditionResult {
	if amount <= 0 {
		msg := "Token amount must be positive"
		return TokenAdditionResult{Success: false, ErrorMessage: &msg}
	}

	balance, err := s.TokenRepository.GetBalance(ctx, userID)
	if err != nil {
		msg := fmt.Sprintf("Failed to add tokens: %s", err.Error())
		return TokenAdditionResult{Success: false, ErrorMessage: &msg}
	}

	if balance == nil {
		if _, err := s.TokenRepository.CreateBalance(ctx, userID, amount, 10000); err != nil {
			msg := fmt.Sprintf("Failed to add tokens: %s", err.Error())
			return TokenAdditionResult{Success: false, ErrorMessage: &msg}
		}
		balance, _ = s.TokenRepository.GetBalance(ctx, userID)
	} else {
		success, err := s.TokenRepository.AddTokens(ctx, userID, amount)
		if err != nil {
			msg := fmt.Sprintf("Failed to add tokens: %s", err.Error())
			return TokenAdditionResult{Success: false, ErrorMessage: &msg}
		}
		if !success {
			msg := "Failed to add tokens - user not found"
			return TokenAdditionResult{Success: false, ErrorMessage: &msg}
		}
		balance, _ = s.TokenRepository.GetBalance(ctx, userID)
	}

	newBalance := walletAvailableTokens(balance)
	return TokenAdditionResult{Success: true, NewBalance: &newBalance, Added: &amount}
}

// GetBalance is get_balance.
func (s *TokenConsumptionService) GetBalance(ctx context.Context, userID string) TokenBalanceResult {
	balance, err := s.TokenRepository.GetBalance(ctx, userID)
	if err != nil {
		msg := fmt.Sprintf("Failed to get balance: %s", err.Error())
		return TokenBalanceResult{Success: false, ErrorMessage: &msg}
	}
	if balance == nil {
		if _, err := s.TokenRepository.CreateBalance(ctx, userID, 10000, 10000); err != nil {
			msg := fmt.Sprintf("Failed to get balance: %s", err.Error())
			return TokenBalanceResult{Success: false, ErrorMessage: &msg}
		}
		balance, _ = s.TokenRepository.GetBalance(ctx, userID)
	}
	return TokenBalanceResult{Success: true, Balance: balance}
}

// GetUsageStats is get_usage_stats.
func (s *TokenConsumptionService) GetUsageStats(ctx context.Context, userID string) TokenBalanceResult {
	stats, err := s.TokenRepository.GetUsageStats(ctx, userID)
	if err != nil {
		msg := fmt.Sprintf("Failed to get usage stats: %s", err.Error())
		return TokenBalanceResult{Success: false, ErrorMessage: &msg}
	}
	if stats == nil {
		if _, err := s.TokenRepository.CreateBalance(ctx, userID, 10000, 10000); err != nil {
			msg := fmt.Sprintf("Failed to get usage stats: %s", err.Error())
			return TokenBalanceResult{Success: false, ErrorMessage: &msg}
		}
		stats, _ = s.TokenRepository.GetUsageStats(ctx, userID)
	}
	return TokenBalanceResult{Success: true, Balance: stats}
}

// UpdateQuota is update_quota.
func (s *TokenConsumptionService) UpdateQuota(ctx context.Context, userID string, newQuota int, reason *string) TokenAdditionResult {
	if newQuota < 0 {
		msg := "Quota cannot be negative"
		return TokenAdditionResult{Success: false, ErrorMessage: &msg}
	}

	success, err := s.TokenRepository.UpdateQuota(ctx, userID, newQuota)
	if err != nil {
		msg := fmt.Sprintf("Failed to update quota: %s", err.Error())
		return TokenAdditionResult{Success: false, ErrorMessage: &msg}
	}
	if !success {
		msg := "Failed to update quota - user not found"
		return TokenAdditionResult{Success: false, ErrorMessage: &msg}
	}

	balance, _ := s.TokenRepository.GetBalance(ctx, userID)
	newBalance := walletAvailableTokens(balance)
	return TokenAdditionResult{Success: true, NewBalance: &newBalance}
}

// ResetMonthlyQuota is reset_monthly_quota.
func (s *TokenConsumptionService) ResetMonthlyQuota(ctx context.Context, userID string) TokenBalanceResult {
	success, err := s.TokenRepository.ResetMonthlyQuota(ctx, userID)
	if err != nil {
		msg := fmt.Sprintf("Failed to reset quota: %s", err.Error())
		return TokenBalanceResult{Success: false, ErrorMessage: &msg}
	}
	if !success {
		msg := "Failed to reset quota - user not found"
		return TokenBalanceResult{Success: false, ErrorMessage: &msg}
	}

	balance, _ := s.TokenRepository.GetBalance(ctx, userID)
	return TokenBalanceResult{Success: true, Balance: balance}
}

// CheckSufficientBalance is check_sufficient_balance: (has_enough, required_cost, available).
func (s *TokenConsumptionService) CheckSufficientBalance(ctx context.Context, userID, operation string, customCost *int) (bool, int, int) {
	cost := tokenConsumptionCost(operation, customCost)

	balance, err := s.TokenRepository.GetBalance(ctx, userID)
	if err != nil {
		return false, 0, 0
	}
	if balance == nil {
		return false, cost, 0
	}

	available := walletAvailableTokens(balance)
	return available >= cost, cost, available
}
