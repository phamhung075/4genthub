package database

import "reflect"

// Register seat_messages with the shared DDL-vs-struct map so TestSeatORMMatchesDDL covers it. The
// guard requires one entry per DDL table ("the guard requires one entry per DDL table, so these are
// mandatory, not optional"), and it also compares the registry's size with the schema file's table
// count — so a new table that skipped either half would fail there rather than quietly diverge.
func init() {
	seatTableTypes["seat_messages"] = reflect.TypeOf(SeatMessageORM{})
}
