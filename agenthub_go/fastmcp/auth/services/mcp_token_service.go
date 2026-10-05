package services

// MCP Token Service (Python auth/services/mcp_token_service.py): MCP protocol token
// generation, validation and management. Tokens live only in memory; the Python dict is an
// entities.OrderedMap so iteration order stays observable. Usage updates go to the
// api_tokens table (task_management/infrastructure/database.APIToken). Logging calls are
// dropped. The async Python methods become ctx-first Go methods.

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// MCPToken mirrors the Python dataclass MCPToken. A nil pointer is Python None.
type MCPToken struct {
	Token     string
	UserID    string
	Email     *string
	CreatedAt *time.Time
	ExpiresAt *time.Time
	Metadata  *entities.OrderedMap[any]
	IsActive  bool
}

// MCPTokenService mirrors the Python class.
type MCPTokenService struct {
	tokens *entities.OrderedMap[*MCPToken]

	// updateUsage is _update_token_usage's database write. It is a field so tests can
	// substitute it, the Go counterpart of patching the module's get_session.
	updateUsage func(ctx context.Context, tokenHash string)
}

// NewMCPTokenService initializes the service (Python __init__).
func NewMCPTokenService() *MCPTokenService {
	s := &MCPTokenService{tokens: entities.NewOrderedMap[*MCPToken]()}
	s.updateUsage = mcpTokenUpdateUsage
	return s
}

// GenerateMCPTokenFromUserID generates a token, stores it and returns it.
func (s *MCPTokenService) GenerateMCPTokenFromUserID(ctx context.Context, userID string, email *string, expiresInHours int, metadata *entities.OrderedMap[any]) *MCPToken {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	token := "mcp_" + hex.EncodeToString(b)

	createdAt := time.Now().UTC()
	expiresAt := createdAt.Add(time.Duration(expiresInHours) * time.Hour)

	if metadata == nil || metadata.Len() == 0 {
		metadata = entities.NewOrderedMap[any]()
	}

	mcpToken := &MCPToken{
		Token:     token,
		UserID:    userID,
		Email:     email,
		CreatedAt: &createdAt,
		ExpiresAt: &expiresAt,
		Metadata:  metadata,
		IsActive:  true,
	}
	s.tokens.Set(token, mcpToken)
	return mcpToken
}

// ValidateMCPToken returns the token when it is valid, else nil. An expired token is
// removed from the in-memory store.
func (s *MCPTokenService) ValidateMCPToken(ctx context.Context, token string) *MCPToken {
	if token == "" || !strings.HasPrefix(token, "mcp_") {
		return nil
	}

	mcpToken, ok := s.tokens.Get(token)
	if !ok || mcpToken == nil {
		return nil
	}

	if !mcpToken.IsActive {
		return nil
	}

	if mcpToken.ExpiresAt != nil && time.Now().UTC().After(*mcpToken.ExpiresAt) {
		s.tokens.Delete(token)
		return nil
	}

	s.updateTokenUsage(ctx, token)
	return mcpToken
}

// updateTokenUsage is _update_token_usage: hash the token and record the use in the
// database.
func (s *MCPTokenService) updateTokenUsage(ctx context.Context, token string) {
	sum := sha256.Sum256([]byte(token))
	s.updateUsage(ctx, hex.EncodeToString(sum[:]))
}

// mcpTokenUpdateUsage executes the UPDATE; failures are swallowed like the Python except
// clause. The statement mirrors SQLAlchemy's
// update(ApiToken).where(token_hash == hash).values(usage_count=usage_count + 1,
// last_used_at=now).
func mcpTokenUpdateUsage(ctx context.Context, tokenHash string) {
	sessions, err := database.GetSessionManager(ctx, database.OSDeps())
	if err != nil {
		return
	}
	_ = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			"UPDATE "+mcpTokenTableName()+" SET usage_count = usage_count + 1, last_used_at = $1 WHERE token_hash = $2",
			time.Now().UTC(), tokenHash)
		return err
	})
}

// mcpTokenTableName is the table backing taskdb.APIToken.
func mcpTokenTableName() string {
	for _, t := range database.Tables {
		if t.Model == "APIToken" {
			return t.Name
		}
	}
	return "api_tokens"
}

// RevokeUserTokens deactivates and removes every active token of a user; reports whether
// any was revoked.
func (s *MCPTokenService) RevokeUserTokens(ctx context.Context, userID string) bool {
	tokensRevoked := 0
	tokensToRemove := []string{}

	for _, token := range s.tokens.Keys() {
		mcpToken, _ := s.tokens.Get(token)
		if mcpToken.UserID == userID && mcpToken.IsActive {
			mcpToken.IsActive = false
			tokensToRemove = append(tokensToRemove, token)
			tokensRevoked++
		}
	}

	for _, token := range tokensToRemove {
		s.tokens.Delete(token)
	}

	return tokensRevoked > 0
}

// CleanupExpiredTokens removes expired tokens and returns how many were removed.
func (s *MCPTokenService) CleanupExpiredTokens(ctx context.Context) int {
	currentTime := time.Now().UTC()
	tokensToRemove := []string{}

	for _, token := range s.tokens.Keys() {
		mcpToken, _ := s.tokens.Get(token)
		if mcpToken.ExpiresAt != nil && currentTime.After(*mcpToken.ExpiresAt) {
			tokensToRemove = append(tokensToRemove, token)
		}
	}

	for _, token := range tokensToRemove {
		s.tokens.Delete(token)
	}

	return len(tokensToRemove)
}

// GetTokenStats returns the token statistics in the Python dict's key order.
func (s *MCPTokenService) GetTokenStats() *entities.OrderedMap[any] {
	currentTime := time.Now().UTC()
	activeTokens := 0
	expiredTokens := 0

	for _, mcpToken := range s.tokens.Values() {
		if mcpToken.IsActive {
			if mcpToken.ExpiresAt != nil && currentTime.After(*mcpToken.ExpiresAt) {
				expiredTokens++
			} else {
				activeTokens++
			}
		} else {
			expiredTokens++
		}
	}

	stats := entities.NewOrderedMap[any]()
	stats.Set("total_tokens", s.tokens.Len())
	stats.Set("active_tokens", activeTokens)
	stats.Set("expired_tokens", expiredTokens)
	stats.Set("service_status", "running")
	stats.Set("storage_type", "in-memory")
	return stats
}

// GetUserTokens returns the user's tokens in insertion order, marking expired ones
// inactive.
func (s *MCPTokenService) GetUserTokens(ctx context.Context, userID string) []*MCPToken {
	userTokens := []*MCPToken{}
	currentTime := time.Now().UTC()

	for _, mcpToken := range s.tokens.Values() {
		if mcpToken.UserID == userID {
			if mcpToken.ExpiresAt != nil && currentTime.After(*mcpToken.ExpiresAt) {
				mcpToken.IsActive = false
			}
			userTokens = append(userTokens, mcpToken)
		}
	}

	return userTokens
}

// MCPTokenServiceInstance is Python's module-level mcp_token_service singleton.
var MCPTokenServiceInstance = NewMCPTokenService()
