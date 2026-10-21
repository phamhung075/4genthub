// Package orm stores the safeguard rows the connector socket receives (agent-boundaries.md 7.3).
//
// It is deliberately small: the frame is an upsert of one row per (user, connector, room, safeguard),
// the latest state wins, and the ONLY decision the server makes on it is the alert - the transition
// rule in transitionAlerts below. The client's machine-level supervisor (`agent`, the safeguard it
// renamed from `rigd` on 2026-10-15) judges the silence of its children; the server judges the rows
// that supervisor sends, and its own socket's liveness (7.4).
package orm

import (
	"context"
	"database/sql"

	roomdb "agenthub/fastmcp/room_safeguard/infrastructure/database"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// validate checks the closed set of safeguard names and the room rule that belongs to each name's
// scope (7.2, 7.6) before any statement is built, so a refused frame costs the connector that frame
// and nothing else. The CHECK constraints in the table state the same two rules to the database;
// this is the refusal that explains itself over the socket instead of surfacing as an internal
// error.
//
// THE NAME IS CHECKED FIRST, because the name's scope is what decides the room rule: a room-scoped
// safeguard needs a room of 1..255, and a machine-scoped one needs EXACTLY none. The three messages
// are unchanged - `bad room`, `bad safeguard`, `bad state` - so the codes the socket answers with
// (`bad_rig`, `bad_safeguard`, `bad_state`) are the ones the client already reads.
func validate(row roomdb.RoomSafeguardORM) error {
	switch row.Safeguard {
	case roomdb.SafeguardCompact, roomdb.SafeguardWatchdog, roomdb.SafeguardMessages, roomdb.SafeguardRoomGuard,
		roomdb.SafeguardBudget:
		if row.Room == "" || len(row.Room) > 255 {
			return &tmvo.ValueError{Msg: "bad room"}
		}
	case roomdb.SafeguardBridge, roomdb.SafeguardAgent:
		if row.Room != "" {
			return &tmvo.ValueError{Msg: "bad room"}
		}
	default:
		return &tmvo.ValueError{Msg: "bad safeguard"}
	}
	switch row.State {
	case roomdb.StateRunning, roomdb.StateStopped, roomdb.StateSilent, roomdb.StateFailing:
	default:
		return &tmvo.ValueError{Msg: "bad state"}
	}
	return nil
}

// transitionAlerts is 7.3's rule, and the whole of the server's judgement about a safeguard row:
//
//	a notification is raised when the STORED state changes from running to stopped, silent or
//	failing, or when restarts goes up.
//
// Two consequences are the rule rather than accidents. A re-sent identical row changes neither the
// state nor restarts, so it alerts once and never again. And the first row ever stored for a key
// alerts nothing at all, because there is no stored state it could have changed FROM - a failure
// that happened while the connector was offline is alerted by the re-send after the next ready,
// which compares against the running row stored before the disconnect.
func transitionAlerts(prevState string, prevRestarts int64, next roomdb.RoomSafeguardORM) bool {
	if next.Restarts > prevRestarts {
		return true
	}
	if prevState != roomdb.StateRunning {
		return false
	}
	switch next.State {
	case roomdb.StateStopped, roomdb.StateSilent, roomdb.StateFailing:
		return true
	default:
		return false
	}
}

// Upsert stores the latest state of one safeguard and reports whether the transition warrants an
// alert (7.3). The previous row is read FOR UPDATE inside the same transaction as the write, so two
// frames for the same key cannot both see the same previous state and both alert - the alert is
// decided where the state it compares against is held still.
//
// The INSERT carries ON CONFLICT DO UPDATE for the one race the read cannot cover: an overlapping
// reconnect whose two sockets both send the row's first frame. Whichever statement loses arrives
// with no row to compare against and therefore alerts nothing, which is why the row is not lost and
// no duplicate alert can be produced.
func Upsert(ctx context.Context, sessions *database.SessionManager, row roomdb.RoomSafeguardORM) (bool, error) {
	if sessions == nil {
		return false, &tmvo.ValueError{Msg: "database configuration not available"}
	}
	if err := validate(row); err != nil {
		return false, err
	}
	alert := false
	err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{row.UserID, row.ConnectorID, row.Room, row.Safeguard}
		var prevState string
		var prevRestarts int64
		scanErr := s.QueryRowContext(ctx,
			`SELECT "state", "restarts" FROM "room_safeguards" WHERE "user_id" = $1 AND "connector_id" = $2 AND "room" = $3 AND "safeguard" = $4 FOR UPDATE`,
			args...).Scan(&prevState, &prevRestarts)
		values := append([]any{}, args...)
		values = append(values, row.State, row.PID, row.Restarts, row.AgeS, row.LastBeatAt)
		switch {
		case scanErr == sql.ErrNoRows:
			_, err := s.ExecContext(ctx,
				`INSERT INTO "room_safeguards" ("user_id", "connector_id", "room", "safeguard", "state", "pid", "restarts", "age_s", "last_beat_at") `+
					`VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) `+
					`ON CONFLICT ("user_id", "connector_id", "room", "safeguard") DO UPDATE SET `+
					`"state" = EXCLUDED."state", "pid" = EXCLUDED."pid", "restarts" = EXCLUDED."restarts", `+
					`"age_s" = EXCLUDED."age_s", "last_beat_at" = EXCLUDED."last_beat_at"`,
				values...)
			return err
		case scanErr != nil:
			return scanErr
		default:
			alert = transitionAlerts(prevState, prevRestarts, row)
			_, err := s.ExecContext(ctx,
				`UPDATE "room_safeguards" SET "state" = $5, "pid" = $6, "restarts" = $7, "age_s" = $8, "last_beat_at" = $9 `+
					`WHERE "user_id" = $1 AND "connector_id" = $2 AND "room" = $3 AND "safeguard" = $4`,
				values...)
			return err
		}
	})
	if err != nil {
		return false, err
	}
	return alert, nil
}
