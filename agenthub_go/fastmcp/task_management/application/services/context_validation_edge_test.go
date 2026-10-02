package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestValidateContextDataNonStringTitleRaisesLikePython(t *testing.T) {
	svc := &ContextValidationService{}
	_, err := svc.ValidateContextData(value_objects.ContextLevelTask, map[string]any{"title": nil})
	if err == nil || err.Error() != "'NoneType' object has no attribute 'strip'" {
		t.Fatalf("got %v", err)
	}
	_, err = svc.ValidateContextData(value_objects.ContextLevelProject, map[string]any{"name": int64(5)})
	if err == nil || err.Error() != "'int' object has no attribute 'strip'" {
		t.Fatalf("got %v", err)
	}
}

func TestValidateContextDataBoolIsANumber(t *testing.T) {
	svc := &ContextValidationService{}
	res, err := svc.ValidateContextData(value_objects.ContextLevelTask, map[string]any{"completion_percentage": true, "vision_alignment_score": false})
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := res.Get("valid"); v != true {
		t.Fatalf("%v", res)
	}
}
