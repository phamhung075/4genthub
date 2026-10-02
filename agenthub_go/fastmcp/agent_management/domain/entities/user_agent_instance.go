package entities

import (
	"fmt"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

func now() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// UserAgentInstance is a user's personal, customizable instance of an agent template.
// Business rules: unique per (user, template); public visibility needs a share token and
// private visibility must not have one; usage_count never negative.
type UserAgentInstance struct {
	base.BaseTimestampEntity

	ID                *value_objects.UserAgentInstanceId
	UserID            *value_objects.UserId
	TemplateID        *value_objects.AgentTemplateId
	AgentName         string
	IsCustomized      bool
	IsEnabled         bool // controls visibility in the call_agent tools
	Configuration     *value_objects.AgentConfiguration
	Visibility        string // "private" or "public"
	ShareToken        *string
	OriginalCreatorID *value_objects.UserId // set when imported from another user
	UsageCount        int
	LastUsedAt        *time.Time
	Metadata          *tmentities.OrderedMap[any] // nil is Python's None
}

// DefaultUserAgentInstance has the dataclass defaults (enabled, private, empty
// metadata); set the fields and pass it to NewUserAgentInstance.
func DefaultUserAgentInstance() UserAgentInstance {
	return UserAgentInstance{IsEnabled: true, Visibility: "private", Metadata: tmentities.NewOrderedMap[any]()}
}

// NewUserAgentInstance initializes the timestamps and validates the business rules.
func NewUserAgentInstance(u UserAgentInstance) (*UserAgentInstance, error) {
	s := u
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// GetEntityID is the instance id or "unknown".
func (u *UserAgentInstance) GetEntityID() string {
	if u.ID != nil {
		return u.ID.String()
	}
	return "unknown"
}

// ValidateEntity checks the instance invariants.
func (u *UserAgentInstance) ValidateEntity() error {
	switch {
	case u.UserID == nil:
		return tmvo.ValueErrorf("UserAgentInstance must have a user_id")
	case u.TemplateID == nil:
		return tmvo.ValueErrorf("UserAgentInstance must have a template_id")
	case tmvo.PyStrip(u.AgentName) == "":
		return tmvo.ValueErrorf("UserAgentInstance agent_name cannot be empty")
	case u.Visibility != "private" && u.Visibility != "public":
		return tmvo.ValueErrorf("UserAgentInstance visibility must be 'private' or 'public', got '%s'", u.Visibility)
	}
	hasToken := u.ShareToken != nil && *u.ShareToken != ""
	switch {
	case u.Visibility == "public" && !hasToken:
		return tmvo.ValueErrorf("UserAgentInstance with visibility='public' must have a share_token")
	case u.Visibility == "private" && hasToken:
		return tmvo.ValueErrorf("UserAgentInstance with visibility='private' should not have a share_token")
	case u.Configuration == nil:
		return tmvo.ValueErrorf("UserAgentInstance must have a configuration")
	case u.UsageCount < 0:
		return tmvo.ValueErrorf("UserAgentInstance usage_count cannot be negative")
	}
	return nil
}

// CustomizeConfiguration replaces the configuration and marks the instance customized;
// non-empty notes are recorded in the metadata under "last_customization".
func (u *UserAgentInstance) CustomizeConfiguration(newConfiguration value_objects.AgentConfiguration, customizationNotes *string) error {
	// Python applies the configuration and the flag before touching the metadata, so a
	// failure on None metadata leaves those two changes in place.
	u.Configuration = &newConfiguration
	u.IsCustomized = true
	if customizationNotes == nil || *customizationNotes == "" {
		return nil
	}
	if u.Metadata == nil {
		return tmvo.TypeErrorf("'NoneType' object has no attribute 'copy'")
	}
	metadata := u.Metadata.Copy()
	last := tmentities.NewOrderedMap[any]()
	last.Set("timestamp", tmvo.IsoFormat(now()))
	last.Set("notes", *customizationNotes)
	metadata.Set("last_customization", last)
	u.Metadata = metadata
	return nil
}

// TrackUsage increments the usage count and sets last_used_at.
func (u *UserAgentInstance) TrackUsage() {
	u.UsageCount++
	t := now()
	u.LastUsedAt = &t
}

// GetCreatorDisplayName is the creator's email for an imported instance, otherwise
// "System Default".
func (u *UserAgentInstance) GetCreatorDisplayName(creatorEmail *string) string {
	if u.OriginalCreatorID != nil && creatorEmail != nil && *creatorEmail != "" {
		return *creatorEmail
	}
	return "System Default"
}

// GenerateShareToken sets a 64-character share token and makes the instance public.
func (u *UserAgentInstance) GenerateShareToken(token string) error {
	if utf8.RuneCountInString(token) != 64 {
		return tmvo.ValueErrorf("Share token must be exactly 64 characters")
	}
	u.ShareToken = &token
	u.Visibility = "public"
	return nil
}

// RevokeShareToken removes the share token and makes the instance private.
func (u *UserAgentInstance) RevokeShareToken() {
	u.ShareToken = nil
	u.Visibility = "private"
}

// IsPublic: public visibility and a share token.
func (u *UserAgentInstance) IsPublic() bool { return u.Visibility == "public" && u.ShareToken != nil }

// IsImported: the instance was imported from another user.
func (u *UserAgentInstance) IsImported() bool { return u.OriginalCreatorID != nil }

func truthyBool(data *tmentities.OrderedMap[any], key string, def bool) bool {
	if v, ok := data.Get(key); ok {
		return tmvo.PyTruthy(v)
	}
	return def
}

// UserAgentInstanceFromDict creates an instance from a dict (e.g. a database row).
func UserAgentInstanceFromDict(data *tmentities.OrderedMap[any]) (*UserAgentInstance, error) {
	u := UserAgentInstance{}
	var err error
	if u.ID, err = optionalID(data, "id", value_objects.NewUserAgentInstanceId); err != nil {
		return nil, err
	}
	if u.UserID, err = optionalID(data, "user_id", value_objects.NewUserId); err != nil {
		return nil, err
	}
	if u.TemplateID, err = optionalID(data, "template_id", value_objects.NewAgentTemplateId); err != nil {
		return nil, err
	}
	if u.OriginalCreatorID, err = optionalID(data, "original_creator_id", value_objects.NewUserId); err != nil {
		return nil, err
	}
	if u.Configuration, err = configurationField(data, "configuration", "Invalid configuration format"); err != nil {
		return nil, err
	}
	if u.LastUsedAt, err = optionalTime(data, "last_used_at"); err != nil {
		return nil, err
	}
	if u.CreatedAt, err = optionalTime(data, "created_at"); err != nil {
		return nil, err
	}
	if u.UpdatedAt, err = optionalTime(data, "updated_at"); err != nil {
		return nil, err
	}
	if u.AgentName, err = stringField(data, "agent_name", ""); err != nil {
		return nil, err
	}
	if u.Visibility, err = stringField(data, "visibility", "private"); err != nil {
		return nil, err
	}
	u.IsCustomized = truthyBool(data, "is_customized", false)
	u.IsEnabled = truthyBool(data, "is_enabled", true)
	if v, ok := data.Get("share_token"); ok && v != nil {
		s, isStr := v.(string)
		if !isStr {
			return nil, tmvo.TypeErrorf("share_token must be a string, got %s", pyTypeName(v))
		}
		u.ShareToken = &s
	}
	if v, ok := data.Get("usage_count"); ok {
		switch n := v.(type) {
		case int64:
			u.UsageCount = int(n)
		case int:
			u.UsageCount = n
		case float64:
			u.UsageCount = int(n)
		default:
			return nil, tmvo.TypeErrorf("usage_count must be an integer, got %s", pyTypeName(v))
		}
	}
	if u.Metadata, err = metadataField(data); err != nil {
		return nil, err
	}
	return NewUserAgentInstance(u)
}

// ToDict converts the instance for storage / serialization.
func (u *UserAgentInstance) ToDict() *tmentities.OrderedMap[any] {
	d := tmentities.NewOrderedMap[any]()
	d.Set("id", idOrNil(u.ID))
	d.Set("user_id", idOrNil(u.UserID))
	d.Set("template_id", idOrNil(u.TemplateID))
	d.Set("agent_name", u.AgentName)
	d.Set("is_customized", u.IsCustomized)
	d.Set("is_enabled", u.IsEnabled)
	if u.Configuration != nil {
		d.Set("configuration", u.Configuration.ToDict())
	} else {
		d.Set("configuration", tmentities.NewOrderedMap[any]())
	}
	d.Set("visibility", u.Visibility)
	if u.ShareToken != nil {
		d.Set("share_token", *u.ShareToken)
	} else {
		d.Set("share_token", nil)
	}
	d.Set("original_creator_id", idOrNil(u.OriginalCreatorID))
	d.Set("usage_count", int64(u.UsageCount))
	d.Set("last_used_at", isoOrNil(u.LastUsedAt))
	d.Set("metadata", metaOrNone(u.Metadata))
	d.Set("created_at", isoOrNil(u.CreatedAt))
	d.Set("updated_at", isoOrNil(u.UpdatedAt))
	return d
}

func (u *UserAgentInstance) String() string {
	str := func(id any) string {
		if id == nil {
			return "None"
		}
		return id.(string)
	}
	return fmt.Sprintf("UserAgentInstance(id=%s, user_id=%s, agent_name='%s', is_customized=%s, visibility='%s')",
		str(idOrNil(u.ID)), str(idOrNil(u.UserID)), u.AgentName, tmvo.PyStr(u.IsCustomized), u.Visibility)
}
