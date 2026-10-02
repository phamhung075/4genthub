package config_test

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

type obj = *entities.OrderedMap[any]

func field(v any, k string) any { x, _ := v.(obj).Get(k); return x }

func load(t *testing.T, name string) []any {
	raw, err := os.ReadFile("testdata/" + name)
	if err != nil {
		t.Fatal(err)
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	return v.([]any)
}

func dump(t *testing.T, v any) string {
	s, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func envMap(v any) map[string]string {
	env := map[string]string{}
	m := v.(obj)
	for _, k := range m.Keys() {
		x, _ := m.Get(k)
		env[k] = x.(string)
	}
	return env
}

func TestVersionAndAuthConfigParity(t *testing.T) {
	for i, c := range load(t, "version_cases.json") {
		env := envMap(field(c, "env"))
		lookup := func(k string) (string, bool) { v, ok := env[k]; return v, ok }
		version := config.ResolveVersion(lookup)
		if version != field(c, "version") {
			t.Fatalf("case %d: version %q want %v", i, version, field(c, "version"))
		}
		if g, w := dump(t, config.VersionInfoFor(version)), dump(t, field(c, "info")); g != w {
			t.Fatalf("case %d info: got %s want %s", i, g, w)
		}
		sec := config.ValidateSecurityRequirements(func(k string) string { return env[k] })
		if g, w := dump(t, sec), dump(t, field(c, "sec")); g != w {
			t.Fatalf("case %d sec: got %s want %s", i, g, w)
		}
		if !config.ShouldEnforceAuthentication() {
			t.Fatal("authentication must always be enforced")
		}
	}
}

var keep = []string{"Access-Control-Allow-Origin", "Access-Control-Allow-Credentials", "Access-Control-Expose-Headers",
	"Access-Control-Allow-Methods", "Access-Control-Max-Age", "Access-Control-Allow-Headers", "Vary", "Content-Type"}

func TestCORSParity(t *testing.T) {
	for i, c := range load(t, "cors_cases.json") {
		env := envMap(field(c, "env"))
		getenv := func(k string) string { return env[k] }
		var custom []string
		if cu, ok := field(c, "custom").([]any); ok {
			for _, o := range cu {
				custom = append(custom, o.(string))
			}
		}
		app := http.NewServeMux()
		app.HandleFunc("/plain", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write([]byte("hello")) })
		app.HandleFunc("/vary", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Vary", "Accept-Encoding")
			_, _ = w.Write([]byte("v"))
		})
		handler := config.ConfigureCORS(app, field(c, "creds").(bool), custom, getenv)
		reqs := field(c, "reqs").([]any)
		outs := field(c, "outs").([]any)
		for j, rq := range reqs {
			req := httptest.NewRequest(field(rq, "m").(string), field(rq, "path").(string), nil)
			hm := field(rq, "h").(obj)
			for _, k := range hm.Keys() {
				v, _ := hm.Get(k)
				req.Header.Set(k, v.(string))
			}
			rec := httptest.NewRecorder()
			handler.ServeHTTP(rec, req)
			body, _ := io.ReadAll(rec.Result().Body)
			headers := entities.NewOrderedMap[any]()
			for _, k := range keep {
				if v := rec.Header().Get(k); v != "" {
					headers.Set(lower(k), v)
				}
			}
			want := outs[j]
			if rec.Code != int(field(want, "status").(int64)) || string(body) != field(want, "body").(string) {
				t.Fatalf("case %d req %d %v: status/body = %d %q, want %v %q", i, j, rq, rec.Code, body, field(want, "status"), field(want, "body"))
			}
			if g, w := dump(t, sorted(headers)), dump(t, sorted(field(want, "headers").(obj))); g != w {
				t.Fatalf("case %d req %d %v (env %v custom %v creds %v):\n got  %s\n want %s", i, j, rq, env, custom, field(c, "creds"), g, w)
			}
		}
		old := os.Getenv("CORS_ORIGINS")
		_ = old
		cfg := config.GetCORSConfig(getenv)
		wantCfg := field(c, "config").(obj)
		for _, k := range []string{"allowed_origins", "allow_credentials", "allow_methods", "allow_headers", "expose_headers", "max_age"} {
			g, _ := cfg.Get(k)
			if dump(t, g) != dump(t, field(wantCfg, k)) {
				t.Fatalf("case %d config %s: got %s want %s", i, k, dump(t, g), dump(t, field(wantCfg, k)))
			}
		}
	}
}

func lower(s string) string {
	b := []byte(s)
	for i, c := range b {
		if c >= 'A' && c <= 'Z' {
			b[i] = c + 32
		}
	}
	return string(b)
}

func sorted(m obj) obj {
	keys := m.Keys()
	for i := range keys {
		for j := i + 1; j < len(keys); j++ {
			if keys[j] < keys[i] {
				keys[i], keys[j] = keys[j], keys[i]
			}
		}
	}
	out := entities.NewOrderedMap[any]()
	for _, k := range keys {
		v, _ := m.Get(k)
		out.Set(k, v)
	}
	return out
}
