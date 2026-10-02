package rest

import (
	"context"
	"errors"
	"testing"
	"time"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
)

type fakeFacade struct {
	templates   []*entities.AgentTemplate
	instances   []*entities.UserAgentInstance
	marketplace []*entities.UserAgentInstance
	shared      *entities.UserAgentInstance
}

func (f *fakeFacade) ListAvailableTemplates(context.Context) ([]*entities.AgentTemplate, error) {
	return f.templates, nil
}
func (f *fakeFacade) GetTemplateBySlug(_ context.Context, slug string) (*entities.AgentTemplate, error) {
	for _, t := range f.templates {
		if t.Slug == slug {
			return t, nil
		}
	}
	return nil, nil
}
func (f *fakeFacade) GetTemplateByID(_ context.Context, id string) (*entities.AgentTemplate, error) {
	for _, t := range f.templates {
		if t.ID.Value == id {
			return t, nil
		}
	}
	return nil, nil
}
func (f *fakeFacade) GetUserInstances(context.Context, value_objects.UserId) ([]*entities.UserAgentInstance, error) {
	return f.instances, nil
}
func (f *fakeFacade) GetOrCreateInstance(context.Context, value_objects.UserId, string) (*entities.UserAgentInstance, error) {
	return f.instances[0], nil
}
func (f *fakeFacade) BulkCreateInstances(context.Context, value_objects.UserId, []string) ([]*entities.UserAgentInstance, error) {
	return f.instances, nil
}
func (f *fakeFacade) UpdateInstance(context.Context, value_objects.UserId, string, *string, *bool, *string, []string, *tmentities.OrderedMap[any], []string, *string, *string) (*entities.UserAgentInstance, error) {
	return f.instances[0], nil
}
func (f *fakeFacade) DeleteInstance(context.Context, value_objects.UserId, string) (bool, error) {
	return true, nil
}
func (f *fakeFacade) UpdateConfiguration(context.Context, value_objects.UserId, string, *string, []string, *tmentities.OrderedMap[any], []string, *string) (*entities.UserAgentInstance, error) {
	return f.instances[0], nil
}
func (f *fakeFacade) ResetConfiguration(context.Context, value_objects.UserId, string) (*entities.UserAgentInstance, error) {
	return f.instances[0], nil
}
func (f *fakeFacade) ShareAgent(context.Context, value_objects.UserId, string) (*string, error) {
	tok := "token"
	return &tok, nil
}
func (f *fakeFacade) UnshareAgent(context.Context, value_objects.UserId, string) (bool, error) {
	return true, nil
}
func (f *fakeFacade) ImportAgent(context.Context, string, value_objects.UserId, string) (*entities.UserAgentInstance, error) {
	return f.instances[0], nil
}
func (f *fakeFacade) GetMarketplaceAgents(context.Context, int, int) ([]*entities.UserAgentInstance, error) {
	return f.marketplace, nil
}
func (f *fakeFacade) GetSharedAgentPreview(context.Context, string) (*entities.UserAgentInstance, error) {
	return f.shared, nil
}

func testUser() *authdomain.User {
	id := "11111111-1111-1111-1111-111111111111"
	return &authdomain.User{ID: &id, Email: "dev@example.com"}
}

func testInstance(t *testing.T, name string, usage int, lastUsed *time.Time, rules []string) *entities.UserAgentInstance {
	t.Helper()
	id, err := value_objects.NewUserAgentInstanceId("22222222-2222-2222-2222-222222222222")
	if err != nil {
		t.Fatal(err)
	}
	uid, err := value_objects.NewUserId("11111111-1111-1111-1111-111111111111")
	if err != nil {
		t.Fatal(err)
	}
	tid, err := value_objects.NewAgentTemplateId("33333333-3333-3333-3333-333333333333")
	if err != nil {
		t.Fatal(err)
	}
	created := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	return &entities.UserAgentInstance{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &created},
		ID:                  &id,
		UserID:              &uid,
		TemplateID:          &tid,
		AgentName:           name,
		IsEnabled:           true,
		Visibility:          "private",
		UsageCount:          usage,
		LastUsedAt:          lastUsed,
		Configuration: &value_objects.AgentConfiguration{
			SystemPrompt: "prompt",
			Tools:        []string{"read"},
			Capabilities: tmentities.NewOrderedMap[any](),
			Rules:        rules,
		},
	}
}

func TestGetUserUsageStats(t *testing.T) {
	earlier := time.Date(2024, 2, 1, 0, 0, 0, 0, time.UTC)
	later := time.Date(2024, 3, 1, 0, 0, 0, 0, time.UTC)
	f := &fakeFacade{instances: []*entities.UserAgentInstance{
		testInstance(t, "zero-agent", 0, &earlier, nil),
		testInstance(t, "busy-agent", 5, &later, []string{"r1"}),
	}}
	resp, err := GetUserUsageStats(context.Background(), testUser(), f)
	if err != nil {
		t.Fatal(err)
	}
	st := resp.UserStats
	if st.TotalCalls != 5 || st.UniqueAgents != 2 {
		t.Fatalf("total=%d unique=%d", st.TotalCalls, st.UniqueAgents)
	}
	if st.MostUsedAgent == nil || *st.MostUsedAgent != "busy-agent" {
		t.Fatalf("most_used=%v", st.MostUsedAgent)
	}
	if st.LastActivity == nil || !st.LastActivity.Equal(later) {
		t.Fatalf("last_activity=%v", st.LastActivity)
	}
	if v, _ := st.UsageByAgent.Get("busy-agent"); v != 5 {
		t.Fatalf("usage_by_agent busy=%v", v)
	}
	if keys := st.UsageByAgent.Keys(); len(keys) != 2 || keys[0] != "zero-agent" {
		t.Fatalf("usage_by_agent keys=%v", keys)
	}
}

func TestInstanceResponseRulesNil(t *testing.T) {
	inst := testInstance(t, "coding-agent", 0, nil, nil)
	resp := instanceResponse(inst)
	if resp.Rules != nil {
		t.Fatalf("empty rules should be nil, got %v", resp.Rules)
	}
	if resp.Capabilities == nil {
		t.Fatal("capabilities should default to empty dict, not nil")
	}
	if resp.Tools == nil {
		t.Fatal("tools should be a non-nil empty slice")
	}
	if resp.IsReadOnly {
		t.Fatal("owner instance must not be read-only")
	}
}

func TestBrowseMarketplaceValidation(t *testing.T) {
	f := &fakeFacade{}
	_, err := BrowseMarketplace(context.Background(), nil, nil, nil, 0, 50, f)
	var he *auth.HTTPException
	if !errors.As(err, &he) || he.StatusCode != 400 || he.Detail != "Page number must be >= 1" {
		t.Fatalf("page<1 err=%v", err)
	}
	_, err = BrowseMarketplace(context.Background(), nil, nil, nil, 1, 101, f)
	if !errors.As(err, &he) || he.StatusCode != 400 || he.Detail != "Page size must be between 1 and 100" {
		t.Fatalf("page_size>100 err=%v", err)
	}
}

func TestListTemplates(t *testing.T) {
	created := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	tid, err := value_objects.NewAgentTemplateId("44444444-4444-4444-4444-444444444444")
	if err != nil {
		t.Fatal(err)
	}
	tmpl := &entities.AgentTemplate{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &created},
		ID:                  &tid, Slug: "coding-agent", Name: "Coding Agent", Description: "d",
		Category: "development", Version: "1.0.0",
		DefaultConfiguration: &value_objects.AgentConfiguration{
			SystemPrompt: "p", Tools: []string{"read", "write"},
			Capabilities: tmentities.NewOrderedMap[any](),
		},
		Metadata: tmentities.NewOrderedMap[any](),
	}
	resp, err := ListTemplates(context.Background(), testUser(), &fakeFacade{templates: []*entities.AgentTemplate{tmpl}})
	if err != nil {
		t.Fatal(err)
	}
	if !resp.Success || resp.Count != 1 || resp.Templates[0].Slug != "coding-agent" {
		t.Fatalf("resp=%+v", resp)
	}
	if len(resp.Templates[0].Tools) != 2 || resp.Templates[0].Rules != nil {
		t.Fatalf("tools/rules=%v/%v", resp.Templates[0].Tools, resp.Templates[0].Rules)
	}
}
