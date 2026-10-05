package database

import (
	"encoding/json"
	"os"
	"path"
	"testing"
)

func envFrom(m map[string]string) Getenv {
	return func(k string) (string, bool) { v, ok := m[k]; return v, ok }
}

func TestDatabaseURLParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/dburl_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		Kind string
		Type string
		Env  map[string]string
		Want *string
		Err  *string
		Cwd  string
		Cfg  bool
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		deps := Deps{
			Getenv: envFrom(c.Env),
			Exists: func(p string) bool { return p == c.Cwd },
			Abs: func(p string) (string, error) {
				if path.IsAbs(p) {
					return path.Clean(p), nil
				}
				return path.Join(c.Cwd, p), nil
			},
		}
		if c.Kind == "cfg" {
			d := &DatabaseConfig{DatabaseType: c.Type, deps: deps}
			got := d.secureDatabaseURL()
			want := ""
			if c.Want != nil {
				want = *c.Want
			}
			if got != want {
				t.Errorf("cfg %s %v: got %q want %q", c.Type, c.Env, got, want)
			}
			continue
		}
		s := &SupabaseConfig{SupabaseURL: c.Env["SUPABASE_URL"], deps: deps}
		got, err := s.supabaseDatabaseURL()
		if c.Err != nil {
			if err == nil || err.Error() != *c.Err {
				t.Errorf("sup %v: got (%q, %v) want error %q", c.Env, got, err, *c.Err)
			}
		} else if err != nil || got != *c.Want {
			t.Errorf("sup %v: got (%q, %v) want %q", c.Env, got, err, *c.Want)
		}
		if IsSupabaseConfigured(deps.Getenv) != c.Cfg {
			t.Errorf("is_supabase_configured %v: got %v want %v", c.Env, !c.Cfg, c.Cfg)
		}
	}
}
