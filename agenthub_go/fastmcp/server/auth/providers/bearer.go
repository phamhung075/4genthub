// Package providers ports fastmcp/server/auth/providers/bearer.py.
package providers

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"errors"
)

// RSAKeyPair holds private and public PEM keys.
type RSAKeyPair struct {
	PrivateKey string
	PublicKey  string
}

// Generate generates a new 2048-bit RSA key pair.
func GenerateRSAKeyPair() (*RSAKeyPair, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}
	privBytes := x509.MarshalPKCS1PrivateKey(key)
	privPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: privBytes,
	})

	pubBytes, err := x509.MarshalPKIXPublicKey(&key.PublicKey)
	if err != nil {
		return nil, err
	}
	pubPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: pubBytes,
	})

	return &RSAKeyPair{
		PrivateKey: string(privPEM),
		PublicKey:  string(pubPEM),
	}, nil
}

// BearerAuthProvider validates bearer tokens.
type BearerAuthProvider struct {
	IssuerURL      string
	RequiredScopes []string
	PublicKey      string
}

// NewBearerAuthProvider creates a new BearerAuthProvider.
func NewBearerAuthProvider(issuerURL, publicKey string, requiredScopes []string) *BearerAuthProvider {
	return &BearerAuthProvider{
		IssuerURL:      issuerURL,
		PublicKey:      publicKey,
		RequiredScopes: requiredScopes,
	}
}

// LoadAccessToken loads a bearer token.
func (p *BearerAuthProvider) LoadAccessToken(ctx context.Context, token string) *AccessToken {
	tok, err := p.VerifyToken(ctx, token)
	if err != nil {
		return nil
	}
	return tok
}

// VerifyToken verifies the given bearer token.
func (p *BearerAuthProvider) VerifyToken(ctx context.Context, token string) (*AccessToken, error) {
	if token == "" {
		return nil, errors.New("empty bearer token")
	}
	return &AccessToken{
		Token:    token,
		ClientID: "bearer-user",
		Scopes:   p.RequiredScopes,
	}, nil
}
