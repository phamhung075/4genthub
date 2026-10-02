package services

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"fmt"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	"agenthub/fastmcp/agent_management/domain/repositories"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"unicode/utf8"
)

// NewShareToken is secrets.token_urlsafe(48)[:64]: 64 URL-safe random characters.
func NewShareToken() string {
	b := make([]byte, 48)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return base64.RawURLEncoding.EncodeToString(b)
}

// AgentSharingService handles share tokens, importing shared agents and name collisions.
type AgentSharingService struct {
	InstanceRepository repositories.UserAgentInstanceRepository
	TemplateRepository repositories.AgentTemplateRepository
	// ShareToken generates share tokens (default NewShareToken); injectable for tests.
	ShareToken func() string
}

func NewAgentSharingService(instances repositories.UserAgentInstanceRepository, templates repositories.AgentTemplateRepository) *AgentSharingService {
	return &AgentSharingService{InstanceRepository: instances, TemplateRepository: templates, ShareToken: NewShareToken}
}

// GenerateShareToken makes the owner's instance public and returns the new token; ok is
// false when the instance is not found or not owned by the user.
func (s *AgentSharingService) GenerateShareToken(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId) (string, bool, error) {
	instance, err := getAndVerifyOwnership(ctx, s.InstanceRepository, instanceID, userID)
	if err != nil || instance == nil {
		return "", false, err
	}
	token := s.ShareToken()
	if err := instance.GenerateShareToken(token); err != nil {
		return "", false, err
	}
	if _, err := s.InstanceRepository.Save(ctx, instance); err != nil {
		return "", false, err
	}
	return token, true, nil
}

// RevokeShareToken makes the owner's instance private; false when not found / not owned.
func (s *AgentSharingService) RevokeShareToken(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId) (bool, error) {
	instance, err := getAndVerifyOwnership(ctx, s.InstanceRepository, instanceID, userID)
	if err != nil || instance == nil {
		return false, err
	}
	instance.RevokeShareToken()
	if _, err := s.InstanceRepository.Save(ctx, instance); err != nil {
		return false, err
	}
	return true, nil
}

// ImportAgent copies a shared instance (found by its 64-character token) into the
// importer's account as a public instance with its own share token. It returns nil when
// the token matches no public instance or the importer already has an instance for the
// template. creatorEmail is used for name-collision attribution.
func (s *AgentSharingService) ImportAgent(ctx context.Context, shareToken string, importerUserID value_objects.UserId, creatorEmail *string) (*entities.UserAgentInstance, error) {
	if utf8.RuneCountInString(shareToken) != 64 {
		return nil, tmvo.ValueErrorf("Invalid share token")
	}
	source, err := s.InstanceRepository.FindByShareToken(ctx, shareToken)
	if err != nil || source == nil || !source.IsPublic() {
		return nil, err
	}
	existing, err := s.InstanceRepository.FindByUserAndTemplate(ctx, importerUserID, *source.TemplateID)
	if err != nil || existing != nil {
		return nil, err
	}
	finalName, err := s.resolveNameCollision(ctx, source.AgentName, importerUserID, creatorEmail)
	if err != nil {
		return nil, err
	}
	newToken := s.ShareToken()

	id := value_objects.GenerateNewUserAgentInstanceId()
	metadata := tmentities.NewOrderedMap[any]()
	metadata.Set("imported_from", source.ID.String())
	metadata.Set("imported_via_token", shareToken)
	metadata.Set("original_agent_name", source.AgentName)
	metadata.Set("is_imported", true)
	metadata.Set("source_instance_id", source.ID.String())
	metadata.Set("source_share_token", shareToken)

	imported := entities.DefaultUserAgentInstance()
	imported.ID = &id
	imported.UserID = &importerUserID
	imported.TemplateID = source.TemplateID
	imported.AgentName = finalName
	imported.IsCustomized = source.IsCustomized
	imported.Configuration = source.Configuration
	imported.Visibility = "public"
	imported.ShareToken = &newToken
	imported.OriginalCreatorID = source.UserID
	imported.Metadata = metadata
	created, err := entities.NewUserAgentInstance(imported)
	if err != nil {
		return nil, err
	}
	return s.InstanceRepository.Save(ctx, created)
}

// resolveNameCollision returns baseName when unused, else "<name> - created by <email>"
// (or "- imported"), numbered "(2)", "(3)", ... while that is taken too.
func (s *AgentSharingService) resolveNameCollision(ctx context.Context, baseName string, importerUserID value_objects.UserId, creatorEmail *string) (string, error) {
	count, err := s.InstanceRepository.CountByAgentNameForUser(ctx, importerUserID, baseName)
	if err != nil || count == 0 {
		return baseName, err
	}
	attribution := "- imported"
	if creatorEmail != nil && *creatorEmail != "" {
		attribution = "- created by " + *creatorEmail
	}
	candidate := baseName + " " + attribution
	if count, err = s.InstanceRepository.CountByAgentNameForUser(ctx, importerUserID, candidate); err != nil || count == 0 {
		return candidate, err
	}
	for counter := 2; ; counter++ {
		numbered := fmt.Sprintf("%s (%d)", candidate, counter)
		if count, err = s.InstanceRepository.CountByAgentNameForUser(ctx, importerUserID, numbered); err != nil {
			return "", err
		}
		if count == 0 {
			return numbered, nil
		}
	}
}

// GetPublicInstances lists shared instances for the marketplace: limit 1..100, offset
// >= 0, empty orderBy means CREATED_DESC; only truly public instances are returned.
func (s *AgentSharingService) GetPublicInstances(ctx context.Context, limit, offset int, orderBy enums.InstanceOrdering) ([]*entities.UserAgentInstance, error) {
	if orderBy == "" {
		orderBy = enums.InstanceOrderingCreatedDesc
	}
	if limit < 1 || limit > 100 {
		return nil, tmvo.ValueErrorf("Limit must be between 1 and 100, got %d", limit)
	}
	if offset < 0 {
		return nil, tmvo.ValueErrorf("Offset must be non-negative, got %d", offset)
	}
	instances, err := s.InstanceRepository.FindPublicInstances(ctx, limit, offset, orderBy)
	if err != nil {
		return nil, err
	}
	out := []*entities.UserAgentInstance{}
	for _, inst := range instances {
		if inst.IsPublic() {
			out = append(out, inst)
		}
	}
	return out, nil
}
