package config_test

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"agenthub/fastmcp/config"
)

// A handler that writes nothing must still get CORS headers; a recorder snapshots
// headers late and hides this, so use a real server.
func TestCORSEmptyHandlerGetsHeaders(t *testing.T) {
	h := config.ConfigureCORS(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}), false, []string{"*"}, func(string) string { return "" })
	srv := httptest.NewServer(h)
	defer srv.Close()
	req, _ := http.NewRequest(http.MethodGet, srv.URL, nil)
	req.Header.Set("Origin", "http://x.test")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.Header.Get("Access-Control-Allow-Origin") == "" {
		t.Fatal("missing Access-Control-Allow-Origin on empty response")
	}
}

// Starlette treats a preflight as the mere presence of Access-Control-Request-Method.
func TestCORSPreflightEmptyMethodHeader(t *testing.T) {
	h := config.ConfigureCORS(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(204) }), false, nil, func(string) string { return "" })
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodOptions, "/", nil)
	req.Header.Set("Origin", "http://x.test")
	req.Header["Access-Control-Request-Method"] = []string{""}
	h.ServeHTTP(rec, req)
	if rec.Code != 400 {
		t.Fatalf("status %d, want 400", rec.Code)
	}
}
