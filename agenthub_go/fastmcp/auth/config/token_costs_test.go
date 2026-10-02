package config

import (
	"reflect"
	"testing"
)

func TestTokenCostsContentAndOrder(t *testing.T) {
	if got := TokenCosts.Len(); got != 68 {
		t.Fatalf("TOKEN_COSTS length = %d, want 68", got)
	}
	wantFirst := []string{"create_project", "update_project", "delete_project", "list_projects", "get_project"}
	if got := TokenCosts.Keys()[:5]; !reflect.DeepEqual(got, wantFirst) {
		t.Fatalf("first keys = %v, want %v", got, wantFirst)
	}
	cases := map[string]int{
		"create_project": 10,
		"call_agent":     20,
		"ai_plan":        15,
		"login":          0,
		"update_quota":   0,
	}
	for op, want := range cases {
		if got, _ := TokenCosts.Get(op); got != want {
			t.Errorf("TOKEN_COSTS[%q] = %d, want %d", op, got, want)
		}
	}
}

func TestGetOperationCost(t *testing.T) {
	if got := GetOperationCost("call_agent", 1); got != 20 {
		t.Errorf("call_agent = %d, want 20", got)
	}
	if got := GetOperationCost("missing", 1); got != 1 {
		t.Errorf("missing default = %d, want 1", got)
	}
	if got := GetOperationCost("missing", 7); got != 7 {
		t.Errorf("missing default = %d, want 7", got)
	}
}

func TestGetAllCostsIsCopy(t *testing.T) {
	all := GetAllCosts()
	if all.Len() != 68 {
		t.Fatalf("copy length = %d, want 68", all.Len())
	}
	all.Set("new_op", 99)
	if _, ok := TokenCosts.Get("new_op"); ok {
		t.Fatal("GetAllCosts must return a copy; TOKEN_COSTS was mutated")
	}
}

func TestGetFreeOperations(t *testing.T) {
	want := []string{"login", "register", "logout", "refresh_token", "verify_email", "forgot_password", "reset_password", "get_balance", "get_usage_stats", "add_tokens", "update_quota"}
	if got := GetFreeOperations(); !reflect.DeepEqual(got, want) {
		t.Fatalf("free ops = %v, want %v", got, want)
	}
}

func TestGetExpensiveOperations(t *testing.T) {
	want := map[string]int{"create_project": 10, "ai_plan": 15, "ai_create": 10, "call_agent": 20}
	got := GetExpensiveOperations(10)
	if got.Len() != len(want) {
		t.Fatalf("expensive len = %d, want %d", got.Len(), len(want))
	}
	wantOrder := []string{"create_project", "ai_plan", "ai_create", "call_agent"}
	if !reflect.DeepEqual(got.Keys(), wantOrder) {
		t.Fatalf("expensive order = %v, want %v", got.Keys(), wantOrder)
	}
	for k, v := range want {
		gv, _ := got.Get(k)
		if gv != v {
			t.Errorf("expensive[%q] = %d, want %d", k, gv, v)
		}
	}
	if e := GetExpensiveOperations(100); e.Len() != 0 {
		t.Errorf("threshold 100 len = %d, want 0", e.Len())
	}
}
