package utilities

import (
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// oaCompact is PyJSONDumpsCompact (json.dumps(separators=(",", ":"))) for a schema.
func oaCompact(t *testing.T, schema *JsonSchema) string {
	t.Helper()
	out, err := value_objects.PyJSONDumpsCompact(schema)
	if err != nil {
		t.Fatalf("PyJSONDumpsCompact: %v", err)
	}
	return out
}

func oaCanonicalValue(v any) any {
	switch x := v.(type) {
	case *JsonSchema:
		keys := x.Keys()
		sort.Strings(keys)
		out := entities.NewOrderedMap[any]()
		for _, k := range keys {
			val, _ := x.Get(k)
			out.Set(k, oaCanonicalValue(val))
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = oaCanonicalValue(e)
		}
		return out
	default:
		return v
	}
}

// oaCanonical sorts keys recursively so Python's pydantic field order can be compared
// against this parser's raw-dict input order.
func oaCanonical(t *testing.T, schema *JsonSchema) string {
	t.Helper()
	out, err := value_objects.PyJSONDumpsCompact(oaCanonicalValue(schema))
	if err != nil {
		t.Fatalf("PyJSONDumpsCompact: %v", err)
	}
	return out
}

func TestOpenAPIGenerateExampleFromSchema(t *testing.T) {
	cases := []struct {
		name string
		in   string // JSON object, or "" for nil
		want string // Python repr
	}{
		{"nil", "", `'unknown'`},
		{"empty", `{}`, `'unknown'`},
		{"default zero", `{"default":0}`, `0`},
		{"default false", `{"default":false}`, `False`},
		{"default none", `{"default":null}`, `None`},
		{"enum", `{"enum":["a","b"]}`, `'a'`},
		{"empty enum", `{"enum":[]}`, `'unknown_type'`},
		{"non-list enum", `{"enum":"notalist"}`, `'unknown_type'`},
		{"examples", `{"examples":[{"x":1},2]}`, `{'x': 1}`},
		{"example", `{"example":7}`, `7`},
		{"object empty", `{"type":"object"}`, `{'key': 'value'}`},
		{"object one", `{"type":"object","properties":{"a":{"type":"string"}}}`, `{'a': 'string'}`},
		{"object first three", `{"type":"object","properties":{"a":{"type":"string"},"b":{"type":"integer"},"c":{"type":"number"},"d":{"type":"boolean"}}}`, `{'a': 'string', 'b': 1, 'c': 1.5}`},
		{"object required beyond three", `{"type":"object","properties":{"a":{"type":"string"},"b":{"type":"integer"},"c":{"type":"number"},"d":{"type":"boolean"}},"required":["d"]}`, `{'a': 'string', 'b': 1, 'c': 1.5, 'd': True}`},
		{"array", `{"type":"array","items":{"type":"string"}}`, `['string']`},
		{"array null item", `{"type":"array","items":{"type":"null"}}`, `[]`},
		{"array fallback", `{"type":"array"}`, `['example_item']`},
		{"string", `{"type":"string"}`, `'string'`},
		{"date-time", `{"type":"string","format":"date-time"}`, `'2024-01-01T12:00:00Z'`},
		{"date", `{"type":"string","format":"date"}`, `'2024-01-01'`},
		{"email", `{"type":"string","format":"email"}`, `'user@example.com'`},
		{"uuid", `{"type":"string","format":"uuid"}`, `'123e4567-e89b-12d3-a456-426614174000'`},
		{"byte", `{"type":"string","format":"byte"}`, `'ZXhhbXBsZQ=='`},
		{"integer", `{"type":"integer"}`, `1`},
		{"number", `{"type":"number"}`, `1.5`},
		{"boolean", `{"type":"boolean"}`, `True`},
		{"null type", `{"type":"null"}`, `None`},
		{"unknown type", `{"type":"weird"}`, `'unknown_type'`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var schema *JsonSchema
			if tc.in != "" {
				schema = mustSchema(t, tc.in)
			}
			got := value_objects.PyRepr(GenerateExampleFromSchema(schema))
			if got != tc.want {
				t.Fatalf("got  %s\nwant %s", got, tc.want)
			}
		})
	}
}

func TestOpenAPIFormatJSONForDescription(t *testing.T) {
	data := mustSchema(t, `{"a":1,"b":[true,null,"x"]}`)
	want := "```json\n{\n  \"a\": 1,\n  \"b\": [\n    true,\n    null,\n    \"x\"\n  ]\n}\n```"
	if got := FormatJSONForDescription(data, 2); got != want {
		t.Fatalf("got  %q\nwant %q", got, want)
	}
}

func TestOpenAPICleanSchemaForDisplayPythonBug(t *testing.T) {
	if got := CleanSchemaForDisplay(nil); got != nil {
		t.Fatalf("nil: got %v", got)
	}
	empty := mustSchema(t, `{}`)
	if got := CleanSchemaForDisplay(empty); got != empty {
		t.Fatalf("empty dict should be returned unchanged")
	}
	if got := CleanSchemaForDisplay(mustSchema(t, `{"type":"string"}`)); got != nil {
		t.Fatalf("non-empty dict must return None (missing return in Python)")
	}
	if got := CleanSchemaForDisplay(mustSchema(t, `{"allOf":[{"type":"string"}],"type":"object"}`)); got != nil {
		t.Fatalf("non-empty dict must return None (missing return in Python)")
	}
	if got := CleanSchemaForDisplay(mustSchema(t, `{"type":"object","properties":{}}`)); got != nil {
		t.Fatalf("non-empty dict must return None (missing return in Python)")
	}
}

func TestOpenAPIReplaceRefWithDefs(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{`{"$ref":"#/components/schemas/Pet"}`, `{"$ref":"#/$defs/Pet"}`},
		{`{"type":"object","properties":{"p":{"$ref":"#/components/schemas/Pet"}}}`, `{"type":"object","properties":{"p":{"$ref":"#/$defs/Pet"}}}`},
		{`{"items":{"$ref":"#/components/schemas/Pet"}}`, `{"items":{"$ref":"#/$defs/Pet"}}`},
		{`{"anyOf":[{"$ref":"#/components/schemas/A"},{"type":"string"}]}`, `{"anyOf":[{"$ref":"#/$defs/A"},{"type":"string"}]}`},
		{`{"properties":{"$ref":"#/components/schemas/Foo"}}`, `{"properties":{"$ref":"#/$defs/Foo"}}`},
		{`{"type":"string","description":"keep"}`, `{"type":"string","description":"keep"}`},
		// A falsy $ref does not take the ref branch, so properties still rewrites.
		{`{"$ref":"","properties":{"a":{"$ref":"#/components/schemas/A"}}}`, `{"$ref":"","properties":{"a":{"$ref":"#/$defs/A"}}}`},
	}
	for _, tc := range cases {
		got := oaCompact(t, ReplaceRefWithDefs(mustSchema(t, tc.in), nil))
		if got != tc.want {
			t.Fatalf("in %s\n got  %s\n want %s", tc.in, got, tc.want)
		}
	}

	got := oaCompact(t, ReplaceRefWithDefs(mustSchema(t, `{"type":"string"}`), strPtr("hello world")))
	if got != `{"type":"string","description":"hello world"}` {
		t.Fatalf("description fallback: %s", got)
	}
}

// The Python body is `schema = info.copy()` (shallow) and then mutates the anyOf/allOf/oneOf
// list in place, so the caller's list elements are rewritten. Preserve that quirk.
func TestOpenAPIReplaceRefWithDefsMutatesSharedList(t *testing.T) {
	info := mustSchema(t, `{"anyOf":[{"$ref":"#/components/schemas/A"}]}`)
	originalFirst := outanyList(t, info, "anyOf")[0]

	out := ReplaceRefWithDefs(info, nil)
	first, _ := outanyList(t, out, "anyOf")[0].(*JsonSchema)
	if got := oaCompact(t, first); got != `{"$ref":"#/$defs/A"}` {
		t.Fatalf("rewritten element: %s", got)
	}
	if outanyList(t, info, "anyOf")[0] == originalFirst {
		t.Fatalf("input list element was not replaced in place")
	}
}

func outanyList(t *testing.T, schema *JsonSchema, key string) []any {
	t.Helper()
	v, ok := schema.Get(key)
	if !ok {
		t.Fatalf("missing %s", key)
	}
	list, ok := v.([]any)
	if !ok {
		t.Fatalf("%s is not a list", key)
	}
	return list
}

func TestOpenAPIFormatDescriptionWithResponses(t *testing.T) {
	params := []*ParameterInfo{
		{Name: "pet_id", Location: ParameterLocationPath, Required: true, Schema: mustSchema(t, `{"type":"string"}`), Description: strPtr("The pet id")},
		{Name: "limit", Location: ParameterLocationQuery, Required: false, Schema: mustSchema(t, `{"type":"integer"}`)},
		{Name: "limit", Location: ParameterLocationQuery, Required: true, Schema: mustSchema(t, `{"type":"integer"}`), Description: strPtr("dup skipped")},
		{Name: "X-Trace", Location: ParameterLocationHeader, Required: false, Schema: mustSchema(t, `{"type":"string"}`), Description: strPtr("trace")},
	}

	rbContent := entities.NewOrderedMap[*JsonSchema]()
	rbContent.Set("application/json", mustSchema(t,
		`{"type":"object","properties":{"name":{"type":"string","description":"Name of pet"},"age":{"type":"integer"}},"required":["name"]}`))
	rb := &RequestBodyInfo{Required: true, Description: strPtr("Pet payload"), ContentSchema: rbContent}

	responses := entities.NewOrderedMap[*ResponseInfo]()
	c404 := entities.NewOrderedMap[*JsonSchema]()
	c404.Set("application/json", mustSchema(t, `{"type":"object","properties":{"detail":{"type":"string","description":"Why"}}}`))
	responses.Set("404", &ResponseInfo{Description: strPtr("Not found"), ContentSchema: c404})
	c200 := entities.NewOrderedMap[*JsonSchema]()
	c200.Set("application/json", mustSchema(t, `{"type":"array","items":{"type":"object","properties":{"id":{"type":"string","description":"id desc"}}}}`))
	responses.Set("200", &ResponseInfo{Description: strPtr("OK"), ContentSchema: c200})
	responses.Set("204", &ResponseInfo{Description: nil, ContentSchema: entities.NewOrderedMap[*JsonSchema]()})

	want := "Base desc\n\n\n**Path Parameters:**\n\n- **pet_id** (Required): The pet id\n\n\n**Query Parameters:**\n\n- **limit**: No description.\n\n- **limit** (Required): dup skipped\n\n\n**Request Body:**\n\nPet payload (Required)\n\n\n**Request Properties:**\n\n- **name** (Required): Name of pet\n\n\n**Responses:**\n\n- **200** (Success): OK\n  - Content-Type: `application/json`\n\n  - **Response Item Properties:**\n\n    - **id**: id desc\n\n  - **Example:**\n```json\n[\n  {\n    \"id\": \"string\"\n  }\n]\n```\n\n- **204**: No description.\n\n- **404**: Not found\n  - Content-Type: `application/json`\n\n  - **Response Properties:**\n\n    - **detail**: Why\n\n  - **Example:**\n```json\n{\n  \"detail\": \"string\"\n}\n```"

	got := FormatDescriptionWithResponses("Base desc", responses, params, rb)
	if got != want {
		t.Fatalf("got  %q\nwant %q", got, want)
	}
}

func TestOpenAPICombineSchemas(t *testing.T) {
	content := entities.NewOrderedMap[*JsonSchema]()
	content.Set("application/json", mustSchema(t, `{"type":"object","properties":{"owner":{"$ref":"#/components/schemas/Owner"}}}`))
	defs := entities.NewOrderedMap[*JsonSchema]()
	defs.Set("Pet", mustSchema(t, `{"type":"object","properties":{"name":{"type":"string"}}}`))
	defs.Set("Owner", mustSchema(t, `{"type":"object","properties":{"id":{"type":"string"}}}`))
	defs.Set("Unused", mustSchema(t, `{"type":"string"}`))

	route := &HTTPRoute{
		Path:        "/pets",
		Method:      HttpMethodPOST,
		OperationID: strPtr("createPet"),
		Parameters: []*ParameterInfo{
			{Name: "body", Location: ParameterLocationQuery, Required: true,
				Schema: mustSchema(t, `{"$ref":"#/components/schemas/Pet"}`)},
		},
		RequestBody:       &RequestBodyInfo{Required: false, ContentSchema: content},
		Responses:         entities.NewOrderedMap[*ResponseInfo](),
		SchemaDefinitions: defs,
	}

	result, err := CombineSchemas(route)
	if err != nil {
		t.Fatalf("CombineSchemas: %v", err)
	}
	want := `{"type":"object","properties":{"body":{"$ref":"#/$defs/Pet"},"owner":{"$ref":"#/$defs/Owner"}},"required":["body"],"$defs":{"Pet":{"type":"object","properties":{"name":{"type":"string"}}},"Owner":{"type":"object","properties":{"id":{"type":"string"}}}}}`
	if got := oaCompact(t, result); got != want {
		t.Fatalf("got  %s\nwant %s", got, want)
	}
}

// All $defs are unused, so compress_schema removes the whole $defs key, and body properties
// overwrite parameter properties in place while required preserves parameter order first.
func TestOpenAPICombineSchemasUnusedDefsRemoved(t *testing.T) {
	rbContent := entities.NewOrderedMap[*JsonSchema]()
	rbContent.Set("application/json", mustSchema(t,
		`{"type":"object","properties":{"name":{"type":"string","description":"Name of pet"},"age":{"type":"integer"}},"required":["name"]}`))
	defs := entities.NewOrderedMap[*JsonSchema]()
	defs.Set("Pet", mustSchema(t, `{"type":"object","properties":{"name":{"type":"string"}}}`))

	route := &HTTPRoute{
		Path:   "/pets/{pet_id}",
		Method: HttpMethodPOST,
		Parameters: []*ParameterInfo{
			{Name: "pet_id", Location: ParameterLocationPath, Required: true, Schema: mustSchema(t, `{"type":"string"}`), Description: strPtr("The pet id")},
			{Name: "limit", Location: ParameterLocationQuery, Required: false, Schema: mustSchema(t, `{"type":"integer"}`)},
			{Name: "limit", Location: ParameterLocationQuery, Required: true, Schema: mustSchema(t, `{"type":"integer"}`), Description: strPtr("dup skipped")},
			{Name: "X-Trace", Location: ParameterLocationHeader, Required: false, Schema: mustSchema(t, `{"type":"string"}`), Description: strPtr("trace")},
		},
		RequestBody:       &RequestBodyInfo{Required: true, Description: strPtr("Pet payload"), ContentSchema: rbContent},
		Responses:         entities.NewOrderedMap[*ResponseInfo](),
		SchemaDefinitions: defs,
	}

	result, err := CombineSchemas(route)
	if err != nil {
		t.Fatalf("CombineSchemas: %v", err)
	}
	want := `{"type":"object","properties":{"pet_id":{"type":"string","description":"The pet id"},"limit":{"type":"integer","description":"dup skipped"},"X-Trace":{"type":"string","description":"trace"},"name":{"type":"string","description":"Name of pet"},"age":{"type":"integer"}},"required":["pet_id","limit","name"]}`
	if got := oaCompact(t, result); got != want {
		t.Fatalf("got  %s\nwant %s", got, want)
	}
}

const openAPIDoc31 = `{
  "openapi":"3.1.0",
  "info":{"title":"T","version":"1.0"},
  "paths":{
    "/pets/{pet_id}":{
      "parameters":[
        {"name":"pet_id","in":"path","required":true,"schema":{"type":"string"}},
        {"name":"verbose","in":"query","required":false,"schema":{"type":"boolean"},"description":"path verbose"}
      ],
      "get":{
        "operationId":"getPet","summary":"Get a pet","description":"desc","tags":["pets"],
        "parameters":[{"name":"verbose","in":"query","required":false,"schema":{"type":"boolean","default":false},"description":"verbose flag"}],
        "responses":{
          "200":{"description":"OK","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Pet"}}}},
          "404":{"description":"nf","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}}
        }
      },
      "post":{
        "operationId":"createPet",
        "requestBody":{"required":true,"description":"body","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Pet"}}}},
        "responses":{"201":{"description":"created"}}
      }
    }
  },
  "components":{"schemas":{
    "Pet":{"type":"object","properties":{"name":{"type":"string"},"age":{"type":"integer"}},"required":["name"]},
    "Error":{"type":"object","properties":{"detail":{"type":"string"}}}
  }}
}`

func TestOpenAPIParseOpenAPIToHTTPRoutes(t *testing.T) {
	for _, tc := range []struct{ name, doc string }{
		{"3.1", openAPIDoc31},
		{"3.0", strings.Replace(openAPIDoc31, `"3.1.0"`, `"3.0.3"`, 1)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			routes, err := ParseOpenAPIToHTTPRoutes(mustSchema(t, tc.doc))
			if err != nil {
				t.Fatalf("ParseOpenAPIToHTTPRoutes: %v", err)
			}
			if len(routes) != 2 {
				t.Fatalf("expected 2 routes, got %d", len(routes))
			}

			get := routes[0]
			if get.Path != "/pets/{pet_id}" || get.Method != HttpMethodGET {
				t.Fatalf("route 0: %s %s", get.Method, get.Path)
			}
			if get.OperationID == nil || *get.OperationID != "getPet" {
				t.Fatalf("operation_id: %v", get.OperationID)
			}
			if get.Summary == nil || *get.Summary != "Get a pet" {
				t.Fatalf("summary: %v", get.Summary)
			}
			if len(get.Tags) != 1 || get.Tags[0] != "pets" {
				t.Fatalf("tags: %v", get.Tags)
			}

			// Operation-level params come before path-level params; the duplicate
			// (verbose, query) path-level entry is skipped.
			if len(get.Parameters) != 2 {
				t.Fatalf("GET params: %d", len(get.Parameters))
			}
			p0, p1 := get.Parameters[0], get.Parameters[1]
			if p0.Name != "verbose" || p0.Location != ParameterLocationQuery || p0.Required {
				t.Fatalf("param 0: %+v", p0)
			}
			if p0.Description == nil || *p0.Description != "verbose flag" {
				t.Fatalf("param 0 description: %v", p0.Description)
			}
			if got := oaCompact(t, p0.Schema); got != `{"type":"boolean","default":false}` {
				t.Fatalf("param 0 schema (raw input order): %s", got)
			}
			if p1.Name != "pet_id" || p1.Location != ParameterLocationPath || !p1.Required || p1.Description != nil {
				t.Fatalf("param 1: %+v", p1)
			}

			if got := strings.Join(get.Responses.Keys(), ","); got != "200,404" {
				t.Fatalf("response keys: %s", got)
			}
			resp200, _ := get.Responses.Get("200")
			if resp200.Description == nil || *resp200.Description != "OK" {
				t.Fatalf("200 description: %v", resp200.Description)
			}
			// Raw-dict parser preserves the document order (pydantic reorders fields).
			if got := oaCompact(t, mustGetSchema(t, resp200.ContentSchema, "application/json")); got != `{"type":"object","properties":{"name":{"type":"string"},"age":{"type":"integer"}},"required":["name"]}` {
				t.Fatalf("200 schema: %s", got)
			}
			// Semantically identical to Python's pydantic dump.
			wantPet := mustSchema(t, `{"properties":{"name":{"type":"string"},"age":{"type":"integer"}},"type":"object","required":["name"]}`)
			if got, want := oaCanonical(t, mustGetSchema(t, resp200.ContentSchema, "application/json")), oaCanonical(t, wantPet); got != want {
				t.Fatalf("200 canonical: got %s want %s", got, want)
			}
			resp404, _ := get.Responses.Get("404")
			if resp404.Description == nil || *resp404.Description != "nf" {
				t.Fatalf("404 description: %v", resp404.Description)
			}

			if got := strings.Join(get.SchemaDefinitions.Keys(), ","); got != "Pet,Error" {
				t.Fatalf("schema_definitions keys: %s", got)
			}
			defPet, _ := get.SchemaDefinitions.Get("Pet")
			wantDefPet := mustSchema(t, `{"properties":{"name":{"type":"string"},"age":{"type":"integer"}},"type":"object","required":["name"]}`)
			if got, want := oaCanonical(t, defPet), oaCanonical(t, wantDefPet); got != want {
				t.Fatalf("Pet def canonical: got %s want %s", got, want)
			}

			post := routes[1]
			if post.Path != "/pets/{pet_id}" || post.Method != HttpMethodPOST {
				t.Fatalf("route 1: %s %s", post.Method, post.Path)
			}
			// POST has no operation-level params, so the path-level verbose is kept.
			if len(post.Parameters) != 2 || post.Parameters[1].Name != "verbose" {
				t.Fatalf("POST params: %+v", post.Parameters)
			}
			if post.Parameters[1].Description == nil || *post.Parameters[1].Description != "path verbose" {
				t.Fatalf("POST path-level param description: %v", post.Parameters[1].Description)
			}
			if post.RequestBody == nil || !post.RequestBody.Required {
				t.Fatalf("POST request body: %+v", post.RequestBody)
			}
			if post.RequestBody.Description == nil || *post.RequestBody.Description != "body" {
				t.Fatalf("POST request body description: %v", post.RequestBody.Description)
			}
			if got, want := oaCanonical(t, mustGetSchema(t, post.RequestBody.ContentSchema, "application/json")), oaCanonical(t, wantPet); got != want {
				t.Fatalf("POST request schema canonical: got %s want %s", got, want)
			}
			if got := strings.Join(post.Responses.Keys(), ","); got != "201" {
				t.Fatalf("POST response keys: %s", got)
			}
			resp201, _ := post.Responses.Get("201")
			if resp201.ContentSchema == nil || resp201.ContentSchema.Len() != 0 {
				t.Fatalf("201 content schema should be empty")
			}

			// pydantic gives each route an independent (deep) copy of schema_definitions.
			if get.SchemaDefinitions == post.SchemaDefinitions {
				t.Fatalf("routes must not share the schema_definitions map")
			}
			defPetGet, _ := get.SchemaDefinitions.Get("Pet")
			defPetPost, _ := post.SchemaDefinitions.Get("Pet")
			if defPetGet == defPetPost {
				t.Fatalf("routes must not share nested schema definitions")
			}
		})
	}
}

func mustGetSchema(t *testing.T, content *entities.OrderedMap[*JsonSchema], key string) *JsonSchema {
	t.Helper()
	schema, ok := content.Get(key)
	if !ok {
		t.Fatalf("missing content schema %s", key)
	}
	return schema
}

func TestOpenAPIParseNestedRef(t *testing.T) {
	doc := `{
      "openapi":"3.1.0","info":{"title":"T","version":"1"},
      "paths":{"/pets":{"get":{"operationId":"g","responses":{"200":{"description":"ok","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Pet"}}}}}}}},
      "components":{"schemas":{
        "Pet":{"type":"object","properties":{"owner":{"$ref":"#/components/schemas/Owner"}},"required":["owner"]},
        "Owner":{"type":"object","properties":{"id":{"type":"string"}}}
      }}
    }`
	routes, err := ParseOpenAPIToHTTPRoutes(mustSchema(t, doc))
	if err != nil {
		t.Fatalf("ParseOpenAPIToHTTPRoutes: %v", err)
	}
	if len(routes) != 1 {
		t.Fatalf("routes: %d", len(routes))
	}
	resp200, _ := routes[0].Responses.Get("200")
	schema := mustGetSchema(t, resp200.ContentSchema, "application/json")
	if got := oaCompact(t, schema); got != `{"type":"object","properties":{"owner":{"$ref":"#/$defs/Owner"}},"required":["owner"]}` {
		t.Fatalf("nested ref: %s", got)
	}
	defPet, _ := routes[0].SchemaDefinitions.Get("Pet")
	if got := oaCompact(t, defPet); got != `{"type":"object","properties":{"owner":{"$ref":"#/$defs/Owner"}},"required":["owner"]}` {
		t.Fatalf("Pet def nested ref: %s", got)
	}
}

func TestOpenAPIParseMalformed(t *testing.T) {
	if _, err := ParseOpenAPIToHTTPRoutes(nil); err == nil {
		t.Fatalf("nil doc should fail")
	} else if _, ok := err.(*value_objects.ValueError); !ok {
		t.Fatalf("expected *ValueError, got %T", err)
	}
	if _, err := ParseOpenAPIToHTTPRoutes(mustSchema(t, `{"openapi":"3.1.0"}`)); err == nil {
		t.Fatalf("missing info should fail")
	}
	if _, err := ParseOpenAPIToHTTPRoutes(mustSchema(t, `{"openapi":3.1,"info":{}}`)); err == nil {
		t.Fatalf("non-string openapi should fail")
	}
	// A valid document with no paths yields an empty (non-nil) slice.
	routes, err := ParseOpenAPIToHTTPRoutes(mustSchema(t, `{"openapi":"3.1.0","info":{"title":"t","version":"1"}}`))
	if err != nil || len(routes) != 0 {
		t.Fatalf("no paths: routes=%v err=%v", routes, err)
	}
}
