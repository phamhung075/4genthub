// Package seatsync decides whether the hash a machine reports as running equals the hash of the
// seat's newest stored resolved snapshot. InSync says nothing more: it is not "up to date" with the
// seat type or its modules, because a newer resolve that was never stored cannot be compared.
package seatsync

// Sync states of a reported seat. InSync: running hash == newest stored snapshot hash. Drift: both
// known and different. Unknown: either hash is missing.
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
