package linkgraph

import (
	"strings"
	"testing"
)

func TestFindLaunchCycle(t *testing.T) {
	edge := func(kind, from, to string) Edge { return Edge{Kind: kind, From: from, To: to} }
	cases := []struct {
		name  string
		edges []Edge
		want  string
	}{
		{"none", nil, ""},
		{"self loop", []Edge{edge("delegates_to", "a", "a")}, "a>a"},
		{"self loop spawned_by", []Edge{edge("spawned_by", "a", "a")}, "a>a"},
		{"chain", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "c")}, ""},
		{"opposite delegates_to", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "a")}, "a>b>a"},
		{"three seats", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "c"), edge("delegates_to", "c", "a")}, "a>b>c>a"},
		{"spawned_by is the reverse order", []Edge{edge("spawned_by", "a", "b"), edge("spawned_by", "b", "c"), edge("spawned_by", "c", "a")}, "a>c>b>a"},
		{"delegates_to and spawned_by together", []Edge{edge("delegates_to", "a", "b"), edge("spawned_by", "a", "b")}, "a>b>a"},
		{"spawned_by parent and delegates_to child agree", []Edge{edge("delegates_to", "a", "b"), edge("spawned_by", "b", "a")}, ""},
		{"descriptive kinds are not counted", []Edge{edge("collaborates_with", "a", "b"), edge("collaborates_with", "b", "a"), edge("escalates_to", "a", "b"), edge("escalates_to", "b", "a"), edge("can_observe", "a", "b"), edge("can_observe", "b", "a")}, ""},
		{"cycle behind a tail", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "c"), edge("delegates_to", "c", "b")}, "b>c>b"},
	}
	for _, c := range cases {
		if got := strings.Join(FindLaunchCycle(c.edges), ">"); got != c.want {
			t.Errorf("%s: cycle = %q, want %q", c.name, got, c.want)
		}
	}
}
