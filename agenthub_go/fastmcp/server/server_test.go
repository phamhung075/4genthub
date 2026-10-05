package server

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

func serverBoolPtr(b bool) *bool { return &b }

func assertServerValueError(t *testing.T, err error, want string) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected error %q, got nil", want)
	}
	ve, ok := err.(*value_objects.ValueError)
	if !ok {
		t.Fatalf("expected *value_objects.ValueError, got %T: %v", err, err)
	}
	if ve.Msg != want {
		t.Fatalf("error = %q, want %q", ve.Msg, want)
	}
}

// Expectations read from server.py add_resource_prefix.
func TestAddResourcePrefix(t *testing.T) {
	cases := []struct {
		uri, prefix, format, want string
	}{
		{"resource://path/to/resource", "prefix", "path", "resource://prefix/path/to/resource"},
		{"resource:///absolute/path", "prefix", "path", "resource://prefix//absolute/path"},
		{"resource://path/to/resource", "prefix", "protocol", "prefix+resource://path/to/resource"},
		{"resource://x", "", "path", "resource://x"},
	}
	for _, c := range cases {
		got, err := AddResourcePrefix(c.uri, c.prefix, strptr(c.format))
		if err != nil {
			t.Fatalf("AddResourcePrefix(%q,%q,%q) error: %v", c.uri, c.prefix, c.format, err)
		}
		if got != c.want {
			t.Fatalf("AddResourcePrefix(%q,%q,%q) = %q, want %q", c.uri, c.prefix, c.format, got, c.want)
		}
	}

	if _, err := AddResourcePrefix("no-scheme", "prefix", strptr("path")); err == nil {
		t.Fatalf("expected ValueError for invalid URI")
	} else {
		assertServerValueError(t, err, "Invalid URI format: no-scheme. Expected protocol://path format.")
	}

	_, err := AddResourcePrefix("resource://x", "prefix", strptr("bogus"))
	assertServerValueError(t, err, "Invalid prefix format: bogus")
}

// Expectations read from server.py remove_resource_prefix.
func TestRemoveResourcePrefix(t *testing.T) {
	cases := []struct {
		uri, prefix, format, want string
	}{
		{"resource://prefix/path/to/resource", "prefix", "path", "resource://path/to/resource"},
		{"prefix+resource://path/to/resource", "prefix", "protocol", "resource://path/to/resource"},
		{"resource://prefix//absolute/path", "prefix", "path", "resource:///absolute/path"},
		{"resource://other/path", "prefix", "path", "resource://other/path"},
		{"resource://x/y", "prefix", "protocol", "resource://x/y"},
		{"resource://x", "", "path", "resource://x"},
	}
	for _, c := range cases {
		got, err := RemoveResourcePrefix(c.uri, c.prefix, strptr(c.format))
		if err != nil {
			t.Fatalf("RemoveResourcePrefix(%q,%q,%q) error: %v", c.uri, c.prefix, c.format, err)
		}
		if got != c.want {
			t.Fatalf("RemoveResourcePrefix(%q,%q,%q) = %q, want %q", c.uri, c.prefix, c.format, got, c.want)
		}
	}

	_, err := RemoveResourcePrefix("no-scheme", "prefix", strptr("path"))
	assertServerValueError(t, err, "Invalid URI format: no-scheme. Expected protocol://path format.")

	_, err = RemoveResourcePrefix("resource://x", "prefix", strptr("bogus"))
	assertServerValueError(t, err, "Invalid prefix format: bogus")
}

// Expectations read from server.py has_resource_prefix.
func TestHasResourcePrefix(t *testing.T) {
	cases := []struct {
		uri, prefix, format string
		want                bool
	}{
		{"resource://prefix/path/to/resource", "prefix", "path", true},
		{"prefix+resource://path/to/resource", "prefix", "protocol", true},
		{"resource://other/path/to/resource", "prefix", "path", false},
		{"resource://x", "", "path", false},
		{"resource://x/y", "prefix", "protocol", false},
	}
	for _, c := range cases {
		got, err := HasResourcePrefix(c.uri, c.prefix, strptr(c.format))
		if err != nil {
			t.Fatalf("HasResourcePrefix(%q,%q,%q) error: %v", c.uri, c.prefix, c.format, err)
		}
		if got != c.want {
			t.Fatalf("HasResourcePrefix(%q,%q,%q) = %v, want %v", c.uri, c.prefix, c.format, got, c.want)
		}
	}

	_, err := HasResourcePrefix("no-scheme", "prefix", strptr("path"))
	assertServerValueError(t, err, "Invalid URI format: no-scheme. Expected protocol://path format.")

	_, err = HasResourcePrefix("resource://x", "prefix", strptr("bogus"))
	assertServerValueError(t, err, "Invalid prefix format: bogus")
}

// Expectations read from server.py _should_enable_component.
func TestShouldEnableComponent(t *testing.T) {
	comp := utilities.NewFastMCPComponent("t", nil, []string{"a", "b"}, nil, nil)
	disabled := utilities.NewFastMCPComponent("t", nil, nil, serverBoolPtr(false), nil)

	set := func(vals ...string) *entities.StringSet {
		s := &entities.StringSet{}
		for _, v := range vals {
			s.Add(v)
		}
		return s
	}

	if ShouldEnableComponent(disabled, nil, nil) {
		t.Fatalf("disabled component should be disabled")
	}
	if !ShouldEnableComponent(comp, nil, nil) {
		t.Fatalf("no tag filters should enable")
	}
	if ShouldEnableComponent(comp, nil, set("a")) {
		t.Fatalf("excluded tag present should disable")
	}
	if !ShouldEnableComponent(comp, nil, set("z")) {
		t.Fatalf("exclude with no match should fall through to true")
	}
	if !ShouldEnableComponent(comp, set("b"), nil) {
		t.Fatalf("included tag present should enable")
	}
	if ShouldEnableComponent(comp, set("z"), nil) {
		t.Fatalf("include without match should disable")
	}
	if ShouldEnableComponent(comp, set("a"), set("a")) {
		t.Fatalf("exclude wins over include")
	}
	if !ShouldEnableComponent(comp, set("a"), set("z")) {
		t.Fatalf("include matches and exclude does not should enable")
	}
}
