package session_stream

import (
	"context"
	"crypto/sha1"
	"database/sql"
	"fmt"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// MAX_EVENTS_PER_BATCH and MAX_PAYLOAD_CHARS.
const (
	MaxEventsPerBatch = 200
	MaxPayloadChars   = 64 * 1024
)

// streamNamespace is uuid.UUID("6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f").
var streamNamespace = [16]byte{
	0x6f, 0x1c, 0x2d, 0x3e, 0x4a, 0x5b, 0x4c, 0x6d,
	0x8e, 0x7f, 0x0a, 0x1b, 0x2c, 0x3d, 0x4e, 0x5f,
}

// DefaultSessions is the process-wide session manager used when a function is
// called with a nil sessions argument (Python's _default_factory).
var DefaultSessions *database.SessionManager

// PermissionError mirrors Python's PermissionError raised by this module.
type PermissionError struct{ Msg string }

func (e *PermissionError) Error() string { return e.Msg }

// resolveSessions is `(factory or _default_factory)()`.
func resolveSessions(sessions *database.SessionManager) (*database.SessionManager, error) {
	if sessions != nil {
		return sessions, nil
	}
	if DefaultSessions != nil {
		return DefaultSessions, nil
	}
	return nil, &tmvo.ValueError{Msg: "database configuration not available"}
}

// SessionIDFor is session_id_for: a deterministic UUIDv5 so a reconnecting
// connector resumes the same session.
func SessionIDFor(userID, connectorID, sessionKey string) string {
	return uuid5String(streamNamespace, userID+":"+connectorID+":"+sessionKey)
}

// uuid5String is uuid.uuid5(namespace, name): SHA-1 of the namespace bytes plus
// the UTF-8 name, with version 5 and the RFC 4122 variant.
func uuid5String(ns [16]byte, name string) string {
	h := sha1.New()
	_, _ = h.Write(ns[:])
	_, _ = h.Write([]byte(name))
	sum := h.Sum(nil)
	var b [16]byte
	copy(b[:], sum[:16])
	b[6] = (b[6] & 0x0f) | 0x50
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// pyClip is Python slicing s[:n] over code points (n < 0 returns s).
func pyClip(s string, n int) string {
	if n < 0 {
		return s
	}
	rs := []rune(s)
	if len(rs) <= n {
		return s
	}
	return string(rs[:n])
}

// clip is _clip: coerce an untrusted optional field to a short string.
func clip(value *string) *string {
	if value == nil || *value == "" {
		return nil
	}
	s := pyClip(*value, 255)
	return &s
}

// tNow is _now: datetime.now(UTC).replace(tzinfo=None).
func tNow() time.Time { return time.Now().UTC() }

// sessionRow is _row.
func sessionRow(s *database.AgentSession) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", s.ID)
	m.Set("name", s.Name)
	if s.Project != nil {
		m.Set("project", *s.Project)
	} else {
		m.Set("project", nil)
	}
	m.Set("status", s.Status)
	m.Set("connector_id", s.ConnectorID)
	m.Set("last_seq", s.LastSeq)
	if s.CreatedAt.IsZero() {
		m.Set("created_at", nil)
	} else {
		m.Set("created_at", tmvo.IsoFormatNaive(s.CreatedAt))
	}
	if s.LastSeen.IsZero() {
		m.Set("last_seen", nil)
	} else {
		m.Set("last_seen", tmvo.IsoFormatNaive(s.LastSeen))
	}
	return m
}

const sessionCols = "id, user_id, connector_id, session_key, name, project, status, last_seq, created_at, last_seen"

type rowScanner interface{ Scan(dest ...any) error }

func scanAgentSession(row rowScanner, dst *database.AgentSession) error {
	return row.Scan(&dst.ID, &dst.UserID, &dst.ConnectorID, &dst.SessionKey, &dst.Name,
		&dst.Project, &dst.Status, &dst.LastSeq, &dst.CreatedAt, &dst.LastSeen)
}

func scanAgentSessionEvent(row rowScanner, dst *database.AgentSessionEvent) error {
	return row.Scan(&dst.ID, &dst.SessionID, &dst.UserID, &dst.Seq, &dst.Type, &dst.Payload, &dst.Ts)
}

// orEmpty is `value or {}` for the payload.
func orEmpty(v any) any {
	if tmvo.PyTruthy(v) {
		return v
	}
	return entities.NewOrderedMap[any]()
}

func truncatedPayload() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("truncated", true)
	return m
}

// UpsertSession is upsert_session.
func UpsertSession(ctx context.Context, sessions *database.SessionManager, userID, connectorID, sessionKey, name string, project *string) (*entities.OrderedMap[any], error) {
	sessions, err := resolveSessions(sessions)
	if err != nil {
		return nil, err
	}
	sid := SessionIDFor(userID, connectorID, sessionKey)
	var out *entities.OrderedMap[any]
	err = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var existing database.AgentSession
		scanErr := scanAgentSession(s.QueryRowContext(ctx, "SELECT "+sessionCols+" FROM agent_sessions WHERE id = $1", sid), &existing)
		if scanErr != nil && scanErr != sql.ErrNoRows {
			return scanErr
		}
		if scanErr == nil && existing.UserID != userID {
			return &PermissionError{Msg: "session belongs to another user"}
		}
		if scanErr == sql.ErrNoRows {
			ts := tNow()
			row := database.AgentSession{
				ID:          sid,
				UserID:      userID,
				ConnectorID: connectorID,
				SessionKey:  sessionKey,
				Name:        pyClip(name, 255),
				Project:     clip(project),
				Status:      "active",
				LastSeq:     0,
				CreatedAt:   ts,
				LastSeen:    ts,
			}
			if _, err := s.ExecContext(ctx,
				"INSERT INTO agent_sessions (id, user_id, connector_id, session_key, name, project, status, last_seq, created_at, last_seen) "+
					"VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
				row.ID, row.UserID, row.ConnectorID, row.SessionKey, row.Name, row.Project,
				row.Status, row.LastSeq, row.CreatedAt, row.LastSeen); err != nil {
				return err
			}
			out = sessionRow(&row)
			return nil
		}

		// Existing row: update name, keep the project when the new value is empty.
		newProject := existing.Project
		if p := clip(project); p != nil {
			newProject = p
		}
		ts := tNow()
		if _, err := s.ExecContext(ctx,
			"UPDATE agent_sessions SET name = $1, project = $2, status = $3, last_seen = $4 WHERE id = $5",
			pyClip(name, 255), newProject, "active", ts, sid); err != nil {
			return err
		}
		existing.Name = pyClip(name, 255)
		existing.Project = newProject
		existing.Status = "active"
		existing.LastSeen = ts
		out = sessionRow(&existing)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// AppendEvents is append_events: append events, assigning seq on the server.
func AppendEvents(ctx context.Context, sessions *database.SessionManager, userID, sessionID string, events []any) ([]*entities.OrderedMap[any], error) {
	if len(events) > MaxEventsPerBatch {
		return nil, &tmvo.ValueError{Msg: fmt.Sprintf("at most %d events per batch", MaxEventsPerBatch)}
	}
	sessions, err := resolveSessions(sessions)
	if err != nil {
		return nil, err
	}
	stored := []*entities.OrderedMap[any]{}
	err = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		for _, ev := range events {
			if _, ok := ev.(*entities.OrderedMap[any]); !ok {
				return &tmvo.ValueError{Msg: "each event must be an object"}
			}
		}
		var row database.AgentSession
		scanErr := scanAgentSession(s.QueryRowContext(ctx,
			"SELECT "+sessionCols+" FROM agent_sessions WHERE id = $1 AND user_id = $2 FOR UPDATE",
			sessionID, userID), &row)
		if scanErr == sql.ErrNoRows {
			return &PermissionError{Msg: "unknown session"}
		}
		if scanErr != nil {
			return scanErr
		}

		stored = stored[:0]
		for _, evAny := range events {
			ev := evAny.(*entities.OrderedMap[any])
			payloadAny, _ := ev.Get("payload")
			payload := orEmpty(payloadAny)
			if utf8.RuneCountInString(tmvo.PyJSONDumpsDefaultStr(payload, -1)) > MaxPayloadChars {
				payload = truncatedPayload()
			}

			typeAny, ok := ev.Get("type")
			if !ok {
				typeAny = "message"
			}
			typ := pyClip(tmvo.PyStr(typeAny), 32)

			row.LastSeq++
			ts := tNow()
			if _, err := s.ExecContext(ctx,
				"INSERT INTO agent_session_events (session_id, user_id, seq, type, payload, ts) VALUES ($1, $2, $3, $4, $5, $6)",
				sessionID, userID, row.LastSeq, typ, tmvo.PyJSONDumpsDefaultStr(payload, -1), ts); err != nil {
				return err
			}
			m := entities.NewOrderedMap[any]()
			m.Set("seq", row.LastSeq)
			m.Set("type", typ)
			m.Set("payload", payload)
			stored = append(stored, m)
		}

		if _, err := s.ExecContext(ctx,
			"UPDATE agent_sessions SET last_seq = $1, last_seen = $2 WHERE id = $3",
			row.LastSeq, tNow(), sessionID); err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return stored, nil
}

// ListSessions is list_sessions, newest last_seen first.
func ListSessions(ctx context.Context, sessions *database.SessionManager, userID string) ([]*entities.OrderedMap[any], error) {
	sessions, err := resolveSessions(sessions)
	if err != nil {
		return nil, err
	}
	out := []*entities.OrderedMap[any]{}
	err = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			"SELECT "+sessionCols+" FROM agent_sessions WHERE user_id = $1 ORDER BY last_seen DESC", userID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var r database.AgentSession
			if err := scanAgentSession(rows, &r); err != nil {
				return err
			}
			out = append(out, sessionRow(&r))
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// GetSessionForUser is get_session_for_user; nil means Python None.
func GetSessionForUser(ctx context.Context, sessions *database.SessionManager, userID, sessionID string) (*entities.OrderedMap[any], error) {
	sessions, err := resolveSessions(sessions)
	if err != nil {
		return nil, err
	}
	var out *entities.OrderedMap[any]
	err = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var r database.AgentSession
		scanErr := scanAgentSession(s.QueryRowContext(ctx,
			"SELECT "+sessionCols+" FROM agent_sessions WHERE id = $1 AND user_id = $2", sessionID, userID), &r)
		if scanErr == sql.ErrNoRows {
			return nil
		}
		if scanErr != nil {
			return scanErr
		}
		out = sessionRow(&r)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ListEvents is list_events; the page limit is clamped to 1000.
func ListEvents(ctx context.Context, sessions *database.SessionManager, userID, sessionID string, afterSeq, limit int64) ([]*entities.OrderedMap[any], error) {
	sessions, err := resolveSessions(sessions)
	if err != nil {
		return nil, err
	}
	if limit > 1000 {
		limit = 1000
	}
	out := []*entities.OrderedMap[any]{}
	err = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			"SELECT id, session_id, user_id, seq, type, payload, ts FROM agent_session_events "+
				"WHERE user_id = $1 AND session_id = $2 AND seq > $3 ORDER BY seq LIMIT $4",
			userID, sessionID, afterSeq, limit)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var r database.AgentSessionEvent
			if err := scanAgentSessionEvent(rows, &r); err != nil {
				return err
			}
			m := entities.NewOrderedMap[any]()
			m.Set("seq", r.Seq)
			m.Set("type", r.Type)
			payload, err := entities.DecodeJSON(r.Payload)
			if err != nil {
				return err
			}
			m.Set("payload", payload)
			if r.Ts.IsZero() {
				m.Set("ts", nil)
			} else {
				m.Set("ts", tmvo.IsoFormatNaive(r.Ts))
			}
			out = append(out, m)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// MarkOffline is mark_offline: all of a connector's sessions become offline.
func MarkOffline(ctx context.Context, sessions *database.SessionManager, userID, connectorID string) error {
	sessions, err := resolveSessions(sessions)
	if err != nil {
		return err
	}
	return sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			"UPDATE agent_sessions SET status = $1, last_seen = $2 WHERE user_id = $3 AND connector_id = $4",
			"offline", tNow(), userID, connectorID)
		return err
	})
}
