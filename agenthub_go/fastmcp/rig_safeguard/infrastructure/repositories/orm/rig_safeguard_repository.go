// Package orm stores the safeguard rows the connector socket receives (rigd-boundaries.md 7.3).
//
// It is deliberately small: the frame is an upsert of one row per (user, connector, rig, safeguard),
// the latest state wins, and the ONLY decision the server makes on it is the alert - the transition
// rule in transitionAlerts below. rigd judges the silence of its children; the server judges the
// rows rigd sends, and its own socket's liveness (7.4).
package orm

import (
	"context"
	"database/sql"

	rigdb "agenthub/fastmcp/rig_safeguard/infrastructure/database"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// validate checks the closed sets the safeguard frame reports (7.6) before any statement is built,
// so an unknown state or safeguard costs the connector one frame and nothing else. The CHECK
// constraints in the table state the same two sets to the database; this is the refusal that
// explains itself over the socket instead of surfacing as an internal error.
func validate(row rigdb.RigSafeguardORM) error {
	if row.Rig == "" || len(row.Rig) > 255 {
		return &tmvo.ValueError{Msg: "bad rig"}
	}
	switch row.Safeguard {
	case rigdb.SafeguardCompact, rigdb.SafeguardWatchdog, rigdb.SafeguardBridge, rigdb.SafeguardRigd:
	default:
		return &tmvo.ValueError{Msg: "bad safeguard"}
	}
	switch row.State {
	case rigdb.StateRunning, rigdb.StateStopped, rigdb.StateSilent, rigdb.StateFailing:
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
func transitionAlerts(prevState string, prevRestarts int64, next rigdb.RigSafeguardORM) bool {
	if next.Restarts > prevRestarts {
		return true
	}
	if prevState != rigdb.StateRunning {
		return false
	}
	switch next.State {
	case rigdb.StateStopped, rigdb.StateSilent, rigdb.StateFailing:
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
func Upsert(ctx context.Context, sessions *database.SessionManager, row rigdb.RigSafeguardORM) (bool, error) {
	if sessions == nil {
		return false, &tmvo.ValueError{Msg: "database configuration not available"}
	}
	if err := validate(row); err != nil {
		return false, err
	}
	alert := false
	err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{row.UserID, row.ConnectorID, row.Rig, row.Safeguard}
		var prevState string
		var prevRestarts int64
		scanErr := s.QueryRowContext(ctx,
			`SELECT "state", "restarts" FROM "rig_safeguards" WHERE "user_id" = $1 AND "connector_id" = $2 AND "rig" = $3 AND "safeguard" = $4 FOR UPDATE`,
			args...).Scan(&prevState, &prevRestarts)
		values := append([]any{}, args...)
		values = append(values, row.State, row.PID, row.Restarts, row.AgeS, row.LastBeatAt)
		switch {
		case scanErr == sql.ErrNoRows:
			_, err := s.ExecContext(ctx,
				`INSERT INTO "rig_safeguards" ("user_id", "connector_id", "rig", "safeguard", "state", "pid", "restarts", "age_s", "last_beat_at") `+
					`VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) `+
					`ON CONFLICT ("user_id", "connector_id", "rig", "safeguard") DO UPDATE SET `+
					`"state" = EXCLUDED."state", "pid" = EXCLUDED."pid", "restarts" = EXCLUDED."restarts", `+
					`"age_s" = EXCLUDED."age_s", "last_beat_at" = EXCLUDED."last_beat_at"`,
				values...)
			return err
		case scanErr != nil:
			return scanErr
		default:
			alert = transitionAlerts(prevState, prevRestarts, row)
			_, err := s.ExecContext(ctx,
				`UPDATE "rig_safeguards" SET "state" = $5, "pid" = $6, "restarts" = $7, "age_s" = $8, "last_beat_at" = $9 `+
					`WHERE "user_id" = $1 AND "connector_id" = $2 AND "rig" = $3 AND "safeguard" = $4`,
				values...)
			return err
		}
	})
	if err != nil {
		return false, err
	}
	return alert, nil
}
