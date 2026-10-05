package services

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PaginationService is the stateless pagination domain service.
// FEATURE_CLEAN_REPOSITORIES (unused class flag in Python) is not ported.

// floorDiv is Python's // for ints (floors toward -inf).
func floorDiv(a, b int) int {
	q := a / b
	if (a%b != 0) && ((a < 0) != (b < 0)) {
		q--
	}
	return q
}

// CreatePaginationResult builds a result with metadata. A zero page size returns
// entities.ErrZeroDivision (Python ZeroDivisionError).
func CreatePaginationResult[T any](items []T, totalCount int, p value_objects.PaginationRequest) (value_objects.PaginationResult[T], error) {
	if p.PageSize == 0 {
		return value_objects.PaginationResult[T]{}, entities.ErrZeroDivision
	}
	totalPages := floorDiv(totalCount+p.PageSize-1, p.PageSize)
	return value_objects.PaginationResult[T]{
		Items: items, TotalCount: totalCount, Page: p.Page, PageSize: p.PageSize,
		TotalPages: totalPages, HasNext: p.Page < totalPages, HasPrevious: p.Page > 1,
	}, nil
}

// MaxPageSize is the upper limit enforced by ValidatePaginationRequest.
const MaxPageSize = 100

// ValidatePaginationRequest rejects page < 1 and page sizes outside 1..100.
func ValidatePaginationRequest(p value_objects.PaginationRequest) error {
	if p.Page < 1 {
		return value_objects.ValueErrorf("Page must be >= 1, got %d", p.Page)
	}
	if p.PageSize <= 0 {
		return value_objects.ValueErrorf("Page size must be > 0, got %d", p.PageSize)
	}
	if p.PageSize > MaxPageSize {
		return value_objects.ValueErrorf("Page size must be <= %d, got %d", MaxPageSize, p.PageSize)
	}
	return nil
}

// CalculateOffset is (page - 1) * page_size.
func CalculateOffset(p value_objects.PaginationRequest) int { return (p.Page - 1) * p.PageSize }
