package services

import (
	"context"
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

type memoryMachineTokens struct {
	rows []*repositories.MachineToken
}

func (m *memoryMachineTokens) Create(_ context.Context, userID, machineID, hash string) (*repositories.MachineToken, error) {
	for _, r := range m.rows {
		if r.UserID == userID && r.MachineID == machineID && r.RevokedAt == nil {
			return nil, repositories.ErrMachineTokenExists
		}
	}
	row := &repositories.MachineToken{UserID: userID, MachineID: machineID, TokenHash: hash}
	m.rows = append(m.rows, row)
	return row, nil
}

func (m *memoryMachineTokens) Revoke(_ context.Context, userID, machineID string) (bool, error) {
	for _, r := range m.rows {
		if r.UserID == userID && r.MachineID == machineID && r.RevokedAt == nil {
			revoked := repositories.MachineToken{}
			r.RevokedAt = &revoked.CreatedAt
			return true, nil
		}
	}
	return false, nil
}

func (m *memoryMachineTokens) FindActive(_ context.Context, hash string) (*repositories.MachineToken, error) {
	for _, r := range m.rows {
		if r.TokenHash == hash && r.RevokedAt == nil {
			return r, nil
		}
	}
	return nil, nil
}

func TestMachineTokenLifecycle(t *testing.T) {
	ctx := context.Background()
	store := &memoryMachineTokens{}
	svc := NewMachineTokenService(store)

	token, err := svc.Register(ctx, "u1", "pc-home")
	if err != nil || !strings.HasPrefix(token, MachineTokenPrefix) {
		t.Fatalf("Register = %q, %v", token, err)
	}
	if store.rows[0].TokenHash == token || store.rows[0].TokenHash != HashMachineToken(token) {
		t.Fatalf("stored %q: want only the SHA-256 of the token", store.rows[0].TokenHash)
	}
	if other, _ := svc.Register(ctx, "u2", "pc-home"); other == token {
		t.Fatal("two registrations returned the same token")
	}

	got, err := svc.Authenticate(ctx, token)
	if err != nil || got.UserID != "u1" || got.MachineID != "pc-home" {
		t.Fatalf("Authenticate = %+v, %v", got, err)
	}
	if _, err := svc.Register(ctx, "u1", "pc-home"); !errors.Is(err, repositories.ErrMachineTokenExists) {
		t.Fatalf("second Register = %v, want ErrMachineTokenExists", err)
	}

	if err := svc.Revoke(ctx, "u2", "ghost"); !errors.Is(err, ErrMachineTokenNotFound) {
		t.Fatalf("Revoke unknown = %v, want ErrMachineTokenNotFound", err)
	}
	if err := svc.Revoke(ctx, "u1", "pc-home"); err != nil {
		t.Fatalf("Revoke: %v", err)
	}
	if _, err := svc.Authenticate(ctx, token); !errors.Is(err, ErrInvalidMachineToken) {
		t.Fatalf("Authenticate revoked = %v, want ErrInvalidMachineToken", err)
	}
}

func TestMachineTokenAuthenticateRejectsAnythingThatIsNotAnActiveMachineToken(t *testing.T) {
	ctx := context.Background()
	store := &memoryMachineTokens{}
	svc := NewMachineTokenService(store)
	token, err := svc.Register(ctx, "u1", "pc-home")
	if err != nil {
		t.Fatal(err)
	}
	// A stored hash must never authenticate by itself, and a token without the prefix is
	// rejected before any lookup.
	for name, presented := range map[string]string{
		"empty":           "",
		"the stored hash": store.rows[0].TokenHash,
		"no prefix":       strings.TrimPrefix(token, MachineTokenPrefix),
		"prefix only":     MachineTokenPrefix,
		"unknown":         MachineTokenPrefix + "unknown",
	} {
		if _, err := svc.Authenticate(ctx, presented); !errors.Is(err, ErrInvalidMachineToken) {
			t.Errorf("%s: err = %v, want ErrInvalidMachineToken", name, err)
		}
	}
}

func TestMachineTokenRegisterRejectsInvalidMachineID(t *testing.T) {
	svc := NewMachineTokenService(&memoryMachineTokens{})
	for _, id := range []string{"", "pc.home", "-pc", "a b"} {
		if _, err := svc.Register(context.Background(), "u1", id); !errors.Is(err, ErrInvalidMachineID) {
			t.Errorf("Register(%q) = %v, want ErrInvalidMachineID", id, err)
		}
	}
}
