package validation

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func ov(t *testing.T, o *entities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := o.Get(key)
	if !ok {
		t.Fatalf("key %q missing", key)
	}
	return v
}

func TestDocumentValidatorConstructorDefect(t *testing.T) {
	if _, err := NewDocumentValidator(); err == nil {
		t.Fatalf("NewDocumentValidator did not fail")
	}
	want := []DocumentType{DocumentTypeConfig, DocumentTypeTemplate, DocumentTypeDocument}
	if len(DocumentTypeValues) != len(want) {
		t.Fatalf("DocumentTypeValues = %#v", DocumentTypeValues)
	}
	for i := range want {
		if DocumentTypeValues[i] != want[i] {
			t.Fatalf("DocumentTypeValues[%d] = %q, want %q", i, DocumentTypeValues[i], want[i])
		}
	}
}

func newGlobalContext(t *testing.T) *entities.GlobalContext {
	t.Helper()
	ctx := entities.NewGlobalContext("user-1", "Acme", map[string]any{}, map[string]any{})
	if ctx.GetNestedData() == nil {
		t.Fatalf("nested data is nil")
	}
	return ctx
}

func TestValidateNestedStructureValid(t *testing.T) {
	ctx := newGlobalContext(t)
	v := NewGlobalContextValidator()
	ok, errors := v.ValidateNestedStructure(ctx.GetNestedData().ToDict())
	if !ok || len(errors) != 0 {
		t.Fatalf("valid nested: ok=%v errors=%#v", ok, errors)
	}
}

func TestValidateNestedStructureMissingCategory(t *testing.T) {
	ctx := newGlobalContext(t)
	nested := ctx.GetNestedData().ToDict()
	delete(nested, "organization")
	ok, errors := NewGlobalContextValidator().ValidateNestedStructure(nested)
	if ok {
		t.Fatalf("missing category validated")
	}
	want := []string{
		"Schema validation failed: 'organization' is a required property",
		"Missing required category: organization",
	}
	if len(errors) != len(want) {
		t.Fatalf("errors = %#v", errors)
	}
	for i := range want {
		if errors[i] != want[i] {
			t.Fatalf("errors[%d] = %q, want %q", i, errors[i], want[i])
		}
	}
}

func TestValidateNestedStructureAdditionalProperty(t *testing.T) {
	ctx := newGlobalContext(t)
	nested := ctx.GetNestedData().ToDict()
	nested["extra"] = map[string]any{}
	ok, errors := NewGlobalContextValidator().ValidateNestedStructure(nested)
	if ok {
		t.Fatalf("additional property validated")
	}
	if len(errors) != 1 || errors[0] != "Schema validation failed: Additional properties are not allowed ('extra' was unexpected)" {
		t.Fatalf("errors = %#v", errors)
	}
}

func TestValidateNestedStructureWrongCategoryType(t *testing.T) {
	ctx := newGlobalContext(t)
	nested := ctx.GetNestedData().ToDict()
	nested["organization"] = "x"
	ok, errors := NewGlobalContextValidator().ValidateNestedStructure(nested)
	if ok {
		t.Fatalf("wrong category type validated")
	}
	want := []string{
		"Schema validation failed: 'x' is not of type 'object'",
		"Path: organization",
		"Category organization must be an object",
	}
	if len(errors) != len(want) {
		t.Fatalf("errors = %#v", errors)
	}
	for i := range want {
		if errors[i] != want[i] {
			t.Fatalf("errors[%d] = %q, want %q", i, errors[i], want[i])
		}
	}
}

func TestValidateFlatStructure(t *testing.T) {
	ctx := newGlobalContext(t)
	v := NewGlobalContextValidator()
	flat := ctx.ToDict()
	ok, errors := v.ValidateFlatStructure(flat)
	if !ok || len(errors) != 0 {
		t.Fatalf("valid flat: ok=%v errors=%#v", ok, errors)
	}

	missing := map[string]any{}
	ok, errors = v.ValidateFlatStructure(missing)
	if ok {
		t.Fatalf("empty flat validated")
	}
	want := []string{
		"Schema validation failed: 'id' is a required property",
		"Missing required field: id",
		"Missing required field: global_settings",
	}
	if len(errors) != len(want) {
		t.Fatalf("errors = %#v", errors)
	}
	for i := range want {
		if errors[i] != want[i] {
			t.Fatalf("errors[%d] = %q, want %q", i, errors[i], want[i])
		}
	}
}

func TestValidateGlobalContextEntity(t *testing.T) {
	ctx := newGlobalContext(t)
	v := NewGlobalContextValidator()
	ok, errors := v.ValidateGlobalContextEntity(ctx)
	if ok {
		t.Fatalf("entity validated despite the migrator import defect")
	}
	want := "Error validating structure consistency: " + migrationImportError
	if len(errors) != 1 || errors[0] != want {
		t.Fatalf("errors = %#v", errors)
	}
}

func TestValidateMigrationData(t *testing.T) {
	ctx := newGlobalContext(t)
	errors := NewGlobalContextValidator().ValidateMigrationData(map[string]any{"organization_standards": map[string]any{}}, ctx.GetNestedData())
	want := "Error validating migration: " + migrationImportError
	if len(errors) != 1 || errors[0] != want {
		t.Fatalf("errors = %#v", errors)
	}
}

func TestCreateValidationReport(t *testing.T) {
	ctx := newGlobalContext(t)
	report := NewGlobalContextValidator().CreateValidationReport(ctx)

	if ov(t, report, "is_valid") != false {
		t.Fatalf("is_valid = %#v", ov(t, report, "is_valid"))
	}
	structure := ov(t, report, "structure_info").(*entities.OrderedMap[any])
	if ov(t, structure, "has_nested_structure") != true || ov(t, structure, "has_flat_structure") != true {
		t.Fatalf("structure_info = %#v", structure.Keys())
	}
	if ov(t, structure, "schema_version") != "2.0" || ov(t, structure, "is_migrated") != false {
		t.Fatalf("structure_info = %#v", structure.Keys())
	}
	counts := ov(t, report, "field_counts").(*entities.OrderedMap[any])
	if ov(t, counts, "nested_categories") != 5 {
		t.Fatalf("nested_categories = %#v", ov(t, counts, "nested_categories"))
	}
	if ov(t, counts, "flat_fields") != 7 {
		t.Fatalf("flat_fields = %#v", ov(t, counts, "flat_fields"))
	}
}

func TestValidateGlobalContextRaise(t *testing.T) {
	ctx := newGlobalContext(t)
	ok, errors, err := ValidateGlobalContext(ctx, true)
	if ok || len(errors) != 1 || err == nil {
		t.Fatalf("ok=%v errors=%#v err=%v", ok, errors, err)
	}
	if err.Error() != "Global context validation failed with 1 errors" {
		t.Fatalf("error = %q", err.Error())
	}

	ok, errors, err = ValidateGlobalContext(ctx, false)
	if ok || len(errors) != 1 || err != nil {
		t.Fatalf("raise_on_error=false: ok=%v errors=%#v err=%v", ok, errors, err)
	}
}
