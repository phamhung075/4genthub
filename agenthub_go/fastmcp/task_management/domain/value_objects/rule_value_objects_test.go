package value_objects

import "testing"

func TestClientConfigDefaultsAndHistory(t *testing.T) {
	c, err := NewClientConfig("c", "n", ClientAuthMethodToken, nil, []string{"read"})
	if err != nil || c.RateLimit != 100 || c.SyncFrequency != 300 || !c.AutoSync || c.ConflictResolution != ConflictResolutionMerge ||
		len(c.AllowedRuleTypes) != len(RuleTypeValues) || !c.CanSyncRuleType(RuleTypeCore) {
		t.Fatal(c, err)
	}
	for i := 0; i < 105; i++ {
		c.AddToHistory("e")
	}
	if len(c.SyncHistory) != 100 {
		t.Fatal(len(c.SyncHistory))
	}
	c.AddPermission("read")
	c.AddPermission("write")
	c.RemovePermission("read")
	if c.HasPermission("read") || !c.HasPermission("write") {
		t.Fatal(c.SyncPermissions)
	}
	c.RateLimit = 0
	if err := c.Validate(); err == nil || err.Error() != "Rate limit must be positive" {
		t.Fatal(err)
	}
	if _, err := NewClientConfig("", "n", ClientAuthMethodToken, nil, nil); err == nil || err.Error() != "Client ID cannot be empty" {
		t.Fatal(err)
	}
}

func TestSyncObjects(t *testing.T) {
	if _, err := NewSyncRequest("r", "c", SyncOperationPush, nil, nil, 0, 0); err == nil || err.Error() != "Priority must be at least 1" {
		t.Fatal(err)
	}
	r, _ := NewSyncRequest("r", "c", SyncOperationPush, nil, nil, 0, 5)
	if !r.IsHighPriority() {
		t.Fatal("priority")
	}
	res, err := NewSyncResult("r", "c", SyncStatusCompleted, SyncOperationPush, nil, nil, nil, nil, 1.5, 0, 0)
	if err != nil || !res.IsSuccessful() {
		t.Fatal(err)
	}
	res.AddError("x")
	res.AddError("x")
	if res.IsSuccessful() || len(res.Errors) != 1 {
		t.Fatal(res.Errors)
	}
}

func TestGenericRuleTypes(t *testing.T) {
	if _, err := NewCompositionResult[int]("", nil, nil, nil, nil, true); err == nil || err.Error() != "Successful composition must have content" {
		t.Fatal(err)
	}
	e, err := NewCacheEntry("content", unixNow()-10, 0, 5)
	if err != nil || !e.IsExpired() {
		t.Fatal(err)
	}
	e.UpdateTimestamp()
	if e.IsExpired() {
		t.Fatal("fresh entry")
	}
	if _, err := NewCacheEntry("c", 0, 0, 0); err == nil || err.Error() != "TTL must be positive" {
		t.Fatal(err)
	}
	h, _ := NewRuleHierarchyInfo(3, 1, 2, [][]string{{"a", "b"}}, nil, nil)
	if h.IsHealthy() || !h.HasCircularDependencies() {
		t.Fatal("hierarchy")
	}
}
