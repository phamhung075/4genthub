package fastmcp_test

import (
	"testing"

	"agenthub/fastmcp"
)

func TestDatabaseInitializerURL(t *testing.T) {
	t.Setenv("DATABASE_TYPE", "postgresql")
	t.Setenv("DATABASE_HOST", "h")
	t.Setenv("DATABASE_PORT", "1")
	t.Setenv("DATABASE_NAME", "db")
	t.Setenv("DATABASE_USER", "u")
	t.Setenv("DATABASE_PASSWORD", "p")
	if got := fastmcp.NewDatabaseInitializer("").DatabaseURL; got != "postgresql://u:p@h:1/db" {
		t.Fatalf("DatabaseURL = %q", got)
	}
	if got := fastmcp.NewDatabaseInitializer("postgresql://a:b@c:2/d").DatabaseURL; got != "postgresql://a:b@c:2/d" {
		t.Fatalf("explicit DatabaseURL = %q", got)
	}
}
