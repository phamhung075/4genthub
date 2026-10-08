// Package config ports the fastmcp/config modules.
package config

// ReleaseVersion is THE release identity of this server: one string, one place.
//
// Every surface that advertises the server's own version reads this. They used to disagree:
// /health carried this marker while the MCP initialize serverInfo, the MCP status tool, the
// register_mcp_client response, the access-level health checker and the connection-management
// server records carried either the ported module's default (0.0.2c) or the Python framework's
// version (2.1.0). Three answers to "which release is this?" is how a deploy gets called
// complete when it is not, so the field is now one value (measured 2026-10-06; see CHANGELOG).
//
// The Python port also kept the version overridable with SERVER_VERSION and its metadata in
// VersionInfo; both went with that tree. SERVER_VERSION is set nowhere in this repo and an
// environment variable that can rename the release is a second identity by construction, so a
// literal is the honest form of a deploy marker.
//
// Bump this with every change that must be confirmable after a deploy. It is the LAST commit in
// the set before a deploy is requested, so the string can never cover a tree that lacks the
// content it marks; if a commit lands after the bump, the bump moves to it or the deploy waits.
const ReleaseVersion = "0.0.26"

// ServerName is the server's NAME — the brand subtitle after the dash, not a
// description sentence. One definition for every place that advertises the
// server name: the health endpoint, the MCP initialize serverInfo, the MCP status
// tool and the server records built by the connection-management use cases.
const ServerName = "agenthub - AI Orchestration Platform"
