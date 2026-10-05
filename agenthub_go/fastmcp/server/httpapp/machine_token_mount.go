package httpapp

// machine_token_mount.go registers bridge machines and authenticates their reports:
//
//	POST   /api/v2/openrig/machines                    {machine_id}: user token; returns the machine token once
//	DELETE /api/v2/openrig/machines/{machine}/token    user token; revokes the machine's token
//
// A machine token is valid on one route, POST /api/v2/openrig/seat-status, and only for the
// machine it was issued to. It is never logged and never returned again after registration.

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newMachineTokenRepo is a package variable so tests can substitute a fake without a database.
var newMachineTokenRepo = func(sessions *database.SessionManager) (repositories.MachineTokenRepository, error) {
	return seatorm.NewORMMachineTokenRepository(sessions)
}

type machineTokenRequest struct {
	MachineID string `json:"machine_id"`
}

func mountMachineTokenRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("POST /api/v2/openrig/machines", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRegisterMachine(w, r, u, sessions)
	}))
	mux.HandleFunc("DELETE /api/v2/openrig/machines/{machine}/token", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRevokeMachineToken(w, r, u, sessions)
	}))
}

func machineTokenServiceFor(w http.ResponseWriter, sessions *database.SessionManager) (*seatservices.MachineTokenService, bool) {
	repo, err := newMachineTokenRepo(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return seatservices.NewMachineTokenService(repo), true
}

func handleRegisterMachine(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	var req machineTokenRequest
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	svc, ok := machineTokenServiceFor(w, sessions)
	if !ok {
		return
	}
	token, err := svc.Register(r.Context(), userID(u), req.MachineID)
	switch {
	case errors.Is(err, seatservices.ErrInvalidMachineID):
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	case errors.Is(err, repositories.ErrMachineTokenExists):
		writeDetail(w, http.StatusConflict, "machine \""+req.MachineID+"\" already has an active token; revoke it first")
		return
	case err != nil:
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("machine_id", req.MachineID)
	body.Set("token", token)
	w.Header().Set("Cache-Control", "no-store")
	writeJSON(w, http.StatusOK, body)
}

func handleRevokeMachineToken(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	svc, ok := machineTokenServiceFor(w, sessions)
	if !ok {
		return
	}
	err := svc.Revoke(r.Context(), userID(u), r.PathValue("machine"))
	switch {
	case errors.Is(err, seatservices.ErrMachineTokenNotFound):
		writeDetail(w, http.StatusNotFound, err.Error())
		return
	case err != nil:
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	writeJSON(w, http.StatusOK, body)
}

// machineAuthed authenticates a bridge request by its machine token. A missing header is 403
// like authed; an unknown, revoked or malformed token is 401 without saying which.
func machineAuthed(sessions *database.SessionManager, h func(w http.ResponseWriter, r *http.Request, token *repositories.MachineToken)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		scheme, bearer, _ := strings.Cut(r.Header.Get("Authorization"), " ")
		if !strings.EqualFold(scheme, "bearer") || strings.TrimSpace(bearer) == "" {
			writeDetail(w, http.StatusForbidden, "Not authenticated")
			return
		}
		svc, ok := machineTokenServiceFor(w, sessions)
		if !ok {
			return
		}
		token, err := svc.Authenticate(r.Context(), strings.TrimSpace(bearer))
		switch {
		case errors.Is(err, seatservices.ErrInvalidMachineToken):
			writeDetail(w, http.StatusUnauthorized, "Invalid machine token")
			return
		case err != nil:
			writeDetail(w, http.StatusInternalServerError, "machine token lookup failed")
			return
		}
		h(w, r, token)
	}
}
