package use_cases

import (
	"context"
	"errors"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/application/dtos"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ---- fakes -------------------------------------------------------------------

type templateUseCasesFakeRepo struct {
	repositories.TemplateRepositoryInterface

	getByIDResult *entities.Template
	getByIDErr    error

	saveErr    error
	saved      []*entities.Template
	saveResult *entities.Template

	listResult  []*entities.Template
	listTotal   int
	listErr     error
	listFilter  *repositories.TemplateListFilter
	usageStats  map[string]any
	usageStatEr error
	usageCalls  []value_objects.TemplateId

	savedUsage   []entities.TemplateUsage
	saveUsageErr error

	analytics     map[string]any
	analyticsErr  error
	analyticsID   *string
	analyticsCall bool
}

func (f *templateUseCasesFakeRepo) Save(_ context.Context, template *entities.Template) (*entities.Template, error) {
	if f.saveErr != nil {
		return nil, f.saveErr
	}
	f.saved = append(f.saved, template)
	if f.saveResult != nil {
		return f.saveResult, nil
	}
	return template, nil
}

func (f *templateUseCasesFakeRepo) GetByID(_ context.Context, _ value_objects.TemplateId) (*entities.Template, error) {
	return f.getByIDResult, f.getByIDErr
}

func (f *templateUseCasesFakeRepo) ListTemplates(_ context.Context, filter repositories.TemplateListFilter) ([]*entities.Template, int, error) {
	f.listFilter = &filter
	return f.listResult, f.listTotal, f.listErr
}

func (f *templateUseCasesFakeRepo) SaveUsage(_ context.Context, usage entities.TemplateUsage) (bool, error) {
	if f.saveUsageErr != nil {
		return false, f.saveUsageErr
	}
	f.savedUsage = append(f.savedUsage, usage)
	return true, nil
}

func (f *templateUseCasesFakeRepo) GetUsageStats(_ context.Context, templateID value_objects.TemplateId) (map[string]any, error) {
	f.usageCalls = append(f.usageCalls, templateID)
	return f.usageStats, f.usageStatEr
}

func (f *templateUseCasesFakeRepo) GetAnalytics(_ context.Context, templateID *string) (map[string]any, error) {
	f.analyticsCall = true
	f.analyticsID = templateID
	return f.analytics, f.analyticsErr
}

type templateUseCasesFakeEngine struct {
	result *entities.TemplateResult
	err    error
	got    *entities.TemplateRenderRequest
	calls  int
}

func (f *templateUseCasesFakeEngine) RenderTemplate(_ context.Context, request entities.TemplateRenderRequest) (*entities.TemplateResult, error) {
	f.calls++
	f.got = &request
	return f.result, f.err
}

// ---- helpers -----------------------------------------------------------------

func templateUseCasesTestTemplate(t *testing.T, name string, priority value_objects.TemplatePriority) *entities.Template {
	t.Helper()
	id := value_objects.GenerateNewTemplateId()
	templateType := value_objects.TemplateTypeTask
	category := value_objects.TemplateCategoryGeneral
	status := value_objects.TemplateStatusActive
	template, err := entities.NewTemplate(entities.Template{
		ID:               &id,
		Name:             name,
		Description:      "desc",
		Content:          "content",
		TemplateType:     &templateType,
		Category:         &category,
		Status:           &status,
		Priority:         &priority,
		CompatibleAgents: []string{"*"},
		FilePatterns:     []string{},
		Variables:        []string{},
		Metadata:         map[string]any{},
	})
	if err != nil {
		t.Fatalf("build template: %v", err)
	}
	return template
}

func templateUseCasesRequireKeys(t *testing.T, m *entities.OrderedMap[any], want []string) {
	t.Helper()
	got := m.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

// ---- create_template ---------------------------------------------------------

func TestTemplateUseCasesCreateTemplate(t *testing.T) {
	repo := &templateUseCasesFakeRepo{}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("z", 1)
	metadata.Set("a", 2)
	createDTO := dtos.NewTemplateCreateDTO(dtos.TemplateCreateDTO{
		Name:             "name",
		Description:      "desc",
		Content:          "content",
		TemplateType:     "task",
		Category:         "general",
		Priority:         "high",
		CompatibleAgents: []string{"*"},
		FilePatterns:     []string{"*.go"},
		Variables:        []string{"x"},
		Metadata:         metadata,
	})

	resp, err := uc.CreateTemplate(context.Background(), createDTO)
	if err != nil {
		t.Fatalf("CreateTemplate: %v", err)
	}
	if resp.ID == "" {
		t.Fatalf("id must be generated")
	}
	if resp.Name != "name" || resp.Description != "desc" || resp.Content != "content" {
		t.Fatalf("unexpected fields: %+v", resp)
	}
	if resp.TemplateType != "task" || resp.Category != "general" || resp.Priority != "high" {
		t.Fatalf("unexpected enums: %+v", resp)
	}
	if resp.Status != "active" || !resp.IsActive {
		t.Fatalf("new template must be active: %+v", resp)
	}
	if resp.Version != 1 {
		t.Fatalf("version = %d, want 1", resp.Version)
	}
	if resp.CreatedAt == "" || resp.UpdatedAt == "" {
		t.Fatalf("timestamps must be set: %+v", resp)
	}
	if len(resp.CompatibleAgents) != 1 || resp.CompatibleAgents[0] != "*" {
		t.Fatalf("compatible agents = %v", resp.CompatibleAgents)
	}
	if len(resp.FilePatterns) != 1 || resp.FilePatterns[0] != "*.go" {
		t.Fatalf("file patterns = %v", resp.FilePatterns)
	}
	if len(resp.Variables) != 1 || resp.Variables[0] != "x" {
		t.Fatalf("variables = %v", resp.Variables)
	}
	// Go maps lose insertion order; the port uses sorted keys.
	templateUseCasesRequireKeys(t, resp.Metadata, []string{"a", "z"})

	if len(repo.saved) != 1 {
		t.Fatalf("save calls = %d, want 1", len(repo.saved))
	}
	if repo.saved[0].ID.Value != resp.ID {
		t.Fatalf("saved id %q != response id %q", repo.saved[0].ID.Value, resp.ID)
	}
}

func TestTemplateUseCasesCreateTemplateInvalidEnum(t *testing.T) {
	repo := &templateUseCasesFakeRepo{}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)
	createDTO := dtos.NewTemplateCreateDTO(dtos.TemplateCreateDTO{
		Name:         "name",
		Description:  "desc",
		Content:      "content",
		TemplateType: "bogus",
		Category:     "general",
	})

	_, err := uc.CreateTemplate(context.Background(), createDTO)
	var valueErr *value_objects.ValueError
	if !errors.As(err, &valueErr) {
		t.Fatalf("err = %v, want *value_objects.ValueError", err)
	}
	if valueErr.Msg != "'bogus' is not a valid TemplateType" {
		t.Fatalf("message = %q", valueErr.Msg)
	}
}

func TestTemplateUseCasesCreateTemplateValidationError(t *testing.T) {
	repo := &templateUseCasesFakeRepo{}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)
	createDTO := dtos.NewTemplateCreateDTO(dtos.TemplateCreateDTO{
		Name:         "name",
		Description:  "desc",
		Content:      "content",
		TemplateType: "task",
		Category:     "general",
		Variables:    []string{"bad name"},
	})

	_, err := uc.CreateTemplate(context.Background(), createDTO)
	var validationErr *exceptions.TemplateValidationError
	if !errors.As(err, &validationErr) {
		t.Fatalf("err = %v, want *exceptions.TemplateValidationError", err)
	}
	if validationErr.Msg != "Template validation failed" {
		t.Fatalf("message = %q", validationErr.Msg)
	}
	if len(validationErr.ValidationErrors) != 1 ||
		validationErr.ValidationErrors[0] != "Variable 'bad name' contains invalid characters" {
		t.Fatalf("validation errors = %v", validationErr.ValidationErrors)
	}
	if validationErr.TemplateID == nil || *validationErr.TemplateID == "" {
		t.Fatalf("template id must be set")
	}
}

// ---- get_template ------------------------------------------------------------

func TestTemplateUseCasesGetTemplate(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "name", value_objects.TemplatePriorityMedium)
	repo := &templateUseCasesFakeRepo{getByIDResult: template}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	resp, err := uc.GetTemplate(context.Background(), template.ID.Value)
	if err != nil {
		t.Fatalf("GetTemplate: %v", err)
	}
	if resp.ID != template.ID.Value || resp.Name != "name" || resp.Status != "active" {
		t.Fatalf("unexpected response: %+v", resp)
	}
}

func TestTemplateUseCasesGetTemplateNotFound(t *testing.T) {
	repo := &templateUseCasesFakeRepo{}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)
	id := value_objects.GenerateNewTemplateId().Value

	_, err := uc.GetTemplate(context.Background(), id)
	var notFound *exceptions.TemplateNotFoundError
	if !errors.As(err, &notFound) {
		t.Fatalf("err = %v, want *exceptions.TemplateNotFoundError", err)
	}
	want := "Template not found: " + id
	if notFound.Msg != want {
		t.Fatalf("message = %q, want %q", notFound.Msg, want)
	}
}

// ---- update_template ---------------------------------------------------------

func TestTemplateUseCasesUpdateTemplate(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "old", value_objects.TemplatePriorityMedium)
	repo := &templateUseCasesFakeRepo{getByIDResult: template}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	newName := "new"
	newContent := "new content"
	inactive := false
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("k", "v")
	updateDTO := &dtos.TemplateUpdateDTO{
		TemplateID: template.ID.Value,
		Name:       &newName,
		Content:    &newContent,
		Metadata:   metadata,
		IsActive:   &inactive,
	}

	resp, err := uc.UpdateTemplate(context.Background(), updateDTO)
	if err != nil {
		t.Fatalf("UpdateTemplate: %v", err)
	}
	if resp.Name != "new" || resp.Content != "new content" {
		t.Fatalf("unexpected fields: %+v", resp)
	}
	if resp.Version != 2 {
		t.Fatalf("version = %d, want 2 after content update", resp.Version)
	}
	if resp.Status != "inactive" || resp.IsActive {
		t.Fatalf("template must be deactivated: %+v", resp)
	}
	if v, _ := resp.Metadata.Get("k"); v != "v" {
		t.Fatalf("metadata not updated: %v", resp.Metadata.Keys())
	}
	if len(repo.saved) != 1 {
		t.Fatalf("save calls = %d, want 1", len(repo.saved))
	}
}

// ---- delete_template ---------------------------------------------------------

func TestTemplateUseCasesDeleteTemplate(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "name", value_objects.TemplatePriorityMedium)
	repo := &templateUseCasesFakeRepo{getByIDResult: template}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	ok, err := uc.DeleteTemplate(context.Background(), template.ID.Value)
	if err != nil {
		t.Fatalf("DeleteTemplate: %v", err)
	}
	if !ok {
		t.Fatalf("DeleteTemplate returned false")
	}
	if template.Status == nil || *template.Status != value_objects.TemplateStatusArchived {
		t.Fatalf("status = %v, want archived", template.Status)
	}
	if template.IsActive == nil || *template.IsActive {
		t.Fatalf("is_active must be false")
	}
	if len(repo.saved) != 1 {
		t.Fatalf("save calls = %d, want 1", len(repo.saved))
	}
}

// ---- list_templates ----------------------------------------------------------

func TestTemplateUseCasesListTemplates(t *testing.T) {
	template1 := templateUseCasesTestTemplate(t, "one", value_objects.TemplatePriorityLow)
	template2 := templateUseCasesTestTemplate(t, "two", value_objects.TemplatePriorityLow)
	repo := &templateUseCasesFakeRepo{listResult: []*entities.Template{template1, template2}, listTotal: 5}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	searchDTO := dtos.NewTemplateSearchDTO(dtos.TemplateSearchDTO{Limit: 2, Offset: 2})
	resp, err := uc.ListTemplates(context.Background(), searchDTO)
	if err != nil {
		t.Fatalf("ListTemplates: %v", err)
	}
	if len(resp.Templates) != 2 {
		t.Fatalf("templates = %d, want 2", len(resp.Templates))
	}
	if resp.TotalCount != 5 {
		t.Fatalf("total = %d, want 5", resp.TotalCount)
	}
	if resp.Page != 2 {
		t.Fatalf("page = %d, want 2", resp.Page)
	}
	if resp.PageSize != 2 {
		t.Fatalf("page_size = %d, want 2", resp.PageSize)
	}
	if !resp.HasNext || !resp.HasPrevious {
		t.Fatalf("has_next=%v has_previous=%v, want true/true", resp.HasNext, resp.HasPrevious)
	}
	if repo.listFilter == nil || repo.listFilter.Limit != 2 || repo.listFilter.Offset != 2 {
		t.Fatalf("filter not forwarded: %+v", repo.listFilter)
	}
}

func TestTemplateUseCasesListTemplatesZeroLimit(t *testing.T) {
	repo := &templateUseCasesFakeRepo{}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	_, err := uc.ListTemplates(context.Background(), &dtos.TemplateSearchDTO{Limit: 0})
	if !errors.Is(err, entities.ErrZeroDivision) {
		t.Fatalf("err = %v, want ErrZeroDivision", err)
	}
}

// ---- render_template ---------------------------------------------------------

func TestTemplateUseCasesRenderTemplate(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "name", value_objects.TemplatePriorityMedium)
	repo := &templateUseCasesFakeRepo{getByIDResult: template}
	generatedAt := time.Date(2024, 5, 1, 12, 30, 45, 0, time.UTC)
	engine := &templateUseCasesFakeEngine{result: &entities.TemplateResult{
		Content:          "rendered",
		TemplateID:       *template.ID,
		VariablesUsed:    map[string]any{"b": "2", "a": "1"},
		GeneratedAt:      generatedAt,
		GenerationTimeMs: 7,
		CacheHit:         true,
		OutputPath:       nil,
	}}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, engine, nil)

	variables := entities.NewOrderedMap[any]()
	variables.Set("b", "2")
	variables.Set("a", "1")
	renderDTO := dtos.NewTemplateRenderRequestDTO(dtos.TemplateRenderRequestDTO{
		TemplateID: template.ID.Value,
		Variables:  variables,
	})

	resp, err := uc.RenderTemplate(context.Background(), renderDTO)
	if err != nil {
		t.Fatalf("RenderTemplate: %v", err)
	}
	if resp.Content != "rendered" || resp.TemplateID != template.ID.Value {
		t.Fatalf("unexpected response: %+v", resp)
	}
	if resp.GenerationTimeMs != 7 || !resp.CacheHit {
		t.Fatalf("unexpected timing/cache: %+v", resp)
	}
	if resp.GeneratedAt != value_objects.IsoFormat(generatedAt) {
		t.Fatalf("generated_at = %q", resp.GeneratedAt)
	}
	if resp.OutputPath != nil {
		t.Fatalf("output_path = %v, want nil", resp.OutputPath)
	}
	if engine.calls != 1 {
		t.Fatalf("engine calls = %d, want 1", engine.calls)
	}
	if engine.got == nil || engine.got.TemplateID.Value != template.ID.Value {
		t.Fatalf("engine request not forwarded: %+v", engine.got)
	}
	if engine.got.TaskContext != nil {
		t.Fatalf("nil task_context must stay None, got %v", engine.got.TaskContext)
	}
	if engine.got.Variables["a"] != "1" || engine.got.Variables["b"] != "2" {
		t.Fatalf("variables not forwarded: %v", engine.got.Variables)
	}
	templateUseCasesRequireKeys(t, resp.VariablesUsed, []string{"a", "b"})
	if len(repo.savedUsage) != 1 {
		t.Fatalf("save_usage calls = %d, want 1", len(repo.savedUsage))
	}
	if repo.savedUsage[0].TemplateID.Value != template.ID.Value {
		t.Fatalf("usage template id = %q", repo.savedUsage[0].TemplateID.Value)
	}
}

func TestTemplateUseCasesRenderTemplateValidationError(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "name", value_objects.TemplatePriorityMedium)
	repo := &templateUseCasesFakeRepo{getByIDResult: template}
	engine := &templateUseCasesFakeEngine{}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, engine, nil)

	renderDTO := dtos.NewTemplateRenderRequestDTO(dtos.TemplateRenderRequestDTO{
		TemplateID: template.ID.Value,
		Variables:  entities.NewOrderedMap[any](),
	})

	_, err := uc.RenderTemplate(context.Background(), renderDTO)
	var renderErr *exceptions.TemplateRenderError
	if !errors.As(err, &renderErr) {
		t.Fatalf("err = %v, want *exceptions.TemplateRenderError", err)
	}
	if renderErr.Msg != "Template render request validation failed" {
		t.Fatalf("message = %q", renderErr.Msg)
	}
	errs, ok := renderErr.RenderContext["validation_errors"].([]string)
	if !ok || len(errs) != 1 || errs[0] != "Variables are required" {
		t.Fatalf("render context = %v", renderErr.RenderContext)
	}
	if engine.calls != 0 {
		t.Fatalf("engine must not be called, calls = %d", engine.calls)
	}
}

// ---- suggest_templates -------------------------------------------------------

func TestTemplateUseCasesSuggestTemplates(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "suggested", value_objects.TemplatePriorityHigh)
	repo := &templateUseCasesFakeRepo{
		listResult: []*entities.Template{template},
		listTotal:  1,
		usageStats: map[string]any{},
	}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	suggestionDTO := dtos.NewTemplateSuggestionRequestDTO(dtos.TemplateSuggestionRequestDTO{})
	suggestions, err := uc.SuggestTemplates(context.Background(), suggestionDTO)
	if err != nil {
		t.Fatalf("SuggestTemplates: %v", err)
	}
	if len(suggestions) != 1 {
		t.Fatalf("suggestions = %d, want 1", len(suggestions))
	}
	got := suggestions[0]
	if got.SuggestionScore != 45 {
		t.Fatalf("score = %v, want 45", got.SuggestionScore)
	}
	if got.SuggestionReason != "High priority template; Good option for this type of task" {
		t.Fatalf("reason = %q", got.SuggestionReason)
	}
	if got.TemplateID != template.ID.Value || got.Name != "suggested" ||
		got.TemplateType != "task" || got.Category != "general" || got.Priority != "high" {
		t.Fatalf("unexpected suggestion: %+v", got)
	}
	if repo.listFilter == nil || repo.listFilter.IsActive == nil || !*repo.listFilter.IsActive ||
		repo.listFilter.Limit != 1000 {
		t.Fatalf("active filter not forwarded: %+v", repo.listFilter)
	}
}

func TestTemplateUseCasesSuggestTemplatesSortAndLimit(t *testing.T) {
	high := templateUseCasesTestTemplate(t, "high", value_objects.TemplatePriorityHigh)
	low := templateUseCasesTestTemplate(t, "low", value_objects.TemplatePriorityLow)
	repo := &templateUseCasesFakeRepo{
		listResult: []*entities.Template{low, high},
		listTotal:  2,
		usageStats: map[string]any{},
	}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	suggestionDTO := dtos.NewTemplateSuggestionRequestDTO(dtos.TemplateSuggestionRequestDTO{Limit: 1})
	suggestions, err := uc.SuggestTemplates(context.Background(), suggestionDTO)
	if err != nil {
		t.Fatalf("SuggestTemplates: %v", err)
	}
	if len(suggestions) != 1 {
		t.Fatalf("suggestions = %d, want 1", len(suggestions))
	}
	if suggestions[0].Name != "high" {
		t.Fatalf("first suggestion = %q, want high (sorted by score desc)", suggestions[0].Name)
	}
}

// ---- validate_template -------------------------------------------------------

func TestTemplateUseCasesValidateTemplate(t *testing.T) {
	template := templateUseCasesTestTemplate(t, "name", value_objects.TemplatePriorityMedium)
	repo := &templateUseCasesFakeRepo{getByIDResult: template}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	resp, err := uc.ValidateTemplate(context.Background(), template.ID.Value)
	if err != nil {
		t.Fatalf("ValidateTemplate: %v", err)
	}
	if !resp.IsValid || len(resp.Errors) != 0 || len(resp.Warnings) != 0 {
		t.Fatalf("unexpected validation response: %+v", resp)
	}
	if resp.TemplateID == nil || *resp.TemplateID != template.ID.Value {
		t.Fatalf("template id = %v", resp.TemplateID)
	}

	template.Variables = []string{"bad name"}
	resp, err = uc.ValidateTemplate(context.Background(), template.ID.Value)
	if err != nil {
		t.Fatalf("ValidateTemplate (invalid): %v", err)
	}
	if resp.IsValid || len(resp.Errors) != 1 {
		t.Fatalf("expected one validation error: %+v", resp)
	}
}

// ---- get_template_analytics --------------------------------------------------

// Preserved Python quirk: TemplateAnalyticsDTO has no usage_by_project field, so the
// constructor raises TypeError after the repository call succeeds.
func TestTemplateUseCasesGetTemplateAnalyticsRaisesTypeError(t *testing.T) {
	repo := &templateUseCasesFakeRepo{analytics: map[string]any{
		"usage_count": 7,
	}}
	uc := NewTemplateUseCases(repo, &services.TemplateDomainService{}, nil, nil)

	templateID := ""
	resp, err := uc.GetTemplateAnalytics(context.Background(), &templateID)
	if resp != nil {
		t.Fatalf("resp = %+v, want nil", resp)
	}
	var typeErr *value_objects.TypeError
	if !errors.As(err, &typeErr) {
		t.Fatalf("err = %v (%T), want TypeError", err, err)
	}
	if err.Error() != "TemplateAnalyticsDTO.__init__() got an unexpected keyword argument 'usage_by_project'" {
		t.Fatalf("err = %q", err.Error())
	}
	if !repo.analyticsCall || repo.analyticsID == nil || *repo.analyticsID != "" {
		t.Fatalf("analytics id not forwarded: %v", repo.analyticsID)
	}
}

// ---- helpers -----------------------------------------------------------------

func TestTemplateUseCasesFloorDivAndLimitSlice(t *testing.T) {
	cases := []struct{ a, b, want int }{
		{4, 2, 2}, {5, 2, 2}, {-1, 2, -1}, {-5, 2, -3}, {5, -2, -3},
	}
	for _, c := range cases {
		if got := templateUseCasesFloorDiv(c.a, c.b); got != c.want {
			t.Fatalf("floorDiv(%d,%d) = %d, want %d", c.a, c.b, got, c.want)
		}
	}

	items := []*dtos.TemplateSuggestionDTO{{Name: "a"}, {Name: "b"}, {Name: "c"}}
	if got := templateUseCasesLimitSlice(items, 10); len(got) != 3 {
		t.Fatalf("len = %d, want 3", len(got))
	}
	if got := templateUseCasesLimitSlice(items, -1); len(got) != 2 || got[1].Name != "b" {
		t.Fatalf("negative limit slice = %v", got)
	}
	if got := templateUseCasesLimitSlice(items, -10); len(got) != 0 {
		t.Fatalf("over-negative limit slice = %v", got)
	}
}
