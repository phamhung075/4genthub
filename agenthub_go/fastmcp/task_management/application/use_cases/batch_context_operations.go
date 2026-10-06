package use_cases

import (
	"agenthub/fastmcp/utilities"
	"context"
	"fmt"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/cache"
)

// BatchOperationType: types of batch operations.
type BatchOperationType string

const (
	BatchOperationTypeCreate BatchOperationType = "create"
	BatchOperationTypeUpdate BatchOperationType = "update"
	BatchOperationTypeDelete BatchOperationType = "delete"
	BatchOperationTypeUpsert BatchOperationType = "upsert"
)

func (e BatchOperationType) String() string { return string(e) }

// BatchOperation is a single operation in a batch.
type BatchOperation struct {
	Operation   BatchOperationType
	Level       value_objects.ContextLevel
	ContextID   string
	Data        map[string]any
	UserID      *string
	ProjectID   *string
	GitBranchID *string

	PropagateChanges bool
	IncludeInherited bool
	ForceRefresh     bool
}

// NewBatchOperation applies the Python defaults (propagate_changes=True).
func NewBatchOperation(operation BatchOperationType, level value_objects.ContextLevel, contextID string) *BatchOperation {
	return &BatchOperation{Operation: operation, Level: level, ContextID: contextID, PropagateChanges: true}
}

// BatchOperationResult is the result of a single batch operation.
type BatchOperationResult struct {
	Success         bool
	Operation       *BatchOperation
	Result          map[string]any
	Error           *string
	ExecutionTimeMs *float64
}

// BatchContextService is the UnifiedContextService surface used by the batch
// operations. The Python module calls it with context_level=... and awaits a
// synchronous method, so the real Python call raises TypeError; the port keeps the
// call shape.
type BatchContextService interface {
	CreateContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, data map[string]any, userID, projectID, gitBranchID *string) (map[string]any, error)
	UpdateContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, data map[string]any, userID *string, propagateChanges bool) (map[string]any, error)
	DeleteContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, userID *string) (map[string]any, error)
	GetContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, userID *string, includeInherited bool) (map[string]any, error)
}

// BatchContextOperations ports batch_context_operations.BatchContextOperations.
type BatchContextOperations struct {
	contextService BatchContextService
	cache          *cache.ContextCache
}

// NewBatchContextOperations builds the batch executor.
func NewBatchContextOperations(contextService BatchContextService) *BatchContextOperations {
	return &BatchContextOperations{contextService: contextService, cache: cache.GetContextCache()}
}

// ExecuteBatch ports execute_batch.
func (b *BatchContextOperations) ExecuteBatch(ctx context.Context, operations []*BatchOperation, transaction, parallel, stopOnError bool, userID *string) []*BatchOperationResult {
	if userID != nil {
		for _, op := range operations {
			if op.UserID == nil {
				op.UserID = userID
			}
		}
	}

	var results []*BatchOperationResult
	switch {
	case transaction && !parallel:
		results = b.executeTransactional(ctx, operations, stopOnError)
	case parallel && !transaction:
		results = b.executeParallel(ctx, operations, stopOnError)
	default:
		results = b.executeSequential(ctx, operations, stopOnError)
	}

	b.invalidateCaches(operations, userID)
	return results
}

func (b *BatchContextOperations) executeTransactional(ctx context.Context, operations []*BatchOperation, stopOnError bool) []*BatchOperationResult {
	results := []*BatchOperationResult{}
	rolledBack := false
	for _, op := range operations {
		start := time.Now()
		result, err := b.executeSingleOperation(ctx, op)
		if err == nil {
			results = append(results, batchSuccess(op, result, start))
			continue
		}
		results = append(results, batchFailure(op, err.Error(), start))
		if stopOnError {
			rolledBack = true
			break
		}
	}
	if rolledBack {
		for i := len(results); i < len(operations); i++ {
			results = append(results, &BatchOperationResult{Success: false, Operation: operations[i], Error: strPtr("Transaction rolled back")})
		}
	}
	return results
}

func (b *BatchContextOperations) executeSequential(ctx context.Context, operations []*BatchOperation, stopOnError bool) []*BatchOperationResult {
	results := []*BatchOperationResult{}
	for _, op := range operations {
		start := time.Now()
		result, err := b.executeSingleOperation(ctx, op)
		if err == nil {
			results = append(results, batchSuccess(op, result, start))
			continue
		}
		results = append(results, batchFailure(op, err.Error(), start))
		if stopOnError {
			for i := len(results); i < len(operations); i++ {
				results = append(results, &BatchOperationResult{Success: false, Operation: operations[i], Error: strPtr("Skipped due to previous error")})
			}
			break
		}
	}
	return results
}

func (b *BatchContextOperations) executeParallel(ctx context.Context, operations []*BatchOperation, stopOnError bool) []*BatchOperationResult {
	results := make([]*BatchOperationResult, len(operations))
	var wg sync.WaitGroup
	for i, op := range operations {
		wg.Add(1)
		go func(i int, op *BatchOperation) {
			defer wg.Done()
			start := time.Now()
			var result map[string]any
			var err error
			// asyncio.gather(return_exceptions) turns a raised exception into a failed result
			if rec := utilities.SafeCall(func() { result, err = b.executeSingleOperation(ctx, op) }); rec != nil {
				err = fmt.Errorf("%v", rec)
			}
			if err == nil {
				results[i] = batchSuccess(op, result, start)
				return
			}
			results[i] = batchFailure(op, err.Error(), start)
		}(i, op)
	}
	wg.Wait()
	// stop_on_error does not cancel the gathered tasks in Python; it only logs.
	return results
}

func (b *BatchContextOperations) executeSingleOperation(ctx context.Context, op *BatchOperation) (map[string]any, error) {
	switch op.Operation {
	case BatchOperationTypeCreate:
		return b.contextService.CreateContext(ctx, op.Level, op.ContextID, orEmptyData(op.Data), op.UserID, op.ProjectID, op.GitBranchID)
	case BatchOperationTypeUpdate:
		return b.contextService.UpdateContext(ctx, op.Level, op.ContextID, orEmptyData(op.Data), op.UserID, op.PropagateChanges)
	case BatchOperationTypeDelete:
		return b.contextService.DeleteContext(ctx, op.Level, op.ContextID, op.UserID)
	case BatchOperationTypeUpsert:
		existing, err := b.contextService.GetContext(ctx, op.Level, op.ContextID, op.UserID, false)
		if err != nil {
			return nil, err
		}
		if existing != nil {
			return b.contextService.UpdateContext(ctx, op.Level, op.ContextID, orEmptyData(op.Data), op.UserID, op.PropagateChanges)
		}
		return b.contextService.CreateContext(ctx, op.Level, op.ContextID, orEmptyData(op.Data), op.UserID, op.ProjectID, op.GitBranchID)
	default:
		return nil, &value_objects.ValueError{Msg: "Unknown operation type: " + op.Operation.String()}
	}
}

func (b *BatchContextOperations) invalidateCaches(operations []*BatchOperation, userID *string) {
	for _, op := range operations {
		if op.Operation == BatchOperationTypeDelete {
			continue
		}
		effective := userID
		if op.UserID != nil {
			effective = op.UserID
		}
		uid := ""
		if effective != nil {
			uid = *effective
		}
		contextID := op.ContextID
		level := op.Level.String()
		b.cache.InvalidateContext(uid, &level, &contextID)
		b.cache.InvalidateInheritance(uid, &level, &contextID)
	}
}

// BulkCreate ports bulk_create.
func (b *BatchContextOperations) BulkCreate(ctx context.Context, contexts []*entities.OrderedMap[any], level value_objects.ContextLevel, userID string, transaction bool) []*BatchOperationResult {
	operations := make([]*BatchOperation, 0, len(contexts))
	for _, ctxData := range contexts {
		contextID, _ := orderedStringValue(ctxData, "context_id")
		op := NewBatchOperation(BatchOperationTypeCreate, level, contextID)
		op.Data = orderedMapToData(ctxData, "data")
		op.UserID = strPtr(userID)
		op.ProjectID = orderedOptionalString(ctxData, "project_id")
		op.GitBranchID = orderedOptionalString(ctxData, "git_branch_id")
		operations = append(operations, op)
	}
	return b.ExecuteBatch(ctx, operations, transaction, false, true, strPtr(userID))
}

// BulkUpdate ports bulk_update.
func (b *BatchContextOperations) BulkUpdate(ctx context.Context, updates []*entities.OrderedMap[any], level value_objects.ContextLevel, userID string, transaction, parallel bool) []*BatchOperationResult {
	operations := make([]*BatchOperation, 0, len(updates))
	for _, update := range updates {
		contextID, _ := orderedStringValue(update, "context_id")
		op := NewBatchOperation(BatchOperationTypeUpdate, level, contextID)
		op.Data = orderedMapToData(update, "data")
		op.UserID = strPtr(userID)
		if v, ok := update.Get("propagate_changes"); ok {
			if b, ok := v.(bool); ok {
				op.PropagateChanges = b
			}
		}
		operations = append(operations, op)
	}
	return b.ExecuteBatch(ctx, operations, transaction, parallel, true, strPtr(userID))
}

// CopyContexts ports copy_contexts.
func (b *BatchContextOperations) CopyContexts(ctx context.Context, sourceBranchID, targetBranchID, userID string, includeTaskContexts bool) ([]*BatchOperationResult, error) {
	sourceContexts, err := b.contextService.GetContext(ctx, value_objects.ContextLevelBranch, sourceBranchID, strPtr(userID), false)
	if err != nil {
		return nil, err
	}

	operations := []*BatchOperation{}
	if sourceContexts != nil {
		op := NewBatchOperation(BatchOperationTypeUpsert, value_objects.ContextLevelBranch, targetBranchID)
		op.Data = mapDataValue(sourceContexts["data"])
		op.UserID = strPtr(userID)
		operations = append(operations, op)
	}
	// include_task_contexts is a no-op (task contexts need a repository query).

	return b.ExecuteBatch(ctx, operations, true, false, true, strPtr(userID)), nil
}

// --- helpers ---

func batchSuccess(op *BatchOperation, result map[string]any, start time.Time) *BatchOperationResult {
	return &BatchOperationResult{Success: true, Operation: op, Result: result, ExecutionTimeMs: elapsedMS(start)}
}

func batchFailure(op *BatchOperation, message string, start time.Time) *BatchOperationResult {
	return &BatchOperationResult{Success: false, Operation: op, Error: strPtr(message), ExecutionTimeMs: elapsedMS(start)}
}

func elapsedMS(start time.Time) *float64 {
	ms := value_objects.PyTotalSeconds(time.Since(start)) * 1000
	return &ms
}

func strPtr(s string) *string { return &s }

func orEmptyData(data map[string]any) map[string]any {
	if data == nil {
		return map[string]any{}
	}
	return data
}

func orderedStringValue(m *entities.OrderedMap[any], key string) (string, bool) {
	v, ok := m.Get(key)
	if !ok || v == nil {
		return "", false
	}
	s, ok := v.(string)
	return s, ok
}

func orderedOptionalString(m *entities.OrderedMap[any], key string) *string {
	if s, ok := orderedStringValue(m, key); ok {
		return &s
	}
	return nil
}

func orderedMapToData(m *entities.OrderedMap[any], key string) map[string]any {
	v, ok := m.Get(key)
	if !ok {
		return map[string]any{}
	}
	return mapDataValue(v)
}

func mapDataValue(v any) map[string]any {
	switch d := v.(type) {
	case map[string]any:
		return d
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		for _, k := range d.Keys() {
			out[k], _ = d.Get(k)
		}
		return out
	}
	return map[string]any{}
}
