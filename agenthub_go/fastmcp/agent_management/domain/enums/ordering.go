// Package enums ports agent_management/domain/enums.
package enums

// InstanceOrdering is the ordering options for UserAgentInstance queries; the
// infrastructure layer translates these to SQL.
type InstanceOrdering string

const (
	InstanceOrderingCreatedDesc InstanceOrdering = "created_desc" // newest first (default for marketplace)
	InstanceOrderingCreatedAsc  InstanceOrdering = "created_asc"  // oldest first
	InstanceOrderingUpdatedDesc InstanceOrdering = "updated_desc" // recently updated first
	InstanceOrderingUpdatedAsc  InstanceOrdering = "updated_asc"  // least recently updated first
	InstanceOrderingNameAsc     InstanceOrdering = "name_asc"     // alphabetical A-Z
	InstanceOrderingNameDesc    InstanceOrdering = "name_desc"    // alphabetical Z-A
)
