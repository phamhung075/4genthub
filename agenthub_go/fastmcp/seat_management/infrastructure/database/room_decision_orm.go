package database

import (
	"encoding/json"
	"time"
)

// RoomDecisionORM is the row struct for room_decisions.
//
// It is the SOURCE OF TRUTH for the table's columns: the schema file
// (infrastructure/schema/seat_management_postgresql.sql) and this package's runtime TableDef
// (seat_tables.go) both have to agree with it, and TestSeatORMMatchesDDL (schema file vs struct
// tags) plus TestSeatDDLParity (the two DDL sources against each other) own those comparisons.
//
// Answers and Questions are JSONB and carried as json.RawMessage, the convention seat_orm.go
// records. Summary and Detail are POINTERS because NULL is a state rather than a missing value here:
// an ask may carry no summary and no humanDetail, and the row is what says so - the domain entity
// renders nil as an empty string, which is what a panel shows.
type RoomDecisionORM struct {
	ID             string          `db:"id"`
	UserID         string          `db:"user_id"`
	RoomID         string          `db:"room_id"`
	RoomName        string          `db:"room_name"`
	QitemID        string          `db:"qitem_id"`
	AuthorSeatKey  string          `db:"author_seat_key"`
	Destination    string          `db:"destination"`
	Summary        *string         `db:"summary"`
	Detail         *string         `db:"detail"`
	Questions      json.RawMessage `db:"questions"`
	Answers        json.RawMessage `db:"answers"`
	State          string          `db:"state"`
	IdempotencyKey string          `db:"idempotency_key"`
	CreatedAt      time.Time       `db:"created_at"`
	AnsweredAt     *time.Time      `db:"answered_at"`
	ResolvedAt     *time.Time      `db:"resolved_at"`
	// AckedAt is the DELIVERY record, not a state: the daemon's ack that this answer no longer has to
	// be handed out. It is separate from ResolvedAt because a dropped answer - one the daemon decided
	// not to apply - is acked and never retried while the row's state says what the decision itself
	// became. NULL means no ack has landed, which is exactly what the pull selects on.
	AckedAt *time.Time `db:"acked_at"`
}
