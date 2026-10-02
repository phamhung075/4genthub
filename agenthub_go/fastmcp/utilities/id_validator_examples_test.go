package utilities

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestDatabaseConstraintExampleSQL(t *testing.T) {
	create := DatabaseConstraintExample{}.CreateIDValidationConstraints()
	if got, want := len(create), 4; got != want {
		t.Fatalf("create constraints: %d", got)
	}
	for i, want := range []int{185, 206, 171, 179} {
		if len(create[i]) != want {
			t.Fatalf("create[%d] len %d want %d", i, len(create[i]), want)
		}
	}
	sum := sha256.Sum256([]byte(strings.Join(create, "\x00")))
	if got := hex.EncodeToString(sum[:]); got != "6d535404315e42752f9e728043fd1690945df63d0c1ff35062c1df2c46f70eeb" {
		t.Fatalf("create constraints hash: %s", got)
	}

	validate := DatabaseConstraintExample{}.ValidateExistingData()
	if got, want := len(validate), 3; got != want {
		t.Fatalf("validate queries: %d", got)
	}
	for i, want := range []int{205, 215, 336} {
		if len(validate[i]) != want {
			t.Fatalf("validate[%d] len %d want %d", i, len(validate[i]), want)
		}
	}
	sum = sha256.Sum256([]byte(strings.Join(validate, "\x00")))
	if got := hex.EncodeToString(sum[:]); got != "a0185068dc3e96930e290a9bd0a14c9864292dca45efe4cc216dc3759fe398fe" {
		t.Fatalf("validate queries hash: %s", got)
	}
}

type oaRecordingFacadeService struct {
	taskFacade           TaskFacade
	receivedGitBranchIDs []string
}

func (r *oaRecordingFacadeService) GetTaskFacade(userID string) TaskFacade { return r.taskFacade }

func (r *oaRecordingFacadeService) GetSubtaskFacade(userID, gitBranchID string) SubtaskFacade {
	r.receivedGitBranchIDs = append(r.receivedGitBranchIDs, gitBranchID)
	return idValidatorExamplesMockSubtaskFacade{}
}

type oaStaticTaskFacade struct{ response *entities.OrderedMap[any] }

func (s oaStaticTaskFacade) GetTask(taskID string) *entities.OrderedMap[any] { return s.response }

func oaTaskResponse(taskID, gitBranchID string, success bool) *entities.OrderedMap[any] {
	response := entities.NewOrderedMap[any]()
	response.Set("success", success)
	data := entities.NewOrderedMap[any]()
	task := entities.NewOrderedMap[any]()
	task.Set("id", taskID)
	task.Set("git_branch_id", gitBranchID)
	data.Set("task", task)
	response.Set("data", data)
	return response
}

func TestGetFacadeForRequestFixedSuccess(t *testing.T) {
	const (
		taskID   = "550e8400-e29b-41d4-a716-446655440000"
		userID   = "550e8400-e29b-41d4-a716-446655440002"
		branchID = "550e8400-e29b-41d4-a716-446655440001"
	)
	service := &oaRecordingFacadeService{
		taskFacade: oaStaticTaskFacade{response: oaTaskResponse(taskID, branchID, true)},
	}
	controller := NewSubtaskControllerExample(service)

	facade, err := controller.getFacadeForRequestFixed(taskID, userID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if _, ok := facade.(idValidatorExamplesMockSubtaskFacade); !ok {
		t.Fatalf("unexpected facade type: %T", facade)
	}
	if len(service.receivedGitBranchIDs) != 1 || service.receivedGitBranchIDs[0] != branchID {
		t.Fatalf("subtask facade received %v, want [%s]", service.receivedGitBranchIDs, branchID)
	}
}

func TestGetFacadeForRequestWrongForwardsTaskID(t *testing.T) {
	const (
		taskID = "550e8400-e29b-41d4-a716-446655440000"
		userID = "550e8400-e29b-41d4-a716-446655440002"
	)
	service := &oaRecordingFacadeService{}
	controller := NewSubtaskControllerExample(service)

	controller.getFacadeForRequestWrong(taskID, userID)
	if len(service.receivedGitBranchIDs) != 1 || service.receivedGitBranchIDs[0] != taskID {
		t.Fatalf("WRONG path must forward task_id as git_branch_id, got %v", service.receivedGitBranchIDs)
	}
}

// The Python example's user_id is not a UUID, so prevent_id_confusion fails before any
// facade lookup. Preserve that bug (confirmed against the Python: returns False).
func TestGetFacadeForRequestFixedInvalidUserIDAndIntegrationExample(t *testing.T) {
	const taskID = "550e8400-e29b-41d4-a716-446655440000"
	const userID = "user-550e8400-e29b-41d4-a716-446655440002"
	want := "Invalid parameters: user_id: Invalid UUID format: " + userID +
		". Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

	controller := NewSubtaskControllerExample(idValidatorExamplesMockFacadeService{})
	_, err := controller.getFacadeForRequestFixed(taskID, userID)
	if err == nil || err.Error() != want {
		t.Fatalf("got  %v\nwant %s", err, want)
	}

	if TestIntegrationExample() {
		t.Fatalf("TestIntegrationExample must return false: the example's user_id is not a UUID")
	}
}

func TestHandleRequestWithValidationFailureDict(t *testing.T) {
	controller := NewMCPControllerBaseExample()
	kwargs := entities.NewOrderedMap[any]()
	kwargs.Set("task_id", "not-a-uuid")

	result := controller.HandleRequestWithValidation("do_thing", kwargs)

	if got, want := strings.Join(result.Keys(), ","), "success,error,message,suggestions"; got != want {
		t.Fatalf("key order: got %s want %s", got, want)
	}
	if success, _ := result.Get("success"); success != false {
		t.Fatalf("success: %v", success)
	}
	if errorCode, _ := result.Get("error"); errorCode != "PARAMETER_VALIDATION_FAILED" {
		t.Fatalf("error: %v", errorCode)
	}
	wantMessage := "task_id: Invalid UUID format: not-a-uuid. Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
	if message, _ := result.Get("message"); message != wantMessage {
		t.Fatalf("message: got %v want %s", message, wantMessage)
	}
	suggestions, ok := result.Get("suggestions")
	if !ok {
		t.Fatalf("missing suggestions")
	}
	suggestionMap, ok := suggestions.(map[string]string)
	if !ok {
		t.Fatalf("suggestions type: %T", suggestions)
	}
	if suggestionMap["confused_id"] != "not-a-uuid" {
		t.Fatalf("confused_id: %q", suggestionMap["confused_id"])
	}
	if suggestionMap["issue"] != "ID confusion detected in MCP controller do_thing action" {
		t.Fatalf("issue: %q", suggestionMap["issue"])
	}
}

func TestHandleRequestWithValidationSuccessDict(t *testing.T) {
	controller := NewMCPControllerBaseExample()
	kwargs := entities.NewOrderedMap[any]()
	kwargs.Set("task_id", "550e8400-e29b-41d4-a716-446655440000")
	kwargs.Set("user_id", "550e8400-e29b-41d4-a716-446655440002")

	result := controller.HandleRequestWithValidation("get_task", kwargs)

	if got, want := strings.Join(result.Keys(), ","), "success,message"; got != want {
		t.Fatalf("key order: got %s want %s", got, want)
	}
	if success, _ := result.Get("success"); success != true {
		t.Fatalf("success: %v", success)
	}
	if message, _ := result.Get("message"); message != "Request processed successfully" {
		t.Fatalf("message: %v", message)
	}
}

func TestFacadeServiceExampleGetSubtaskFacadeWithValidation(t *testing.T) {
	service := NewFacadeServiceExample()

	want := "Invalid facade parameters: user_id: Invalid UUID format: user-550e8400-e29b-41d4-a716-446655440002. " +
		"Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
	if err := service.GetSubtaskFacadeWithValidation("user-550e8400-e29b-41d4-a716-446655440002", nil, nil); err == nil || err.Error() != want {
		t.Fatalf("got  %v\nwant %s", err, want)
	}

	if err := service.GetSubtaskFacadeWithValidation("550e8400-e29b-41d4-a716-446655440002", nil, nil); err != nil {
		t.Fatalf("valid user_id should pass: %v", err)
	}
}
