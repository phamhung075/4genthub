package server

import (
	"regexp"
	"testing"

	openapi "agenthub/fastmcp/utilities"
)

func strptr(s string) *string { return &s }

func TestSlugify(t *testing.T) {
	// Expected values produced by running the Python _slugify body.
	cases := map[string]string{
		"":                "",
		"Hello World":     "Hello_World",
		"get-user.by-id!": "get_user_by_id",
		"a--b..c  d":      "a_b_c_d",
		"__leading__":     "leading",
		"CamelCase123":    "CamelCase123",
	}
	for in, want := range cases {
		if got := Slugify(in); got != want {
			t.Errorf("Slugify(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestRouteMapPostInit(t *testing.T) {
	// mcp_type missing -> Python ValueError("`mcp_type` must be provided").
	rm := &RouteMap{}
	if err := rm.PostInit(); err == nil || err.Error() != "`mcp_type` must be provided" {
		t.Fatalf("PostInit() err = %v, want ValueError text", err)
	}

	// Deprecated RouteType.IGNORE converts to MCPType.EXCLUDE and route_type follows
	// mcp_type. Default tests use MCPType.TOOL.
	rt := RouteTypeIgnore
	rm = &RouteMap{RouteType: &rt}
	if err := rm.PostInit(); err != nil {
		t.Fatal(err)
	}
	if rm.MCPType == nil || *rm.MCPType != MCPTypeExclude {
		t.Fatalf("IGNORE -> %v, want EXCLUDE", rm.MCPType)
	}
	// Python only assigns route_type = mcp_type when route_type was None, so an explicit
	// deprecated IGNORE stays IGNORE while mcp_type becomes EXCLUDE.
	if rm.RouteType == nil || *rm.RouteType != RouteTypeIgnore {
		t.Fatalf("route_type must stay IGNORE, got %v", rm.RouteType)
	}
}

func TestDetermineRouteType(t *testing.T) {
	// DEFAULT_ROUTE_MAPPINGS (all routes become tools).
	base := &openapi.HTTPRoute{Path: "/users/1", Method: openapi.HttpMethodGET}
	if got := DetermineRouteType(base, DefaultRouteMappings); got == nil || *got.MCPType != MCPTypeTool {
		t.Fatalf("default mapping = %v, want TOOL", got)
	}

	// First matching mapping wins; methods filter, then regex search, then tags.
	rt := RouteTypeResource
	m := &RouteMap{
		Methods:   []HttpMethod{"GET"},
		Pattern:   regexp.MustCompile(`.*/users/.*`),
		RouteType: &rt,
		Tags:      map[string]struct{}{"public": {}},
		MCPTags:   map[string]struct{}{},
	}
	if err := m.PostInit(); err != nil {
		t.Fatal(err)
	}
	tagged := &openapi.HTTPRoute{Path: "/users/1", Method: openapi.HttpMethodGET, Tags: []string{"public"}}
	if got := DetermineRouteType(tagged, []*RouteMap{m}); got != m {
		t.Fatalf("expected custom mapping to match")
	}
	untagged := &openapi.HTTPRoute{Path: "/users/1", Method: openapi.HttpMethodGET}
	if got := DetermineRouteType(untagged, []*RouteMap{m}); got == m || *got.MCPType != MCPTypeTool {
		t.Fatalf("tags must all be present; got %v", got)
	}
	if got := DetermineRouteType(&openapi.HTTPRoute{Path: "/users/1", Method: openapi.HttpMethodPOST}, []*RouteMap{m}); got == m {
		t.Fatalf("method filter must reject POST")
	}
}

func TestGenerateDefaultName(t *testing.T) {
	// operation_id with "__" -> first part, slugified.
	r := &openapi.HTTPRoute{Method: openapi.HttpMethodGET, Path: "/a", OperationID: strptr("get_user__extra")}
	if got := GenerateDefaultName(r, nil); got != "get_user" {
		t.Errorf("opid split = %q, want get_user", got)
	}
	// custom mcp_names mapping takes precedence.
	if got := GenerateDefaultName(r, map[string]string{"get_user__extra": "Custom Name!"}); got != "Custom_Name" {
		t.Errorf("custom mapping = %q, want Custom_Name", got)
	}
	// summary used when no operation_id, then slugified.
	r = &openapi.HTTPRoute{Method: openapi.HttpMethodGET, Path: "/a", Summary: strptr("List Things")}
	if got := GenerateDefaultName(r, nil); got != "List_Things" {
		t.Errorf("summary = %q, want List_Things", got)
	}
	// no operation_id and empty summary -> "{method}_{path}", then slugified (the "/" is
	// stripped by _slugify).
	r = &openapi.HTTPRoute{Method: openapi.HttpMethodGET, Path: "/a", Summary: strptr("")}
	if got := GenerateDefaultName(r, nil); got != "GET_a" {
		t.Errorf("fallback = %q, want GET_a", got)
	}
	// truncated to 56 characters.
	long := Slugify("x")
	_ = long
	r = &openapi.HTTPRoute{Method: openapi.HttpMethodGET, Path: "/a", Summary: strptr("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")}
	if got := GenerateDefaultName(r, nil); len(got) != 56 {
		t.Errorf("truncation len = %d, want 56", len(got))
	}
}

func TestGetUniqueName(t *testing.T) {
	used := NewUsedNames()
	if got := GetUniqueName(used, "foo", "tool"); got != "foo" {
		t.Errorf("first = %q, want foo", got)
	}
	if got := GetUniqueName(used, "foo", "tool"); got != "foo_2" {
		t.Errorf("second = %q, want foo_2", got)
	}
	if got := GetUniqueName(used, "foo", "tool"); got != "foo_3" {
		t.Errorf("third = %q, want foo_3", got)
	}
}
