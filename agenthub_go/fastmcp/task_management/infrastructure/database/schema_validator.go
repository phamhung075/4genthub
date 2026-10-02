package database

// Database Schema Validator (Python
// task_management/infrastructure/database/schema_validator.py).
//
// SQLAlchemy model classes and class_mapper map to Tables' TableDef (TableDef.Model is the
// Python class name). Inspector.get_columns/get_foreign_keys are information_schema /
// pg_catalog queries. The Python schema-validation summary is an OrderedMap in key order.

import (
	"context"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// SchemaValidator validates Tables against the live schema.
type SchemaValidator struct {
	ctx    context.Context
	engine *Engine
	models []string
}

// NewSchemaValidator builds a validator over an engine.
func NewSchemaValidator(ctx context.Context, engine *Engine) *SchemaValidator {
	return &SchemaValidator{
		ctx:    ctx,
		engine: engine,
		models: schemaValidatorModelNames,
	}
}

var schemaValidatorModelNames = []string{
	"Project", "ProjectGitBranch", "Task", "TaskDependency", "Subtask", "TaskAssignee",
	"Agent", "Label", "TaskLabel", "Template", "GlobalContext", "ProjectContext",
	"BranchContext", "TaskContext", "ContextDelegation", "ContextInheritanceCache",
}

// ValidateAll mirrors validate_all.
func (v *SchemaValidator) ValidateAll() (*entities.OrderedMap[any], error) {
	tables, err := tableNames(v.ctx, v.engine.DB)
	if err != nil {
		return nil, err
	}
	existing := map[string]bool{}
	for _, t := range tables {
		existing[t] = true
	}
	issues := []any{}
	warnings := []any{}
	validated := []any{}
	for _, modelName := range v.models {
		def, ok := schemaValidatorTableByModel(modelName)
		if !ok {
			continue
		}
		modelIssues, modelWarnings := v.validateModel(def, existing)
		validated = append(validated, modelName)
		issues = append(issues, modelIssues...)
		warnings = append(warnings, modelWarnings...)
	}
	status := "PASS"
	if len(issues) > 0 {
		status = "FAIL"
	}
	summary := entities.NewOrderedMap[any]()
	summary.Set("total_models", len(v.models))
	summary.Set("issues_count", len(issues))
	summary.Set("warnings_count", len(warnings))
	summary.Set("status", status)
	summary.Set("issues", issues)
	summary.Set("warnings", warnings)
	summary.Set("validated_models", validated)
	return summary, nil
}

// validateModel validates one model against its table.
func (v *SchemaValidator) validateModel(def TableDef, existing map[string]bool) ([]any, []any) {
	issues := []any{}
	warnings := []any{}
	tableName := def.Name
	if !existing[tableName] {
		issues = append(issues, schemaValidatorIssue(def.Model, tableName, "", "missing_table",
			"Table '"+tableName+"' does not exist in database"))
		return issues, warnings
	}
	columns, err := introspectColumnTypes(v.ctx, v.engine.DB, tableName)
	if err != nil {
		issues = append(issues, schemaValidatorIssue(def.Model, "", "", "validation_error", err.Error()))
		return issues, warnings
	}
	dbColumns := map[string]string{}
	for _, c := range columns {
		dbColumns[c.Name] = c.Type
	}
	for _, mc := range def.Columns {
		dbType, ok := dbColumns[mc.Name]
		if !ok {
			issues = append(issues, schemaValidatorIssue(def.Model, tableName, mc.Name, "missing_column",
				"Column '"+mc.Name+"' defined in model but missing in database"))
			continue
		}
		if msg := schemaValidateColumnType(mc.SQLType, dbType); msg != "" {
			warnings = append(warnings, schemaValidatorIssue(def.Model, tableName, mc.Name, "type_mismatch", msg))
		}
	}
	for _, c := range columns {
		if !schemaValidatorHasColumn(def, c.Name) {
			warnings = append(warnings, schemaValidatorIssue(def.Model, tableName, c.Name, "extra_column",
				"Column '"+c.Name+"' exists in database but not in model"))
		}
	}
	dbFKs, err := introspectForeignKeys(v.ctx, v.engine.DB, tableName)
	if err != nil {
		issues = append(issues, schemaValidatorIssue(def.Model, "", "", "validation_error", err.Error()))
		return issues, warnings
	}
	fkSet := map[string]bool{}
	for _, c := range dbFKs {
		fkSet[c] = true
	}
	for _, mc := range def.Columns {
		if mc.ForeignKey == "" {
			continue
		}
		if !fkSet[mc.Name] {
			warnings = append(warnings, schemaValidatorIssue(def.Model, tableName, mc.Name, "missing_foreign_key",
				"Foreign key constraint on '"+mc.Name+"' defined in model but not in database"))
		}
	}
	return issues, warnings
}

func schemaValidatorIssue(model, table, column, typ, message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("model", model)
	if table != "" {
		m.Set("table", table)
	}
	if column != "" {
		m.Set("column", column)
	}
	m.Set("type", typ)
	m.Set("message", message)
	return m
}

func schemaValidatorTableByModel(name string) (TableDef, bool) {
	for _, t := range Tables {
		if t.Model == name {
			return t, true
		}
	}
	return TableDef{}, false
}

func schemaValidatorHasColumn(def TableDef, name string) bool {
	for _, c := range def.Columns {
		if c.Name == name {
			return true
		}
	}
	return false
}

// schemaValidateColumnType mirrors _validate_column_type; "" means compatible.
func schemaValidateColumnType(modelType, dbType string) string {
	modelNorm := schemaNormalizeType(modelType)
	dbNorm := schemaNormalizeType(dbType)
	compatible := [][2]string{
		{"UUID", "UUID"},
		{"VARCHAR", "VARCHAR"},
		{"TEXT", "TEXT"},
		{"INTEGER", "INTEGER"},
		{"BIGINT", "BIGINT"},
		{"BOOLEAN", "BOOLEAN"},
		{"TIMESTAMP", "TIMESTAMP"},
		{"JSON", "JSON"},
		{"JSONB", "JSONB"},
		{"UUID", "CHAR(36)"},
		{"TEXT", "VARCHAR"},
		{"TIMESTAMP", "DATETIME"},
		{"UUID", "VARCHAR"},
		{"VARCHAR", "UUID"},
	}
	for _, c := range compatible {
		if strings.HasPrefix(modelNorm, c[0]) && strings.HasPrefix(dbNorm, c[1]) {
			return ""
		}
		if strings.HasPrefix(modelNorm, c[1]) && strings.HasPrefix(dbNorm, c[0]) {
			return ""
		}
	}
	if modelNorm != dbNorm {
		return "Type mismatch: Model has " + modelType + ", Database has " + dbType
	}
	return ""
}

// schemaNormalizeType mirrors _normalize_type (upper-case, drop parameters, alias map).
func schemaNormalizeType(typeStr string) string {
	normalized := strings.ToUpper(typeStr)
	if i := strings.Index(normalized, "("); i >= 0 {
		normalized = normalized[:i]
	}
	aliases := [][2]string{
		{"CHAR", "VARCHAR"},
		{"CHARACTER", "VARCHAR"},
		{"CHARACTER VARYING", "VARCHAR"},
		{"INT", "INTEGER"},
		{"SMALLINT", "INTEGER"},
		{"SERIAL", "INTEGER"},
		{"BIGSERIAL", "BIGINT"},
		{"DOUBLE PRECISION", "FLOAT"},
		{"REAL", "FLOAT"},
		{"DATETIME", "TIMESTAMP"},
		{"TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP"},
		{"TIMESTAMP WITH TIME ZONE", "TIMESTAMP"},
	}
	for _, a := range aliases {
		if normalized == a[0] {
			normalized = a[1]
			break
		}
	}
	return normalized
}

// ValidateSchemaOnStartup mirrors validate_schema_on_startup; it returns whether validation
// passed (the Python logging around FAIL/warnings is dropped).
func ValidateSchemaOnStartup(ctx context.Context, engine *Engine) bool {
	validator := NewSchemaValidator(ctx, engine)
	results, err := validator.ValidateAll()
	if err != nil {
		return false
	}
	status, _ := results.Get("status")
	return status != "FAIL"
}
