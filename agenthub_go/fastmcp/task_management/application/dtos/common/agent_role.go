// Package common ports task_management/application/dtos/common.
package common

// AgentRole is the application DTO definition of an agent role. It is distinct
// from the domain value object value_objects.AgentRole.
type AgentRole struct {
	Name                string
	Persona             string
	PrimaryFocus        string
	Rules               []string
	ContextInstructions []string
	ToolsGuidance       []string
	OutputFormat        string
	PersonaIcon         *string
}
