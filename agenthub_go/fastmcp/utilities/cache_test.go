package utilities

import (
	"testing"
	"time"
)

func TestTimedCacheSetGetClear(t *testing.T) {
	c := NewTimedCache(time.Minute)
	c.Set("k", 42)
	if got := c.Get("k"); got != 42 {
		t.Fatalf("Get = %v, want 42", got)
	}
	if got := c.Get("missing"); got != TimedCacheNotFound {
		t.Fatalf("missing Get = %v, want NOT_FOUND", got)
	}
	// Overwrite.
	c.Set("k", "v")
	if got := c.Get("k"); got != "v" {
		t.Fatalf("overwritten Get = %v, want v", got)
	}
	c.Clear()
	if got := c.Get("k"); got != TimedCacheNotFound {
		t.Fatalf("cleared Get = %v, want NOT_FOUND", got)
	}
}

func TestTimedCacheExpiredValueNotDeleted(t *testing.T) {
	c := NewTimedCache(-time.Second)
	c.Set("k", "v")
	if got := c.Get("k"); got != TimedCacheNotFound {
		t.Fatalf("expired Get = %v, want NOT_FOUND", got)
	}
	if _, ok := c.Cache["k"]; !ok {
		t.Fatal("expired entry should remain in the cache, like Python")
	}
}

func TestTimedCacheZeroValueUsable(t *testing.T) {
	c := &TimedCache{Expiration: time.Minute}
	c.Set("k", 1)
	if got := c.Get("k"); got != 1 {
		t.Fatalf("Get = %v, want 1", got)
	}
}
