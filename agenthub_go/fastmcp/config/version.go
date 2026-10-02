// Package config ports the fastmcp/config modules.
package config

import (
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
)

// DefaultVersion is the default server version, overridable with SERVER_VERSION.
const DefaultVersion = "0.0.2c"

// ResolveVersion is SERVER_VERSION when set (even to the empty string), else DefaultVersion.
func ResolveVersion(lookup func(string) (string, bool)) string {
	if v, ok := lookup("SERVER_VERSION"); ok {
		return v
	}
	return DefaultVersion
}

// Version is the server version, resolved once at startup (Python: at import).
var Version = ResolveVersion(os.LookupEnv)

// VersionInfo is the additional version metadata.
func VersionInfo() *entities.OrderedMap[any] { return VersionInfoFor(Version) }

// VersionInfoFor builds the metadata for a given version.
func VersionInfoFor(version string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("version", version)
	m.Set("name", "agenthub - Task Management & Agent Orchestration")
	m.Set("codename", "Vision System Enhanced")
	m.Set("release_date", "2025-09-10")
	return m
}
