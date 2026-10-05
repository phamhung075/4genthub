package models

import (
	"encoding/json"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

func TestAPITokenToDictOrderAndValues(t *testing.T) {
	created := time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)
	expires := time.Date(2024, 2, 2, 3, 4, 5, 0, time.UTC)
	lastUsed := time.Date(2024, 1, 3, 10, 20, 30, 0, time.UTC)
	row := &taskdb.APIToken{
		ID:         "tok_12345abcde",
		UserID:     "user_67890fghij",
		Name:       "Test API Token",
		TokenHash:  "sha256_hash_of_token",
		Scopes:     json.RawMessage(`["read", "write"]`),
		CreatedAt:  created,
		ExpiresAt:  expires,
		LastUsedAt: &lastUsed,
		UsageCount: 5,
		RateLimit:  1000,
		UsageStats: json.RawMessage(`{"task_create": 10, "task_update": 5}`),
		IsActive:   true,
	}

	got := APITokenToDict(row, false, nil)

	wantKeys := []string{"id", "name", "scopes", "created_at", "expires_at", "last_used_at", "usage_count", "rate_limit", "usage_stats", "is_active", "user_id"}
	if !reflect.DeepEqual(got.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", got.Keys(), wantKeys)
	}

	if v, _ := got.Get("id"); v != "tok_12345abcde" {
		t.Fatalf("id = %v", v)
	}
	if v, _ := got.Get("name"); v != "Test API Token" {
		t.Fatalf("name = %v", v)
	}
	if v, _ := got.Get("scopes"); !reflect.DeepEqual(v, []any{"read", "write"}) {
		t.Fatalf("scopes = %#v", v)
	}
	if v, _ := got.Get("created_at"); v != "2024-01-02T03:04:05+00:00" {
		t.Fatalf("created_at = %v", v)
	}
	if v, _ := got.Get("expires_at"); v != "2024-02-02T03:04:05+00:00" {
		t.Fatalf("expires_at = %v", v)
	}
	if v, _ := got.Get("last_used_at"); v != "2024-01-03T10:20:30+00:00" {
		t.Fatalf("last_used_at = %v", v)
	}
	if v, _ := got.Get("usage_count"); v != int64(5) {
		t.Fatalf("usage_count = %#v", v)
	}
	if v, _ := got.Get("rate_limit"); v != int64(1000) {
		t.Fatalf("rate_limit = %#v", v)
	}
	if v, _ := got.Get("is_active"); v != true {
		t.Fatalf("is_active = %v", v)
	}
	if v, _ := got.Get("user_id"); v != "user_67890fghij" {
		t.Fatalf("user_id = %v", v)
	}

	statsAny, _ := got.Get("usage_stats")
	stats, ok := statsAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("usage_stats = %#v, want ordered dict", statsAny)
	}
	if !reflect.DeepEqual(stats.Keys(), []string{"task_create", "task_update"}) {
		t.Fatalf("usage_stats keys = %v", stats.Keys())
	}
	if v, _ := stats.Get("task_create"); v != int64(10) {
		t.Fatalf("task_create = %#v", v)
	}
	if v, _ := stats.Get("task_update"); v != int64(5) {
		t.Fatalf("task_update = %#v", v)
	}

	if got.Has("token") {
		t.Fatal("token must not be present by default")
	}
}

func TestAPITokenToDictIncludeToken(t *testing.T) {
	row := &taskdb.APIToken{ID: "tok", Name: "n", ExpiresAt: time.Now().UTC()}
	token := "mcp_live_1234567890abcdef"

	got := APITokenToDict(row, true, &token)
	if v, _ := got.Get("token"); v != token {
		t.Fatalf("token = %v", v)
	}
	keys := got.Keys()
	if keys[len(keys)-1] != "token" {
		t.Fatalf("token should be the last key, keys = %v", keys)
	}

	if withNil := APITokenToDict(row, true, nil); withNil.Has("token") {
		t.Fatal("token must be absent when no value is given")
	}
	empty := ""
	if withEmpty := APITokenToDict(row, true, &empty); withEmpty.Has("token") {
		t.Fatal("token must be absent for an empty value")
	}
	if without := APITokenToDict(row, false, &token); without.Has("token") {
		t.Fatal("token must be absent when include_token is false")
	}
}

func TestAPITokenToDictEmptyScopes(t *testing.T) {
	row := &taskdb.APIToken{ID: "tok", Name: "n", ExpiresAt: time.Now().UTC()}

	for _, raw := range []json.RawMessage{nil, json.RawMessage(`null`), json.RawMessage(`[]`)} {
		row.Scopes = raw
		got := APITokenToDict(row, false, nil)
		if v, _ := got.Get("scopes"); !reflect.DeepEqual(v, []any{}) {
			t.Fatalf("scopes for %s = %#v, want []", raw, v)
		}
	}
}

func TestAPITokenToDictUsageStatsDefaults(t *testing.T) {
	row := &taskdb.APIToken{ID: "tok", Name: "n", ExpiresAt: time.Now().UTC()}

	for _, raw := range []json.RawMessage{nil, json.RawMessage(`null`), json.RawMessage(`{}`)} {
		row.UsageStats = raw
		got := APITokenToDict(row, false, nil)
		statsAny, _ := got.Get("usage_stats")
		stats, ok := statsAny.(*entities.OrderedMap[any])
		if !ok || stats.Len() != 0 {
			t.Fatalf("usage_stats for %s = %#v, want empty dict", raw, statsAny)
		}
	}
}

func TestAPITokenToDictNoneDatetimes(t *testing.T) {
	expires := time.Date(2024, 2, 2, 3, 4, 5, 0, time.UTC)
	row := &taskdb.APIToken{ID: "tok", Name: "n", ExpiresAt: expires}

	got := APITokenToDict(row, false, nil)
	if v, _ := got.Get("created_at"); v != nil {
		t.Fatalf("created_at = %v, want None", v)
	}
	if v, _ := got.Get("last_used_at"); v != nil {
		t.Fatalf("last_used_at = %v, want None", v)
	}
	if v, _ := got.Get("expires_at"); v != "2024-02-02T03:04:05+00:00" {
		t.Fatalf("expires_at = %v", v)
	}

	lastUsed := time.Date(2024, 1, 3, 10, 20, 30, 0, time.UTC)
	row.LastUsedAt = &lastUsed
	got = APITokenToDict(row, false, nil)
	if v, _ := got.Get("last_used_at"); v != "2024-01-03T10:20:30+00:00" {
		t.Fatalf("last_used_at = %v", v)
	}
}

func TestAPITokenToDictMicroseconds(t *testing.T) {
	created := time.Date(2024, 1, 2, 3, 4, 5, 123456000, time.UTC)
	row := &taskdb.APIToken{ID: "tok", Name: "n", CreatedAt: created, ExpiresAt: created}

	got := APITokenToDict(row, false, nil)
	if v, _ := got.Get("created_at"); v != "2024-01-02T03:04:05.123456+00:00" {
		t.Fatalf("created_at = %v", v)
	}
}

func TestAPITokenToDictNilRow(t *testing.T) {
	if got := APITokenToDict(nil, false, nil); got != nil {
		t.Fatalf("APITokenToDict(nil) = %#v, want nil", got)
	}
}
