package adapters

import "testing"

func TestCacheKeyBuilderAdapter(t *testing.T) {
	b := &CacheKeyBuilderAdapter{}
	if got := b.BuildKey("ctx", []any{"u1", 2}, nil); got != "ctx:u1:2" {
		t.Fatalf("BuildKey = %q", got)
	}
	if got := b.BuildKey("ctx", nil, map[string]any{"b": 2, "a": 1}); got != "ctx:a:1:b:2" {
		t.Fatalf("BuildKey kwargs = %q", got)
	}
	if got := b.BuildKey("ctx", []any{"x"}, map[string]any{"a": "v"}); got != "ctx:x:a:v" {
		t.Fatalf("BuildKey mixed = %q", got)
	}
	if got := b.BuildPattern("ctx", "*"); got != "ctx:*" {
		t.Fatalf("BuildPattern = %q", got)
	}
}
