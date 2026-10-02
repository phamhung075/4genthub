package models

// API token response mapping (Python auth/models/api_token.py). The api_tokens table and
// its row are already ported as task_management/infrastructure/database.APIToken; only the
// model's to_dict behaviour is ported here.

import (
	"encoding/json"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// APITokenToDict is ApiToken.to_dict(include_token, token_value). The key order is the
// Python dict's; the token key is appended only when requested with a truthy value.
func APITokenToDict(row *taskdb.APIToken, includeToken bool, tokenValue *string) *entities.OrderedMap[any] {
	if row == nil {
		return nil
	}

	result := entities.NewOrderedMap[any]()
	result.Set("id", row.ID)
	result.Set("name", row.Name)
	result.Set("scopes", apiTokenScopes(row.Scopes))
	result.Set("created_at", apiTokenTimeISO(row.CreatedAt))
	result.Set("expires_at", apiTokenTimeISO(row.ExpiresAt))
	result.Set("last_used_at", apiTokenTimePtrISO(row.LastUsedAt))
	result.Set("usage_count", row.UsageCount)
	result.Set("rate_limit", row.RateLimit)
	result.Set("usage_stats", apiTokenUsageStats(row.UsageStats))
	result.Set("is_active", row.IsActive)
	result.Set("user_id", row.UserID)

	// Only include the actual token when generating (not on list/get).
	if includeToken && tokenValue != nil && *tokenValue != "" {
		result.Set("token", *tokenValue)
	}

	return result
}

// apiTokenScopes is `self.scopes or []`: missing, null or empty becomes an empty list.
func apiTokenScopes(raw json.RawMessage) any {
	if len(raw) == 0 {
		return []any{}
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		return []any{}
	}
	if list, ok := v.([]any); ok && len(list) > 0 {
		return list
	}
	return []any{}
}

// apiTokenUsageStats is `self.usage_stats or {}`: missing, null, malformed or empty becomes
// an empty ordered dict.
func apiTokenUsageStats(raw json.RawMessage) any {
	if len(raw) == 0 {
		return entities.NewOrderedMap[any]()
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		return entities.NewOrderedMap[any]()
	}
	if m, ok := v.(*entities.OrderedMap[any]); ok && m.Len() > 0 {
		return m
	}
	return entities.NewOrderedMap[any]()
}

// apiTokenTimeISO is `self.created_at.isoformat() if self.created_at else None`; the zero
// time stands for an unset value.
func apiTokenTimeISO(t time.Time) any {
	if t.IsZero() {
		return nil
	}
	return value_objects.IsoFormat(t)
}

// apiTokenTimePtrISO is the same for an optional datetime.
func apiTokenTimePtrISO(t *time.Time) any {
	if t == nil || t.IsZero() {
		return nil
	}
	return value_objects.IsoFormat(*t)
}
