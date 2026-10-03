package seatsync

import "testing"

func TestSync(t *testing.T) {
	cases := []struct{ running, expected, want string }{
		{"", "x", Unknown},
		{"x", "", Unknown},
		{"", "", Unknown},
		{"x", "x", InSync},
		{"x", "y", Drift},
	}
	for _, c := range cases {
		if got := Sync(c.running, c.expected); got != c.want {
			t.Errorf("Sync(%q, %q) = %q, want %q", c.running, c.expected, got, c.want)
		}
	}
}
