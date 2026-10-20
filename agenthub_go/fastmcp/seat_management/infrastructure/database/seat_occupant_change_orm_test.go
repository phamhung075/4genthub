package database

import "reflect"

// Register seat_occupant_changes with the shared DDL-vs-struct map so TestSeatORMMatchesDDL covers it.
func init() {
	seatTableTypes["seat_occupant_changes"] = reflect.TypeOf(SeatOccupantChangeORM{})
}
