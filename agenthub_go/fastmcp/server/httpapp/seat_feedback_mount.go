package httpapp

// seat_feedback_mount.go is the seat friction channel over HTTP: a seat, its operator, or a bridge
// reporting for its seats submits friction, and the owner reads it grouped by the layer the
// friction is in.
//
//	POST /api/v2/openrig/feedback   user token OR machine token
//	GET  /api/v2/openrig/feedback   user token, tenant-scoped by the caller
//
// This file owns the transport only. The writer contract — the layer vocabulary, the bounds, and
// the credential scan — is SeatFeedbackService, because the channel's other submission path (the
// MCP tool) reaches the same service rather than opening a socket back into this server.
//
// The layer is a first-class column with a closed vocabulary (domain/feedback, checked against the
// DDL by TestSeatFeedbackLayerCheckMatchesDomain), not a tag: the read side groups by it, and a
// free-text layer would fragment that grouping into near-duplicates.
//
// AUTH, and the one deliberate looseness in it. The POST accepts a user token or a machine token
// because the two submission paths differ: an MCP-calling seat carries its AGENTHUB_TOKEN (a user
// token) while a bridge holds only its machine token. Either way the row is written under the
// TOKEN'S user id, so a machine token cannot write outside its own tenant. What a machine token is
// NOT restricted to is the seat set: it may name any room and seat in its tenant, because the token
// is bound to a machine (machine_token_mount.go) and not to seats, and the precedent is
// POST /seat-status — that route checks only that the report names the token's own machine, and it
// has no roster to check a seat against. Enforcing "this seat is on this machine" here would need a
// join against a snapshot that is replaced wholesale and can legitimately be empty, so it would
// refuse true reports to catch nothing: the tenant boundary already holds.

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"sort"
	"strings"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/feedback"
	"agenthub/fastmcp/seat_management/domain/repositories"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// A report is text, not a payload.
const seatFeedbackMaxBody = 1 << 18

// newSeatFeedbackService is a package variable so tests can substitute a service without a database.
var newSeatFeedbackService = func(sessions *database.SessionManager) (*services.SeatFeedbackService, error) {
	repo, err := seatorm.NewORMSeatFeedbackRepository(sessions)
	if err != nil {
		return nil, err
	}
	return services.NewSeatFeedbackService(repo), nil
}

// seatFeedbackNow is the server clock; tests substitute a fixed one.
var seatFeedbackNow = time.Now

// seatFeedbackSubmission is the POST body. session is optional; everything else is required.
type seatFeedbackSubmission struct {
	Room    string `json:"room"`
	Seat    string `json:"seat"`
	Session string `json:"session"`
	Layer   string `json:"layer"`
	Text    string `json:"text"`
}

func mountSeatFeedbackRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("POST /api/v2/openrig/feedback", seatFeedbackAuthed(sessions, func(w http.ResponseWriter, r *http.Request, poster services.SeatFeedbackPoster) {
		handleSubmitSeatFeedback(w, r, poster, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/feedback", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListSeatFeedback(w, r, u, sessions)
	}))
}

// seatFeedbackAuthed accepts a machine token or a user token on the POST.
//
// The machine token is tried first, and the order is load-bearing rather than arbitrary: a machine
// token is an exact hash match in the machine-token store, while the user path can resolve a token
// that is not a user token at all when the deployment runs the auth layer's development fallback.
// Asking the exact store first is the only order that answers the same way in every deployment.
//
// An invalid machine token is not an error: it falls through to the user path, which is what lets
// one header carry both credentials. A machine-token LOOKUP failure is an error, because falling
// through would answer "not authenticated" for a broken store.
func seatFeedbackAuthed(sessions *database.SessionManager, h func(w http.ResponseWriter, r *http.Request, poster services.SeatFeedbackPoster)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		scheme, bearer, _ := strings.Cut(r.Header.Get("Authorization"), " ")
		if !strings.EqualFold(scheme, "bearer") || strings.TrimSpace(bearer) == "" {
			writeDetail(w, http.StatusForbidden, "Not authenticated")
			return
		}
		bearer = strings.TrimSpace(bearer)

		svc, ok := machineTokenServiceFor(w, sessions)
		if !ok {
			return
		}
		token, err := svc.Authenticate(r.Context(), bearer)
		switch {
		case err == nil && token != nil:
			h(w, r, services.SeatFeedbackPoster{UserID: token.UserID, MachineID: token.MachineID})
			return
		case errors.Is(err, services.ErrInvalidMachineToken):
			// Not a machine token: the user path gets it.
		case err != nil:
			writeDetail(w, http.StatusInternalServerError, "machine token lookup failed")
			return
		}

		u, err := authinterface.GetCurrentUser(r.Context(), &bearer, nil)
		if err != nil {
			writeDetail(w, http.StatusForbidden, "Not authenticated")
			return
		}
		h(w, withAuthContext(r, u), services.SeatFeedbackPoster{UserID: userID(u)})
	}
}

func seatFeedbackServiceFor(w http.ResponseWriter, sessions *database.SessionManager) (*services.SeatFeedbackService, bool) {
	svc, err := newSeatFeedbackService(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return svc, true
}

func handleSubmitSeatFeedback(w http.ResponseWriter, r *http.Request, poster services.SeatFeedbackPoster, sessions *database.SessionManager) {
	var submission seatFeedbackSubmission
	if !decodeSeatFeedbackBody(w, r, &submission) {
		return
	}
	svc, ok := seatFeedbackServiceFor(w, sessions)
	if !ok {
		return
	}
	stored, err := svc.Submit(r.Context(), poster, services.SeatFeedbackInput{
		Room:    submission.Room,
		Seat:    submission.Seat,
		Session: submission.Session,
		Layer:   submission.Layer,
		Text:    submission.Text,
	}, seatFeedbackNow().UTC())
	if err != nil {
		var rejection *services.SeatFeedbackRejection
		if errors.As(err, &rejection) {
			if rejection.SecretField != "" {
				// The same {"success": false, "error": ...} body the seat-status report answers with.
				writeSeatStatusError(w, http.StatusUnprocessableEntity, rejection.Message)
				return
			}
			writeDetail(w, http.StatusBadRequest, rejection.Message)
			return
		}
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("id", stored.ID)
	body.Set("layer", stored.Layer)
	writeJSON(w, http.StatusOK, body)
}

func handleListSeatFeedback(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	svc, ok := seatFeedbackServiceFor(w, sessions)
	if !ok {
		return
	}
	reports, err := svc.List(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, seatFeedbackBody(reports))
}

// seatFeedbackBody groups the reports by layer in the vocabulary's own order, which is the contract
// the page renders: the grouping is decided here, once, rather than by every reader. A layer with no
// reports is absent; an empty table is an empty layers array with total 0.
//
// A row whose layer is outside the vocabulary cannot exist (the DDL CHECK enforces the set), but an
// unknown value is still rendered in its own group rather than dropped: a read that silently loses
// rows is worse than one that shows a value nobody expected.
func seatFeedbackBody(reports []repositories.SeatFeedback) *entities.OrderedMap[any] {
	grouped := map[string][]repositories.SeatFeedback{}
	for _, report := range reports {
		grouped[report.Layer] = append(grouped[report.Layer], report)
	}
	order := make([]string, 0, len(feedback.Layers)+len(grouped))
	known := map[string]bool{}
	for _, layer := range feedback.Layers {
		order = append(order, string(layer))
		known[string(layer)] = true
	}
	extra := make([]string, 0, len(grouped))
	for layer := range grouped {
		if !known[layer] {
			extra = append(extra, layer)
		}
	}
	sort.Strings(extra)
	order = append(order, extra...)

	layers := make([]any, 0, len(order))
	for _, layer := range order {
		items := grouped[layer]
		if len(items) == 0 {
			continue
		}
		rows := make([]any, 0, len(items))
		for _, report := range items {
			rows = append(rows, seatFeedbackRow(report))
		}
		group := entities.NewOrderedMap[any]()
		group.Set("layer", layer)
		group.Set("count", len(items))
		group.Set("reports", rows)
		layers = append(layers, group)
	}

	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("total", len(reports))
	body.Set("layers", layers)
	return body
}

// seatFeedbackRow is the row shape the page reads. Every key is always present; session and
// machine_id are empty strings rather than null, so a reader never has to tell "unknown" from
// "absent". created_at is RFC3339 in UTC.
func seatFeedbackRow(report repositories.SeatFeedback) *entities.OrderedMap[any] {
	row := entities.NewOrderedMap[any]()
	row.Set("id", report.ID)
	row.Set("room", report.Room)
	row.Set("seat", report.Seat)
	row.Set("session", report.Session)
	row.Set("layer", report.Layer)
	row.Set("text", report.Text)
	row.Set("machine_id", report.MachineID)
	row.Set("created_at", report.CreatedAt.UTC().Format(time.RFC3339))
	return row
}

func decodeSeatFeedbackBody(w http.ResponseWriter, r *http.Request, out *seatFeedbackSubmission) bool {
	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(http.MaxBytesReader(w, r.Body, seatFeedbackMaxBody)); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return false
	}
	dec := json.NewDecoder(buf)
	dec.DisallowUnknownFields()
	if err := dec.Decode(out); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return false
	}
	return true
}
