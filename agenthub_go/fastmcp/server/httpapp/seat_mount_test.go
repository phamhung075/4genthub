package httpapp

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type fakeSeatSource struct {
	resolved *repositories.ResolvedSeat
	err      error
	seeded   int
}

func (f *fakeSeatSource) ResolveSeat(_ context.Context, _, _, _ string) (*repositories.ResolvedSeat, error) {
	return f.resolved, f.err
}

func (f *fakeSeatSource) SeedSeatTypes(_ context.Context, _ string) (int, error) {
	return f.seeded, f.err
}

func seatTestMux(t *testing.T, source seatSource) *http.ServeMux {
	t.Helper()
	previous := newSeatSource
	newSeatSource = func(*database.SessionManager, string) (seatSource, error) { return source, nil }
	t.Cleanup(func() { newSeatSource = previous })
	authenticateAgentsTestUser(t)
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux
}

func TestResolveSeatReturnsSnapshot(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{
		Hash: "abc", Runtime: "claude-code",
		Files:  []repositories.ResolvedFile{{Path: "agent.yaml", Content: "name: x"}},
		Policy: map[string]any{"Seat": "coder"},
	}})
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/coder", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"hash":"abc"`, `"room":"dev"`, `"seat":"coder"`, `"path":"agent.yaml"`, `"Seat":"coder"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("body missing %s: %s", want, rec.Body.String())
		}
	}
}

func TestResolveSeatStatusMapping(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	cases := []struct {
		err  error
		want int
	}{
		{errors.New(`seat "x" not found in room "dev"`), http.StatusNotFound},
		{errors.New("database down"), http.StatusInternalServerError},
	}
	for _, c := range cases {
		mux := seatTestMux(t, &fakeSeatSource{err: c.err})
		if rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", ""); rec.Code != c.want {
			t.Errorf("%v: status = %d, want %d", c.err, rec.Code, c.want)
		}
	}
}

func TestSeatRoutesNeedPublicURLAndAuth(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{})
	if rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", ""); rec.Code != http.StatusInternalServerError {
		t.Errorf("without %s: status = %d", publicURLEnv, rec.Code)
	}
	bare := httptest.NewRecorder()
	mux.ServeHTTP(bare, httptest.NewRequest(http.MethodGet, "/api/v2/openrig/seats/dev/x", nil))
	if bare.Code == http.StatusNotFound || bare.Code == http.StatusOK {
		t.Errorf("unauthenticated request: status = %d, want 401/403", bare.Code)
	}
}

func TestSeedSeatTypesReportsCount(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{seeded: 9})
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seat_types":9`) {
		t.Errorf("seed: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeedSeatTypesWorksWithoutPublicURL(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{seeded: 9})
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seat_types":9`) {
		t.Errorf("seed without %s: status = %d %s", publicURLEnv, rec.Code, rec.Body.String())
	}
}

func TestSeedSeatTypesErrorMapping(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{err: errors.New("database down")})
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("seed error: status = %d, want 500", rec.Code)
	}
}
