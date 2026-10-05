package fastmcp

// Custom exceptions. The McpError re-export of Python belongs to the MCP protocol port.

// FastMCPError is the base error for FastMCP.
type FastMCPError struct{ Msg string }

func (e *FastMCPError) Error() string { return e.Msg }

// ValidationError is an error in validating parameters or return values.
type ValidationError struct{ FastMCPError }

// ResourceError is an error in resource operations.
type ResourceError struct{ FastMCPError }

// ToolError is an error in tool operations.
type ToolError struct{ FastMCPError }

// PromptError is an error in prompt operations.
type PromptError struct{ FastMCPError }

// Unwrap makes errors.As(err, **FastMCPError) match the subclasses.
func (e *ValidationError) Unwrap() error { return &e.FastMCPError }
func (e *ResourceError) Unwrap() error   { return &e.FastMCPError }
func (e *ToolError) Unwrap() error       { return &e.FastMCPError }
func (e *PromptError) Unwrap() error     { return &e.FastMCPError }

// InvalidSignature is an invalid signature for use with FastMCP.
type InvalidSignature struct{ Msg string }

func (e *InvalidSignature) Error() string { return e.Msg }

// ClientError is an error in client operations.
type ClientError struct{ Msg string }

func (e *ClientError) Error() string { return e.Msg }

// NotFoundError means an object was not found.
type NotFoundError struct{ Msg string }

func (e *NotFoundError) Error() string { return e.Msg }

// DisabledError means an object is disabled.
type DisabledError struct{ Msg string }

func (e *DisabledError) Error() string { return e.Msg }
