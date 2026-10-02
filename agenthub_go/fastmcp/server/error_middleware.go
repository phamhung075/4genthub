// Package server ports fastmcp/server/error_middleware.py.
package server

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"time"

	"agenthub/fastmcp/auth"
	baseexc "agenthub/fastmcp/task_management/domain/exceptions"
)

// ErrorHandlingMiddleware is net/http middleware that catches panics and formats error responses.
func ErrorHandlingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		reqID := r.Header.Get("X-Request-ID")
		if reqID == "" {
			reqID = fmt.Sprintf("%d", start.UnixNano())
		}

		defer func() {
			if rec := recover(); rec != nil {
				duration := time.Since(start)
				log.Printf("[ERROR] panic recovered on %s %s (took %v): %v", r.Method, r.URL.Path, duration, rec)

				var httpErr *auth.HTTPException
				if err, ok := rec.(error); ok && errors.As(err, &httpErr) {
					writeErrorJSON(w, httpErr.StatusCode, httpErr.Detail, reqID)
					return
				}

				var notFound *baseexc.ResourceNotFoundException
				if err, ok := rec.(error); ok && errors.As(err, &notFound) {
					writeErrorJSON(w, http.StatusNotFound, notFound.Error(), reqID)
					return
				}

				var valErr *baseexc.ValidationException
				if err, ok := rec.(error); ok && errors.As(err, &valErr) {
					writeErrorJSON(w, http.StatusUnprocessableEntity, valErr.Error(), reqID)
					return
				}

				writeErrorJSON(w, http.StatusInternalServerError, fmt.Sprintf("%v", rec), reqID)
			}
		}()

		next.ServeHTTP(w, r)
	})
}

func writeErrorJSON(w http.ResponseWriter, statusCode int, detail, reqID string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	body := map[string]any{
		"detail":     detail,
		"request_id": reqID,
		"success":    false,
	}
	_ = json.NewEncoder(w).Encode(body)
}
