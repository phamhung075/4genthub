package value_objects

// PaginationRequest holds pagination parameters. Page numbering starts at 1.
type PaginationRequest struct {
	Page     int
	PageSize int
	Offset   int
}

// NewPaginationRequest computes the offset from page and pageSize when offset is nil.
func NewPaginationRequest(page, pageSize int, offset *int) PaginationRequest {
	r := PaginationRequest{Page: page, PageSize: pageSize}
	if offset != nil {
		r.Offset = *offset
	} else {
		r.Offset = (page - 1) * pageSize
	}
	return r
}

// DefaultPaginationRequest is page 1 with 20 items per page.
func DefaultPaginationRequest() PaginationRequest { return NewPaginationRequest(1, 20, nil) }

// PaginationResult wraps a page of items with pagination metadata.
type PaginationResult[T any] struct {
	Items       []T
	TotalCount  int
	Page        int
	PageSize    int
	TotalPages  int
	HasNext     bool
	HasPrevious bool
}
