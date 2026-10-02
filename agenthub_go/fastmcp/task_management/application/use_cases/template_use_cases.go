// Package use_cases ports task_management/application/use_cases/template_use_cases.py.
package use_cases

import (
	"context"
	"sort"
	"time"

	"agenthub/fastmcp/task_management/application/dtos"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// templateUseCasesTemplateEngine is the minimal rendering dependency. The Python
// TemplateEngineService lives in the infrastructure layer and is not ported yet, so
// only the method this use case calls is declared here.
type templateUseCasesTemplateEngine interface {
	RenderTemplate(ctx context.Context, request entities.TemplateRenderRequest) (*entities.TemplateResult, error)
}

// TemplateUseCases orchestrates template business logic.
type TemplateUseCases struct {
	templateRepository    repositories.TemplateRepositoryInterface
	templateDomainService *services.TemplateDomainService
	templateEngineService templateUseCasesTemplateEngine
	cacheService          any
}

// NewTemplateUseCases mirrors TemplateUseCases.__init__ (cache_service defaults to None).
func NewTemplateUseCases(templateRepository repositories.TemplateRepositoryInterface,
	templateDomainService *services.TemplateDomainService,
	templateEngineService templateUseCasesTemplateEngine, cacheService any) *TemplateUseCases {
	return &TemplateUseCases{
		templateRepository:    templateRepository,
		templateDomainService: templateDomainService,
		templateEngineService: templateEngineService,
		cacheService:          cacheService,
	}
}

// CreateTemplate creates a new template.
func (uc *TemplateUseCases) CreateTemplate(ctx context.Context, createDTO *dtos.TemplateCreateDTO) (*dtos.TemplateResponseDTO, error) {
	templateType, err := templateUseCasesEnum("TemplateType", createDTO.TemplateType, value_objects.TemplateTypeValues)
	if err != nil {
		return nil, err
	}
	category, err := templateUseCasesEnum("TemplateCategory", createDTO.Category, value_objects.TemplateCategoryValues)
	if err != nil {
		return nil, err
	}
	priority, err := templateUseCasesEnum("TemplatePriority", createDTO.Priority, value_objects.TemplatePriorityValues)
	if err != nil {
		return nil, err
	}
	newID := value_objects.GenerateNewTemplateId()
	status := value_objects.TemplateStatusActive
	template, err := entities.NewTemplate(entities.Template{
		ID:               &newID,
		Name:             createDTO.Name,
		Description:      createDTO.Description,
		Content:          createDTO.Content,
		TemplateType:     &templateType,
		Category:         &category,
		Status:           &status,
		Priority:         &priority,
		CompatibleAgents: createDTO.CompatibleAgents,
		FilePatterns:     createDTO.FilePatterns,
		Variables:        createDTO.Variables,
		Metadata:         templateUseCasesMapFromOrdered(createDTO.Metadata),
	})
	if err != nil {
		return nil, err
	}

	validationErrors := uc.templateDomainService.ValidateTemplate(template)
	if len(validationErrors) > 0 {
		id, idErr := templateUseCasesIDValue(template.ID)
		if idErr != nil {
			return nil, idErr
		}
		return nil, exceptions.NewTemplateValidationError("Template validation failed", &id, validationErrors)
	}

	savedTemplate, err := uc.templateRepository.Save(ctx, template)
	if err != nil {
		return nil, err
	}
	return uc.templateToResponseDTO(savedTemplate)
}

// GetTemplate gets a template by ID.
func (uc *TemplateUseCases) GetTemplate(ctx context.Context, templateID string) (*dtos.TemplateResponseDTO, error) {
	id, err := value_objects.NewTemplateId(templateID)
	if err != nil {
		return nil, err
	}
	template, err := uc.templateRepository.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if template == nil {
		return nil, exceptions.NewTemplateNotFoundError(templateID)
	}
	return uc.templateToResponseDTO(template)
}

// UpdateTemplate updates an existing template.
func (uc *TemplateUseCases) UpdateTemplate(ctx context.Context, updateDTO *dtos.TemplateUpdateDTO) (*dtos.TemplateResponseDTO, error) {
	id, err := value_objects.NewTemplateId(updateDTO.TemplateID)
	if err != nil {
		return nil, err
	}
	template, err := uc.templateRepository.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if template == nil {
		return nil, exceptions.NewTemplateNotFoundError(updateDTO.TemplateID)
	}

	if updateDTO.Name != nil {
		template.Name = *updateDTO.Name
	}
	if updateDTO.Description != nil {
		template.Description = *updateDTO.Description
	}
	if updateDTO.Content != nil {
		if err := template.UpdateContent(*updateDTO.Content); err != nil {
			return nil, err
		}
	}
	if updateDTO.TemplateType != nil {
		templateType, err := templateUseCasesEnum("TemplateType", *updateDTO.TemplateType, value_objects.TemplateTypeValues)
		if err != nil {
			return nil, err
		}
		template.TemplateType = &templateType
	}
	if updateDTO.Category != nil {
		category, err := templateUseCasesEnum("TemplateCategory", *updateDTO.Category, value_objects.TemplateCategoryValues)
		if err != nil {
			return nil, err
		}
		template.Category = &category
	}
	if updateDTO.Priority != nil {
		priority, err := templateUseCasesEnum("TemplatePriority", *updateDTO.Priority, value_objects.TemplatePriorityValues)
		if err != nil {
			return nil, err
		}
		template.Priority = &priority
	}
	if updateDTO.CompatibleAgents != nil {
		template.CompatibleAgents = updateDTO.CompatibleAgents
	}
	if updateDTO.FilePatterns != nil {
		template.FilePatterns = updateDTO.FilePatterns
	}
	if updateDTO.Variables != nil {
		template.Variables = updateDTO.Variables
	}
	if updateDTO.Metadata != nil {
		if err := template.UpdateMetadata(templateUseCasesMapFromOrdered(updateDTO.Metadata)); err != nil {
			return nil, err
		}
	}
	if updateDTO.IsActive != nil {
		if *updateDTO.IsActive {
			if err := template.Activate(); err != nil {
				return nil, err
			}
		} else {
			if err := template.Deactivate(); err != nil {
				return nil, err
			}
		}
	}

	validationErrors := uc.templateDomainService.ValidateTemplate(template)
	if len(validationErrors) > 0 {
		idValue, idErr := templateUseCasesIDValue(template.ID)
		if idErr != nil {
			return nil, idErr
		}
		return nil, exceptions.NewTemplateValidationError("Template validation failed", &idValue, validationErrors)
	}

	updatedTemplate, err := uc.templateRepository.Save(ctx, template)
	if err != nil {
		return nil, err
	}
	return uc.templateToResponseDTO(updatedTemplate)
}

// DeleteTemplate archives the template instead of hard deleting it.
func (uc *TemplateUseCases) DeleteTemplate(ctx context.Context, templateID string) (bool, error) {
	id, err := value_objects.NewTemplateId(templateID)
	if err != nil {
		return false, err
	}
	template, err := uc.templateRepository.GetByID(ctx, id)
	if err != nil {
		return false, err
	}
	if template == nil {
		return false, exceptions.NewTemplateNotFoundError(templateID)
	}
	if err := template.Archive(); err != nil {
		return false, err
	}
	if _, err := uc.templateRepository.Save(ctx, template); err != nil {
		return false, err
	}
	return true, nil
}

// ListTemplates lists templates with filtering and pagination.
func (uc *TemplateUseCases) ListTemplates(ctx context.Context, searchDTO *dtos.TemplateSearchDTO) (*dtos.TemplateListDTO, error) {
	templates, totalCount, err := uc.templateRepository.ListTemplates(ctx, repositories.TemplateListFilter{
		TemplateType:    searchDTO.TemplateType,
		Category:        searchDTO.Category,
		AgentCompatible: searchDTO.AgentCompatible,
		IsActive:        searchDTO.IsActive,
		Limit:           searchDTO.Limit,
		Offset:          searchDTO.Offset,
	})
	if err != nil {
		return nil, err
	}
	templateDTOs := make([]*dtos.TemplateResponseDTO, 0, len(templates))
	for _, template := range templates {
		dto, err := uc.templateToResponseDTO(template)
		if err != nil {
			return nil, err
		}
		templateDTOs = append(templateDTOs, dto)
	}
	if searchDTO.Limit == 0 {
		return nil, entities.ErrZeroDivision
	}
	return &dtos.TemplateListDTO{
		Templates:   templateDTOs,
		TotalCount:  totalCount,
		Page:        templateUseCasesFloorDiv(searchDTO.Offset, searchDTO.Limit) + 1,
		PageSize:    searchDTO.Limit,
		HasNext:     (searchDTO.Offset + searchDTO.Limit) < totalCount,
		HasPrevious: searchDTO.Offset > 0,
	}, nil
}

// RenderTemplate renders a template with variables.
func (uc *TemplateUseCases) RenderTemplate(ctx context.Context, renderDTO *dtos.TemplateRenderRequestDTO) (*dtos.TemplateRenderResponseDTO, error) {
	id, err := value_objects.NewTemplateId(renderDTO.TemplateID)
	if err != nil {
		return nil, err
	}
	template, err := uc.templateRepository.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if template == nil {
		return nil, exceptions.NewTemplateNotFoundError(renderDTO.TemplateID)
	}

	renderRequest := entities.TemplateRenderRequest{
		TemplateID:      *template.ID,
		Variables:       templateUseCasesOptionalMapFromOrdered(renderDTO.Variables),
		TaskContext:     templateUseCasesOptionalMapFromOrdered(renderDTO.TaskContext),
		OutputPath:      renderDTO.OutputPath,
		CacheStrategy:   renderDTO.CacheStrategy,
		ForceRegenerate: renderDTO.ForceRegenerate,
	}

	validationErrors := uc.templateDomainService.ValidateRenderRequest(renderRequest)
	if len(validationErrors) > 0 {
		idValue, idErr := templateUseCasesIDValue(template.ID)
		if idErr != nil {
			return nil, idErr
		}
		return nil, exceptions.NewTemplateRenderError("Template render request validation failed", &idValue,
			map[string]any{"validation_errors": validationErrors})
	}

	result, err := uc.templateEngineService.RenderTemplate(ctx, renderRequest)
	if err != nil {
		return nil, err
	}

	usage := uc.templateDomainService.CreateTemplateUsage(*template.ID, nil, nil, nil,
		result.VariablesUsed, result.OutputPath, result.GenerationTimeMs, result.CacheHit)
	if _, err := uc.templateRepository.SaveUsage(ctx, usage); err != nil {
		return nil, err
	}

	return &dtos.TemplateRenderResponseDTO{
		Content:          result.Content,
		TemplateID:       result.TemplateID.Value,
		VariablesUsed:    templateUseCasesOrderedFromMap(result.VariablesUsed),
		GeneratedAt:      value_objects.IsoFormat(result.GeneratedAt),
		GenerationTimeMs: result.GenerationTimeMs,
		CacheHit:         result.CacheHit,
		OutputPath:       result.OutputPath,
	}, nil
}

// SuggestTemplates suggests templates based on context.
func (uc *TemplateUseCases) SuggestTemplates(ctx context.Context, suggestionDTO *dtos.TemplateSuggestionRequestDTO) ([]*dtos.TemplateSuggestionDTO, error) {
	active := true
	templates, _, err := uc.templateRepository.ListTemplates(ctx, repositories.TemplateListFilter{
		IsActive: &active,
		Limit:    1000,
	})
	if err != nil {
		return nil, err
	}

	suggestions := []*dtos.TemplateSuggestionDTO{}
	for _, template := range templates {
		agentType := ""
		if suggestionDTO.AgentType != nil && *suggestionDTO.AgentType != "" {
			agentType = *suggestionDTO.AgentType
		}
		taskContext := templateUseCasesMapFromOrdered(suggestionDTO.TaskContext)

		if !uc.templateDomainService.CanRenderTemplate(template, agentType, suggestionDTO.FilePatterns) {
			continue
		}

		usageStats, err := uc.templateRepository.GetUsageStats(ctx, *template.ID)
		if err != nil {
			return nil, err
		}

		score, err := uc.templateDomainService.CalculateTemplateScore(template, taskContext,
			agentType, suggestionDTO.FilePatterns, usageStats)
		if err != nil {
			return nil, err
		}

		if score > 0 {
			reason, err := uc.templateDomainService.GetSuggestionReason(template, taskContext, score)
			if err != nil {
				return nil, err
			}
			templateType, err := templateUseCasesEnumValue(template.TemplateType)
			if err != nil {
				return nil, err
			}
			category, err := templateUseCasesEnumValue(template.Category)
			if err != nil {
				return nil, err
			}
			priority, err := templateUseCasesEnumValue(template.Priority)
			if err != nil {
				return nil, err
			}
			suggestions = append(suggestions, &dtos.TemplateSuggestionDTO{
				TemplateID:       template.ID.Value,
				Name:             template.Name,
				Description:      template.Description,
				TemplateType:     templateType,
				Category:         category,
				Priority:         priority,
				SuggestionScore:  score,
				SuggestionReason: reason,
				CompatibleAgents: template.CompatibleAgents,
				FilePatterns:     template.FilePatterns,
				Variables:        template.Variables,
			})
		}
	}

	sort.SliceStable(suggestions, func(i, j int) bool {
		return suggestions[i].SuggestionScore > suggestions[j].SuggestionScore
	})
	return templateUseCasesLimitSlice(suggestions, suggestionDTO.Limit), nil
}

// ValidateTemplate validates a template.
func (uc *TemplateUseCases) ValidateTemplate(ctx context.Context, templateID string) (*dtos.TemplateValidationDTO, error) {
	id, err := value_objects.NewTemplateId(templateID)
	if err != nil {
		return nil, err
	}
	template, err := uc.templateRepository.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if template == nil {
		return nil, exceptions.NewTemplateNotFoundError(templateID)
	}

	validationErrors := uc.templateDomainService.ValidateTemplate(template)
	return dtos.NewTemplateValidationDTO(dtos.TemplateValidationDTO{
		IsValid:    len(validationErrors) == 0,
		Errors:     validationErrors,
		Warnings:   []string{},
		TemplateID: &templateID,
	}), nil
}

// GetTemplateAnalytics gets template analytics; a nil templateID means all templates.
//
// Quirk preserved: the Python builds TemplateAnalyticsDTO(usage_by_project=...), but
// the DTO declares `usage_by_task`, so the constructor raises TypeError. The
// surrounding except logs and re-raises it, meaning this method always fails after
// the repository call succeeds. Reproduce that instead of silently remapping the key.
func (uc *TemplateUseCases) GetTemplateAnalytics(ctx context.Context, templateID *string) (*dtos.TemplateAnalyticsDTO, error) {
	if _, err := uc.templateRepository.GetAnalytics(ctx, templateID); err != nil {
		return nil, err
	}
	return nil, value_objects.TypeErrorf(
		"TemplateAnalyticsDTO.__init__() got an unexpected keyword argument 'usage_by_project'")
}

// templateToResponseDTO converts a template entity to a response DTO.
func (uc *TemplateUseCases) templateToResponseDTO(template *entities.Template) (*dtos.TemplateResponseDTO, error) {
	id, err := templateUseCasesIDValue(template.ID)
	if err != nil {
		return nil, err
	}
	templateType, err := templateUseCasesEnumValue(template.TemplateType)
	if err != nil {
		return nil, err
	}
	category, err := templateUseCasesEnumValue(template.Category)
	if err != nil {
		return nil, err
	}
	status, err := templateUseCasesEnumValue(template.Status)
	if err != nil {
		return nil, err
	}
	priority, err := templateUseCasesEnumValue(template.Priority)
	if err != nil {
		return nil, err
	}
	createdAt, err := templateUseCasesIsoTimestamp(template.CreatedAt, "isoformat")
	if err != nil {
		return nil, err
	}
	updatedAt, err := templateUseCasesIsoTimestamp(template.UpdatedAt, "isoformat")
	if err != nil {
		return nil, err
	}

	version := 1
	if template.Version != nil {
		version = *template.Version
	}
	isActive := true
	if template.IsActive != nil {
		isActive = *template.IsActive
	}

	compatibleAgents := template.CompatibleAgents
	if compatibleAgents == nil {
		compatibleAgents = []string{}
	}
	filePatterns := template.FilePatterns
	if filePatterns == nil {
		filePatterns = []string{}
	}
	variables := template.Variables
	if variables == nil {
		variables = []string{}
	}

	return &dtos.TemplateResponseDTO{
		ID:               id,
		Name:             template.Name,
		Description:      template.Description,
		Content:          template.Content,
		TemplateType:     templateType,
		Category:         category,
		Status:           status,
		Priority:         priority,
		CompatibleAgents: compatibleAgents,
		FilePatterns:     filePatterns,
		Variables:        variables,
		Metadata:         templateUseCasesOrderedFromMap(template.Metadata),
		CreatedAt:        createdAt,
		UpdatedAt:        updatedAt,
		Version:          version,
		IsActive:         isActive,
	}, nil
}

// templateUseCasesEnum mirrors a Python enum class call; the message matches ValueError.
func templateUseCasesEnum[T ~string](name, v string, all []T) (T, error) {
	for _, e := range all {
		if string(e) == v {
			return e, nil
		}
	}
	var zero T
	return zero, value_objects.ValueErrorf("%s is not a valid %s", value_objects.PyRepr(v), name)
}

// templateUseCasesEnumValue is `.value` on an optional enum: a None enum raises the
// same AttributeError text Python does.
func templateUseCasesEnumValue[T ~string](e *T) (string, error) {
	if e == nil {
		return "", value_objects.TypeErrorf("'NoneType' object has no attribute 'value'")
	}
	return string(*e), nil
}

// templateUseCasesIDValue is `template.id.value` with the None guard.
func templateUseCasesIDValue(id *value_objects.TemplateId) (string, error) {
	if id == nil {
		return "", value_objects.TypeErrorf("'NoneType' object has no attribute 'value'")
	}
	return id.Value, nil
}

// templateUseCasesIsoTimestamp is `dt.isoformat()` with the None guard.
func templateUseCasesIsoTimestamp(t *time.Time, attr string) (string, error) {
	if t == nil {
		return "", value_objects.TypeErrorf("'NoneType' object has no attribute '%s'", attr)
	}
	return value_objects.IsoFormat(*t), nil
}

// templateUseCasesMapFromOrdered converts an ordered map to the map[string]any the
// domain layer uses.
func templateUseCasesMapFromOrdered(m *entities.OrderedMap[any]) map[string]any {
	out := map[string]any{}
	if m == nil {
		return out
	}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out[k] = v
	}
	return out
}

// templateUseCasesOptionalMapFromOrdered is like templateUseCasesMapFromOrdered but a
// nil ordered map stays nil (Python None).
func templateUseCasesOptionalMapFromOrdered(m *entities.OrderedMap[any]) map[string]any {
	if m == nil {
		return nil
	}
	return templateUseCasesMapFromOrdered(m)
}

// templateUseCasesOrderedFromMap converts a map[string]any to an ordered map. Go maps
// carry no insertion order, so keys are sorted for a deterministic equivalent (the same
// convention used by the ported repositories).
func templateUseCasesOrderedFromMap(m map[string]any) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		out.Set(k, m[k])
	}
	return out
}

// templateUseCasesIntValue is dict.get(key, default) for an int field.
func templateUseCasesIntValue(v any, def int) int {
	if v == nil {
		return def
	}
	if f, ok := value_objects.PyFloat(v); ok {
		return int(f)
	}
	return def
}

// templateUseCasesFloatValue is dict.get(key, default) for a float field.
func templateUseCasesFloatValue(v any, def float64) float64 {
	if v == nil {
		return def
	}
	if f, ok := value_objects.PyFloat(v); ok {
		return f
	}
	return def
}

// templateUseCasesOrderedList converts a list-of-dicts value to ordered maps.
func templateUseCasesOrderedList(v any) []*entities.OrderedMap[any] {
	out := []*entities.OrderedMap[any]{}
	switch list := v.(type) {
	case []*entities.OrderedMap[any]:
		return append(out, list...)
	case []any:
		for _, item := range list {
			switch d := item.(type) {
			case *entities.OrderedMap[any]:
				out = append(out, d)
			case map[string]any:
				out = append(out, templateUseCasesOrderedFromMap(d))
			}
		}
	}
	return out
}

// templateUseCasesIntMap converts a dict[str, int] value (or a value_objects.OrderedAny)
// to an ordered int map; keys are sorted since Go maps are unordered.
func templateUseCasesIntMap(v any) *entities.OrderedMap[int] {
	out := entities.NewOrderedMap[int]()
	switch m := v.(type) {
	case nil:
		return out
	case map[string]int:
		keys := make([]string, 0, len(m))
		for k := range m {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			out.Set(k, m[k])
		}
	case map[string]any:
		keys := make([]string, 0, len(m))
		for k := range m {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			out.Set(k, templateUseCasesIntValue(m[k], 0))
		}
	case *entities.OrderedMap[any]:
		for _, k := range m.Keys() {
			val, _ := m.Get(k)
			out.Set(k, templateUseCasesIntValue(val, 0))
		}
	}
	return out
}

// templateUseCasesFloorDiv is Python's // for ints (floors toward negative infinity).
func templateUseCasesFloorDiv(a, b int) int {
	q := a / b
	if (a%b != 0) && ((a < 0) != (b < 0)) {
		q--
	}
	return q
}

// templateUseCasesLimitSlice is Python's items[:limit], including the negative-limit and
// oversized-limit clamps.
func templateUseCasesLimitSlice(items []*dtos.TemplateSuggestionDTO, limit int) []*dtos.TemplateSuggestionDTO {
	n := len(items)
	end := limit
	if end < 0 {
		end = n + end
	}
	if end < 0 {
		end = 0
	}
	if end > n {
		end = n
	}
	return items[:end]
}
