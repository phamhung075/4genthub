// Row structs and table metadata for agent_management/infrastructure/database/models.py.
// The generated task_management database/models.go does not include these tables, so they
// are declared here in the model's own package and registered into the shared Tables
// registry (the base ORM repository resolves tables by name there).
package database

import (
	"time"

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// AgentTemplateORM is a row of agent_templates.
type AgentTemplateORM struct {
	ID           string    `db:"id"`
	Slug         string    `db:"slug"`
	Name         string    `db:"name"`
	Description  string    `db:"description"`
	Category     string    `db:"category"`
	Version      string    `db:"version"`
	SystemPrompt string    `db:"system_prompt"`
	Tools        string    `db:"tools"`
	Capabilities string    `db:"capabilities"`
	Rules        *string   `db:"rules"`
	OutputFormat *string   `db:"output_format"`
	MetadataJSON *string   `db:"metadata"`
	CreatedAt    time.Time `db:"created_at"`
	UpdatedAt    time.Time `db:"updated_at"`
}

// UserAgentInstanceORM is a row of user_agent_instances.
type UserAgentInstanceORM struct {
	ID                 string     `db:"id"`
	UserID             string     `db:"user_id"`
	TemplateID         string     `db:"template_id"`
	AgentName          string     `db:"agent_name"`
	IsCustomized       bool       `db:"is_customized"`
	IsEnabled          bool       `db:"is_enabled"`
	CustomizationNotes *string    `db:"customization_notes"`
	SystemPrompt       string     `db:"system_prompt"`
	Tools              string     `db:"tools"`
	Capabilities       string     `db:"capabilities"`
	Rules              *string    `db:"rules"`
	OutputFormat       *string    `db:"output_format"`
	MetadataJSON       *string    `db:"metadata"`
	Visibility         string     `db:"visibility"`
	ShareToken         *string    `db:"share_token"`
	ShareCreatedAt     *time.Time `db:"share_created_at"`
	OriginalCreatorID  *string    `db:"original_creator_id"`
	ImportedAt         *time.Time `db:"imported_at"`
	CreatedAt          time.Time  `db:"created_at"`
	UpdatedAt          time.Time  `db:"updated_at"`
	LastUsedAt         *time.Time `db:"last_used_at"`
	UsageCount         int64      `db:"usage_count"`
}

// agentManagementDatabaseTables mirrors the SQLAlchemy metadata of the agent models.
var agentManagementDatabaseTables = []taskdb.TableDef{
	{Name: "agent_templates", Model: "AgentTemplateORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true},
		{Name: "slug", Attr: "slug", GoField: "Slug", SQLType: "VARCHAR", Nullable: false},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false},
		{Name: "category", Attr: "category", GoField: "Category", SQLType: "VARCHAR", Nullable: false},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "VARCHAR", Nullable: false},
		{Name: "system_prompt", Attr: "system_prompt", GoField: "SystemPrompt", SQLType: "TEXT", Nullable: false},
		{Name: "tools", Attr: "tools", GoField: "Tools", SQLType: "TEXT", Nullable: false},
		{Name: "capabilities", Attr: "capabilities", GoField: "Capabilities", SQLType: "TEXT", Nullable: false},
		{Name: "rules", Attr: "rules", GoField: "Rules", SQLType: "TEXT", Nullable: true},
		{Name: "output_format", Attr: "output_format", GoField: "OutputFormat", SQLType: "TEXT", Nullable: true},
		{Name: "metadata", Attr: "metadata_json", GoField: "MetadataJSON", SQLType: "TEXT", Nullable: true},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false},
	}, DDL: []string{
		"CREATE TABLE agent_templates (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tslug VARCHAR(100) NOT NULL,\n" +
			"\tname VARCHAR(200) NOT NULL,\n" +
			"\tdescription TEXT NOT NULL,\n" +
			"\tcategory VARCHAR(100) NOT NULL,\n" +
			"\tversion VARCHAR(50) NOT NULL,\n" +
			"\tsystem_prompt TEXT NOT NULL,\n" +
			"\ttools TEXT NOT NULL,\n" +
			"\tcapabilities TEXT NOT NULL,\n" +
			"\trules TEXT,\n" +
			"\toutput_format TEXT,\n" +
			"\tmetadata TEXT,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL,\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL,\n" +
			"\tPRIMARY KEY (id)\n" +
			")",
		"CREATE UNIQUE INDEX ix_agent_templates_slug ON agent_templates (slug)",
		"CREATE INDEX ix_agent_templates_category ON agent_templates (category)",
		"CREATE INDEX ix_agent_templates_version ON agent_templates (version)",
		"CREATE INDEX ix_agent_templates_category_version ON agent_templates (category, version)",
	}},
	{Name: "user_agent_instances", Model: "UserAgentInstanceORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "UUID", Nullable: false},
		{Name: "template_id", Attr: "template_id", GoField: "TemplateID", SQLType: "UUID", Nullable: false},
		{Name: "agent_name", Attr: "agent_name", GoField: "AgentName", SQLType: "VARCHAR", Nullable: false},
		{Name: "is_customized", Attr: "is_customized", GoField: "IsCustomized", SQLType: "BOOLEAN", Nullable: false, Default: taskdb.DefaultBool, DefaultValue: "false"},
		{Name: "is_enabled", Attr: "is_enabled", GoField: "IsEnabled", SQLType: "BOOLEAN", Nullable: false, Default: taskdb.DefaultBool, DefaultValue: "true"},
		{Name: "customization_notes", Attr: "customization_notes", GoField: "CustomizationNotes", SQLType: "TEXT", Nullable: true},
		{Name: "system_prompt", Attr: "system_prompt", GoField: "SystemPrompt", SQLType: "TEXT", Nullable: false},
		{Name: "tools", Attr: "tools", GoField: "Tools", SQLType: "TEXT", Nullable: false},
		{Name: "capabilities", Attr: "capabilities", GoField: "Capabilities", SQLType: "TEXT", Nullable: false},
		{Name: "rules", Attr: "rules", GoField: "Rules", SQLType: "TEXT", Nullable: true},
		{Name: "output_format", Attr: "output_format", GoField: "OutputFormat", SQLType: "TEXT", Nullable: true},
		{Name: "metadata", Attr: "metadata_json", GoField: "MetadataJSON", SQLType: "TEXT", Nullable: true},
		{Name: "visibility", Attr: "visibility", GoField: "Visibility", SQLType: "VARCHAR", Nullable: false, Default: taskdb.DefaultString, DefaultValue: "\"private\""},
		{Name: "share_token", Attr: "share_token", GoField: "ShareToken", SQLType: "VARCHAR", Nullable: true},
		{Name: "share_created_at", Attr: "share_created_at", GoField: "ShareCreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: true},
		{Name: "original_creator_id", Attr: "original_creator_id", GoField: "OriginalCreatorID", SQLType: "UUID", Nullable: true},
		{Name: "imported_at", Attr: "imported_at", GoField: "ImportedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: true},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false},
		{Name: "last_used_at", Attr: "last_used_at", GoField: "LastUsedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: true},
		{Name: "usage_count", Attr: "usage_count", GoField: "UsageCount", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
	}, DDL: []string{
		"CREATE TABLE user_agent_instances (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id UUID NOT NULL,\n" +
			"\ttemplate_id UUID NOT NULL,\n" +
			"\tagent_name VARCHAR(200) NOT NULL,\n" +
			"\tis_customized BOOLEAN NOT NULL,\n" +
			"\tis_enabled BOOLEAN NOT NULL,\n" +
			"\tcustomization_notes TEXT,\n" +
			"\tsystem_prompt TEXT NOT NULL,\n" +
			"\ttools TEXT NOT NULL,\n" +
			"\tcapabilities TEXT NOT NULL,\n" +
			"\trules TEXT,\n" +
			"\toutput_format TEXT,\n" +
			"\tmetadata TEXT,\n" +
			"\tvisibility VARCHAR(50) NOT NULL,\n" +
			"\tshare_token VARCHAR(64),\n" +
			"\tshare_created_at TIMESTAMP WITH TIME ZONE,\n" +
			"\toriginal_creator_id UUID,\n" +
			"\timported_at TIMESTAMP WITH TIME ZONE,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL,\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL,\n" +
			"\tlast_used_at TIMESTAMP WITH TIME ZONE,\n" +
			"\tusage_count INTEGER NOT NULL,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_user_agent_instances_user_template UNIQUE (user_id, template_id)\n" +
			")",
		"CREATE UNIQUE INDEX ix_user_agent_instances_share_token ON user_agent_instances (share_token)",
		"CREATE INDEX ix_user_agent_instances_user_id ON user_agent_instances (user_id)",
		"CREATE INDEX ix_user_agent_instances_template_id ON user_agent_instances (template_id)",
		"CREATE INDEX ix_user_agent_instances_visibility ON user_agent_instances (visibility)",
		"CREATE INDEX ix_user_agent_instances_user_visibility ON user_agent_instances (user_id, visibility)",
		"CREATE INDEX ix_user_agent_instances_visibility_created ON user_agent_instances (visibility, created_at)",
		"CREATE INDEX ix_user_agent_instances_user_enabled ON user_agent_instances (user_id, is_enabled)",
	}},
}

func init() { taskdb.Tables = append(taskdb.Tables, agentManagementDatabaseTables...) }
