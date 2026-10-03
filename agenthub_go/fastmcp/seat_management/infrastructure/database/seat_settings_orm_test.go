package database

import "reflect"

// Register seat_settings with the shared DDL-vs-struct map so TestSeatORMMatchesDDL covers it.
func init() {
	seatTableTypes["seat_settings"] = reflect.TypeOf(SeatSettingsORM{})
}
