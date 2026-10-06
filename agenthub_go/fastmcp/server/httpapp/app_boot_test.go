package httpapp

// The composition root, exercised the way cmd/agenthub exercises it, up to the listener.
//
// WHY: on 2026-10-06 the server could not be constructed - `app: unknown table "seat_feedback"`,
// exit 1 - while `go build`, `go vet` and every package test were green. The composition root had
// grown a controller whose repository asks the shared ORM registry for a table by NAME, and the
// registry lookup happens at RUNTIME, so only an actual NewApp call could see it.
//
// THIS IS NOT THE ALWAYS-RUNNING GUARD FOR THAT CLASS, and it must not be mistaken for one: it
// SKIPS without AGENTHUB_TEST_PG_URL, so it would not have run in the default `go test` that the
// defect slipped through. The default-run guard is
// TestORMRepositoriesAskForRegisteredTables in the ORM repositories package. This file covers what
// only a real database can reach: that the composition root composes against a MIGRATED schema.
//
// ITS OWN LIMIT, stated: it proves the composition composes against a schema the tree's migration
// path created. It does NOT prove that a production schema is migrated - a different question, and
// not the one that bit us.

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestAppBootsAgainstAMigratedDatabase is the boot step of cmd/agenthub's main: the tree's own
// migration path on a throwaway database, then NewApp. The bring-up helper is the one this package
// already has (missed_notification_replay_test.go), used rather than reimplemented so there is one
// database bring-up in the package.
func TestAppBootsAgainstAMigratedDatabase(t *testing.T) {
	sessions := newMissedNotificationAppEnv(t)
	ctx := context.Background()

	app, err := NewApp(ctx, sessions)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	if app == nil {
		t.Fatal("NewApp returned no app and no error")
	}

	// The composition produced the MCP tool surface it promises: the two seat tools and the
	// friction channel's tool. A controller that failed to compose shows up here as a missing tool.
	tools, err := app.getMCPToolsList()
	if err != nil {
		t.Fatalf("getMCPToolsList: %v", err)
	}
	published := map[string]bool{}
	for _, tool := range tools {
		name, _ := tool["name"].(string)
		published[name] = true
	}
	for _, want := range []string{"manage_seat", "call_seat", "submit_feedback"} {
		if !published[want] {
			t.Errorf("tools/list does not publish %s; published: %v", want, published)
		}
	}

	// And the handler serves the routes the composition mounted, the friction channel's included:
	// its two lines (the boot-time composition and the mount) land together, because composed
	// without the table the process dies and mounted without the composition the routes answer
	// 500. A path that lost its mount shows up here as a 404.
	handler := app.Handler()
	for _, probe := range []struct {
		method string
		path   string
	}{
		{http.MethodPost, "/api/v2/openrig/seat-status"},
		{http.MethodGet, "/api/v2/openrig/machines"},
		{http.MethodPost, "/api/v2/openrig/feedback"},
		{http.MethodGet, "/api/v2/openrig/feedback"},
	} {
		req := httptest.NewRequest(probe.method, probe.path, strings.NewReader(``))
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		if rec.Code == http.StatusNotFound {
			t.Errorf("%s %s is not mounted (404): the composition root stopped registering it", probe.method, probe.path)
		}
	}
}
