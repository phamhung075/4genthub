// Package providers ports fastmcp/server/auth/providers/in_memory.py.
package providers

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"sync"
	"time"
)

// InMemoryOAuthProvider simulates an OAuth provider locally in-memory.
type InMemoryOAuthProvider struct {
	mu            sync.RWMutex
	IssuerURL     string
	Clients       map[string]map[string]any
	AuthCodes     map[string]map[string]any
	AccessTokens  map[string]*AccessToken
	RefreshTokens map[string]string
}

// NewInMemoryOAuthProvider creates an in-memory OAuth provider.
func NewInMemoryOAuthProvider(issuerURL string) *InMemoryOAuthProvider {
	if issuerURL == "" {
		issuerURL = "http://fastmcp.example.com"
	}
	return &InMemoryOAuthProvider{
		IssuerURL:     issuerURL,
		Clients:       make(map[string]map[string]any),
		AuthCodes:     make(map[string]map[string]any),
		AccessTokens:  make(map[string]*AccessToken),
		RefreshTokens: make(map[string]string),
	}
}

// LoadAccessToken loads an access token.
func (p *InMemoryOAuthProvider) LoadAccessToken(ctx context.Context, token string) *AccessToken {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.AccessTokens[token]
}

// VerifyToken verifies an access token.
func (p *InMemoryOAuthProvider) VerifyToken(ctx context.Context, token string) (*AccessToken, error) {
	tok := p.LoadAccessToken(ctx, token)
	if tok == nil {
		return nil, errors.New("token not found")
	}
	return tok, nil
}

// CreateAccessToken creates and stores a new random token.
func (p *InMemoryOAuthProvider) CreateAccessToken(clientID string, scopes []string, ttlSeconds int) *AccessToken {
	p.mu.Lock()
	defer p.mu.Unlock()

	b := make([]byte, 16)
	_, _ = rand.Read(b)
	tokStr := hex.EncodeToString(b)

	exp := int(time.Now().Unix()) + ttlSeconds
	tok := &AccessToken{
		Token:     tokStr,
		ClientID:  clientID,
		Scopes:    scopes,
		ExpiresAt: &exp,
	}
	p.AccessTokens[tokStr] = tok
	return tok
}
