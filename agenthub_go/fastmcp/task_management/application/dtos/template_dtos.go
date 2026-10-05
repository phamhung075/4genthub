package dtos

import "agenthub/fastmcp/task_management/domain/entities"

// TemplateCreateDTO is the DTO for creating a new template.
type TemplateCreateDTO struct {
	Name             string
	Description      string
	Content          string
	TemplateType     string
	Category         string
	Priority         string
	CompatibleAgents []string
	FilePatterns     []string
	Variables        []string
	Metadata         *entities.OrderedMap[any]
}

// NewTemplateCreateDTO mirrors TemplateCreateDTO.__post_init__.
func NewTemplateCreateDTO(r TemplateCreateDTO) *TemplateCreateDTO {
	if r.Priority == "" {
		r.Priority = "medium"
	}
	if r.CompatibleAgents == nil {
		r.CompatibleAgents = []string{"*"}
	}
	if r.FilePatterns == nil {
		r.FilePatterns = []string{}
	}
	if r.Variables == nil {
		r.Variables = []string{}
	}
	if r.Metadata == nil {
		r.Metadata = entities.NewOrderedMap[any]()
	}
	return &r
}

// TemplateUpdateDTO is the DTO for updating an existing template.
type TemplateUpdateDTO struct {
	TemplateID       string
	Name             *string
	Description      *string
	Content          *string
	TemplateType     *string
	Category         *string
	Priority         *string
	CompatibleAgents []string
	FilePatterns     []string
	Variables        []string
	Metadata         *entities.OrderedMap[any]
	IsActive         *bool
}

// TemplateResponseDTO is the DTO for a template response.
type TemplateResponseDTO struct {
	ID               string
	Name             string
	Description      string
	Content          string
	TemplateType     string
	Category         string
	Status           string
	Priority         string
	CompatibleAgents []string
	FilePatterns     []string
	Variables        []string
	Metadata         *entities.OrderedMap[any]
	CreatedAt        string
	UpdatedAt        string
	Version          int
	IsActive         bool
}

// TemplateListDTO is the DTO for a template list response.
type TemplateListDTO struct {
	Templates   []*TemplateResponseDTO
	TotalCount  int
	Page        int
	PageSize    int
	HasNext     bool
	HasPrevious bool
}

// TemplateRenderRequestDTO is the DTO for a template render request.
type TemplateRenderRequestDTO struct {
	TemplateID      string
	Variables       *entities.OrderedMap[any]
	TaskContext     *entities.OrderedMap[any]
	OutputPath      *string
	CacheStrategy   string
	ForceRegenerate bool
}

// NewTemplateRenderRequestDTO applies the Python default cache_strategy="default".
func NewTemplateRenderRequestDTO(r TemplateRenderRequestDTO) *TemplateRenderRequestDTO {
	if r.CacheStrategy == "" {
		r.CacheStrategy = "default"
	}
	return &r
}

// TemplateRenderResponseDTO is the DTO for a template render response.
type TemplateRenderResponseDTO struct {
	Content          string
	TemplateID       string
	VariablesUsed    *entities.OrderedMap[any]
	GeneratedAt      string
	GenerationTimeMs int
	CacheHit         bool
	OutputPath       *string
}

// TemplateSuggestionDTO is the DTO for a template suggestion.
type TemplateSuggestionDTO struct {
	TemplateID       string
	Name             string
	Description      string
	TemplateType     string
	Category         string
	Priority         string
	SuggestionScore  float64
	SuggestionReason string
	CompatibleAgents []string
	FilePatterns     []string
	Variables        []string
}

// TemplateSuggestionRequestDTO is the DTO for a template suggestion request.
type TemplateSuggestionRequestDTO struct {
	TaskContext  *entities.OrderedMap[any]
	AgentType    *string
	FilePatterns []string
	Limit        int
}

// NewTemplateSuggestionRequestDTO applies the Python default limit=10.
func NewTemplateSuggestionRequestDTO(r TemplateSuggestionRequestDTO) *TemplateSuggestionRequestDTO {
	if r.Limit == 0 {
		r.Limit = 10
	}
	return &r
}

// TemplateUsageDTO is the DTO for template usage tracking.
type TemplateUsageDTO struct {
	TemplateID       string
	TaskID           *string
	AgentName        *string
	VariablesUsed    *entities.OrderedMap[any]
	OutputPath       *string
	GenerationTimeMs int
	CacheHit         bool
	UsedAt           *string
}

// NewTemplateUsageDTO mirrors TemplateUsageDTO.__post_init__ (variables_used {}).
func NewTemplateUsageDTO(r TemplateUsageDTO) *TemplateUsageDTO {
	if r.VariablesUsed == nil {
		r.VariablesUsed = entities.NewOrderedMap[any]()
	}
	return &r
}

// TemplateAnalyticsDTO is the DTO for template analytics.
type TemplateAnalyticsDTO struct {
	TemplateID          *string
	UsageCount          int
	SuccessRate         float64
	AvgGenerationTime   float64
	TotalGenerationTime int
	CacheHitRate        float64
	MostUsedVariables   []*entities.OrderedMap[any]
	UsageByAgent        *entities.OrderedMap[int]
	UsageByTask         *entities.OrderedMap[int]
	UsageOverTime       []*entities.OrderedMap[any]
}

// NewTemplateAnalyticsDTO mirrors TemplateAnalyticsDTO.__post_init__.
func NewTemplateAnalyticsDTO(r TemplateAnalyticsDTO) *TemplateAnalyticsDTO {
	if r.MostUsedVariables == nil {
		r.MostUsedVariables = []*entities.OrderedMap[any]{}
	}
	if r.UsageByAgent == nil {
		r.UsageByAgent = entities.NewOrderedMap[int]()
	}
	if r.UsageByTask == nil {
		r.UsageByTask = entities.NewOrderedMap[int]()
	}
	if r.UsageOverTime == nil {
		r.UsageOverTime = []*entities.OrderedMap[any]{}
	}
	return &r
}

// TemplateSearchDTO is the DTO for template search.
type TemplateSearchDTO struct {
	Query           string
	TemplateType    *string
	Category        *string
	AgentCompatible *string
	IsActive        *bool
	Limit           int
	Offset          int
}

// NewTemplateSearchDTO applies the Python defaults limit=50 and offset=0.
func NewTemplateSearchDTO(r TemplateSearchDTO) *TemplateSearchDTO {
	if r.Limit == 0 {
		r.Limit = 50
	}
	return &r
}

// TemplateValidationDTO is the DTO for a template validation response.
type TemplateValidationDTO struct {
	IsValid    bool
	Errors     []string
	Warnings   []string
	TemplateID *string
}

// NewTemplateValidationDTO mirrors TemplateValidationDTO.__post_init__.
func NewTemplateValidationDTO(r TemplateValidationDTO) *TemplateValidationDTO {
	if r.Errors == nil {
		r.Errors = []string{}
	}
	if r.Warnings == nil {
		r.Warnings = []string{}
	}
	return &r
}

// TemplateCacheDTO is the DTO for template cache operations.
type TemplateCacheDTO struct {
	TemplateID *string
	CacheKey   *string
	Operation  string
	TTL        *int
	Data       *entities.OrderedMap[any]
}

// NewTemplateCacheDTO applies the Python default operation="get".
func NewTemplateCacheDTO(r TemplateCacheDTO) *TemplateCacheDTO {
	if r.Operation == "" {
		r.Operation = "get"
	}
	return &r
}
