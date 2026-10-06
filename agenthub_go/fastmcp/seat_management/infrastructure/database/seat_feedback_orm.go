// Row struct for seat_feedback, the seat friction channel. Same conventions as seat_orm.go: one
// Go field per column, tagged with the `db` column name, in DDL order; string carries UUID and
// TEXT, time.Time carries TIMESTAMP WITH TIME ZONE.
//
// The table is tenant-scoped by user_id (TEXT) and carries no foreign key: room and seat are
// slugs, not references, so friction stays readable after the seat it is about is gone — which
// is the point of the channel. No CASCADE anywhere, matching the rest of the schema.
package database

import "time"

// SeatFeedbackORM is a row of seat_feedback.
//
// Layer is one of the closed set in seat_management/domain/feedback; the DDL CHECK constraint
// and that list are checked against each other (TestSeatFeedbackLayerCheckMatchesDomain).
//
// MachineID is the bridge machine that submitted the report and is EMPTY when the submitter
// authenticated with a user token. It is provenance, not a scope column.
type SeatFeedbackORM struct {
	ID        string    `db:"id"`
	UserID    string    `db:"user_id"`
	Room      string    `db:"room"`
	Seat      string    `db:"seat"`
	Session   string    `db:"session"`
	Layer     string    `db:"layer"`
	Text      string    `db:"text"`
	MachineID string    `db:"machine_id"`
	CreatedAt time.Time `db:"created_at"`
}
