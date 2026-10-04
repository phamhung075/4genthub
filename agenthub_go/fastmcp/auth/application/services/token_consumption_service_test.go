package services

import (
	"context"
	"testing"
)

type fakeTokenRepo struct {
	balance     map[string]any
	usageStats  map[string]any
	consumeOK   bool
	addOK       bool
	updateOK    bool
	resetOK     bool
	createCalls int
	createArgs  [][2]int
}

func newFakeTokenRepo(available int64) *fakeTokenRepo {
	return &fakeTokenRepo{balance: map[string]any{"available_tokens": available}, consumeOK: true, addOK: true, updateOK: true, resetOK: true}
}

func (f *fakeTokenRepo) GetBalance(_ context.Context, _ string) (map[string]any, error) {
	return f.balance, nil
}
func (f *fakeTokenRepo) CreateBalance(_ context.Context, _ string, initialTokens, monthlyQuota int) (map[string]any, error) {
	f.createCalls++
	f.createArgs = append(f.createArgs, [2]int{initialTokens, monthlyQuota})
	f.balance = map[string]any{"available_tokens": int64(initialTokens), "monthly_quota": int64(monthlyQuota)}
	return f.balance, nil
}
func (f *fakeTokenRepo) ConsumeTokens(_ context.Context, _ string, amount int) (bool, error) {
	if !f.consumeOK {
		return false, nil
	}
	avail := int64(0)
	if v, ok := f.balance["available_tokens"].(int64); ok {
		avail = v
	}
	f.balance["available_tokens"] = avail - int64(amount)
	return true, nil
}
func (f *fakeTokenRepo) AddTokens(_ context.Context, _ string, _ int) (bool, error) {
	return f.addOK, nil
}
func (f *fakeTokenRepo) UpdateQuota(_ context.Context, _ string, _ int) (bool, error) {
	return f.updateOK, nil
}
func (f *fakeTokenRepo) GetUsageStats(_ context.Context, _ string) (map[string]any, error) {
	return f.usageStats, nil
}
func (f *fakeTokenRepo) ResetMonthlyQuota(_ context.Context, _ string) (bool, error) {
	return f.resetOK, nil
}
func (f *fakeTokenRepo) ResetDailyConsumption(_ context.Context, _ string) (bool, error) {
	return false, nil
}
func (f *fakeTokenRepo) CheckAndAutoReset(_ context.Context, _ string) (bool, error) {
	return false, nil
}

func TestConsumeFreeOperation(t *testing.T) {
	svc := NewTokenConsumptionService(newFakeTokenRepo(100))
	res := svc.ConsumeTokensForOperation(context.Background(), "u", "login", nil)
	if !res.Success || res.Consumed == nil || *res.Consumed != 0 || res.ErrorMessage == nil || *res.ErrorMessage != "Operation is free - no tokens consumed" {
		t.Fatalf("unexpected: %+v", res)
	}
	if res.Operation == nil || *res.Operation != "login" {
		t.Fatalf("operation = %v", res.Operation)
	}
}

func TestConsumeOperationCostAndBalance(t *testing.T) {
	repo := newFakeTokenRepo(100)
	svc := NewTokenConsumptionService(repo)
	res := svc.ConsumeTokensForOperation(context.Background(), "u", "create_task", nil)
	if !res.Success || res.Consumed == nil || *res.Consumed != 5 {
		t.Fatalf("unexpected: %+v", res)
	}
	if res.RemainingBalance == nil || *res.RemainingBalance != 95 {
		t.Fatalf("remaining = %v, want 95", res.RemainingBalance)
	}

	custom := 7
	res = svc.ConsumeTokensForOperation(context.Background(), "u", "create_task", &custom)
	if !res.Success || res.Consumed == nil || *res.Consumed != 7 {
		t.Fatalf("custom cost unexpected: %+v", res)
	}
}

func TestConsumeInsufficient(t *testing.T) {
	repo := newFakeTokenRepo(3)
	repo.consumeOK = false
	svc := NewTokenConsumptionService(repo)
	res := svc.ConsumeTokensForOperation(context.Background(), "u", "create_task", nil)
	if res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Insufficient tokens. Required: 5, Available: 3" {
		t.Fatalf("unexpected: %+v", res.ErrorMessage)
	}
	if res.ErrorCode == nil || *res.ErrorCode != "INSUFFICIENT_TOKENS" {
		t.Fatalf("error code = %v", res.ErrorCode)
	}
}

func TestConsumeBalanceAutoCreate(t *testing.T) {
	repo := newFakeTokenRepo(0)
	repo.balance = nil
	svc := NewTokenConsumptionService(repo)
	res := svc.GetBalance(context.Background(), "u")
	if !res.Success {
		t.Fatalf("expected success: %v", res.ErrorMessage)
	}
	if repo.createCalls != 1 || repo.createArgs[0] != [2]int{10000, 10000} {
		t.Fatalf("create args = %v", repo.createArgs)
	}
}

func TestConsumeInvalidAmountAndQuota(t *testing.T) {
	svc := NewTokenConsumptionService(newFakeTokenRepo(10))
	if res := svc.ConsumeTokens(context.Background(), "u", 0, nil); res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Token amount must be positive" || res.ErrorCode == nil || *res.ErrorCode != "INVALID_AMOUNT" {
		t.Fatalf("unexpected: %+v", res)
	}
	if res := svc.AddTokens(context.Background(), "u", -1, nil); res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Token amount must be positive" {
		t.Fatalf("unexpected: %+v", res)
	}
	if res := svc.UpdateQuota(context.Background(), "u", -1, nil); res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Quota cannot be negative" {
		t.Fatalf("unexpected: %+v", res)
	}
}

func TestCheckSufficientBalance(t *testing.T) {
	svc := NewTokenConsumptionService(newFakeTokenRepo(10))
	ok, cost, available := svc.CheckSufficientBalance(context.Background(), "u", "create_task", nil)
	if !ok || cost != 5 || available != 10 {
		t.Fatalf("got (%v,%d,%d)", ok, cost, available)
	}
	ok, cost, available = svc.CheckSufficientBalance(context.Background(), "u", "ai_plan", nil)
	if ok || cost != 15 || available != 10 {
		t.Fatalf("got (%v,%d,%d)", ok, cost, available)
	}
}

func TestAddTokensCreatesWithAmount(t *testing.T) {
	repo := newFakeTokenRepo(0)
	repo.balance = nil
	svc := NewTokenConsumptionService(repo)
	res := svc.AddTokens(context.Background(), "u", 250, nil)
	if !res.Success || res.Added == nil || *res.Added != 250 {
		t.Fatalf("unexpected: %+v", res)
	}
	if repo.createArgs[0] != [2]int{250, 10000} {
		t.Fatalf("create args = %v, want [250 10000]", repo.createArgs)
	}
	if res.NewBalance == nil || *res.NewBalance != 250 {
		t.Fatalf("new balance = %v", res.NewBalance)
	}
}
