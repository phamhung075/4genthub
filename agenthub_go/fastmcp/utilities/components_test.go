package utilities

import "testing"

func TestFastMCPComponentDefaultsAndKey(t *testing.T) {
	c := NewFastMCPComponent("tool-a", nil, []string{"b", "a", "b"}, nil, nil)
	if !c.Enabled {
		t.Fatal("enabled should default to true")
	}
	if len(c.Tags) != 2 || c.Tags[0] != "a" || c.Tags[1] != "b" {
		t.Fatalf("tags = %v, want sorted unique [a b]", c.Tags)
	}
	if c.Key() != "tool-a" {
		t.Fatalf("Key = %q, want name", c.Key())
	}
	withKey := c.WithKey("prefixed/tool-a")
	if withKey.Key() != "prefixed/tool-a" {
		t.Fatalf("WithKey Key = %q", withKey.Key())
	}
	if !c.Equals(withKey) {
		t.Fatal("key is a private attr and must not affect equality")
	}
	if c.Key() != "tool-a" {
		t.Fatalf("WithKey must not mutate the original, Key = %q", c.Key())
	}
}

func TestFastMCPComponentEmptyKeyFallsBackToName(t *testing.T) {
	empty := ""
	c := NewFastMCPComponent("n", nil, nil, nil, &empty)
	if c.Key() != "n" {
		t.Fatalf("Key = %q, want name for falsy key", c.Key())
	}
}

func TestFastMCPComponentEnabledAndEqualityAndRepr(t *testing.T) {
	desc := "d"
	c := NewFastMCPComponent("x", &desc, []string{"a"}, nil, nil)
	if c.Repr() != "FastMCPComponent(name='x', description='d', tags={'a'}, enabled=True)" {
		t.Fatalf("Repr = %q", c.Repr())
	}
	c.Disable()
	if c.Enabled {
		t.Fatal("Disable did not clear enabled")
	}
	c.Enable()
	if !c.Enabled {
		t.Fatal("Enable did not set enabled")
	}
	other := NewFastMCPComponent("x", &desc, []string{"a"}, nil, nil)
	if !c.Equals(other) {
		t.Fatal("equal components reported unequal")
	}
	other.Name = "y"
	if c.Equals(other) {
		t.Fatal("different names must be unequal")
	}
	if c.Equals(nil) {
		t.Fatal("nil must be unequal")
	}
}

func TestFastMCPComponentReprNoneDescriptionAndEmptyTags(t *testing.T) {
	c := NewFastMCPComponent("x", nil, nil, nil, nil)
	if c.Repr() != "FastMCPComponent(name='x', description=None, tags=set(), enabled=True)" {
		t.Fatalf("Repr = %q", c.Repr())
	}
}
