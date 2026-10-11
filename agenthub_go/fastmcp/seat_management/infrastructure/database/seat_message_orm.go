package database

import "time"

// SeatMessageORM is the row struct for seat_messages.
//
// It is the SOURCE OF TRUTH for the table's columns: the schema file
// (infrastructure/schema/seat_management_postgresql.sql) and this package's runtime TableDef
// (seat_tables.go) both have to agree with it, and TestSeatORMMatchesDDL (DDL file vs struct tags)
// plus TestSeatDDLParity (the two DDL sources against each other) own those comparisons.
//
// DeliveredAt is a pointer because NULL is a state rather than a missing value: it is what makes a
// row PENDING, and it is the column the pull filters on.
type SeatMessageORM struct {
	ID          string     `db:"id"`
	UserID      string     `db:"user_id"`
	Room        string     `db:"room"`
	Seat        string     `db:"seat"`
	Text        string     `db:"text"`
	CreatedAt   time.Time  `db:"created_at"`
	DeliveredAt *time.Time `db:"delivered_at"`
	MachineID   string     `db:"machine_id"`
}
