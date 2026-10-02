package utils

// Flexible Schema Generator for MCP Tools (Python interface/utils/flexible_schema_generator.py).
// FlexibleToolDecorator / create_flexible_mcp_tool_decorator are FastMCP-runtime specific and
// have no Go meaning, so only the schema generator is ported.

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// FlexibleArrayParameters is FLEXIBLE_ARRAY_PARAMETERS.
var FlexibleArrayParameters = map[string]bool{
	"insights_found":       true,
	"assignees":            true,
	"labels":               true,
	"tags":                 true,
	"dependencies":         true,
	"challenges_overcome":  true,
	"deliverables":         true,
	"next_recommendations": true,
	"skills_learned":       true,
}

// FlexibleSchemaGenerator generates flexible JSON schemas for MCP tools.
type FlexibleSchemaGenerator struct{}

// CreateFlexibleSchemaForParameter mirrors create_flexible_schema_for_parameter.
func (FlexibleSchemaGenerator) CreateFlexibleSchemaForParameter(paramName string, originalSchema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if !FlexibleArrayParameters[paramName] {
		return originalSchema
	}
	if originalSchema.Has("anyOf") {
		return (FlexibleSchemaGenerator{}).enhanceExistingUnionSchema(originalSchema)
	}
	return (FlexibleSchemaGenerator{}).createFlexibleArraySchema(paramName, originalSchema)
}

func (FlexibleSchemaGenerator) createFlexibleArraySchema(paramName string, originalSchema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	description := "Array parameter for " + paramName
	if v, ok := originalSchema.Get("description"); ok {
		description = pyString(v)
	}

	option1 := entities.NewOrderedMap[any]()
	option1.Set("type", "array")
	items := entities.NewOrderedMap[any]()
	items.Set("type", "string")
	option1.Set("items", items)
	option1.Set("description", "Array of strings")

	option2 := entities.NewOrderedMap[any]()
	option2.Set("type", "string")
	option2.Set("description", `JSON string representation of array (e.g., '["item1", "item2"]')`)
	option2.Set("pattern", `^\s*\[.*\]\s*$`)

	option3 := entities.NewOrderedMap[any]()
	option3.Set("type", "string")
	option3.Set("description", "Comma-separated string (e.g., 'item1, item2, item3')")
	option3.Set("pattern", `^[^[\]]*$`)

	option4 := entities.NewOrderedMap[any]()
	option4.Set("type", "string")
	option4.Set("description", "Single string value (will be converted to single-item array)")

	flexibleSchema := entities.NewOrderedMap[any]()
	flexibleSchema.Set("anyOf", []any{option1, option2, option3, option4})
	flexibleSchema.Set("description", description+". Accepts: array of strings, JSON string array, comma-separated string, or single string.")

	for _, key := range originalSchema.KeysAny() {
		if key != "type" && key != "items" && key != "anyOf" && key != "description" {
			flexibleSchema.Set(key, originalSchema.GetAny(key))
		}
	}

	return flexibleSchema
}

func (FlexibleSchemaGenerator) enhanceExistingUnionSchema(schema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	var anyOf []any
	if v, ok := schema.Get("anyOf"); ok {
		if list, ok := v.([]any); ok {
			anyOf = list
		}
	}

	hasArray := false
	hasString := false
	for _, option := range anyOf {
		if om, ok := option.(*entities.OrderedMap[any]); ok {
			if t, ok := om.Get("type"); ok {
				if pyString(t) == "array" {
					hasArray = true
				}
				if pyString(t) == "string" {
					hasString = true
				}
			}
		}
	}

	if hasArray && hasString {
		return schema
	}

	enhancedAnyOf := append([]any{}, anyOf...)

	if !hasArray {
		opt := entities.NewOrderedMap[any]()
		opt.Set("type", "array")
		items := entities.NewOrderedMap[any]()
		items.Set("type", "string")
		opt.Set("items", items)
		opt.Set("description", "Array of strings")
		enhancedAnyOf = append(enhancedAnyOf, opt)
	}

	if !hasString {
		opt := entities.NewOrderedMap[any]()
		opt.Set("type", "string")
		opt.Set("description", "JSON string representation of array or comma-separated string")
		enhancedAnyOf = append(enhancedAnyOf, opt)
	}

	enhancedSchema := schema.Copy()
	enhancedSchema.Set("anyOf", enhancedAnyOf)
	return enhancedSchema
}

// ApplyFlexibleSchemasToToolSchema mirrors apply_flexible_schemas_to_tool_schema.
func (FlexibleSchemaGenerator) ApplyFlexibleSchemasToToolSchema(toolSchema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if !toolSchema.Has("properties") {
		return toolSchema
	}

	enhancedSchema := toolSchema.Copy()
	enhancedProperties := entities.NewOrderedMap[any]()

	propsAny, _ := toolSchema.Get("properties")
	props, ok := propsAny.(*entities.OrderedMap[any])
	if !ok {
		enhancedSchema.Set("properties", enhancedProperties)
		return enhancedSchema
	}

	for _, paramName := range props.KeysAny() {
		paramSchemaAny := props.GetAny(paramName)
		if FlexibleArrayParameters[paramName] {
			if paramSchema, ok := paramSchemaAny.(*entities.OrderedMap[any]); ok {
				enhancedProperties.Set(paramName, (FlexibleSchemaGenerator{}).CreateFlexibleSchemaForParameter(paramName, paramSchema))
				continue
			}
		}
		enhancedProperties.Set(paramName, paramSchemaAny)
	}

	enhancedSchema.Set("properties", enhancedProperties)
	return enhancedSchema
}

// pyString mirrors str(v) for the values used here.
func pyString(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}
