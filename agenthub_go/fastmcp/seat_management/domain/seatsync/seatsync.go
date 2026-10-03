// Package seatsync decides whether the seat a machine runs matches the cloud's latest snapshot.
package seatsync

// Sync states of a reported seat.
const (
	InSync  = "in_sync"
	Drift   = "drift"
	Unknown = "unknown"
)

// Sync compares the hash a machine reports as running with the hash of the seat's latest
// resolved snapshot. Either hash empty (nothing reported, or the seat is not in the cloud)
// is Unknown.
func Sync(running, expected string) string {
	switch {
	case running == "" || expected == "":
		return Unknown
	case running == expected:
		return InSync
	default:
		return Drift
	}
}
