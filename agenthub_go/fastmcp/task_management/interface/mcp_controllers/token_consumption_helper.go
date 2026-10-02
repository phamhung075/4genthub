package mcp_controllers

// Token Consumption Helper for MCP Controllers
// (Python task_management/interface/mcp_controllers/token_consumption_helper.py).

import (
	"context"
	"strconv"

	authservices "agenthub/fastmcp/auth/application/services"
	authconfig "agenthub/fastmcp/auth/config"
	authdomainrepos "agenthub/fastmcp/auth/domain/repositories"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
)

// TokenConsumptionHelper consumes tokens before MCP operations.
//
// Python takes a SQLAlchemy Session and lazily builds a TokenBalanceRepository;
// Go takes the already-constructed repository (never the database package).
type TokenConsumptionHelper struct {
	tokenRepository authdomainrepos.ITokenBalanceRepository
	tokenService    *authservices.TokenConsumptionService
}

// NewTokenConsumptionHelper ports __init__(session).
func NewTokenConsumptionHelper(tokenRepository authdomainrepos.ITokenBalanceRepository) *TokenConsumptionHelper {
	return &TokenConsumptionHelper{tokenRepository: tokenRepository}
}

// TokenService mirrors the lazy `token_service` property.
func (h *TokenConsumptionHelper) TokenService() *authservices.TokenConsumptionService {
	if h.tokenService == nil {
		h.tokenService = authservices.NewTokenConsumptionService(h.tokenRepository)
	}
	return h.tokenService
}

// ConsumeTokens ports consume_tokens.
func (h *TokenConsumptionHelper) ConsumeTokens(ctx context.Context, operation string, userID *string, customCost *int) (bool, *entities.OrderedMap[any]) {
	authenticatedUserID, err := auth_helper.GetAuthenticatedUserID(ctx, userID, operation)
	if err != nil {
		return false, tokenErrorResponse(operation, err.Error(), "TOKEN_SYSTEM_ERROR")
	}

	result := h.TokenService().ConsumeTokensForOperation(ctx, authenticatedUserID, operation, customCost)

	if !result.Success {
		msg := ""
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		code := "TOKEN_CONSUMPTION_FAILED"
		if result.ErrorCode != nil {
			code = *result.ErrorCode
		}
		d := tokenErrorResponse(operation, msg, code)
		if code == "INSUFFICIENT_TOKENS" {
			d.Set("status_code", 402)
		}
		return false, d
	}

	return true, nil
}

// GetTokenInfo ports get_token_info.
func (h *TokenConsumptionHelper) GetTokenInfo(ctx context.Context, operation string, userID *string, customCost *int) *entities.OrderedMap[any] {
	authenticatedUserID, err := auth_helper.GetAuthenticatedUserID(ctx, userID, operation)
	if err != nil {
		d := entities.NewOrderedMap[any]()
		d.Set("operation", operation)
		d.Set("error", "Could not retrieve balance info")
		return d
	}

	balanceResult := h.TokenService().GetBalance(ctx, authenticatedUserID)
	if !balanceResult.Success {
		d := entities.NewOrderedMap[any]()
		d.Set("operation", operation)
		d.Set("error", "Could not retrieve balance info")
		return d
	}

	cost := 0
	if customCost != nil {
		cost = *customCost
	} else {
		cost = authconfig.GetOperationCost(operation, 1)
	}

	available := 0
	if v, ok := balanceResult.Balance["available_tokens"]; ok {
		switch t := v.(type) {
		case int:
			available = t
		case int64:
			available = int(t)
		case float64:
			available = int(t)
		case string:
			if n, convErr := strconv.Atoi(t); convErr == nil {
				available = n
			}
		}
	}

	d := entities.NewOrderedMap[any]()
	d.Set("consumed", cost)
	d.Set("remaining_balance", available)
	d.Set("operation", operation)
	return d
}

// ConsumeAndAddInfo ports consume_and_add_info.
func (h *TokenConsumptionHelper) ConsumeAndAddInfo(ctx context.Context, operation string, response *entities.OrderedMap[any], userID *string, customCost *int) (bool, *entities.OrderedMap[any]) {
	success, errorResponse := h.ConsumeTokens(ctx, operation, userID, customCost)
	if !success {
		return false, errorResponse
	}
	tokenInfo := h.GetTokenInfo(ctx, operation, userID, customCost)
	response.Set("token_info", tokenInfo)
	return true, response
}

// ConsumeTokensForOperation ports the standalone consume_tokens_for_operation.
func ConsumeTokensForOperation(ctx context.Context, tokenRepository authdomainrepos.ITokenBalanceRepository, operation string, userID *string, customCost *int) (bool, *entities.OrderedMap[any]) {
	helper := NewTokenConsumptionHelper(tokenRepository)
	return helper.ConsumeTokens(ctx, operation, userID, customCost)
}

func tokenErrorResponse(operation, message, code string) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", message)
	d.Set("error_code", code)
	d.Set("operation", operation)
	return d
}
