// Row struct for seat_occupant_changes, the append-only record of a seat's stored occupant.
// Same conventions as seat_orm.go: one Go field per column, tagged with the `db` column name, in
// DDL order; string carries UUID and TEXT, time.Time carries TIMESTAMP WITH TIME ZONE.
//
// Actor is the authenticated caller whose action changed the occupant; UserID is the tenant whose
// seat changed. There is no update path: a row exists exactly when a switch was made.
package database

import "time"

// SeatOccupantChangeORM is a row of seat_occupant_changes.
type SeatOccupantChangeORM struct {
	ID          string    `db:"id"`
	UserID      string    `db:"user_id"`
	SeatID      string    `db:"seat_id"`
	Actor       string    `db:"actor"`
	At          time.Time `db:"at"`
	FromRuntime string    `db:"from_runtime"`
	FromModel   string    `db:"from_model"`
	ToRuntime   string    `db:"to_runtime"`
	ToModel     string    `db:"to_model"`
}
