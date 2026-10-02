package interfaces

// IPathResolver resolves and inspects file system paths (Python Path values are strings).
type IPathResolver interface {
	ResolvePath(path string) string
	ResolveRelative(path, base string) string
	NormalizePath(path string) string
	PathExists(path string) bool
	IsDirectory(path string) bool
	IsFile(path string) bool
	GetParentDirectory(path string) string
	JoinPaths(paths ...string) string
}

// IAgentDocGenerator generates agent documentation.
type IAgentDocGenerator interface {
	GenerateDocumentation(agentID string, agentConfig map[string]any) (string, error)
	GenerateAPIDocs(agentID string) (map[string]any, error)
	ValidateAgentConfig(config map[string]any) bool
	GetAgentCapabilities(agentID string) []string
	FormatAgentResponse(response map[string]any) string
}

// IUtilityService offers general-purpose helpers.
type IUtilityService interface {
	GenerateUUID() string
	GenerateTimestamp() string
	HashString(input string) string
	ValidateUUID(uuid string) bool
	SerializeData(data any) (string, error)
	DeserializeData(data string) (any, error)
	DeepMerge(dict1, dict2 map[string]any) map[string]any
	// FlattenDict flattens nested maps using separator (Python default ".").
	FlattenDict(nested map[string]any, separator string) map[string]any
}
