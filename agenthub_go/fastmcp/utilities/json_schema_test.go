package utilities

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func mustSchema(t *testing.T, s string) *jsonSchema {
	t.Helper()
	v, err := entities.DecodeJSON([]byte(s))
	if err != nil {
		t.Fatalf("DecodeJSON(%s): %v", s, err)
	}
	return v.(*jsonSchema)
}

func schemaText(t *testing.T, s *jsonSchema) string {
	t.Helper()
	out, err := value_objects.PyJSONDumps(s, -1)
	if err != nil {
		t.Fatalf("PyJSONDumps: %v", err)
	}
	return out
}

func TestCompressSchemaPruneParam(t *testing.T) {
	schema := mustSchema(t, `{"type":"object","properties":{"a":{"type":"string"},"b":{"type":"integer"}},"required":["a","b"]}`)
	got, _ := CompressSchema(schema, []string{"a"}, false, false, false)
	want := `{"type": "object", "properties": {"b": {"type": "integer"}}, "required": ["b"]}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
	if schemaText(t, schema) != `{"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "integer"}}, "required": ["a", "b"]}` {
		t.Fatalf("original schema was mutated: %s", schemaText(t, schema))
	}
}

// A property whose value is None is popped before the "nothing to do" early return, so it
// leaves properties but stays in required.
func TestCompressSchemaNonePropertyQuirk(t *testing.T) {
	schema := mustSchema(t, `{"properties":{"a":null,"b":{"type":"string"}},"required":["a","b"]}`)
	got, _ := CompressSchema(schema, []string{"a"}, false, false, false)
	want := `{"properties": {"b": {"type": "string"}}, "required": ["a", "b"]}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
}

func TestCompressSchemaMissingParamUnchanged(t *testing.T) {
	schema := mustSchema(t, `{"properties":{"b":{"type":"string"}},"required":["a"]}`)
	got, _ := CompressSchema(schema, []string{"a"}, false, false, false)
	want := `{"properties": {"b": {"type": "string"}}, "required": ["a"]}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
}

func TestCompressSchemaPruneUnusedDefs(t *testing.T) {
	schema := mustSchema(t, `{"type":"object","properties":{"x":{"$ref":"#/$defs/Used"}},"$defs":{"Used":{"type":"string"},"Unused":{"type":"integer"}}}`)
	got, _ := CompressSchema(schema, nil, true, false, false)
	want := `{"type": "object", "properties": {"x": {"$ref": "#/$defs/Used"}}, "$defs": {"Used": {"type": "string"}}}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
}

func TestCompressSchemaPruneTransitiveDefs(t *testing.T) {
	schema := mustSchema(t, `{"$ref":"#/$defs/A","$defs":{"A":{"$ref":"#/$defs/B"},"B":{"type":"string"},"C":{"type":"integer"}}}`)
	got, _ := CompressSchema(schema, nil, true, false, false)
	want := `{"$ref": "#/$defs/A", "$defs": {"A": {"$ref": "#/$defs/B"}, "B": {"type": "string"}}}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
}

// Python does not pass current_def into list items, so a def referenced only from a list
// inside another def is recorded as a root reference (and the outer def is pruned).
func TestCompressSchemaDefRefInsideListIsRootRef(t *testing.T) {
	schema := mustSchema(t, `{"$defs":{"A":{"oneOf":[{"$ref":"#/$defs/B"}]},"B":{"type":"string"}}}`)
	got, _ := CompressSchema(schema, nil, true, false, false)
	want := `{"$defs": {"B": {"type": "string"}}}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
}

func TestCompressSchemaEmptyDefsRemoved(t *testing.T) {
	schema := mustSchema(t, `{"$defs":{"X":{"type":"string"}}}`)
	got, _ := CompressSchema(schema, nil, true, false, false)
	if schemaText(t, got) != `{}` {
		t.Fatalf("got %s", schemaText(t, got))
	}
}

func TestCompressSchemaPruneTitlesAndAdditionalProperties(t *testing.T) {
	schema := mustSchema(t, `{"title":"Root","additionalProperties":false,"properties":{"a":{"title":"A","additionalProperties":false,"type":"string"}}}`)
	got, _ := CompressSchema(schema, nil, false, true, true)
	want := `{"properties": {"a": {"type": "string"}}}`
	if schemaText(t, got) != want {
		t.Fatalf("got  %s\nwant %s", schemaText(t, got), want)
	}
}

func TestCompressSchemaKeepsAdditionalPropertiesTrue(t *testing.T) {
	schema := mustSchema(t, `{"additionalProperties":true}`)
	got, _ := CompressSchema(schema, nil, false, true, false)
	if schemaText(t, got) != `{"additionalProperties": true}` {
		t.Fatalf("got %s", schemaText(t, got))
	}
}

func TestCompressSchemaDefCycleIsRecursionError(t *testing.T) {
	schema := mustSchema(t, `{"type":"object","$defs":{"A":{"$ref":"#/$defs/A"}}}`)
	if _, err := CompressSchema(schema, nil, true, false, false); err == nil {
		t.Fatal("expected RecursionError for an unreferenced self-referencing def")
	}
	// A cycle reachable from the root is found before recursing.
	ok := mustSchema(t, `{"properties":{"x":{"$ref":"#/$defs/A"}},"$defs":{"A":{"$ref":"#/$defs/B"},"B":{"$ref":"#/$defs/A"}}}`)
	if _, err := CompressSchema(ok, nil, true, false, false); err != nil {
		t.Fatal(err)
	}
}
