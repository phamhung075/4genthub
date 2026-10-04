package seatrenderer

// The AgentSpec file shapes lives here, not in the retired agent_management package:
// the seat renderer is the only producer and seat_management is the only consumer.

// OpenRigTokenEnvVar is expanded by Claude Code from the seat's environment, so
// no credential is ever written into a rendered spec.
const OpenRigTokenEnvVar = "AGENTHUB_TOKEN"

// OpenRigSpecFile is one file of a rendered AgentSpec directory; Path is relative to
// the spec root and always uses forward slashes.
type OpenRigSpecFile struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

// OpenRigSpec is an OpenRig AgentSpec directory rendered from a seat.
// OpenRig resolves agent_ref only from local:/path: directories, so the cloud serves
// the files and the client writes them to disk.
type OpenRigSpec struct {
	Slug    string            `json:"slug"`
	Name    string            `json:"name"`
	Version string            `json:"version"`
	Files   []OpenRigSpecFile `json:"files"`
}
