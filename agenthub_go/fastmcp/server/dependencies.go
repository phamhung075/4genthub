// Package server ports fastmcp/server/dependencies.py.
package server

import (
	"context"
	"net/http"
	"strings"
)

type httpReqContextKey struct{}

// WithHTTPRequest attaches an *http.Request to the context.
func WithHTTPRequest(ctx context.Context, r *http.Request) context.Context {
	return context.WithValue(ctx, httpReqContextKey{}, r)
}

// GetHTTPRequest extracts the *http.Request from context if available.
func GetHTTPRequest(ctx context.Context) *http.Request {
	if ctx == nil {
		return nil
	}
	r, _ := ctx.Value(httpReqContextKey{}).(*http.Request)
	return r
}

var excludedHeaders = map[string]bool{
	"host":                true,
	"content-length":      true,
	"connection":          true,
	"transfer-encoding":   true,
	"upgrade":             true,
	"te":                  true,
	"keep-alive":          true,
	"expect":              true,
	"accept":              true,
	"proxy-authenticate":  true,
	"proxy-authorization": true,
	"proxy-connection":    true,
}

// GetHTTPHeaders extracts headers from the request context or given request.
func GetHTTPHeaders(r *http.Request, includeAll bool) map[string]string {
	headers := make(map[string]string)
	if r == nil {
		return headers
	}
	for name, values := range r.Header {
		lower := strings.ToLower(name)
		if !includeAll && excludedHeaders[lower] {
			continue
		}
		if len(values) > 0 {
			headers[lower] = values[0]
		}
	}
	return headers
}
