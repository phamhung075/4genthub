// Package utilities ports fastmcp/utilities.
package utilities

import (
	"sort"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Exported symbols mirror Python's __all__:
//   HTTPRoute, ParameterInfo, RequestBodyInfo, ResponseInfo, HttpMethod,
//   ParameterLocation, JsonSchema, ParseOpenAPIToHTTPRoutes.

// HttpMethod is Python's Literal["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD","TRACE"].
type HttpMethod string

// ParameterLocation is Python's Literal["path","query","header","cookie"].
type ParameterLocation string

// JsonSchema is the Python dict[str, Any] used for JSON schemas.
//
// The task note said "JsonSchema = map[string]any", but a plain Go map cannot preserve the
// Python dict key iteration order that generate_example_from_schema,
// format_description_with_responses and ReplaceRefWithDefs depend on. This package already
// represents Python dicts as entities.OrderedMap[any] (see json_schema.go), so the exported
// alias points at the same insertion-ordered type.
type JsonSchema = entities.OrderedMap[any]

// HttpMethod values.
const (
	HttpMethodGET     HttpMethod = "GET"
	HttpMethodPOST    HttpMethod = "POST"
	HttpMethodPUT     HttpMethod = "PUT"
	HttpMethodDELETE  HttpMethod = "DELETE"
	HttpMethodPATCH   HttpMethod = "PATCH"
	HttpMethodOPTIONS HttpMethod = "OPTIONS"
	HttpMethodHEAD    HttpMethod = "HEAD"
	HttpMethodTRACE   HttpMethod = "TRACE"
)

// ParameterLocation values.
const (
	ParameterLocationPath   ParameterLocation = "path"
	ParameterLocationQuery  ParameterLocation = "query"
	ParameterLocationHeader ParameterLocation = "header"
	ParameterLocationCookie ParameterLocation = "cookie"
)

// ParameterInfo mirrors ParameterInfo. The Python field is `schema_` with alias `schema`.
type ParameterInfo struct {
	Name        string
	Location    ParameterLocation
	Required    bool
	Schema      *JsonSchema `json:"schema"`
	Description *string
}

// RequestBodyInfo mirrors RequestBodyInfo (content_schema is dict[str, JsonSchema]).
type RequestBodyInfo struct {
	Required      bool
	ContentSchema *entities.OrderedMap[*JsonSchema]
	Description   *string
}

// ResponseInfo mirrors ResponseInfo.
type ResponseInfo struct {
	Description   *string
	ContentSchema *entities.OrderedMap[*JsonSchema]
}

// HTTPRoute mirrors HTTPRoute in field order. Nil pointers/slices represent Python None.
type HTTPRoute struct {
	Path              string
	Method            HttpMethod
	OperationID       *string
	Summary           *string
	Description       *string
	Tags              []string
	Parameters        []*ParameterInfo
	RequestBody       *RequestBodyInfo
	Responses         *entities.OrderedMap[*ResponseInfo]
	SchemaDefinitions *entities.OrderedMap[*JsonSchema]
}

// --- Python-quirk helpers -------------------------------------------------------------

// oaTruthy is bool(v) for the value shapes used here. Unlike value_objects.PyTruthy it
// treats a *string pointer to "" as falsy (Python "" is falsy; the Go pointer is only a
// stand-in for "optional string").
func oaTruthy(v any) bool {
	if s, ok := v.(*string); ok {
		return s != nil && *s != ""
	}
	return value_objects.PyTruthy(v)
}

// oaSchemaOrNil returns v when it is a raw schema dict, else nil.
func oaSchemaOrNil(v any) *JsonSchema {
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return m
	}
	return nil
}

// oaGet is m.get(key) without the presence flag (nil when absent).
func oaGet(m *entities.OrderedMap[any], key string) any {
	v, _ := m.Get(key)
	return v
}

// oaOptString is getattr(m, key) for an optional str field (None -> nil).
func oaOptString(m *entities.OrderedMap[any], key string) *string {
	v, ok := m.Get(key)
	if !ok || v == nil {
		return nil
	}
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

// oaBool is getattr(m, key) coerced to bool (missing/None -> false).
func oaBool(m *entities.OrderedMap[any], key string) bool {
	return oaTruthy(oaGet(m, key))
}

// oaList is m.get(key, []) restricted to Python lists.
func oaList(m *entities.OrderedMap[any], key string) []any {
	v, ok := m.Get(key)
	if !ok {
		return nil
	}
	if list, ok := v.([]any); ok {
		return list
	}
	return nil
}

// oaStringList is `getattr(operation, "tags", []) or []`.
func oaStringList(m *entities.OrderedMap[any], key string) []string {
	out := []string{}
	list := oaList(m, key)
	for _, e := range list {
		if s, ok := e.(string); ok {
			out = append(out, s)
		} else {
			out = append(out, value_objects.PyStr(e))
		}
	}
	return out
}

// oaContainsString is `needle in haystack` for a list that may hold non-strings.
func oaContainsString(list []any, needle string) bool {
	for _, v := range list {
		if s, ok := v.(string); ok && s == needle {
			return true
		}
	}
	return false
}

// oaDescriptionOr is `description or fallback`.
func oaDescriptionOr(desc *string, fallback string) string {
	if desc == nil || *desc == "" {
		return fallback
	}
	return *desc
}

// oaErrorText renders an optional message the way an f-string renders None.
func oaErrorText(msg *string) string {
	if msg == nil {
		return "None"
	}
	return *msg
}

// oaFirstMediaType is `"application/json" if ... else next(iter(content_schema), None)`.
func oaFirstMediaType(content *entities.OrderedMap[*JsonSchema]) *string {
	if content == nil || content.Len() == 0 {
		return nil
	}
	if content.Has("application/json") {
		mt := "application/json"
		return &mt
	}
	keys := content.Keys()
	return &keys[0]
}

func oaIsDigits(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

// --- Pure functions ------------------------------------------------------------------

// CleanSchemaForDisplay mirrors clean_schema_for_display, including its Python bug: when
// `schema` is a non-empty dict the function builds a `cleaned` copy and then falls off the
// end of the function without a return statement, so the result is None. Only the falsy /
// non-dict early return is observable. The body is kept literal to document the intent.
func CleanSchemaForDisplay(schema *JsonSchema) *JsonSchema {
	if schema == nil || schema.Len() == 0 {
		return schema
	}

	cleaned := schema.Copy()
	for _, field := range []string{
		"allOf", "anyOf", "oneOf", "not", "nullable", "discriminator", "readOnly",
		"writeOnly", "deprecated", "xml", "externalDocs",
	} {
		cleaned.Delete(field)
	}

	if propsVal, ok := cleaned.Get("properties"); ok {
		if props, isMap := propsVal.(*JsonSchema); isMap {
			newProps := entities.NewOrderedMap[any]()
			for _, k := range props.Keys() {
				v, _ := props.Get(k)
				newProps.Set(k, oaCleanValue(v))
			}
			cleaned.Set("properties", newProps)
			if newProps.Len() == 0 {
				cleaned.Delete("properties")
			}
		}
	}

	if itemsVal, ok := cleaned.Get("items"); ok {
		newItems := oaCleanValue(itemsVal)
		cleaned.Set("items", newItems)
		if !oaTruthy(newItems) {
			cleaned.Delete("items")
		}
	}

	if apVal, ok := cleaned.Get("additionalProperties"); ok {
		if ap, isMap := apVal.(*JsonSchema); isMap {
			cleaned.Set("additionalProperties", oaCleanValue(ap))
		}
		// `elif cleaned["additionalProperties"] is True: pass`
	}

	// Python has no `return cleaned` here; the function implicitly returns None.
	return nil
}

// oaCleanValue is clean_schema_for_display applied to an arbitrary schema value: non-dict
// values hit the early `return schema`, dict values go through the (buggy) recursion.
func oaCleanValue(v any) any {
	if m, ok := v.(*JsonSchema); ok {
		return CleanSchemaForDisplay(m)
	}
	return v
}

// GenerateExampleFromSchema mirrors generate_example_from_schema.
func GenerateExampleFromSchema(schema *JsonSchema) any {
	if schema == nil || schema.Len() == 0 {
		return "unknown"
	}
	if v, ok := schema.Get("default"); ok {
		return v
	}
	if enumVal, ok := schema.Get("enum"); ok {
		if list, isList := enumVal.([]any); isList && len(list) > 0 {
			return list[0]
		}
	}
	if examplesVal, ok := schema.Get("examples"); ok {
		if list, isList := examplesVal.([]any); isList && len(list) > 0 {
			return list[0]
		}
	}
	if v, ok := schema.Get("example"); ok {
		return v
	}

	schemaType, _ := oaGet(schema, "type").(string)
	switch schemaType {
	case "object":
		result := entities.NewOrderedMap[any]()
		if props, ok := oaGet(schema, "properties").(*JsonSchema); ok {
			requiredList := oaList(schema, "required")
			keys := props.Keys()
			if len(keys) > 3 {
				keys = keys[:3]
			}
			for _, propName := range keys {
				pv, _ := props.Get(propName)
				result.Set(propName, GenerateExampleFromSchema(oaSchemaOrNil(pv)))
			}
			// Python iterates a set here, whose order is unspecified; we use the
			// declaration order of `required`.
			for _, reqAny := range requiredList {
				reqProp, ok := reqAny.(string)
				if !ok {
					continue
				}
				if result.Has(reqProp) {
					continue
				}
				pv, present := props.Get(reqProp)
				if !present {
					continue
				}
				result.Set(reqProp, GenerateExampleFromSchema(oaSchemaOrNil(pv)))
			}
		}
		if result.Len() > 0 {
			return result
		}
		fallback := entities.NewOrderedMap[any]()
		fallback.Set("key", "value")
		return fallback
	case "array":
		if items, ok := oaGet(schema, "items").(*JsonSchema); ok {
			itemExample := GenerateExampleFromSchema(items)
			if itemExample != nil {
				return []any{itemExample}
			}
			return []any{}
		}
		return []any{"example_item"}
	case "string":
		formatType, _ := oaGet(schema, "format").(string)
		switch formatType {
		case "date-time":
			return "2024-01-01T12:00:00Z"
		case "date":
			return "2024-01-01"
		case "email":
			return "user@example.com"
		case "uuid":
			return "123e4567-e89b-12d3-a456-426614174000"
		case "byte":
			return "ZXhhbXBsZQ=="
		}
		return "string"
	case "integer":
		return 1
	case "number":
		return 1.5
	case "boolean":
		return true
	case "null":
		return nil
	}
	return "unknown_type"
}

// FormatJSONForDescription mirrors format_json_for_description (json.dumps fallback on
// TypeError).
func FormatJSONForDescription(data any, indent int) string {
	s, err := value_objects.PyJSONDumps(data, indent)
	if err != nil {
		return "```\nCould not serialize to JSON: " + value_objects.PyStr(data) + "\n```"
	}
	return "```json\n" + s + "\n```"
}

// FormatDescriptionWithResponses mirrors format_description_with_responses.
func FormatDescriptionWithResponses(
	baseDescription string,
	responses *entities.OrderedMap[*ResponseInfo],
	parameters []*ParameterInfo,
	requestBody *RequestBodyInfo,
) string {
	descParts := []string{baseDescription}

	if len(parameters) > 0 {
		pathParams := []*ParameterInfo{}
		for _, p := range parameters {
			if p.Location == ParameterLocationPath {
				pathParams = append(pathParams, p)
			}
		}
		if len(pathParams) > 0 {
			descParts = append(descParts, "\n\n**Path Parameters:**")
			for _, param := range pathParams {
				requiredMarker := ""
				if param.Required {
					requiredMarker = " (Required)"
				}
				descParts = append(descParts,
					"\n- **"+param.Name+"**"+requiredMarker+": "+oaDescriptionOr(param.Description, "No description."))
			}
		}

		queryParams := []*ParameterInfo{}
		for _, p := range parameters {
			if p.Location == ParameterLocationQuery {
				queryParams = append(queryParams, p)
			}
		}
		if len(queryParams) > 0 {
			descParts = append(descParts, "\n\n**Query Parameters:**")
			for _, param := range queryParams {
				requiredMarker := ""
				if param.Required {
					requiredMarker = " (Required)"
				}
				descParts = append(descParts,
					"\n- **"+param.Name+"**"+requiredMarker+": "+oaDescriptionOr(param.Description, "No description."))
			}
		}
	}

	if requestBody != nil && requestBody.Description != nil && *requestBody.Description != "" {
		descParts = append(descParts, "\n\n**Request Body:**")
		requiredMarker := ""
		if requestBody.Required {
			requiredMarker = " (Required)"
		}
		descParts = append(descParts, "\n"+*requestBody.Description+requiredMarker)

		if requestBody.ContentSchema != nil && requestBody.ContentSchema.Len() > 0 {
			if mediaType := oaFirstMediaType(requestBody.ContentSchema); mediaType != nil {
				schema, _ := requestBody.ContentSchema.Get(*mediaType)
				if schema != nil {
					if props, ok := schema.Get("properties"); ok {
						if propMap, isMap := props.(*JsonSchema); isMap {
							descParts = append(descParts, "\n\n**Request Properties:**")
							requiredList := oaList(schema, "required")
							for _, propName := range propMap.Keys() {
								propVal, _ := propMap.Get(propName)
								propSchema, isMap := propVal.(*JsonSchema)
								if !isMap {
									continue
								}
								if descVal, has := propSchema.Get("description"); has {
									reqMark := ""
									if oaContainsString(requiredList, propName) {
										reqMark = " (Required)"
									}
									descParts = append(descParts,
										"\n- **"+propName+"**"+reqMark+": "+value_objects.PyStr(descVal))
								}
							}
						}
					}
				}
			}
		}
	}

	if responses != nil && responses.Len() > 0 {
		responseSection := "\n\n**Responses:**"
		addedResponseSection := false

		// Python uses the set {"200","201","202","204"}; set iteration order is
		// unspecified, so when several are present the "(Success)" marker differs. We
		// pick the first present code in this fixed order.
		successStatus := ""
		for _, code := range []string{"200", "201", "202", "204"} {
			if responses.Has(code) {
				successStatus = code
				break
			}
		}

		keys := responses.Keys()
		sort.Strings(keys)
		for _, statusCode := range keys {
			respInfo, _ := responses.Get(statusCode)
			if !addedResponseSection {
				descParts = append(descParts, responseSection)
				addedResponseSection = true
			}

			statusMarker := ""
			if statusCode == successStatus {
				statusMarker = " (Success)"
			}
			descParts = append(descParts,
				"\n- **"+statusCode+"**"+statusMarker+": "+oaDescriptionOr(respInfo.Description, "No description."))

			if respInfo.ContentSchema == nil || respInfo.ContentSchema.Len() == 0 {
				continue
			}
			mediaType := oaFirstMediaType(respInfo.ContentSchema)
			if mediaType == nil {
				continue
			}
			schema, _ := respInfo.ContentSchema.Get(*mediaType)
			descParts = append(descParts, "  - Content-Type: `"+*mediaType+"`")

			if schema != nil {
				typeVal, _ := schema.Get("type")
				isArray := typeVal == "array"
				if isArray {
					if itemsVal, has := schema.Get("items"); has {
						if items, isMap := itemsVal.(*JsonSchema); isMap {
							if propsVal, has := items.Get("properties"); has {
								if props, isMap := propsVal.(*JsonSchema); isMap {
									descParts = append(descParts, "\n  - **Response Item Properties:**")
									for _, propName := range props.Keys() {
										propVal, _ := props.Get(propName)
										propSchema, isMap := propVal.(*JsonSchema)
										if !isMap {
											continue
										}
										if descVal, has := propSchema.Get("description"); has {
											descParts = append(descParts,
												"\n    - **"+propName+"**: "+value_objects.PyStr(descVal))
										}
									}
								}
							}
						}
					}
				} else if propsVal, has := schema.Get("properties"); has {
					if props, isMap := propsVal.(*JsonSchema); isMap {
						descParts = append(descParts, "\n  - **Response Properties:**")
						for _, propName := range props.Keys() {
							propVal, _ := props.Get(propName)
							propSchema, isMap := propVal.(*JsonSchema)
							if !isMap {
								continue
							}
							if descVal, has := propSchema.Get("description"); has {
								descParts = append(descParts,
									"\n    - **"+propName+"**: "+value_objects.PyStr(descVal))
							}
						}
					}
				}

				if schema.Len() > 0 {
					example := GenerateExampleFromSchema(schema)
					if example != nil && !value_objects.PyEqual(example, "unknown_type") {
						descParts = append(descParts, "\n  - **Example:**")
						descParts = append(descParts, FormatJSONForDescription(example, 2))
					}
				}
			}
		}
	}

	return strings.Join(descParts, "\n")
}

// ReplaceRefWithDefs mirrors _replace_ref_with_defs: replace openapi $ref with jsonschema
// $defs. `description` is an optional fallback (nil = Python None).
func ReplaceRefWithDefs(info *JsonSchema, description *string) *JsonSchema {
	schema := info.Copy()
	if refVal, has := schema.Get("$ref"); has && oaTruthy(refVal) {
		if refStr, isStr := refVal.(string); isStr {
			if strings.HasPrefix(refStr, "#/components/schemas/") {
				schemaName := refStr[strings.LastIndex(refStr, "/")+1:]
				schema.Set("$ref", "#/$defs/"+schemaName)
			}
		}
	} else if propsVal, has := schema.Get("properties"); has && oaTruthy(propsVal) {
		if props, isMap := propsVal.(*JsonSchema); isMap {
			if props.Has("$ref") {
				schema.Set("properties", ReplaceRefWithDefs(props, nil))
			} else {
				newProps := entities.NewOrderedMap[any]()
				for _, propName := range props.Keys() {
					propVal, _ := props.Get(propName)
					if propSchema, isMap := propVal.(*JsonSchema); isMap {
						newProps.Set(propName, ReplaceRefWithDefs(propSchema, nil))
					} else {
						newProps.Set(propName, propVal)
					}
				}
				schema.Set("properties", newProps)
			}
		}
	} else if itemVal, has := schema.Get("items"); has && oaTruthy(itemVal) {
		if itemSchema, isMap := itemVal.(*JsonSchema); isMap {
			schema.Set("items", ReplaceRefWithDefs(itemSchema, nil))
		}
	}

	// Python mutates the shared list in place through the shallow copy.
	for _, section := range []string{"anyOf", "allOf", "oneOf"} {
		if secVal, has := schema.Get(section); has {
			if list, isList := secVal.([]any); isList {
				for i, item := range list {
					if itemSchema, isMap := item.(*JsonSchema); isMap {
						list[i] = ReplaceRefWithDefs(itemSchema, nil)
					}
				}
			}
		}
	}

	infoDesc, hasInfoDesc := info.Get("description")
	var truthValue any = description
	if hasInfoDesc {
		truthValue = infoDesc
	}
	if oaTruthy(truthValue) {
		if sd, has := schema.Get("description"); !has || !oaTruthy(sd) {
			schema.Set("description", description)
		}
	}
	return schema
}

// CombineSchemas mirrors _combine_schemas and returns compress_schema's result.
func CombineSchemas(route *HTTPRoute) (*JsonSchema, error) {
	properties := entities.NewOrderedMap[any]()
	required := []any{}

	for _, param := range route.Parameters {
		if param.Required {
			required = append(required, param.Name)
		}
		var schemaCopy *JsonSchema
		if param.Schema != nil {
			schemaCopy = param.Schema.Copy()
		} else {
			schemaCopy = entities.NewOrderedMap[any]()
		}
		properties.Set(param.Name, ReplaceRefWithDefs(schemaCopy, param.Description))
	}

	if route.RequestBody != nil && route.RequestBody.ContentSchema != nil && route.RequestBody.ContentSchema.Len() > 0 {
		contentType := route.RequestBody.ContentSchema.Keys()[0]
		contentSchema, _ := route.RequestBody.ContentSchema.Get(contentType)
		var schemaCopy *JsonSchema
		if contentSchema != nil {
			schemaCopy = contentSchema.Copy()
		} else {
			schemaCopy = entities.NewOrderedMap[any]()
		}
		bodySchema := ReplaceRefWithDefs(schemaCopy, route.RequestBody.Description)

		if propsVal, ok := bodySchema.Get("properties"); ok {
			if bodyProps, isMap := propsVal.(*JsonSchema); isMap {
				for _, propName := range bodyProps.Keys() {
					propSchema, _ := bodyProps.Get(propName)
					properties.Set(propName, propSchema)
				}
			}
		}
		if route.RequestBody.Required {
			if reqVal, ok := bodySchema.Get("required"); ok {
				if list, isList := reqVal.([]any); isList {
					required = append(required, list...)
				}
			}
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("type", "object")
	result.Set("properties", properties)
	result.Set("required", required)
	if route.SchemaDefinitions != nil && route.SchemaDefinitions.Len() > 0 {
		defs := entities.NewOrderedMap[any]()
		for _, name := range route.SchemaDefinitions.Keys() {
			schema, _ := route.SchemaDefinitions.Get(name)
			defs.Set(name, schema)
		}
		result.Set("$defs", defs)
	}

	return CompressSchema(result, nil, true, true, false)
}

// --- Parser --------------------------------------------------------------------------

// openAPIParser replaces openapi_pydantic's OpenAPIParser. Pydantic validation cannot be
// reproduced, so traversal runs over the raw parsed JSON dicts.
type openAPIParser struct {
	openapi *entities.OrderedMap[any]
}

// ParseOpenAPIToHTTPRoutes parses an OpenAPI 3.0/3.1 document (raw parsed JSON) into routes.
//
// On malformed input it returns a *value_objects.ValueError in the Python spirit. The real
// Python code raises pydantic's ValidationError list; that text is not reproduced. Also,
// openapi_pydantic re-serializes schemas in model field order (model_dump), while this
// raw-dict port preserves the document's key order.
func ParseOpenAPIToHTTPRoutes(openapiDict *entities.OrderedMap[any]) ([]*HTTPRoute, error) {
	if openapiDict == nil {
		return nil, &value_objects.ValueError{Msg: "Invalid OpenAPI schema: expected an object"}
	}
	versionVal, hasVersion := openapiDict.Get("openapi")
	if !hasVersion {
		return nil, &value_objects.ValueError{Msg: "Invalid OpenAPI schema: missing required field 'openapi'"}
	}
	if _, isStr := versionVal.(string); !isStr {
		return nil, &value_objects.ValueError{Msg: "Invalid OpenAPI schema: 'openapi' must be a string"}
	}
	if _, hasInfo := openapiDict.Get("info"); !hasInfo {
		return nil, &value_objects.ValueError{Msg: "Invalid OpenAPI schema: missing required field 'info'"}
	}

	parser := &openAPIParser{openapi: openapiDict}
	return parser.parse(), nil
}

// oaConvertToParameterLocation mirrors _convert_to_parameter_location.
func oaConvertToParameterLocation(paramIn string) ParameterLocation {
	switch paramIn {
	case "path", "query", "header", "cookie":
		return ParameterLocation(paramIn)
	}
	return ParameterLocationQuery
}

// resolveRef mirrors _resolve_ref for raw dicts: a dict carrying a "$ref" is a Reference.
func (p *openAPIParser) resolveRef(item any) (any, error) {
	m := oaSchemaOrNil(item)
	if m == nil {
		return item, nil
	}
	refVal, has := m.Get("$ref")
	if !has {
		return item, nil
	}
	refStr, isStr := refVal.(string)
	if !isStr {
		return nil, value_objects.ValueErrorf("Failed to resolve reference '%v'", refVal)
	}
	resolved, err := p.resolveRefString(refStr)
	if err != nil {
		return nil, value_objects.ValueErrorf("Failed to resolve reference '%s': %s", refStr, err.Error())
	}
	return resolved, nil
}

func (p *openAPIParser) resolveRefString(refStr string) (any, error) {
	if !strings.HasPrefix(refStr, "#/") {
		return nil, value_objects.ValueErrorf("External or non-local reference not supported: %s", refStr)
	}
	parts := strings.Split(strings.Trim(refStr, "#/"), "/")
	var target any = p.openapi
	for _, part := range parts {
		if oaIsDigits(part) {
			if list, isList := target.([]any); isList {
				idx, _ := strconv.Atoi(part)
				if idx >= 0 && idx < len(list) {
					target = list[idx]
				} else {
					target = nil
				}
				if target == nil {
					return nil, value_objects.ValueErrorf("Reference part '%s' not found in path '%s'", part, refStr)
				}
				continue
			}
		}
		switch t := target.(type) {
		case *entities.OrderedMap[any]:
			target = oaGet(t, part)
		default:
			return nil, value_objects.ValueErrorf("Cannot traverse part '%s' in reference '%s'", part, refStr)
		}
		if target == nil {
			return nil, value_objects.ValueErrorf("Reference part '%s' not found in path '%s'", part, refStr)
		}
	}
	if m := oaSchemaOrNil(target); m != nil {
		if _, has := m.Get("$ref"); has {
			return p.resolveRef(target)
		}
	}
	return target, nil
}

// extractSchemaAsDict mirrors _extract_schema_as_dict.
func (p *openAPIParser) extractSchemaAsDict(schemaObj any) *JsonSchema {
	resolved, err := p.resolveRef(schemaObj)
	if err != nil {
		return entities.NewOrderedMap[any]()
	}
	schema := oaSchemaOrNil(resolved)
	if schema == nil {
		return entities.NewOrderedMap[any]()
	}
	return ReplaceRefWithDefs(schema, nil)
}

// extractParameters mirrors _extract_parameters (operation params first, dedup by
// (name, location)).
func (p *openAPIParser) extractParameters(operationParams, pathItemParams []any) []*ParameterInfo {
	extracted := []*ParameterInfo{}
	seen := map[string]bool{}
	allParams := append(append([]any{}, operationParams...), pathItemParams...)

	for _, paramOrRef := range allParams {
		parameter, err := p.resolveRef(paramOrRef)
		if err != nil {
			continue
		}
		paramMap := oaSchemaOrNil(parameter)
		if paramMap == nil {
			continue
		}

		name, _ := oaGet(paramMap, "name").(string)
		paramIn, _ := oaGet(paramMap, "in").(string)
		paramLocation := oaConvertToParameterLocation(paramIn)

		paramKey := name + "\x00" + paramIn
		if seen[paramKey] {
			continue
		}
		seen[paramKey] = true

		paramSchemaObj := oaGet(paramMap, "schema")
		paramSchemaDict := entities.NewOrderedMap[any]()
		if oaTruthy(paramSchemaObj) {
			paramSchemaDict = p.extractSchemaAsDict(paramSchemaObj)
			p.applySchemaDefault(paramSchemaObj, paramSchemaDict)
		} else if contentVal, has := paramMap.Get("content"); has && oaTruthy(contentVal) {
			if content := oaSchemaOrNil(contentVal); content != nil && content.Len() > 0 {
				firstVal, _ := content.Get(content.Keys()[0])
				if firstMediaType := oaSchemaOrNil(firstVal); firstMediaType != nil && firstMediaType.Len() > 0 {
					mediaSchema, has := firstMediaType.Get("schema")
					if has && oaTruthy(mediaSchema) {
						paramSchemaDict = p.extractSchemaAsDict(mediaSchema)
						p.applySchemaDefault(mediaSchema, paramSchemaDict)
					}
				}
			}
		}

		extracted = append(extracted, &ParameterInfo{
			Name:        name,
			Location:    paramLocation,
			Required:    oaBool(paramMap, "required"),
			Schema:      paramSchemaDict,
			Description: oaOptString(paramMap, "description"),
		})
	}
	return extracted
}

// applySchemaDefault mirrors the `resolved_schema.default is not None` block.
func (p *openAPIParser) applySchemaDefault(schemaObj any, target *JsonSchema) {
	resolved, err := p.resolveRef(schemaObj)
	if err != nil {
		return
	}
	resolvedSchema := oaSchemaOrNil(resolved)
	if resolvedSchema == nil {
		return
	}
	if defVal, has := resolvedSchema.Get("default"); has && defVal != nil {
		target.Set("default", defVal)
	}
}

// extractRequestBody mirrors _extract_request_body.
func (p *openAPIParser) extractRequestBody(requestBodyOrRef any) *RequestBodyInfo {
	if !oaTruthy(requestBodyOrRef) {
		return nil
	}
	resolved, err := p.resolveRef(requestBodyOrRef)
	if err != nil {
		return nil
	}
	requestBody := oaSchemaOrNil(resolved)
	if requestBody == nil {
		return nil
	}

	info := &RequestBodyInfo{
		Required:      oaBool(requestBody, "required"),
		ContentSchema: entities.NewOrderedMap[*JsonSchema](),
		Description:   oaOptString(requestBody, "description"),
	}

	if contentVal, has := requestBody.Get("content"); has && oaTruthy(contentVal) {
		if content := oaSchemaOrNil(contentVal); content != nil {
			for _, mediaTypeStr := range content.Keys() {
				mediaTypeVal, _ := content.Get(mediaTypeStr)
				mediaType := oaSchemaOrNil(mediaTypeVal)
				if mediaType == nil || mediaType.Len() == 0 {
					continue
				}
				schemaVal, has := mediaType.Get("schema")
				if !has || !oaTruthy(schemaVal) {
					continue
				}
				info.ContentSchema.Set(mediaTypeStr, p.extractSchemaAsDict(schemaVal))
			}
		}
	}
	return info
}

// extractResponses mirrors _extract_responses.
func (p *openAPIParser) extractResponses(operationResponses *entities.OrderedMap[any]) *entities.OrderedMap[*ResponseInfo] {
	extracted := entities.NewOrderedMap[*ResponseInfo]()
	if operationResponses == nil || operationResponses.Len() == 0 {
		return extracted
	}
	for _, statusCode := range operationResponses.Keys() {
		respOrRef, _ := operationResponses.Get(statusCode)
		response, err := p.resolveRef(respOrRef)
		if err != nil {
			continue
		}
		responseMap := oaSchemaOrNil(response)
		if responseMap == nil {
			continue
		}

		info := &ResponseInfo{
			Description:   oaOptString(responseMap, "description"),
			ContentSchema: entities.NewOrderedMap[*JsonSchema](),
		}
		if contentVal, has := responseMap.Get("content"); has && oaTruthy(contentVal) {
			if content := oaSchemaOrNil(contentVal); content != nil {
				for _, mediaTypeStr := range content.Keys() {
					mediaTypeVal, _ := content.Get(mediaTypeStr)
					mediaType := oaSchemaOrNil(mediaTypeVal)
					if mediaType == nil || mediaType.Len() == 0 {
						continue
					}
					schemaVal, has := mediaType.Get("schema")
					if !has || !oaTruthy(schemaVal) {
						continue
					}
					info.ContentSchema.Set(mediaTypeStr, p.extractSchemaAsDict(schemaVal))
				}
			}
		}
		extracted.Set(statusCode, info)
	}
	return extracted
}

// oaCopySchemaDefinitions gives each route its own independent copy of the component
// schemas, as pydantic does when it validates HTTPRoute(schema_definitions=...).
func oaCopySchemaDefinitions(src *entities.OrderedMap[*JsonSchema]) *entities.OrderedMap[*JsonSchema] {
	dst := entities.NewOrderedMap[*JsonSchema]()
	for _, name := range src.Keys() {
		schema, _ := src.Get(name)
		copied, _ := jsDeepCopy(schema).(*JsonSchema)
		dst.Set(name, copied)
	}
	return dst
}

// parse mirrors OpenAPIParser.parse.
func (p *openAPIParser) parse() []*HTTPRoute {
	routes := []*HTTPRoute{}

	pathsVal, hasPaths := p.openapi.Get("paths")
	paths := oaSchemaOrNil(pathsVal)
	if !hasPaths || paths == nil || paths.Len() == 0 {
		return routes
	}

	schemaDefinitions := entities.NewOrderedMap[*JsonSchema]()
	if componentsVal, has := p.openapi.Get("components"); has {
		if components := oaSchemaOrNil(componentsVal); components != nil {
			if schemasVal, has := components.Get("schemas"); has {
				if schemas := oaSchemaOrNil(schemasVal); schemas != nil && schemas.Len() > 0 {
					for _, name := range schemas.Keys() {
						schemaVal, _ := schemas.Get(name)
						resolved, err := p.resolveRef(schemaVal)
						if err != nil {
							// Python logs a warning and skips the definition.
							continue
						}
						schemaDefinitions.Set(name, p.extractSchemaAsDict(resolved))
					}
				}
			}
		}
	}

	httpMethods := []string{"get", "put", "post", "delete", "options", "head", "patch", "trace"}
	for _, pathStr := range paths.Keys() {
		pathItemVal, _ := paths.Get(pathStr)
		pathItem := oaSchemaOrNil(pathItemVal)
		if pathItem == nil {
			continue
		}

		var pathLevelParams []any
		if v, ok := pathItem.Get("parameters"); ok {
			if list, isList := v.([]any); isList {
				pathLevelParams = list
			}
		}

		for _, methodLower := range httpMethods {
			opVal, ok := pathItem.Get(methodLower)
			if !ok {
				continue
			}
			operation := oaSchemaOrNil(opVal)
			if operation == nil || operation.Len() == 0 {
				continue
			}
			methodUpper := strings.ToUpper(methodLower)

			parameters := p.extractParameters(oaList(operation, "parameters"), pathLevelParams)
			requestBodyInfo := p.extractRequestBody(oaGet(operation, "requestBody"))
			responses := p.extractResponses(oaSchemaOrNil(oaGet(operation, "responses")))

			routes = append(routes, &HTTPRoute{
				Path:              pathStr,
				Method:            HttpMethod(methodUpper),
				OperationID:       oaOptString(operation, "operationId"),
				Summary:           oaOptString(operation, "summary"),
				Description:       oaOptString(operation, "description"),
				Tags:              oaStringList(operation, "tags"),
				Parameters:        parameters,
				RequestBody:       requestBodyInfo,
				Responses:         responses,
				SchemaDefinitions: oaCopySchemaDefinitions(schemaDefinitions),
			})
		}
	}
	return routes
}
