package seatrenderer

// The AgentSpec file shapes lives here, not in the retired agent_management package:
// the seat renderer is the only producer and seat_management is the only consumer.

// TokenEnvVar is expanded by Claude Code from the seat's environment, so
// no credential is ever written into a rendered spec.
const TokenEnvVar = "AGENTHUB_TOKEN"

// SeatSpecFile is one file of a rendered AgentSpec directory; Path is relative to
// the spec root and always uses forward slashes.
type SeatSpecFile struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

// SeatSpec is an AgentSpec directory rendered from a seat.
// 4genteam resolves agent_ref only from local:/path: directories, so the cloud serves
// the files and the client writes them to disk.
type SeatSpec struct {
	Slug    string         `json:"slug"`
	Name    string         `json:"name"`
	Version string         `json:"version"`
	Files   []SeatSpecFile `json:"files"`
}
