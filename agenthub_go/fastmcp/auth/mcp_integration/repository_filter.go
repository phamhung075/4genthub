// Package mcp_integration ports fastmcp/auth/mcp_integration/repository_filter.py.
package mcp_integration

import (
	"context"
	"errors"
	"fmt"
	"log"
	"reflect"
	"strings"

	"agenthub/fastmcp/auth/middleware"
)

// UserFilteredRepository is the base for user-filtered repositories.
type UserFilteredRepository struct {
	BaseRepository any
	UserIDField    string
}

// NewUserFilteredRepository creates a new base user-filtered repository.
func NewUserFilteredRepository(baseRepo any, userIDField ...string) *UserFilteredRepository {
	field := "user_id"
	if len(userIDField) > 0 && userIDField[0] != "" {
		field = userIDField[0]
	}
	return &UserFilteredRepository{
		BaseRepository: baseRepo,
		UserIDField:    field,
	}
}

// GetCurrentUserID retrieves the current user ID from context.
func (r *UserFilteredRepository) GetCurrentUserID(ctx context.Context) (string, error) {
	uidPtr := middleware.GetCurrentUserID(ctx)
	if uidPtr != nil && *uidPtr != "" {
		return *uidPtr, nil
	}
	return "", errors.New("No authenticated user in context")
}

// AddUserFilter adds user_id filter to existing filters map.
func (r *UserFilteredRepository) AddUserFilter(ctx context.Context, filters map[string]any) (map[string]any, error) {
	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}
	res := make(map[string]any)
	for k, v := range filters {
		res[k] = v
	}
	res[r.UserIDField] = uid
	return res, nil
}

// UserFilteredTaskRepository wraps task repository with user filtering.
type UserFilteredTaskRepository struct {
	UserFilteredRepository
}

// NewUserFilteredTaskRepository creates a new UserFilteredTaskRepository.
func NewUserFilteredTaskRepository(baseRepo any, userIDField ...string) *UserFilteredTaskRepository {
	return &UserFilteredTaskRepository{
		UserFilteredRepository: *NewUserFilteredRepository(baseRepo, userIDField...),
	}
}

// FindByID finds task by ID, ensuring it belongs to current user.
func (r *UserFilteredTaskRepository) FindByID(ctx context.Context, taskID any) (any, error) {
	task, err := invokeRepoMethod(r.BaseRepository, "FindByID", ctx, taskID)
	if err != nil {
		log.Printf("[ERROR] Error finding task %v: %v", taskID, err)
		return nil, nil
	}
	if isNilOrZero(task) {
		return nil, nil
	}

	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	taskUID, _ := getEntityField(task, r.UserIDField)
	if fmt.Sprintf("%v", taskUID) == uid {
		return task, nil
	}
	log.Printf("[WARN] User %s attempted to access task %v belonging to %v", uid, taskID, taskUID)
	return nil, nil
}

// FindAll finds all tasks matching filters, filtered by current user.
func (r *UserFilteredTaskRepository) FindAll(ctx context.Context, filters map[string]any) ([]any, error) {
	filteredFilters, err := r.AddUserFilter(ctx, filters)
	if err != nil {
		return nil, err
	}
	res, err := invokeRepoMethod(r.BaseRepository, "FindAll", ctx, filteredFilters)
	if err != nil {
		log.Printf("[ERROR] Error finding tasks: %v", err)
		return []any{}, nil
	}
	return toAnySlice(res), nil
}

// FindByGitBranchID finds tasks by git branch ID, filtered by current user.
func (r *UserFilteredTaskRepository) FindByGitBranchID(ctx context.Context, branchID string) ([]any, error) {
	res, err := invokeRepoMethod(r.BaseRepository, "FindByGitBranchID", ctx, branchID)
	if err != nil {
		log.Printf("[ERROR] Error finding tasks for branch %s: %v", branchID, err)
		return []any{}, nil
	}
	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	var matched []any
	for _, task := range toAnySlice(res) {
		taskUID, _ := getEntityField(task, r.UserIDField)
		if fmt.Sprintf("%v", taskUID) == uid {
			matched = append(matched, task)
		}
	}
	return matched, nil
}

// Save saves a task, ensuring it belongs to current user.
func (r *UserFilteredTaskRepository) Save(ctx context.Context, task any) (any, error) {
	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	idVal, hasID := getEntityField(task, "id")
	if !hasID || isNilOrZero(idVal) {
		_ = setEntityField(task, r.UserIDField, uid)
	} else {
		taskUID, _ := getEntityField(task, r.UserIDField)
		if fmt.Sprintf("%v", taskUID) != uid {
			return nil, errors.New("Cannot save task belonging to another user")
		}
	}

	res, err := invokeRepoMethod(r.BaseRepository, "Save", ctx, task)
	if err != nil {
		log.Printf("[ERROR] Error saving task: %v", err)
		return nil, err
	}
	return res, nil
}

// Delete deletes a task, ensuring it belongs to current user.
func (r *UserFilteredTaskRepository) Delete(ctx context.Context, taskID any) (bool, error) {
	task, err := r.FindByID(ctx, taskID)
	if err != nil || isNilOrZero(task) {
		return false, err
	}
	res, err := invokeRepoMethod(r.BaseRepository, "Delete", ctx, taskID)
	if err != nil {
		log.Printf("[ERROR] Error deleting task %v: %v", taskID, err)
		return false, nil
	}
	if b, ok := res.(bool); ok {
		return b, nil
	}
	return true, nil
}

// UserFilteredProjectRepository wraps project repository with user filtering.
type UserFilteredProjectRepository struct {
	UserFilteredRepository
}

// NewUserFilteredProjectRepository creates a new UserFilteredProjectRepository.
func NewUserFilteredProjectRepository(baseRepo any, userIDField ...string) *UserFilteredProjectRepository {
	return &UserFilteredProjectRepository{
		UserFilteredRepository: *NewUserFilteredRepository(baseRepo, userIDField...),
	}
}

// FindByID finds project by ID, ensuring it belongs to current user.
func (r *UserFilteredProjectRepository) FindByID(ctx context.Context, projectID any) (any, error) {
	project, err := invokeRepoMethod(r.BaseRepository, "FindByID", ctx, projectID)
	if err != nil {
		log.Printf("[ERROR] Error finding project %v: %v", projectID, err)
		return nil, nil
	}
	if isNilOrZero(project) {
		return nil, nil
	}

	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	pUID, _ := getEntityField(project, r.UserIDField)
	if fmt.Sprintf("%v", pUID) == uid {
		return project, nil
	}
	log.Printf("[WARN] User %s attempted to access project %v belonging to %v", uid, projectID, pUID)
	return nil, nil
}

// FindAll finds all projects, filtered by current user.
func (r *UserFilteredProjectRepository) FindAll(ctx context.Context, filters map[string]any) ([]any, error) {
	filteredFilters, err := r.AddUserFilter(ctx, filters)
	if err != nil {
		return nil, err
	}
	res, err := invokeRepoMethod(r.BaseRepository, "FindAll", ctx, filteredFilters)
	if err != nil {
		log.Printf("[ERROR] Error finding projects: %v", err)
		return []any{}, nil
	}
	return toAnySlice(res), nil
}

// Save saves a project, ensuring it belongs to current user.
func (r *UserFilteredProjectRepository) Save(ctx context.Context, project any) (any, error) {
	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	idVal, hasID := getEntityField(project, "id")
	if !hasID || isNilOrZero(idVal) {
		_ = setEntityField(project, r.UserIDField, uid)
	} else {
		pUID, _ := getEntityField(project, r.UserIDField)
		if fmt.Sprintf("%v", pUID) != uid {
			return nil, errors.New("Cannot save project belonging to another user")
		}
	}

	res, err := invokeRepoMethod(r.BaseRepository, "Save", ctx, project)
	if err != nil {
		log.Printf("[ERROR] Error saving project: %v", err)
		return nil, err
	}
	return res, nil
}

// Delete deletes a project, ensuring it belongs to current user.
func (r *UserFilteredProjectRepository) Delete(ctx context.Context, projectID any) (bool, error) {
	project, err := r.FindByID(ctx, projectID)
	if err != nil || isNilOrZero(project) {
		return false, err
	}
	res, err := invokeRepoMethod(r.BaseRepository, "Delete", ctx, projectID)
	if err != nil {
		log.Printf("[ERROR] Error deleting project %v: %v", projectID, err)
		return false, nil
	}
	if b, ok := res.(bool); ok {
		return b, nil
	}
	return true, nil
}

// UserFilteredContextRepository wraps context repository with user filtering.
type UserFilteredContextRepository struct {
	UserFilteredRepository
}

// NewUserFilteredContextRepository creates a new UserFilteredContextRepository.
func NewUserFilteredContextRepository(baseRepo any, userIDField ...string) *UserFilteredContextRepository {
	return &UserFilteredContextRepository{
		UserFilteredRepository: *NewUserFilteredRepository(baseRepo, userIDField...),
	}
}

// FindByID finds context by ID, ensuring it belongs to current user.
func (r *UserFilteredContextRepository) FindByID(ctx context.Context, contextID any) (any, error) {
	c, err := invokeRepoMethod(r.BaseRepository, "FindByID", ctx, contextID)
	if err != nil {
		log.Printf("[ERROR] Error finding context %v: %v", contextID, err)
		return nil, nil
	}
	if isNilOrZero(c) {
		return nil, nil
	}

	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	cUID, _ := getEntityField(c, r.UserIDField)
	if fmt.Sprintf("%v", cUID) == uid {
		return c, nil
	}
	log.Printf("[WARN] User %s attempted to access context %v belonging to %v", uid, contextID, cUID)
	return nil, nil
}

// FindAll finds all contexts, filtered by current user.
func (r *UserFilteredContextRepository) FindAll(ctx context.Context, filters map[string]any) ([]any, error) {
	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	userFilters := make(map[string]any)
	for k, v := range filters {
		userFilters[k] = v
	}
	userFilters[r.UserIDField] = uid

	globalFilters := make(map[string]any)
	for k, v := range filters {
		globalFilters[k] = v
	}
	globalFilters[r.UserIDField] = nil

	userContexts, err := invokeRepoMethod(r.BaseRepository, "FindAll", ctx, userFilters)
	if err != nil {
		log.Printf("[ERROR] Error finding user contexts: %v", err)
	}

	globalContexts, err := invokeRepoMethod(r.BaseRepository, "FindAll", ctx, globalFilters)
	if err != nil {
		log.Printf("[ERROR] Error finding global contexts: %v", err)
	}

	all := append(toAnySlice(userContexts), toAnySlice(globalContexts)...)
	return all, nil
}

// Save saves context, ensuring it belongs to current user.
func (r *UserFilteredContextRepository) Save(ctx context.Context, c any) (any, error) {
	uid, err := r.GetCurrentUserID(ctx)
	if err != nil {
		return nil, err
	}

	level, _ := getEntityField(c, "level")
	if fmt.Sprintf("%v", level) == "global" {
		_ = setEntityField(c, r.UserIDField, uid)
		log.Printf("[DEBUG] Setting user_id %s for global context", uid)
	} else {
		idVal, hasID := getEntityField(c, "id")
		if !hasID || isNilOrZero(idVal) {
			_ = setEntityField(c, r.UserIDField, uid)
		} else {
			cUID, _ := getEntityField(c, r.UserIDField)
			if !isNilOrZero(cUID) && fmt.Sprintf("%v", cUID) != uid {
				return nil, errors.New("Cannot save context belonging to another user")
			}
		}
	}

	res, err := invokeRepoMethod(r.BaseRepository, "Save", ctx, c)
	if err != nil {
		log.Printf("[ERROR] Error saving context: %v", err)
		return nil, err
	}
	return res, nil
}

// Delete deletes context, ensuring it belongs to current user.
func (r *UserFilteredContextRepository) Delete(ctx context.Context, contextID any) (bool, error) {
	c, err := r.FindByID(ctx, contextID)
	if err != nil || isNilOrZero(c) {
		return false, err
	}

	level, _ := getEntityField(c, "level")
	if fmt.Sprintf("%v", level) == "global" {
		uid, _ := r.GetCurrentUserID(ctx)
		log.Printf("[WARN] User %s attempted to delete global context", uid)
		return false, nil
	}

	res, err := invokeRepoMethod(r.BaseRepository, "Delete", ctx, contextID)
	if err != nil {
		log.Printf("[ERROR] Error deleting context %v: %v", contextID, err)
		return false, nil
	}
	if b, ok := res.(bool); ok {
		return b, nil
	}
	return true, nil
}

// CreateUserFilteredRepository creates a user-filtered repository based on repositoryType.
func CreateUserFilteredRepository(repositoryType string, baseRepo any, userIDField ...string) (any, error) {
	switch strings.ToLower(repositoryType) {
	case "task":
		return NewUserFilteredTaskRepository(baseRepo, userIDField...), nil
	case "project":
		return NewUserFilteredProjectRepository(baseRepo, userIDField...), nil
	case "context":
		return NewUserFilteredContextRepository(baseRepo, userIDField...), nil
	default:
		return nil, fmt.Errorf("Unknown repository type: %s", repositoryType)
	}
}

// --- Reflection Helpers ---

func isNilOrZero(v any) bool {
	if v == nil {
		return true
	}
	val := reflect.ValueOf(v)
	switch val.Kind() {
	case reflect.Chan, reflect.Func, reflect.Interface, reflect.Map, reflect.Pointer, reflect.Slice:
		return val.IsNil()
	default:
		return false
	}
}

func toAnySlice(v any) []any {
	if v == nil {
		return nil
	}
	if s, ok := v.([]any); ok {
		return s
	}
	val := reflect.ValueOf(v)
	if val.Kind() == reflect.Slice {
		n := val.Len()
		res := make([]any, n)
		for i := 0; i < n; i++ {
			res[i] = val.Index(i).Interface()
		}
		return res
	}
	return []any{v}
}

func invokeRepoMethod(repo any, methodName string, args ...any) (any, error) {
	if repo == nil {
		return nil, fmt.Errorf("base repository is nil")
	}
	val := reflect.ValueOf(repo)
	method := val.MethodByName(methodName)
	if !method.IsValid() {
		// Try lowercase method name
		method = val.MethodByName(strings.ToLower(methodName[:1]) + methodName[1:])
	}
	if !method.IsValid() {
		return nil, fmt.Errorf("method %s not found on %T", methodName, repo)
	}

	mType := method.Type()
	numArgs := mType.NumIn()

	callArgs := make([]reflect.Value, 0, len(args))
	argIdx := 0
	for i := 0; i < numArgs; i++ {
		targetType := mType.In(i)
		if argIdx < len(args) {
			arg := args[argIdx]
			argIdx++
			if arg == nil {
				callArgs = append(callArgs, reflect.Zero(targetType))
			} else {
				aValue := reflect.ValueOf(arg)
				if aValue.Type().AssignableTo(targetType) {
					callArgs = append(callArgs, aValue)
				} else if aValue.Type().ConvertibleTo(targetType) {
					callArgs = append(callArgs, aValue.Convert(targetType))
				} else {
					callArgs = append(callArgs, aValue)
				}
			}
		}
	}

	out := method.Call(callArgs)
	if len(out) == 0 {
		return nil, nil
	}
	if len(out) == 1 {
		return out[0].Interface(), nil
	}
	// If last return value is error
	last := out[len(out)-1].Interface()
	if last != nil {
		if err, ok := last.(error); ok {
			return nil, err
		}
	}
	return out[0].Interface(), nil
}

func getEntityField(entity any, fieldName string) (any, bool) {
	if entity == nil {
		return nil, false
	}
	if m, ok := entity.(map[string]any); ok {
		val, exists := m[fieldName]
		return val, exists
	}

	val := reflect.ValueOf(entity)
	if val.Kind() == reflect.Pointer {
		val = val.Elem()
	}
	if val.Kind() != reflect.Struct {
		return nil, false
	}

	field := val.FieldByName(fieldName)
	if !field.IsValid() {
		// Try CamelCase
		field = val.FieldByName(strings.Title(fieldName))
	}
	if !field.IsValid() {
		// Case-insensitive sweep
		typ := val.Type()
		for i := 0; i < typ.NumField(); i++ {
			if strings.EqualFold(typ.Field(i).Name, fieldName) {
				field = val.Field(i)
				break
			}
		}
	}
	if field.IsValid() {
		return field.Interface(), true
	}
	return nil, false
}

func setEntityField(entity any, fieldName string, newVal any) error {
	if entity == nil {
		return fmt.Errorf("entity is nil")
	}
	if m, ok := entity.(map[string]any); ok {
		m[fieldName] = newVal
		return nil
	}

	val := reflect.ValueOf(entity)
	if val.Kind() == reflect.Pointer {
		val = val.Elem()
	}
	if val.Kind() != reflect.Struct {
		return fmt.Errorf("entity is not a struct or pointer to struct")
	}

	field := val.FieldByName(fieldName)
	if !field.IsValid() {
		field = val.FieldByName(strings.Title(fieldName))
	}
	if !field.IsValid() {
		typ := val.Type()
		for i := 0; i < typ.NumField(); i++ {
			if strings.EqualFold(typ.Field(i).Name, fieldName) {
				field = val.Field(i)
				break
			}
		}
	}
	if field.IsValid() && field.CanSet() {
		v := reflect.ValueOf(newVal)
		if v.Type().AssignableTo(field.Type()) {
			field.Set(v)
		} else if v.Type().ConvertibleTo(field.Type()) {
			field.Set(v.Convert(field.Type()))
		}
		return nil
	}
	return fmt.Errorf("field %s not found or cannot be set", fieldName)
}
