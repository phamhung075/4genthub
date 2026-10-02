package repositories

import (
	"strings"
	"testing"
)

func TestPortTemplateRepoFactoryMissingDatabaseType(t *testing.T) {
	t.Setenv("DATABASE_TYPE", "")
	f := NewTemplateRepositoryFactory(nil, nil)
	_, err := f.CreateRepository(nil)
	if err == nil {
		t.Fatal("expected ValueError when DATABASE_TYPE is unset")
	}
	want := "DATABASE_TYPE environment variable is not set. " +
		"Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'"
	if err.Error() != want {
		t.Fatalf("error = %q, want %q", err.Error(), want)
	}
	if _, ok := err.(*ValueError); !ok {
		t.Fatalf("error type = %T, want *ValueError", err)
	}
}

func TestPortTemplateRepoFactoryCreateDelegates(t *testing.T) {
	t.Setenv("DATABASE_TYPE", "")
	f := NewTemplateRepositoryFactory(nil, nil)
	_, errS := f.CreateSQLiteRepository(nil)
	_, errO := f.CreateORMRepository()
	for name, err := range map[string]error{"sqlite": errS, "orm": errO} {
		if err == nil || !strings.Contains(err.Error(), "DATABASE_TYPE") {
			t.Fatalf("%s: err = %v, want DATABASE_TYPE error", name, err)
		}
	}
}
