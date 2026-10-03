package services

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

// MachineTokenPrefix starts every machine token so it is recognizable and is never mistaken
// for a user token.
const MachineTokenPrefix = "mt_"

var (
	ErrInvalidMachineID     = errors.New("invalid machine id")
	ErrMachineTokenNotFound = errors.New("machine token not found")
	ErrInvalidMachineToken  = errors.New("invalid machine token")
)

// MachineTokenService registers machines by issuing them a token, revokes tokens and
// authenticates bridge requests. A token is returned once, at registration; only its SHA-256
// is stored.
type MachineTokenService struct {
	tokens repositories.MachineTokenRepository
}

// NewMachineTokenService builds the service over tokens.
func NewMachineTokenService(tokens repositories.MachineTokenRepository) *MachineTokenService {
	return &MachineTokenService{tokens: tokens}
}

// HashMachineToken is the stored form of a token. Tokens are 256 random bits, so a plain
// SHA-256 resists guessing and allows an indexed lookup by hash.
func HashMachineToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}

// Register issues the machine's token. A machine that already has an active token is
// repositories.ErrMachineTokenExists.
func (s *MachineTokenService) Register(ctx context.Context, userID, machineID string) (string, error) {
	if err := repositories.ValidateName("machine id", machineID); err != nil {
		return "", fmt.Errorf("%w: %v", ErrInvalidMachineID, err)
	}
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	token := MachineTokenPrefix + base64.RawURLEncoding.EncodeToString(raw)
	if _, err := s.tokens.Create(ctx, userID, machineID, HashMachineToken(token)); err != nil {
		return "", err
	}
	return token, nil
}

// Revoke revokes the machine's active token; none is ErrMachineTokenNotFound.
func (s *MachineTokenService) Revoke(ctx context.Context, userID, machineID string) error {
	revoked, err := s.tokens.Revoke(ctx, userID, machineID)
	if err != nil {
		return err
	}
	if !revoked {
		return fmt.Errorf("%w: machine %q", ErrMachineTokenNotFound, machineID)
	}
	return nil
}

// Authenticate returns the active token that token matches, or ErrInvalidMachineToken. A
// token that is unknown, revoked or not shaped like a machine token is the same error, so the
// reason is not revealed.
func (s *MachineTokenService) Authenticate(ctx context.Context, token string) (*repositories.MachineToken, error) {
	if !strings.HasPrefix(token, MachineTokenPrefix) {
		return nil, ErrInvalidMachineToken
	}
	found, err := s.tokens.FindActive(ctx, HashMachineToken(token))
	if err != nil {
		return nil, err
	}
	if found == nil {
		return nil, ErrInvalidMachineToken
	}
	return found, nil
}
