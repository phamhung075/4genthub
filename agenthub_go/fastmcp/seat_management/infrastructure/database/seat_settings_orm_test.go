package database

import "reflect"

// Register seat_settings with the shared DDL-vs-struct map so TestSeatORMMatchesDDL covers it.
func init() {
	seatTableTypes["seat_settings"] = reflect.TypeOf(SeatSettingsORM{})
	seatTableTypes["machines"] = reflect.TypeOf(MachineORM{})
	seatTableTypes["seat_status"] = reflect.TypeOf(SeatStatusORM{})
	seatTableTypes["machine_edges"] = reflect.TypeOf(MachineEdgeORM{})
	seatTableTypes["machine_tokens"] = reflect.TypeOf(MachineTokenORM{})
}
