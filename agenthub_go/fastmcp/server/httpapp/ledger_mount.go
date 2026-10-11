// ledger_mount.go mounts the ledger's own TWO routes - the cross-task read (P2) and the intents
// route (P3) - and holds the adapters that carry the request's user onto the ledger's layers.
//
// It is a mount file of its own, for the reason the other mount files here are: app.go's Handler
// composes the mux, and a route family that added its registrations there would put two items' work
// in one file. The handlers themselves are in routes/ledger_routes.go, the shape O1a's read and O3's
// evidence route already use; what lives here is the HTTP half and nothing else.
//
// ONE LINE IN app.go: Handler calls mountLedgerRoutes beside the other mounts. A mount nothing calls
// is a route that does not exist - the same defect as a repository committed without its table.
package httpapp

import (
	"context"
	"encoding/json"
	"math"
	"net/http"
	"strconv"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	ledgerservices "agenthub/fastmcp/ledger/application/services"
	ledgerentities "agenthub/fastmcp/ledger/domain/entities"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

// mountLedgerRoutes registers GET /api/v2/ledger and POST /api/v2/ledger/intents. Handler must call
// it once; the patterns are not registered anywhere else.
//
// BOTH routes sit behind the SAME `authed` wrapper as the task routes and O3's evidence route. There
// is no second guard and no machine token: the ledger is read and written on behalf of the user the
// bearer token resolves, which is the only identity either route knows.
func mountLedgerRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	const base = "/api/v2/ledger"

	mux.HandleFunc("GET "+base, authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		after, ok := ledgerQueryInt(w, r, "after", 0)
		if !ok {
			return
		}
		limit, ok := ledgerQueryInt(w, r, "limit", 0)
		if !ok {
			return
		}
		body, err := routes.GetLedger(r.Context(), after, int(limit), u, ledgerReaderAdapter{sessions: sessions})
		writeResult(w, body, err)
	}))

	mux.HandleFunc("POST "+base+"/intents", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		intents, ok := ledgerIntentsBody(w, r)
		if !ok {
			return
		}
		body, err := routes.SubmitLedgerIntents(r.Context(), intents, u, ledgerIntentsWriterAdapter{sessions: sessions})
		// The answer is a LIST - one object per request item - so it is written as one, through the
		// same writer the server's other list-returning routes use.
		writeSliceResult(w, body, err)
	}))
}

// ledgerQueryInt reads one optional integer query parameter. A value that is not an integer is a 422,
// which is what GET /api/v2/tasks/ does with its own limit: a cursor the server silently
// reinterprets is a cursor that skips rows, and a client would never learn that it had.
func ledgerQueryInt(w http.ResponseWriter, r *http.Request, key string, def int64) (int64, bool) {
	if !r.URL.Query().Has(key) {
		return def, true
	}
	n, err := strconv.ParseInt(r.URL.Query().Get(key), 10, 64)
	if err != nil {
		writeDetail(w, http.StatusUnprocessableEntity, "Input should be a valid integer, unable to parse string as an integer")
		return 0, false
	}
	return n, true
}

// ledgerIntentsBody decodes the intents body: an ARRAY of items, which is not what jsonBody reads
// (that helper reads one object). A body that is not a list is refused whole with FastAPI's 422 for
// a body of the wrong shape; an ITEM that is not an object is NOT refused here, because the route
// answers per item and dropping one silently would lose the client's work.
func ledgerIntentsBody(w http.ResponseWriter, r *http.Request) ([]ledgerentities.Intent, bool) {
	var items []json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&items); err != nil {
		b, _ := json.Marshal(map[string]any{"detail": []map[string]any{{
			"type": "list_type", "loc": []string{"body"},
			"msg": "Input should be a valid list", "input": nil,
		}}})
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnprocessableEntity)
		_, _ = w.Write(b)
		return nil, false
	}
	out := make([]ledgerentities.Intent, 0, len(items))
	for _, raw := range items {
		out = append(out, ledgerIntentFromJSON(raw))
	}
	return out, true
}

// ledgerIntentFromJSON reads one item off the wire into the contract's own fields. An item that is
// not a JSON object leaves every field blank (a nil map reads as absent for every key), which the
// service refuses with the reason the client can act on - it named no usable client_event_id.
//
// base_seq is taken only when it is a whole number in int range: a fractional or absurd one is left
// ABSENT rather than truncated, so a client that sent 3.5 gets "a decision owes a base_seq" instead
// of a decision silently staged on seq 3.
func ledgerIntentFromJSON(raw json.RawMessage) ledgerentities.Intent {
	var m map[string]any
	_ = json.Unmarshal(raw, &m)

	in := ledgerentities.Intent{}
	in.ClientEventID, _ = m["client_event_id"].(string)
	in.TaskID, _ = m["task_id"].(string)
	in.SubtaskID, _ = m["subtask_id"].(string)
	if kind, ok := m["kind"].(string); ok {
		in.Kind = ledgerentities.IntentKind(kind)
	}
	if base, ok := m["base_seq"].(float64); ok && base == math.Trunc(base) && base >= 0 && base <= math.MaxInt32 {
		in.BaseSeq = new(int(base))
	}
	in.Payload = m["payload"]
	return in
}

// ledgerReaderAdapter satisfies routes.LedgerReader over the ledger's application service.
//
// It builds the user-scoped repository per call rather than holding one, because the repository is
// scoped to one user and the user comes from the request - the same seam task_event_controller.go
// uses for the per-task read. The id the rows are scoped to is the token subject NORMALIZED exactly
// as that adapter normalizes it: the ledger's user_id is written normalized by every writer, and
// with the raw subject a read matches nothing and answers 200 with an empty list for any non-UUID
// subject - silently, which is the failure mode this ledger exists to make visible.
type ledgerReaderAdapter struct {
	sessions *database.SessionManager
}

func (a ledgerReaderAdapter) ListUserEvents(ctx context.Context, userID string, after int64, limit int) ([]*taskdomain.TaskEvent, int64, error) {
	raw := userID
	scoped, err := domain.ValidateUserID(&raw, "ledger read")
	if err != nil {
		return nil, 0, err
	}
	page, err := ledgerservices.New(repositories.NewTaskEventRepository(a.sessions, scoped, "")).ReadAfter(ctx, after, limit)
	if err != nil {
		return nil, 0, err
	}
	return page.Events, page.Tip, nil
}

// ledgerIntentsWriterAdapter satisfies routes.LedgerIntentWriter over the ledger's application
// service, with the same per-call user-scoping the reader adapter uses.
type ledgerIntentsWriterAdapter struct {
	sessions *database.SessionManager
}

func (a ledgerIntentsWriterAdapter) SubmitIntents(ctx context.Context, userID string, intents []ledgerentities.Intent) ([]ledgerentities.Answer, error) {
	raw := userID
	scoped, err := domain.ValidateUserID(&raw, "ledger intents")
	if err != nil {
		return nil, err
	}
	// WHO the write is attributed to is the rule the evidence route already applies
	// (task_event_controller.go's evidenceActor, which restates services.actorFor): a seat named on
	// the request acted on the caller's behalf, and a request that named none belongs to the user
	// these rows are scoped to. The rule is REUSED rather than spelled a third time, so the ledger
	// and the evidence path cannot come to attribute the same request differently.
	actor, err := evidenceActor(ctx, scoped)
	if err != nil {
		return nil, err
	}
	service := ledgerservices.New(repositories.NewTaskEventRepository(a.sessions, scoped, ""))
	return service.SubmitIntents(ctx, actor.Kind, actor.ID, intents)
}
