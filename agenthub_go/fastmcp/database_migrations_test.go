package fastmcp

import "testing"

// The migrator guard decides whether the DSN is Postgres by scheme. pgx accepts both
// postgres:// and postgresql://; the throwaway-Postgres tests pass postgres://, which the
// original postgresql-only substring check missed, silently skipping the migration.
func TestIsPostgresURL(t *testing.T) {
	cases := []struct {
		url  string
		want bool
	}{
		{"postgres://postgres@127.0.0.1:54329/db?sslmode=disable", true},
		{"postgresql://u:p@h:5432/db", true},
		{"sqlite:///agenthub_dev.db", false},
		{"mysql://u:p@h/db", false},
		{"", false},
	}
	for _, c := range cases {
		if got := isPostgresURL(c.url); got != c.want {
			t.Errorf("isPostgresURL(%q) = %v, want %v", c.url, got, c.want)
		}
	}
}
